---
inclusion: always
---

# Bash Output Workaround

**Always use wrapper for commands:** `./.kiro_exec.sh <command>`
**Then read:** `cat .kiro_command_output.txt`

**Examples:**
- `./.kiro_exec.sh npm test`
- `./.kiro_exec.sh bash -c "cat file | grep pattern"`
- From subdir: `../.kiro_exec.sh npm test`

**Skip wrapper for:** `mkdir`, `touch`, `rm`, `cp`, `mv` (file ops only)