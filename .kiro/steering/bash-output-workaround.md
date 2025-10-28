---
inclusion: always
---

## Issue
Kiro is broken, when you execute the command in the terminal it does not seems to pass the command output to agent but instead getting surpressed. This is known bug still this is not fixed the workaround is to add the bash script as prefix as explianed below.

## Workspace Context

- Project workspace root: `/home/vedsaga/hackathon/aws-ai-agent`
- The `.kiro_exec.sh` wrapper script is located at workspace root
- Other project scripts are in subdirectories (e.g., `infrastructure/scripts/`)
- **CRITICAL**: Before suggesting commands, verify the script path is relative to workspace root

## Core Rule

Always when executing any command, use the wrapper script to capture the output:

```bash
./.kiro_exec.sh <command> <args>
```

Then immediately read `.kiro_command_output.txt` before running any other command.

**Path Verification**: Always check that `.kiro_exec.sh` exists relative to your current execution context. If running from a subdirectory, adjust the path accordingly (e.g., `../.kiro_exec.sh` from `infrastructure/`).

## Key Behaviors

- Output file is overwritten on every execution - read immediately after command runs
- Output always written to `.kiro_command_output.txt` in workspace root
- Exit codes preserved - check with `echo $?` if needed
- Output limited to 1000 lines (truncation notice added if exceeded)
- ANSI color codes automatically stripped
- Temporary files (`.kiro_command_output.tmp`) are automatically cleaned up

## When to Use

Use wrapper for any command where you need to see output:
- Diagnostics: `ls`, `cat`, `grep`, `find`, `ps`, `df`
- Version checks: `node -v`, `python --version`
- Status checks: `git status`, `npm ls`
- Tests/builds: `npm test`, `pytest`, `make`

Skip wrapper only for pure file operations where only exit code matters: `mkdir`, `touch`, `rm`, `cp`, `mv`

## Usage Examples

Basic commands:
```bash
./.kiro_exec.sh npm test
./.kiro_exec.sh python script.py --arg value
```

Commands with pipes or special characters - wrap in `bash -c`:
```bash
./.kiro_exec.sh bash -c "cat file.txt | grep pattern"
./.kiro_exec.sh bash -c "ps aux | grep node | wc -l"
```

From subdirectories (using `path` parameter):
```bash
# From ./backend directory
../.kiro_exec.sh npm test

# From ./backend/src directory  
../../.kiro_exec.sh npm test
```

Output is always at workspace root: `.kiro_command_output.txt`

## Standard Workflow

1. Run command: `./.kiro_exec.sh npm run build`
2. Read output immediately: `cat .kiro_command_output.txt`
3. Check exit code if needed: `echo $?`

## Troubleshooting

Empty output file: Command produced no output or wasn't found. Verify with `./.kiro_exec.sh echo "test"`

Special characters breaking: Use `bash -c` with proper quoting
- Wrong: `./.kiro_exec.sh echo "test" > file.txt`
- Correct: `./.kiro_exec.sh bash -c "echo 'test' > file.txt"`

Need more than 1000 lines: Redirect directly to a file then read it
```bash
your_command > output.txt 2>&1
cat output.txt
```