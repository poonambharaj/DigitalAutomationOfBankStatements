const fs = require('fs');
const path = require('path');

const root = __dirname;
const runtimeDir = path.join(root, 'runtimes', 'github-copilot');
const outputDir = path.join(root, 'output');

const agents = [
  ['statement-harvester', 'new_banks_manifest'],
  ['jira-ticket-creator', 'jira_ticket_manifest'],
  ['digital-script-builder', 'digital_scripts_manifest'],
  ['test-engineer', 'test_manifest'],
  ['code-guardian', 'review_manifest'],
  ['github-deployer', 'deploy_manifest']
];

const manifestContracts = {
  new_banks_manifest: {
    keys: ['source', 'report', 'extracted_at', 'total_projects_reviewed', 'unsupported_banks_count', 'unsupported_banks'],
    array: 'unsupported_banks',
    itemKeys: ['bank', 'project', 'pages', 'pdf_saved', 'reason']
  },
  jira_ticket_manifest: {
    keys: ['created_at', 'source_manifest', 'total_unsupported', 'tickets_created', 'tickets_failed', 'projects'],
    array: 'projects',
    itemKeys: ['name', 'bank', 'pages', 'pdf_saved', 'status', 'jira_ticket_key', 'jira_ticket_status', 'jira_ticket_error']
  },
  digital_scripts_manifest: {
    keys: ['generated_at', 'total_projects', 'successful', 'failed', 'results', 'next_available_script_id', 'next_available_def_id', 'ids_are_placeholders'],
    array: 'results',
    itemKeys: ['project_name', 'pdf_path', 'sql_file', 'script_id', 'def_id_start', 'def_id_end', 'def_rows_generated', 'document_type', 'verification_rule_set_id', 'status', 'error']
  },
  test_manifest: {
    keys: ['tested_at', 'all_passed', 'total_projects', 'summary', 'projects'],
    array: 'projects',
    itemKeys: ['project_name', 'sql_file', 'document_type', 'verification_rule_set_id', 'test_file', 'status', 'failed_tests', 'missing_variables', 'notes']
  },
  review_manifest: {
    keys: ['reviewed_at', 'summary', 'status', 'findings'],
    array: 'findings',
    itemKeys: ['severity', 'file', 'line_or_range', 'snippet', 'recommendation']
  },
  deploy_manifest: {
    keys: ['branch', 'commit', 'message', 'pr_url', 'status']
  }
};

let failures = 0;

function fail(message) {
  failures += 1;
  console.error(`FAIL ${message}`);
}

function pass(message) {
  console.log(`PASS ${message}`);
}

function readText(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

function assertIncludes(text, expected, label) {
  if (!text.includes(expected)) {
    fail(`${label}: missing "${expected}"`);
  }
}

function validateRequiredKeys(value, keys, label) {
  for (const key of keys) {
    if (!Object.prototype.hasOwnProperty.call(value, key)) {
      fail(`${label}: missing key "${key}"`);
    }
  }
}

function validateManifest(fileName) {
  const fullPath = path.join(outputDir, fileName);
  const manifest = JSON.parse(fs.readFileSync(fullPath, 'utf8'));
  const contractName = Object.keys(manifestContracts).find((name) => fileName.startsWith(name));

  if (!contractName) {
    return;
  }

  const contract = manifestContracts[contractName];
  validateRequiredKeys(manifest, contract.keys, fileName);

  if (contract.array) {
    if (!Array.isArray(manifest[contract.array])) {
      fail(`${fileName}: "${contract.array}" must be an array`);
      return;
    }

    for (const [index, item] of manifest[contract.array].entries()) {
      validateRequiredKeys(item, contract.itemKeys, `${fileName}.${contract.array}[${index}]`);
    }
  }
}

const orchestrator = readText(path.join('runtimes', 'github-copilot', 'orchestrator.md'));
assertIncludes(orchestrator, '`github-copilot`', 'orchestrator runtime');

for (const [agentName, manifestName] of agents) {
  const agentPath = path.join(runtimeDir, 'agents', `${agentName}.md`);
  if (!fs.existsSync(agentPath)) {
    fail(`${agentName}: agent file missing`);
    continue;
  }

  const text = fs.readFileSync(agentPath, 'utf8');
  assertIncludes(orchestrator, `- \`${agentName}\``, 'orchestrator registry');
  assertIncludes(text, '## Required capabilities', agentName);
  assertIncludes(text, '## Inputs', agentName);
  assertIncludes(text, '## Workflow', agentName);
  assertIncludes(text, '## Output', agentName);
  assertIncludes(text, '## Safety rules', agentName);
  assertIncludes(text, manifestName, agentName);
}

pass('GitHub Copilot agent definitions are present and wired in the orchestrator');

if (fs.existsSync(outputDir)) {
  const manifestFiles = fs.readdirSync(outputDir).filter((fileName) => fileName.endsWith('.json'));
  for (const fileName of manifestFiles) {
    validateManifest(fileName);
  }
  pass(`Validated ${manifestFiles.length} output manifest file(s)`);
}

const stage1 = readText('statementrec-stage1.js');
for (const key of manifestContracts.new_banks_manifest.keys) {
  assertIncludes(stage1, key, 'statementrec-stage1.js manifest writer');
}

if (failures > 0) {
  console.error(`${failures} Copilot agent test failure(s)`);
  process.exit(1);
}

console.log('GitHub Copilot agent smoke tests passed.');