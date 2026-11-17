# Secrets handling (always applies)

- Do not Read, Grep, Glob, cat, head, tail, source, diff, edit or otherwise open any `.env*` file. There is no exception: `.env.example` is covered too.
- Do not run `env`, `printenv`, `set`, `export -p`, or print any variable that may hold a credential.
- To add or change a variable: tell the user the variable name(s) and what each is for. The user maintains the env files and sets the real values.
- If an error message contains a secret, do not repeat it in output, commits, PR text or logs.
- Connectivity checks use the app's own health endpoint or an MCP tool, never by reading credentials.
