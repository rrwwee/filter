"""Exercise the actual trainer/report with deterministic fake models, not accuracy claims."""
import contextlib
import importlib.util
import io
import json
import math
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from test_evaluation_contract import row

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'prototypes/model-finetuning'


class PipelineTests(unittest.TestCase):
    def test_checkpoint_comparators_are_retokenized_and_full_population_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scripts = root / 'prototypes/model-finetuning'; scripts.mkdir(parents=True)
            for name in ('evaluation_contract.py', 'compositional_experiment.py', 'compositional_report.py'):
                shutil.copy2(SOURCE / name, scripts / name)
            local = root / 'local-results'; data = local / 'finetune-compositional'; data.mkdir(parents=True)
            import hashlib
            manifest = {'hashes': {}, 'counts': {}}
            for split in ('train', 'validation', 'test'):
                rows = [row(split, i, bool(i % 2)) for i in range(4)]
                for i, r in enumerate(rows):
                    r['origin'] = 'fresh-real-feed'  # Synthetic marker for branch coverage only.
                    r['policy_id'] = 'original_four' if i < 2 else r['policy_id']
                    r['pair_id'] = split + '-pair' if i >= 2 else None
                rows[3]['post_id'] = rows[2]['post_id']
                rows[3]['state'] = rows[2]['state']
                raw = ''.join(json.dumps(r) + '\n' for r in rows).encode()
                (data / (split + '.jsonl')).write_bytes(raw)
                manifest['hashes'][split] = hashlib.sha256(raw).hexdigest()
                manifest['counts'][split] = {'rows': 4, 'posts': 3, 'hide': 2}
            (data / 'manifest.json').write_text(json.dumps(manifest))
            for name in ('finetune-promotions/base', 'finetune-broad/full-checkpoint'):
                path = local / name; path.mkdir(parents=True)
                (path / 'weights.json').write_text('{}')

            class Model:
                def __init__(self, identity): self.identity = identity
                def to(self, device): return self
                def eval(self): return self
                def train(self): return self
            calls = []
            def load_checkpoint(path):
                identity = 'previous-tokenizer' if 'full-checkpoint' in path else 'base-tokenizer'
                return Model(identity), identity, {'max_len': 64, 'head_max_len': 32}
            def items_from_rows(tokenizer, rows, *args, **kwargs):
                calls.append((tokenizer, len(rows)))
                return [(tokenizer, r['expected']['hide']) for r in rows], []
            def calibration_records(model, tokenizer, items, *args, **kwargs):
                # This assertion fails on the original reused-comparator-encoding bug.
                assert all(encoded_tokenizer == model.identity for encoded_tokenizer, _ in items)
                return [(2, [0., 2.] if label else [2., 0.], [0., 1.] if label else [1., 0.], 2) for _, label in items]
            def save_checkpoint(model, tokenizer, cfg, path):
                path = Path(path); path.mkdir(exist_ok=True)
                (path / 'weights.json').write_text(json.dumps({'tokenizer': tokenizer}))
            class TrainConfig:
                def __init__(self, **kwargs): self.__dict__.update(kwargs)
            def train_model(model, tokenizer, items, config, *args, on_epoch_end, **kwargs):
                on_epoch_end(0, .1)
            train = types.ModuleType('laya.train')
            for key, value in locals().copy().items():
                if key in ('load_checkpoint', 'items_from_rows', 'TrainConfig', 'train_model', 'calibration_records', 'save_checkpoint'):
                    setattr(train, key, value)
            laya = types.ModuleType('laya'); laya.train = train
            torch = types.ModuleType('torch')
            torch.set_num_threads = torch.manual_seed = lambda *a: None
            torch.backends = types.SimpleNamespace(mps=types.SimpleNamespace(is_available=lambda: False))
            torch.device = lambda name: types.SimpleNamespace(type=name)
            numpy = types.ModuleType('numpy')
            numpy.mean = lambda values: sum(values) / len(values)
            numpy.log = math.log; numpy.nextafter = math.nextafter; numpy.inf = math.inf
            with patch.dict(sys.modules, {'laya': laya, 'laya.train': train, 'torch': torch, 'numpy': numpy}), patch.object(sys, 'argv', ['compositional_experiment.py']), patch.object(sys, 'path', [str(scripts)] + sys.path), contextlib.redirect_stdout(io.StringIO()):
                # Isolate contract import from any existing module loaded by another test.
                previous = sys.modules.pop('evaluation_contract', None)
                try:
                    runpy.run_path(str(scripts / 'compositional_experiment.py'), run_name='__main__')
                    runpy.run_path(str(scripts / 'compositional_report.py'), run_name='__main__')
                finally:
                    sys.modules.pop('evaluation_contract', None)
                    if previous is not None: sys.modules['evaluation_contract'] = previous
            result = json.loads((data / 'results.json').read_text())
            self.assertEqual(set(result['checkpoint_identities']), {'base', 'previous', 'new'})
            self.assertIn(('previous-tokenizer', 4), calls)
            self.assertTrue(all(len(stage['rows']) == 4 for stage in result['stages'].values()))
            report = (data / 'report.md').read_text()
            self.assertNotIn('remains weak', report)
            self.assertNotIn('improves opposite', report)
            self.assertRegex(report, r'Missing evidence: [^\n]*New combinations')
            self.assertEqual(result['plan']['dataset_hashes'], manifest['hashes'])
            # Historical results can pass arithmetic checks without provenance.
            result.pop('checkpoint_identities')
            result['plan'].pop('runtime_versions')
            (data / 'results.json').write_text(json.dumps(result))
            with patch.object(sys, 'argv', ['compositional_report.py']), patch.object(sys, 'path', [str(scripts)] + sys.path), contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(scripts / 'compositional_report.py'), run_name='__main__')
            report = (data / 'report.md').read_text()
            self.assertIn('Provenance gap:', report)
            self.assertNotIn('starts from the original pinned', report)


if __name__ == '__main__': unittest.main()
