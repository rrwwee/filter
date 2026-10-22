"""Run Filter's model-free completion checks from any working directory."""
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    npm = shutil.which('npm')
    node = shutil.which('node')
    if not npm or not node:
        print('Filter checks require Node.js and npm.', file=sys.stderr)
        return 1
    commands = [
        [sys.executable, 'tools/check_repository.py'],
        [npm, 'test'],
        [sys.executable, '-m', 'compileall', '-q', 'prototypes', 'tests', 'tools'],
        *[[node, '--check', str(path.relative_to(root))]
          for folder in ('prototypes/model-evaluation', 'tests')
          for path in sorted((root / folder).glob('*.mjs'))],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=root, check=False)
        if result.returncode:
            return result.returncode
    print('Filter model-free checks passed; browser/model behavior requires separate evidence.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
