# Manifest Contracts (Canonical)

## A) new_banks_manifest
Required keys:
- source
- report
- extracted_at
- total_projects_reviewed
- unsupported_banks_count
- unsupported_banks[]:
  - bank
  - project
  - pages
  - pdf_saved
  - reason

## B) jira_ticket_manifest
Required keys:
- created_at
- source_manifest
- total_unsupported
- tickets_created
- tickets_failed
- projects[]:
  - name
  - bank
  - pages
  - pdf_saved
  - status
  - jira_ticket_key (nullable)
  - jira_ticket_status
  - jira_ticket_error (nullable)

## C) digital_scripts_manifest
Required keys:
- generated_at
- total_projects
- successful
- failed
- results[]:
  - project_name
  - pdf_path
  - sql_file
  - script_id
  - def_id_start
  - def_id_end
  - def_rows_generated
  - document_type
  - verification_rule_set_id
  - status
  - error (nullable)
- next_available_script_id
- next_available_def_id
- ids_are_placeholders

## D) test_manifest
Required keys:
- tested_at
- all_passed
- total_projects
- summary {passed, failed, skipped, errors}
- projects[]:
  - project_name
  - sql_file
  - document_type
  - verification_rule_set_id
  - test_file
  - status
  - failed_tests[]
  - missing_variables[]
  - notes

## E) review_manifest
Required keys:
- reviewed_at
- summary {critical, warning, suggestion}
- status: APPROVED | BLOCKED
- findings[]:
  - severity
  - file
  - line_or_range
  - snippet
  - recommendation

## F) deploy_manifest
Required keys:
- branch
- commit
- message
- pr_url (nullable)
- status
