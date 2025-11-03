---
inclusion: always
---

DON'T WASTE TOKENS on WRITING DOCs OR ANY MARDKDOWN FILES or ANY SUMMARY.

JUST LET ME KNOW TASK IS DONE. THAT's ENOUGH.


## Hackathon Project Focus

Project: `/home/vedsaga/hackathon/aws-ai-agent`

## Core Efficiency Rules

1. **No Documentation Files** - Skip README.md, CONTRIBUTING.md, CHANGELOG.md, *.txt guides
   - Exception: User explicitly says "I need a markdown file" or asks to update steering files
   - All project docs already exist in `.kiro/specs/`

2. **Minimal Code Only** - Write the absolute minimum code needed
   - No verbose implementations
   - No unnecessary helper functions
   - No example usage comments unless critical
   - Skip tests unless explicitly requested

3. **No Explanatory Preambles** - Just do the work
   - Don't explain what you're about to do
   - Don't repeat yourself
   - Don't summarize what you just did
   - Let the code speak

4. **Parallel Operations** - Use multiple tool calls simultaneously when operations are independent
   - Multiple strReplace calls at once
   - Multiple file reads at once
   - Don't wait unnecessarily

## Command Execution

Always use the wrapper for commands that produce output:
```bash
./.kiro_exec.sh <command>
```
Then immediately read `.kiro_command_output.txt`

## Response Style

- Be direct and concise
- Skip pleasantries after the first exchange
- Ask clarifying questions only when truly unclear
- Focus on the hackathon project deliverables
- Don't repeat information already established

## What to Skip

- Long explanations of what code does (code should be self-evident)
- Installation guides (user knows their environment)
- Architecture overviews (unless explicitly requested)
- "Here's what I'm going to do" announcements
- Apologizing for previous responses

## What to Deliver

- Working code that runs immediately
- Fixes to actual problems
- Direct answers to questions
- Actionable next steps when stuck