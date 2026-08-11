# Tool Capability Matrix

| Capability | Claude Runtime | GitHub Copilot Runtime | Codex Runtime (planned) |
|---|---|---|---|
| Browser automation | Playwright MCP | Playwright MCP (if connected) | TBD |
| File read/write | Read/Write tools | repo file tools / local editor context | TBD |
| Shell commands | Bash | terminal/CI context | TBD |
| GitHub operations | GitHub MCP | GitHub tools/API | TBD |
| Jira comments/issues | Atlassian MCP | Atlassian MCP | TBD |

## Rule
Agent logic must check capability availability before execution and return actionable fallback if unavailable.
