"""Codex Stop hook: enforce checks and request one final review continuation."""
import json
import os
import signal
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run_checks(command, timeout=45):
    # Own a process group so a timed-out npm runner cannot leave tests behind.
    process = subprocess.Popen(
        command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise


def check():
    return run_checks([sys.executable, str(ROOT / 'tools/check.py')])


def decide(event, run_check=check):
    if not isinstance(event, dict) or event.get('hook_event_name') != 'Stop':
        return {'decision': 'block', 'reason': 'Filter completion hook received an invalid Stop event.'}
    try:
        Path(event['cwd']).resolve().relative_to(ROOT)
    except (KeyError, TypeError, ValueError):
        return {'decision': 'block', 'reason': 'Filter completion hook cwd is outside this checkout.'}
    try:
        code = run_check()
    except (OSError, subprocess.TimeoutExpired):
        return {'decision': 'block', 'reason': 'Filter completion checks could not finish. Run npm run check and resolve the failure before concluding.'}
    if code:
        return {'decision': 'block', 'reason': f'Filter completion checks failed (exit {code}). Run npm run check, inspect its output, and resolve the failure before concluding.'}
    if event.get('stop_hook_active') is not True:
        return {'decision': 'block', 'reason': 'Filter checks passed. Before concluding, follow .agents/skills/filter-complete/SKILL.md: review the final diff and exact-head evidence, record unresolved problems in the existing GitHub issue, and distinguish verified outcomes from pending work. This is the one final review continuation; no new experiment or publication is requested by this hook.'}
    return {'systemMessage': 'Filter checks passed after the final review continuation.'}


def main():
    try:
        event = json.load(sys.stdin)
    except (ValueError, OSError):
        event = None
    print(json.dumps(decide(event)))


if __name__ == '__main__':
    main()
