"""Run Filter's model-free completion checks from any working directory."""
from pathlib import Path
import shutil
import subprocess
import sys


def main(mode='check'):
    root = Path(__file__).resolve().parents[1]
    node = shutil.which('node')
    if not node:
        print('Filter checks require Node.js.', file=sys.stderr)
        return 1
    node_tests = [str(path.relative_to(root)) for path in sorted((root / 'tests').glob('*.mjs'))
                  if mode != 'fast' or path.name != 'test_server.mjs']
    commands = [] if mode == 'tests' else [[sys.executable, 'tools/check_repository.py']]
    if mode != 'tests':
        commands += [[sys.executable, '-m', 'compileall', '-q', 'prototypes', 'tests', 'tools']]
        commands += [[node, '--check', str(path.relative_to(root))]
                     for folder in ('prototypes/model-evaluation', 'tests')
                     for path in sorted((root / folder).glob('*.mjs'))]
    commands += [
        [node, '--test', *node_tests],
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=root, check=False)
        if result.returncode:
            return result.returncode
    if mode == 'fast':
        print('Filter fast checks passed; localhost server tests were not run. Run npm run check for the full gate.')
    elif mode == 'tests':
        print('Filter tests passed; run npm run check for artifact and syntax checks.')
    else:
        print('Filter model-free checks passed; browser/model behavior requires separate evidence.')
    return 0


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1:] not in (['fast'], ['tests']):
        from publication import main as publication_main
        raise SystemExit(publication_main(sys.argv[1:]))
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else 'check'))
