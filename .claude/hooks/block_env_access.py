#!/usr/bin/env python3
"""PreToolUse guard: block any tool call that touches .env files or dumps the environment.

Defense in depth alongside permissions.deny (which has had enforcement gaps).
Exit code 2 = block the call and show stderr to Claude. No .env* file is exempt, .env.example
included: the agent names the variables it needs and the user maintains the files.
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

# .env, .env.local, .env.production, .env.example, path/to/.env ... every .env* file, no exemptions
ENV_FILE = re.compile(r"(?<![\w-])\.env(?:\.[\w.-]+)?(?![\w.-])")
ENV_DUMP = re.compile(r"(?:^|[;&|\s(])(?:env|printenv|export\s+-p|declare\s+-x|set)\s*(?:$|[;&|)])", re.M)

reason = None
if ENV_FILE.search(blob):
    reason = "touches a .env file"
elif tool == "Bash" and ENV_DUMP.search(blob):
    reason = "dumps the process environment"

if reason:
    sys.stderr.write(
        f"BLOCKED by project secrets policy: this {tool} call {reason}. "
        "Never read any .env* file (.env.example included) or print environment values. "
        "Tell the user the variable name(s) needed and what each is for, and continue without it.\n"
    )
    sys.exit(2)
sys.exit(0)
