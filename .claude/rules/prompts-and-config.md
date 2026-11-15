---
paths:
  - "app/prompts/**"
  - "app/config/**"
  - "app/flows/**"
---
# Prompts, config, flows
- Prompt files are owned by Doc 5 (Prompt Specification). Header version must equal `prompts.spec_version`. Do not rewrite prompt text unless the task explicitly says so.
- Tunables live only in `app/config/config.yaml` (dev / demo / prod); no secrets in it.
- Flows are ADK graph YAML in `app/flows`; validate with the shared validator before committing.
