#!/usr/bin/env python3
# CARL for ZCode: SessionStart bridge to the carl-hook (hooks/carl-hook.py).
# ZCode has no UserPromptSubmit event, so the per-prompt injection cannot run; this bridge
# emits the full <carl-rules> block once at session start. Re-run the carl-mcp tools or
# reload after editing .carl/carl.json to see changes mid-session.
# Registered in ~/.zcode/cli/config.json hooks.events.SessionStart (the installer does this).
import json
import os
import subprocess
import sys
from pathlib import Path

# The hook ships in the same directory as this bridge (the installer copies both into the
# harness hooks dir). A shipped copy takes precedence; fall back to the Claude Code install.
_HERE = Path(__file__).resolve().parent
_CANDIDATES = [
    _HERE / "carl-hook.py",
    Path.home() / ".claude" / "hooks" / "carl-hook.py",
]
_HOOK = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])


def main() -> int:
    stdin: dict = {}
    try:
        raw = sys.stdin.read()
        if raw.strip():
            stdin = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        stdin = {}

    payload = {
        "prompt": "session-start",
        # ZCode may not pass cwd; fall back to the process cwd (the launched project).
        "cwd": stdin.get("cwd") or str(Path.cwd()),
        "sessionId": stdin.get("sessionId") or stdin.get("session_id") or "zcode-session",
        "contextPercentageRemaining": stdin.get("contextPercentageRemaining", 100),
    }
    try:
        # -X utf8: the hook emits emoji (DEVMODE markers) and Windows pipes default to ANSI.
        r = subprocess.run(
            [sys.executable, "-X", "utf8", str(_HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"[carl-zcode] hook failed: {e}", file=sys.stderr)
        return 0  # never block session start

    out = (r.stdout or "").strip()
    if not out:
        # No .carl scope for this project: stay silent.
        return 0
    try:
        d = json.loads(out)
        ctx = d.get("hookSpecificOutput", {}).get("additionalContext", "")
    except json.JSONDecodeError:
        ctx = out
    if ctx:
        print(ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
