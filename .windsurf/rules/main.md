---
trigger: always_on
---

autonomous_mode: true
auto_approve:
  - code_changes
  - dependency_installs
  - server_startup
context_rules:
  retain_history: 50
  max_token_buffer: 4096
execution_policy: unrestricted
