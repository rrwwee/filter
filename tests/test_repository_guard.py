import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1]/'tools/check_repository.py'
spec = importlib.util.spec_from_file_location('repository_guard', path)
guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)


class RepositoryGuardTests(unittest.TestCase):
    def test_private_artifacts_are_rejected(self):
        for path in ('local-results/cases.json', 'nested/.env', 'weights/model.safetensors', '.aws/credentials'):
            self.assertIn('private artifact path', guard.violations(path, b'{}'))
        self.assertEqual(guard.violations('tests/fixtures/synthetic-evidence.json', b'{}'), [])

    def test_credentials_fail_without_requiring_a_private_filename(self):
        token = b'ghp_' + b'a'*36
        self.assertIn('credential pattern', guard.violations('notes.txt', token))
        self.assertEqual(guard.violations('README.md', b'No credential here.'), [])
