import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

PATH = Path(__file__).resolve().parents[1] / 'tools/stop_review.py'
SPEC = importlib.util.spec_from_file_location('filter_stop_review', PATH)
HOOK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOOK)


class StopReviewTests(unittest.TestCase):
    def event(self, active=False):
        return {'hook_event_name': 'Stop', 'cwd': str(HOOK.ROOT), 'stop_hook_active': active}

    def test_success_requires_one_review_continuation(self):
        self.assertEqual(HOOK.decide(self.event(), lambda: 0)['decision'], 'block')
        result = HOOK.decide(self.event(True), lambda: 0)
        self.assertNotIn('decision', result)
        self.assertIn('passed', result['systemMessage'])

    def test_failed_checks_block_even_after_review(self):
        for active in (False, True):
            result = HOOK.decide(self.event(active), lambda: 1)
            self.assertEqual(result['decision'], 'block')
            self.assertIn('exit 1', result['reason'])

    def test_timeout_and_invalid_context_do_not_claim_success(self):
        def timeout():
            raise subprocess.TimeoutExpired('check', 45)
        self.assertEqual(HOOK.decide(self.event(), timeout)['decision'], 'block')
        for event in (None, {}, {'hook_event_name': 'Stop', 'cwd': '/'}):
            self.assertEqual(HOOK.decide(event, lambda: 0)['decision'], 'block')

    def test_timeout_terminates_owned_descendants(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'orphan-ran'
            child = "import time; from pathlib import Path; time.sleep(0.5); Path(%r).touch()" % str(marker)
            parent = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', %r]); time.sleep(5)" % child
            with self.assertRaises(subprocess.TimeoutExpired):
                HOOK.run_checks([sys.executable, '-c', parent], timeout=0.2)
            time.sleep(0.6)
            self.assertFalse(marker.exists(), 'timed-out check left a descendant running')
