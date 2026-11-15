# Secrets handling (always applies)

- Do not Read, Grep, Glob, cat, head, tail, source, diff or otherwise open `.env` or `.env.*`. `.env.example` is the only exception.
- Do not run `env`, `printenv`, `set`, `export -p`, or print any variable that may hold a credential.
- To add or change a variable: edit `.env.example` (placeholder only) and tell the user the variable name; the user sets the real value.
- If an error message contains a secret, do not repeat it in output, commits, PR text or logs.
- Connectivity checks use the app's own health endpoint or an MCP tool, never by reading credentials.
