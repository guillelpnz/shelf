#!/usr/bin/env python3
"""Stop hook: the agent can't finish its turn while the test suite fails.

Works as a Claude Code or Codex Stop hook. Standard library only.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

MAX_BLOCKS = 3   # consecutive blocks before we let the agent stop and warn you
TAIL_LINES = 40  # lines of test output sent back to the agent

event = json.load(sys.stdin)

# Test the project the agent is working in. `cwd` follows it into worktrees.
here = Path(event.get("cwd") or ".").resolve()
root = next((p for p in (here, *here.parents) if (p / "pyproject.toml").exists()), None)
if root is None:
    sys.exit(0)  # not inside the project: nothing to check

result = subprocess.run(
    [sys.executable, "-m", "unittest"], cwd=root, capture_output=True, text=True
)
counter = Path(tempfile.gettempdir()) / f"stop-gate-{event.get('session_id', 'unknown')}"

if result.returncode == 0:
    counter.unlink(missing_ok=True)
    sys.exit(0)  # silent success

# stop_hook_active is true when the agent is already continuing because a Stop hook blocked it.
blocks = int(counter.read_text()) if event.get("stop_hook_active") and counter.exists() else 0
if blocks >= MAX_BLOCKS:
    counter.unlink(missing_ok=True)
    warning = f"Stop gate: tests still fail after {MAX_BLOCKS} attempts. Don't trust this turn's work."
    print(json.dumps({"systemMessage": warning}))  # shown to you, not to the agent
    sys.exit(0)

counter.write_text(str(blocks + 1))
tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-TAIL_LINES:])
print(
    "The test suite fails, so you can't finish yet.\n"
    "Fix the code, not the tests: don't skip, delete or weaken a test.\n"
    f"Last lines of `python -m unittest`:\n{tail}",
    file=sys.stderr,
)
sys.exit(2)  # 2 blocks the stop; any other non-zero code would not
