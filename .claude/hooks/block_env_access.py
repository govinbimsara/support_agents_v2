#!/usr/bin/env python3
"""PreToolUse guard: block any tool call that touches .env files or dumps the environment.

Defense in depth alongside permissions.deny (which has had enforcement gaps).
Exit code 2 = block the call and show stderr to Claude. Allows .env.example.
"""
import json
import re
import sys

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)  # never break the session on malformed input

tool = payload.get("tool_name", "")
strings = []


def collect(v):
    if isinstance(v, str):
        strings.append(v)
    elif isinstance(v, dict):
        for x in v.values():
            collect(x)
    elif isinstance(v, list):
        for x in v:
            collect(x)


ti = payload.get("tool_input", {})
if tool in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
    # Writing text that merely mentions ".env" (docs, .gitignore) is fine; only the target path matters.
    ti = {k: v for k, v in ti.items() if k in ("file_path", "notebook_path", "path")}
collect(ti)
blob = "\n".join(strings)

# .env, .env.local, .env.production, path/to/.env ... but not .env.example / .env.sample / .env.template
ENV_FILE = re.compile(r"(?<![\w-])\.env(?:\.(?!example\b|sample\b|template\b)[\w.-]+)?(?![\w.-])")
ENV_DUMP = re.compile(r"(?:^|[;&|\s(])(?:env|printenv|export\s+-p|declare\s+-x|set)\s*(?:$|[;&|)])", re.M)

reason = None
if ENV_FILE.search(blob):
    reason = "touches a .env file"
elif tool == "Bash" and ENV_DUMP.search(blob):
    reason = "dumps the process environment"

if reason:
    sys.stderr.write(
        f"BLOCKED by project secrets policy: this {tool} call {reason}. "
        "Never read or print .env or environment values. Ask the user to set or fix the "
        "variable (name only) and continue without it. Only .env.example is allowed.\n"
    )
    sys.exit(2)
sys.exit(0)
