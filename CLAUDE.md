# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repository automates the digital processing of financial statements sourced from StatementRec. The full pipeline — harvest → build → test → review → deploy — is executed by a team of specialised sub-agents that you orchestrate. You never perform specialised work yourself; you delegate every stage.

## Multi-agent architecture

```
CLAUDE.md  (orchestrator — this file)
└── .claude/agents/
    ├── statement-harvester   Playwright MCP · Read · Glob
    ├── digital-script-builder  Read · Write · Bash
    ├── test-engineer           Read · Write · Bash
    ├── code-guardian           Read · Grep · Glob
    └── github-deployer         GitHub MCP · Bash
```

Sub-agents are invoked via the `Agent` tool. Each agent file in `.claude/agents/` contains YAML frontmatter (`name`, `description`, `tools`, `model`) followed by that agent's full system prompt. Agents only have access to the tools listed in their frontmatter.

## Delegation rules

| Trigger | Delegate to |
|---|---|
| Downloading statements, logging in to StatementRec, or identifying projects that have not been digitally processed | `statement-harvester` |
| Writing, updating, or debugging digital processing scripts using the DigitalPDF library | `digital-script-builder` |
| Writing unit tests, running tests, or achieving branch coverage | `test-engineer` |
| Reviewing code quality, security vulnerabilities, or best-practice adherence | `code-guardian` |
| Staging files, committing, or pushing code to GitHub | `github-deployer` |

## Orchestration workflow

When the user gives you a task, follow this sequence unless they instruct otherwise:

1. **Harvest** — invoke `statement-harvester` to open the "Digital (Not Auto-Processed)" tab,
   extract all projects, compare bank names against `DigitalScripts.sql`, download PDFs for
   any unsupported banks to `References/NewBanksIdentified/`, and return a manifest.
2. **Build** — invoke `digital-script-builder` with the manifest to create extraction scripts
   for each unsupported bank.
3. **Test** — invoke `test-engineer` to write and run tests for the new scripts.
4. **Review** — invoke `code-guardian` to review all produced code.
5. **Deploy** — invoke `github-deployer` to commit and push when the review is clean.

## Browser authentication note

StatementRec uses Cloudflare Access + Azure AD MFA. Sub-agents start fresh browser
contexts with no shared session, so they **cannot authenticate** on their own.

When a task requires StatementRec access:
1. The orchestrator (you) handles browser navigation directly using the Playwright MCP tools.
2. If the session has expired, prompt the user: *"Please authenticate in the browser window
   (use Azure AD · Azure AD, email poonam.bharaj@sage.com, then approve the MFA prompt)."*
3. Once authenticated, proceed with browser automation in the orchestrator context.

## Handoff protocol

- Pass the structured output from one sub-agent as the input context to the next.
- If a sub-agent returns errors or findings that block progression (e.g., `code-guardian` flags a critical issue), stop and report back to the user before continuing.
- Never skip a stage unless the user explicitly asks you to.
- Do not attempt to fix code, write tests, or push commits yourself — always delegate.

## Adding or modifying sub-agents

Each file in `.claude/agents/` must begin with YAML frontmatter followed by the system prompt:

```markdown
---
name: <kebab-case-name>
description: <one-sentence description — used by the orchestrator to decide when to invoke>
tools: <comma-separated tool list>
model: claude-haiku-4-5-20251001
---

System prompt content here.
```

The `description` field is the primary signal the orchestrator uses to select the correct agent — keep it precise and action-oriented.
