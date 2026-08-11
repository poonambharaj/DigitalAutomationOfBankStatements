# Agent Platform (Runtime-Agnostic)

This directory defines a provider-agnostic multi-agent pipeline for Digital Automation of Bank Statements.

## Goal
Allow team members to run the same workflow using different runtimes:
- Claude
- GitHub Copilot
- Codex (next phase)

## Core principle
Business rules live in `contracts/`.
Runtime-specific prompting and tool syntax live under `runtimes/<provider>/`.

## Pipeline stages
1. statement-harvester
2. jira-ticket-creator (optional/required by policy)
3. digital-script-builder
4. test-engineer
5. code-guardian
6. github-deployer

## Runtime selection
Set runtime context to one of:
- `claude`
- `github-copilot`
- `codex` (planned)

The orchestrator for each runtime must enforce the same stage gates and manifest contracts.
