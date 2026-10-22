"""Synthetic integrity tests; no model quality measured."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'prototypes/model-finetuning/evaluation_contract.py'
spec = importlib.util.spec_from_file_location('evaluation_contract', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def row(split, number, hide):
    instruction = 'Hide ads' if hide else 'Keep only ads'
    return {'id': f'{split}-{number}', 'post_id': f'{split}-post-{number}',
            'state': f'{split} unique scenario {number}', 'policy_id': 'hide:ad' if hide else 'only:ad',
            'family': 'opposition', 'suite': 'test', 'pair_id': None, 'style': 'paragraph',
            'origin': 'synthetic-test-only', 'instruction': instruction,
            'expected': {'hide': hide}, 'questions': {'hide': {'type': 'noul', 'criteria': {'false': 'Keep the post visible.', 'true': 'Hide the post.'}, 'instructions': 'Filtering rules:\n' + instruction + '\n\nShould this post be hidden?'}}}


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.data = {split: [row(split, 0, False), row(split, 1, True)] for split in m.SPLITS}
        self.write()

    def write(self):
        self.manifest = {'hashes': {}, 'counts': {}}
        for split, rows in self.data.items():
            raw = ''.join(json.dumps(r) + '\n' for r in rows).encode()
            (self.path / (split + '.jsonl')).write_bytes(raw)
            self.manifest['hashes'][split] = hashlib.sha256(raw).hexdigest()
            self.manifest['counts'][split] = {'rows': len(rows), 'posts': len({r['post_id'] for r in rows}), 'hide': sum(r['expected']['hide'] for r in rows)}
        (self.path / 'manifest.json').write_text(json.dumps(self.manifest))

    def predictions(self, split='test'):
        return m.prediction_rows(self.data[split], [(None, [0., 1.] if r['expected']['hide'] else [1., 0.], None, None) for r in self.data[split]])

    def results(self):
        return {'plan': {'dataset_hashes': self.manifest['hashes']}, 'test_unlocked_after_training': True,
                'stages': {name: {'rows': self.predictions()} for name in ('base', 'previous', 'new')},
                'validation': {'rows': self.predictions('validation')}, 'base_validation': {'rows': self.predictions('validation')}}

    def test_valid_dataset_and_results(self):
        self.assertEqual(m.audit(self.path)['status'], 'PASS')
        self.assertTrue(m.validate_results(self.manifest, self.data, self.results()))

    def test_hash_and_counts_are_checked(self):
        (self.path / 'test.jsonl').write_text('')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'): m.read_dataset(self.path)
        self.write()
        self.manifest['counts']['test']['rows'] += 1
        (self.path / 'manifest.json').write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, 'counts'): m.read_dataset(self.path)

    def test_exact_text_leakage_under_new_id(self):
        self.data['test'][0]['state'] = self.data['train'][0]['state'].upper() + '!!!'
        self.write()
        with self.assertRaisesRegex(ValueError, 'text leakage'): m.read_dataset(self.path)

    def test_id_leakage_with_changed_text(self):
        self.data['test'][0]['post_id'] = self.data['train'][0]['post_id']
        self.write()
        with self.assertRaisesRegex(ValueError, 'ID leakage'): m.read_dataset(self.path)

    def test_required_novel_family_cannot_be_empty(self):
        with self.assertRaisesRegex(ValueError, 'empty'): m.read_dataset(self.path, ['novel_combination'])
        self.data['test'][0]['family'] = 'novel_combination'; self.write()
        with self.assertRaisesRegex(ValueError, 'both classes'): m.read_dataset(self.path, ['novel_combination'])

    def test_labels_boolean_and_input_matches_instruction(self):
        self.data['test'][0]['expected']['hide'] = 0; self.write()
        with self.assertRaisesRegex(ValueError, 'boolean'): m.read_dataset(self.path)
        self.data['test'][0]['expected']['hide'] = False
        self.data['test'][0]['instruction'] = 'Different task'; self.write()
        with self.assertRaisesRegex(ValueError, 'model input'): m.read_dataset(self.path)

    def test_duplicate_source_id_and_empty_split(self):
        self.data['test'][1]['id'] = self.data['test'][0]['id']; self.write()
        with self.assertRaisesRegex(ValueError, 'duplicate'): m.read_dataset(self.path)
        self.data['test'] = []; self.write()
        with self.assertRaisesRegex(ValueError, 'empty'): m.read_dataset(self.path)

    def test_rejects_gold_override_and_extra_questions(self):
        # Laya prioritizes gold over expected, so validating expected alone is unsafe.
        self.data['test'][0]['gold'] = {'hide': True}
        self.write()
        with self.assertRaisesRegex(ValueError, 'gold overrides'): m.read_dataset(self.path)
        del self.data['test'][0]['gold']
        self.data['test'][0]['questions']['other'] = self.data['test'][0]['questions']['hide']
        self.write()
        with self.assertRaisesRegex(ValueError, 'questions must contain only hide'): m.read_dataset(self.path)

    def test_converter_never_silently_truncates(self):
        for count in (0, 1, 3):
            with self.assertRaisesRegex(ValueError, 'count'):
                m.prediction_rows(self.data['test'], [(None, [0., 1.], None, None)] * count)

    def test_converter_rejects_nonbinary_and_nonfinite_logits(self):
        for logits in ([0.], [0., 1., 2.], [float('nan'), 1.], [0., float('inf')]):
            with self.assertRaises(ValueError): m.prediction_rows(self.data['test'], [(None, logits, None, None)] * 2)

    def test_prediction_population_and_identity(self):
        good = self.predictions()
        for bad in (good[:1], [good[0], good[0]], [dict(good[0], id='invented'), good[1]], [dict(good[0], post_id='other'), good[1]], [dict(good[0], expected_hide=True), good[1]]):
            with self.assertRaises(ValueError): m.validate_predictions(self.data['test'], bad)
        self.assertTrue(m.validate_predictions(self.data['test'], good[::-1]))

    def test_probability_contract(self):
        for patch in ({'p_hide': float('nan')}, {'p_hide': True}, {'p_hide': -.1}, {'p_hide': .1, 'p_keep': .1}, {'p_hide': .5, 'p_keep': .5}, {'logits': [float('inf'), 0.]}):
            bad = self.predictions(); bad[0].update(patch)
            with self.assertRaises(ValueError): m.validate_predictions(self.data['test'], bad)

    def test_results_require_all_models_and_frozen_data(self):
        for change in ('stage', 'hash', 'validation', 'unlock'):
            results = self.results()
            if change == 'stage': del results['stages']['base']
            elif change == 'hash': results['plan']['dataset_hashes'] = {}
            elif change == 'validation': results['validation']['rows'].pop()
            else: results['test_unlocked_after_training'] = False
            with self.assertRaises(ValueError): m.validate_results(self.manifest, self.data, results)

    def test_checkpoint_identity_detects_changes(self):
        checkpoint = self.path / 'checkpoint'; checkpoint.mkdir()
        with self.assertRaises(ValueError): m.checkpoint_identity(checkpoint)
        (checkpoint / 'config.json').write_text('{}')
        first = m.checkpoint_identity(checkpoint)
        (checkpoint / 'config.json').write_text('{"changed":true}')
        self.assertNotEqual(first['sha256'], m.checkpoint_identity(checkpoint)['sha256'])
        (checkpoint / 'link').symlink_to(checkpoint / 'config.json')
        with self.assertRaisesRegex(ValueError, 'symlink'): m.checkpoint_identity(checkpoint)

    def test_cli_gives_blocked_not_success_for_missing_data(self):
        run = subprocess.run([sys.executable, str(SCRIPT), str(self.path / 'absent')], text=True, capture_output=True)
        self.assertEqual(run.returncode, 1)
        self.assertEqual(json.loads(run.stdout)['status'], 'BLOCKED')

    def test_option_polarity_cannot_silently_reverse(self):
        self.data['test'][0]['questions']['hide']['criteria'] = {'true': 'Keep the post visible.', 'false': 'Hide the post.'}
        self.write()
        with self.assertRaisesRegex(ValueError, 'option mapping'): m.read_dataset(self.path)

    def test_opposite_pairs_require_same_post_and_opposite_labels(self):
        for r in self.data['test']: r['pair_id'] = 'pair'
        self.write()
        with self.assertRaisesRegex(ValueError, 'opposite pair'): m.read_dataset(self.path)
        self.data['test'][1]['post_id'] = self.data['test'][0]['post_id']
        self.data['test'][1]['state'] = self.data['test'][0]['state']
        self.write()
        self.assertEqual(m.audit(self.path)['status'], 'PASS')
        self.data['test'][1]['expected']['hide'] = False; self.write()
        with self.assertRaisesRegex(ValueError, 'opposite pair'): m.read_dataset(self.path)

    def test_cli_valid_fixture(self):
        (self.path / 'results.json').write_text(json.dumps(self.results()))
        run = subprocess.run([sys.executable, str(SCRIPT), str(self.path), '--results'], text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertTrue(json.loads(run.stdout)['results_checked'])


if __name__ == '__main__': unittest.main()
