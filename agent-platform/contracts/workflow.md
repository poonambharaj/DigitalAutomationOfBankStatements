# Workflow Contract

## Stage order
1. Harvest
2. Jira ticket creation (if enabled)
3. Build
4. Test
5. Review
6. Deploy

## Gate rules
- Do not continue if any stage returns blocking critical errors.
- Deploy allowed only when:
  - test manifest `all_passed = true` (or all non-skipped passed),
  - review status is approved (no critical findings).

## Human-in-the-loop checkpoint
If StatementRec auth (Cloudflare + Azure MFA) is required:
- Pause and request user authentication in browser session.
- Resume only after confirmed authenticated state.

## Handoff rule
Each stage must pass structured output manifest to next stage unchanged except additive fields.
