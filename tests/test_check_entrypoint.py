import importlib.util
import contextlib
import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


path = Path(__file__).resolve().parents[1] / 'tools/check.py'
spec = importlib.util.spec_from_file_location('check_entrypoint', path)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class CheckEntrypointTests(unittest.TestCase):
    def test_fast_omits_server_tests_but_full_and_test_modes_retain_them(self):
        for mode in ('fast', 'check', 'tests'):
            with self.subTest(mode=mode), contextlib.redirect_stdout(io.StringIO()), patch.object(check.shutil, 'which', return_value='/node'), patch.object(check.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as run:
                self.assertEqual(check.main(mode), 0)
                commands = [call.args[0] for call in run.call_args_list]
                node_tests = next(command for command in commands if '--test' in command)
                self.assertEqual('tests/test_server.mjs' in node_tests, mode != 'fast')
                self.assertIn('tests/test_score_replay.mjs', node_tests)
                self.assertTrue(any(command[1:4] == ['-m', 'unittest', 'discover'] for command in commands))
                self.assertEqual(any('tools/check_repository.py' in command for command in commands), mode != 'tests')
                self.assertEqual(any('--check' in command for command in commands), mode != 'tests')

    def test_failure_returns_the_actual_exit_code_and_stops(self):
        with patch.object(check.shutil, 'which', return_value='/node'), patch.object(check.subprocess, 'run', return_value=SimpleNamespace(returncode=7)) as run:
            self.assertEqual(check.main('fast'), 7)
            self.assertEqual(run.call_count, 1)

    def test_missing_node_fails_without_starting_checks(self):
        with contextlib.redirect_stderr(io.StringIO()), patch.object(check.shutil, 'which', return_value=None), patch.object(check.subprocess, 'run') as run:
            self.assertEqual(check.main('fast'), 1)
            run.assert_not_called()
