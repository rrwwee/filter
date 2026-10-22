"""Fail CI on accidentally tracked private experiment artifacts or known secret formats."""
from pathlib import Path
import re
import subprocess
import sys

PRIVATE_DIRECTORIES = {'local-results', 'node_modules', '.venv', '__pycache__', '.aws'}
PRIVATE_NAMES = {'.env', 'id_rsa', 'id_ed25519', 'credentials'}
WEIGHT_SUFFIXES = {'.safetensors', '.pt', '.pth', '.ckpt', '.onnx'}
SECRET_PATTERNS = [re.compile(p) for p in (
    rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    rb'\bgh[pousr]_[A-Za-z0-9]{30,}', rb'\bgithub_pat_[A-Za-z0-9_]{30,}',
    rb'\bAKIA[0-9A-Z]{16}\b',
)]


def violations(path, content):
    p = Path(path)
    reasons = []
    if PRIVATE_DIRECTORIES.intersection(p.parts) or p.name in PRIVATE_NAMES or p.suffix in WEIGHT_SUFFIXES:
        reasons.append('private artifact path')
    if any(pattern.search(content) for pattern in SECRET_PATTERNS):
        reasons.append('credential pattern')
    return reasons


def main():
    paths = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
    failures = []
    for path in filter(None, paths):
        failures.extend((path, reason) for reason in violations(path, Path(path).read_bytes()))
    for path, reason in failures:
        # Never print secret values or private file contents into CI logs.
        print(f'{path}: {reason}', file=sys.stderr)
    if failures:
        return 1
    print('Tracked artifact and credential-pattern checks passed; heuristic, not a privacy proof.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
