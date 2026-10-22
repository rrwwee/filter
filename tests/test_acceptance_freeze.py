"""Acceptance plans must bind evidence before inference, without reading models."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'prototypes/model-finetuning/freeze_acceptance.py'


class FreezeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.data, self.history = root/'data', root/'history'
        self.base, self.tuned = root/'base', root/'tuned'
        for p in (self.data, self.history, self.base, self.tuned):
            p.mkdir()
        (self.base/'weights').write_bytes(b'first')
        (self.tuned/'weights').write_bytes(b'second')
        self.cases = [{'id': 'invented', 'instruction': 'Hide purchase offers.',
                       'state': 'A fictional paper kite floated above the orchard.', 'expected_hide': False}]
        self.write('author-labels.json', self.cases)
        self.write('independent-labels.json', [{'id': 'invented', 'expected_hide': False}])
        self.write('ambiguous.json', [])

    def write(self, name, data):
        (self.data/name).write_text(json.dumps(data))

    def run_freeze(self):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.data), str(self.history),
                               '--base-checkpoint', str(self.base), '--tuned-checkpoint', str(self.tuned)],
                              text=True, capture_output=True)

    def test_freeze_binds_distinct_models_and_refuses_overwrite(self):
        result = self.run_freeze()
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads((self.data/'plan.json').read_text())
        self.assertEqual(len(set(plan['checkpoint_bindings'].values())), 2)
        original = (self.data/'plan.json').read_bytes()
        self.assertNotEqual(self.run_freeze().returncode, 0)
        self.assertEqual((self.data/'plan.json').read_bytes(), original)

    def test_known_text_and_review_disagreement_block_freeze(self):
        (self.history/'earlier.json').write_text(json.dumps({'state': self.cases[0]['state']}))
        self.assertNotEqual(self.run_freeze().returncode, 0)
        self.assertFalse((self.data/'plan.json').exists())
        (self.history/'earlier.json').unlink()
        self.write('independent-labels.json', [{'id': 'invented', 'expected_hide': True}])
        self.assertNotEqual(self.run_freeze().returncode, 0)
        self.assertFalse((self.data/'plan.json').exists())

    def test_same_checkpoint_cannot_be_both_comparators(self):
        (self.tuned/'weights').write_bytes(b'first')
        self.assertNotEqual(self.run_freeze().returncode, 0)
        self.assertFalse((self.data/'plan.json').exists())


if __name__ == '__main__':
    unittest.main()
