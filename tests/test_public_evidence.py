"""Pure stdlib checks. The synthetic fixture contains no model predictions."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'prototypes/model-finetuning/audit_public_evidence.py'
spec = importlib.util.spec_from_file_location('audit_public_evidence', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PublicEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((ROOT / 'tests/fixtures/synthetic-evidence.json').read_text())
        self.row = self.doc['format_robust']['slices']['Synthetic repeated posts']['fixture']

    def test_fixture_separates_pairs_posts_and_reports_empty_slice(self):
        result = module.audit(self.doc)
        self.assertEqual(result['errors'], [])
        self.assertEqual((result['records'][0]['pairs'], result['records'][0]['posts']), (6, 2))
        self.assertIn('Empty diagnostic: empty slice; no evidence for this claim', result['warnings'])
        self.assertAlmostEqual(result['records'][0]['wanted_retention'], 2 / 3)

    def test_rejects_bad_counts_and_rates(self):
        for key, value in [('n', 7), ('posts', 7), ('posts', 0), ('wanted_kept', 4), ('wanted', True), ('unwanted_hidden', -1), ('accuracy', .9), ('accuracy', float('nan')), ('unwanted_fraction_visible', .1)]:
            with self.subTest(key=key, value=value):
                doc = copy.deepcopy(self.doc)
                doc['format_robust']['slices']['Synthetic repeated posts']['fixture'][key] = value
                self.assertTrue(module.audit(doc)['errors'])

    def test_rejects_different_model_populations(self):
        other = dict(self.row, posts=1)
        self.doc['format_robust']['slices']['Synthetic repeated posts']['other'] = other
        self.assertTrue(module.audit(self.doc)['errors'])

    def test_missing_class_has_null_rate(self):
        self.row.update(n=3, wanted=0, wanted_kept=0, accuracy=1 / 3, unwanted_fraction_visible=1)
        result = module.audit(self.doc)
        self.assertEqual(result['errors'], [])
        self.assertIsNone(result['records'][0]['wanted_retention'])

    def test_zero_pairs_do_not_invent_rates(self):
        self.row.update({k: 0 for k in module.COUNTS})
        result = module.audit(self.doc)
        self.assertEqual(result['errors'], [])
        self.assertIsNone(result['records'][0]['wanted_retention'])
        self.assertTrue(any('zero pairs' in w for w in result['warnings']))

    def test_invalid_schema(self):
        for doc in ({}, [], {'format_robust': {'slices': []}}):
            self.assertTrue(module.audit(doc)['errors'])

    def test_published_aggregate_counts(self):
        result = module.audit(json.loads(module.DEFAULT_INPUT.read_text()))
        self.assertEqual(result['errors'], [])
        self.assertEqual(len(result['records']), 33)
        self.assertIn('New combinations: empty slice; no evidence for this claim', result['warnings'])
        new = next(r for r in result['records'] if r['slice'] == 'All fresh test pairs' and r['model'] == 'new')
        self.assertEqual((new['pairs'], new['posts'], new['wanted_kept'], new['unwanted_hidden']), (1755, 47, 812, 357))

    def test_cli_rejects_bad_arithmetic_and_unreadable_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.json'
            self.row['accuracy'] = .99
            path.write_text(json.dumps(self.doc))
            result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertTrue(json.loads(result.stdout)['errors'])
            path.write_text('{')
            result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('Cannot read aggregate', result.stderr)

    def test_cli_runs_outside_repository(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], cwd='/tmp', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['errors'], [])


if __name__ == '__main__':
    unittest.main()
