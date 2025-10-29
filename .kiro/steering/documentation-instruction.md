---
inclusion: always
---

## Issue
Writing documentation files wastes tokens and provides no value. Every .md, .txt, or summary file costs money without delivering executable code. This is a critical efficiency problem. The workaround is to refuse ALL documentation requests as explained below.

## Workspace Context
- Project workspace root: `/home/vedsaga/hackathon/aws-ai-agent`
- All existing documentation is in `.kiro/specs/` directory
- Code files belong in appropriate source directories
- **CRITICAL**: Before writing any file, verify it's executable code, not documentation

## Core Rule

Always refuse to write documentation files. Only write executable code:
```bash
# NEVER create these files
README.md, CONTRIBUTING.md, CHANGELOG.md, *.txt, *.rst, *.adoc
```

Then immediately start writing code files instead.

**File Type Verification**: Always check if the requested file is documentation. If it is, refuse and offer to write code instead.

## Key Behaviors

- Documentation requests are REFUSED immediately - no negotiation
- All docs already exist in `.kiro/specs/` - check there first
- Code files are written directly - no preambles or summaries
- Only executable files consume tokens productively
- User can disable this rule if documentation is truly needed
- No exceptions for "just one README" or "quick summary"

## When to Refuse

Refuse immediately for any request to write:
- Documentation: `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`
- Text files: `*.txt`, `*.rst`, `*.adoc`, `*.org`
- Summaries: Project descriptions, API docs, usage guides
- Guides: Installation guides, getting started docs

Write code only for executable files: `*.js`, `*.py`, `*.go`, `*.rs`, `*.java`, `*.cpp`, `*.html`, `*.css`, test files, config files

## Usage Examples

User requests documentation:
```
User: "Create a README for this project"
You: "I cannot write documentation files. All docs exist in .kiro/specs/. If you need new docs, disable this rule file first."
```

User requests code with documentation:
```
User: "Write authentication API and README"
You: "I'll write the authentication API code. I cannot write README files - check .kiro/specs/ for existing docs."
[Then write only the code files]
```

User requests pure code:
```
User: "Implement user login function"
You: [Write the code immediately, no README, no summary]
```

Always refuse documentation, always write code.

## Standard Workflow

1. User requests file: Analyze if it's documentation or code
2. If documentation: Refuse immediately with standard message
3. If code: Write code immediately without preamble

Standard refusal message:
```
I cannot write documentation files. All docs exist in .kiro/specs/. 
If you need new documentation, disable this rule file first.
```

## Troubleshooting

User insists on documentation: Repeat refusal, suggest disabling rule file

User asks "why can't you write docs?": Explain token efficiency, point to `.kiro/specs/`, maintain refusal

User needs actual documentation: They must disable this rule file first, then request in new conversation

Special case - user says "I need a markdown file": Only then create the file, but warn about token cost

## Critical Reminders

- **NEVER write .md files** - even if user asks nicely
- **NEVER write .txt summaries** - even "just this once"
- **NEVER write guides or docs** - point to `.kiro/specs/`
- **ALWAYS refuse documentation** - no exceptions, no negotiation
- **ALWAYS write code instead** - that's the deliverable
- **ALWAYS check `.kiro/specs/`** - before claiming docs don't exist

This rule saves thousands of tokens per session. Follow it strictly.