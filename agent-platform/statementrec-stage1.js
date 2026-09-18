const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const SQL_PATH = path.join(__dirname, '..', 'References', 'DigitalScriptSample', 'DigitalScripts.sql');
const HARVEST_DATE = process.env.HARVEST_DATE || null;

// Words too generic to identify a specific bank on their own
const SKIP_WORDS = new Set([
  // Country/region codes
  'uk', 'us', 'aus', 'za', 'ca', 'fr', 'nz',
  // Account/product types
  'online', 'internet', 'banking', 'credit', 'card', 'account',
  'current', 'business', 'monthly', 'frequency', 'descending',
  'transactions', 'transaction', 'line',
  // English function words
  'and', 'the', 'for', 'not', 'but', 'can', 'are', 'was', 'has',
  'had', 'its', 'who', 'per', 'our', 'out', 'nor', 'yet',
  // Generic bank/finance words (not unique identifiers on their own)
  'bank', 'trust', 'corp', 'inc', 'plc', 'ltd', 'new', 'old'
]);

function loadSupportedBankKeywords(sqlPath) {
  if (!fs.existsSync(sqlPath)) {
    console.warn(`DigitalScripts.sql not found at ${sqlPath} — all banks treated as unsupported.`);
    return [];
  }
  const content = fs.readFileSync(sqlPath, 'utf8');
  // $source values are stored as: $source = \"VALUE\" inside single-quoted SQL strings
  const keywords = new Set();
  for (const [, source] of content.matchAll(/\$source\s*=\s*\\"([^\\]+)\\"/g)) {
    source
      .replace(/([a-z])([A-Z])/g, '$1 $2') // split camelCase
      .split(/[/\s_\-]+/)
      .map(p => p.toLowerCase().trim())
      .filter(p => p.length >= 3 && !SKIP_WORDS.has(p))
      .forEach(w => keywords.add(w));
  }
  console.log(`Loaded ${keywords.size} supported bank keywords from DigitalScripts.sql`);
  return [...keywords];
}

function normalizeText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function findColumnIndex(headers, patterns, fallback) {
  const index = headers.findIndex((header) => patterns.some((pattern) => pattern.test(header)));
  return index >= 0 ? index : fallback;
}

function toIsoDate(value) {
  const text = normalizeText(value);
  if (!text) return null;

  const isoMatch = text.match(/\b(\d{4})-(\d{1,2})-(\d{1,2})\b/);
  if (isoMatch) {
    const [, year, month, day] = isoMatch;
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
  }

  const slashMatch = text.match(/\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b/);
  if (slashMatch) {
    const [, day, month, rawYear] = slashMatch;
    const year = rawYear.length === 2 ? `20${rawYear}` : rawYear;
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
  }

  const parsed = new Date(text);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toISOString().slice(0, 10);
  }

  return null;
}

function formatDateForStatementRec(value) {
  const [year, month, day] = value.split('-');
  return `${Number(month)}/${Number(day)}/${year}`;
}

// Local calendar day, used when no explicit report date is requested.
function todayIso() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

(async () => {
  const EFFECTIVE_DATE = HARVEST_DATE || todayIso();
  const username = process.env.USERNAME || 'YOUR_WINDOWS_USERNAME';
  const defaultEdgeUserDataDir = `C:\\Users\\${username}\\AppData\\Local\\Microsoft\\Edge\\User Data`;
  const userDataDir = process.env.USE_EDGE_DEFAULT_PROFILE === '1'
    ? defaultEdgeUserDataDir
    : process.env.HARVEST_PROFILE_DIR || path.join(__dirname, '.playwright', `edge-profile-${process.pid}`);

  const outputDir = path.join(process.cwd(), 'output');
  const pdfRoot = path.join(process.cwd(), '..', 'References', 'NewBanksIdentified');

  fs.mkdirSync(outputDir, { recursive: true });
  fs.mkdirSync(pdfRoot, { recursive: true });

  let browser;
  try {
    browser = await chromium.launchPersistentContext(userDataDir, {
      channel: 'msedge',
      headless: false,
      args: process.env.USE_EDGE_DEFAULT_PROFILE === '1' ? ['--profile-directory=Default'] : []
    });

    const page = await browser.newPage();
    const url = 'https://app-web.statementrec.com/app/index#allreports';
    const report = 'Digital (Not Auto-Processed)';

    console.log('Opening StatementRec...');
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });

    // If MFA/Cloudflare sign-in is required, pause and let the user complete it manually.
    const signInVisible = await page
      .locator('text=Sign in', { exact: false })
      .isVisible()
      .catch(() => false);

    if (signInVisible) {
      console.log('Cloudflare sign-in page detected. Please complete MFA/authentication in the Edge browser, then press Enter here when done.');
      await new Promise((resolve) => {
        process.stdin.once('data', resolve);
      });
    }

    // Wait for the actual app content after login
    await page.waitForSelector(`text=${report}`, {
      timeout: 300000
    }).catch(() => {
      throw new Error('Authentication did not complete. Please finish MFA and retry.');
    });

    console.log('StatementRec authenticated successfully.');

    // Reopens the Digital (Not Auto-Processed) tab and reapplies the report date filter.
    // Called before every per-project lookup since visiting a project detail page and
    // navigating back can otherwise leave the grid in an unfiltered/unknown state.
    async function openFilteredDigitalReport() {
      await page.getByText('Digital (Not Auto-Processed)', { exact: false }).click();
      await page.waitForTimeout(3000);

      let dateInputsPresent = 0;
      for (let attempt = 0; attempt < 15 && dateInputsPresent < 2; attempt += 1) {
        dateInputsPresent = await page.locator('input[type="text"]').evaluateAll((inputs) => {
          return inputs.filter((input) => {
            const style = window.getComputedStyle(input);
            const rect = input.getBoundingClientRect();
            return style.display !== 'none'
              && style.visibility !== 'hidden'
              && rect.width > 0
              && rect.height > 0
              && /^\d{1,2}\/\d{1,2}\/\d{4}$/.test(input.value || '');
          }).length;
        });
        if (dateInputsPresent < 2) await page.waitForTimeout(1000);
      }

      const statementRecDate = formatDateForStatementRec(EFFECTIVE_DATE);
      const dateInputsUpdated = await page.locator('input[type="text"]').evaluateAll((inputs, dateValue) => {
        const visibleInputs = inputs.filter((input) => {
          const style = window.getComputedStyle(input);
          const rect = input.getBoundingClientRect();
          return style.display !== 'none'
            && style.visibility !== 'hidden'
            && rect.width > 0
            && rect.height > 0
            && /^\d{1,2}\/\d{1,2}\/\d{4}$/.test(input.value || '');
        }).slice(0, 2);

        for (const input of visibleInputs) {
          input.value = dateValue;
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
          input.dispatchEvent(new Event('blur', { bubbles: true }));
        }

        return visibleInputs.length;
      }, statementRecDate);

      if (dateInputsUpdated < 2) {
        throw new Error(`Requested report date ${EFFECTIVE_DATE}, but only ${dateInputsUpdated} date input(s) were found.`);
      }

      console.log(`Applied StatementRec date filter: ${statementRecDate}`);
      const filterClicked = await page.locator('button, [role="button"], a').evaluateAll((elements) => {
        const button = elements.find((element) => {
          const style = window.getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          const text = (element.textContent || '').replace(/\s+/g, ' ').trim();
          const title = element.getAttribute('title') || '';
          return style.display !== 'none'
            && style.visibility !== 'hidden'
            && rect.width > 0
            && rect.height > 0
            && (text === 'Filter' || title === 'Filter');
        });

        if (!button) return false;
        button.click();
        return true;
      });

      if (!filterClicked) {
        throw new Error('StatementRec Filter button was not found after applying the report date.');
      }

      await page.waitForTimeout(5000);
    }

    await openFilteredDigitalReport();

    const supportedKeywords = loadSupportedBankKeywords(SQL_PATH);

    async function extractGridSnapshot() {
      return page.evaluate(() => {
        const isVisibleDataRow = (tr) => {
          const style = window.getComputedStyle(tr);
          return style.display !== 'none'
            && style.visibility !== 'hidden'
            && !tr.classList.contains('k-footer-template')
            && !tr.classList.contains('k-group-footer')
            && !tr.classList.contains('k-grouping-row');
        };

        const rowTables = Array.from(document.querySelectorAll('table'))
          .map((table) => ({ table, rows: Array.from(table.querySelectorAll('tbody tr')).filter(isVisibleDataRow) }))
          .filter((entry) => entry.rows.length > 0)
          .sort((left, right) => right.rows.length - left.rows.length);

        const bodyTable = rowTables[0]?.table || document.querySelector('table');
        const gridRoot = bodyTable?.closest('.k-grid') || bodyTable?.parentElement || document;
        const headerTable = Array.from(gridRoot.querySelectorAll('thead th'));

        const headers = headerTable
          .map((cell) => (cell.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase())
          .filter(Boolean);

        const rows = (rowTables[0]?.rows || []).map((tr) => {
          const cells = Array.from(tr.querySelectorAll('td, th'));
          return cells.map((cell) => (cell.textContent || '').replace(/\s+/g, ' ').trim());
        });

        return { headers, rows };
      });
    }

    console.log('Extracting report rows (including pagination)...');
    let headers = [];
    const allRows = [];
    let previousPageSignature = null;
    for (let pageNumber = 1; pageNumber <= 50; pageNumber += 1) {
      const snapshot = await extractGridSnapshot();
      if (pageNumber === 1) headers = snapshot.headers;
      if (snapshot.rows.length === 0) break;

      const pageSignature = JSON.stringify(snapshot.rows[0]);
      if (pageSignature === previousPageSignature) break;
      previousPageSignature = pageSignature;
      allRows.push(...snapshot.rows);

      const advancedToNextPage = await page.evaluate(() => {
        const next = document.querySelector('a[title="Go to the next page"], a[aria-label="Go to the next page"]');
        if (!next) return false;
        if (next.closest('.k-state-disabled, [aria-disabled="true"]')) return false;
        next.click();
        return true;
      });

      if (!advancedToNextPage) break;
      await page.waitForTimeout(1500);
    }

    console.log(`Downloading Excel report for ${EFFECTIVE_DATE}...`);
    const excelDownloadPromise = page.waitForEvent('download', { timeout: 60000 }).catch(() => null);
    const excelClicked = await page.evaluate(() => {
      const candidates = Array.from(document.querySelectorAll('a, button, [role="button"]'));
      const excelControl = candidates.find((element) => {
        const style = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        const text = (element.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
        const title = (element.getAttribute('title') || '').toLowerCase();
        const aria = (element.getAttribute('aria-label') || '').toLowerCase();
        return style.display !== 'none'
          && style.visibility !== 'hidden'
          && rect.width > 0
          && rect.height > 0
          && (text.includes('excel') || title.includes('excel') || aria.includes('excel'));
      });

      if (!excelControl) return false;
      excelControl.click();
      return true;
    });

    if (!excelClicked) {
      const controls = await page.locator('a, button, [role="button"]').evaluateAll((elements) => {
        return elements.map((element) => {
          const style = window.getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          return {
            tag: element.tagName.toLowerCase(),
            text: (element.textContent || '').replace(/\s+/g, ' ').trim(),
            title: element.getAttribute('title') || '',
            aria: element.getAttribute('aria-label') || '',
            href: element.getAttribute('href') || '',
            visible: style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0
          };
        }).filter((item) => item.visible).slice(0, 80);
      });
      console.log(`Visible link/button controls: ${JSON.stringify(controls, null, 2)}`);
      throw new Error('Excel export link was not found on the Digital (Not Auto-Processed) report.');
    }

    const excelDownload = await excelDownloadPromise;
    if (!excelDownload) {
      throw new Error('Excel download did not start after clicking the Excel export link.');
    }
    const excelFileName = `digital_not_auto_processed_${EFFECTIVE_DATE.replace(/-/g, '')}.xlsx`;
    let excelPath = path.join(outputDir, excelFileName);
    try {
      await excelDownload.saveAs(excelPath);
    } catch (saveErr) {
      // Canonical daily file may be open/locked (e.g. in Excel); fall back to a timestamped copy.
      const fallbackName = `digital_not_auto_processed_${EFFECTIVE_DATE.replace(/-/g, '')}_${Date.now()}.xlsx`;
      excelPath = path.join(outputDir, fallbackName);
      console.warn(`Could not save Excel report to the canonical path (${saveErr.message}). Saving to ${excelPath} instead.`);
      await excelDownload.saveAs(excelPath);
    }
    console.log(`Excel report saved: ${excelPath}`);

    const projectIndex = findColumnIndex(headers, [/project/, /client/, /^name$/, /company/], 0);
    const bankIndex = findColumnIndex(headers, [/bank/, /source/], 1);
    const pagesIndex = findColumnIndex(headers, [/page/], 2);
    const dateIndex = findColumnIndex(headers, [/date/, /upload/, /created/, /submitted/, /received/, /processed/], -1);
    const rows = dateIndex >= 0
      ? allRows.filter((row) => toIsoDate(row[dateIndex]) === EFFECTIVE_DATE)
      : allRows;

    if (process.env.HARVEST_DEBUG_ROWS === '1') {
      console.log(`Headers: ${JSON.stringify(headers)}`);
      console.log(`Column indexes: ${JSON.stringify({ projectIndex, bankIndex, pagesIndex, dateIndex })}`);
      console.log(`Rows collected across pagination: ${allRows.length}`);
      console.log(`Rows after date filter: ${rows.length}`);
      console.log(`Sample rows: ${JSON.stringify(allRows.slice(0, 5), null, 2)}`);
    }

    const unsupported = [];

    for (const row of rows) {
      if (!row || row.length === 0) continue;

      const name = row[projectIndex] || '';
      const bank = row[bankIndex] || '';
      const pages = row[pagesIndex] || '';

      if (!name && !bank && !pages) continue;

      const candidate = `${name} ${bank}`.toLowerCase();

      // Keep this simple and explicit. If you want stricter filtering later, replace this.
      const isSupported = supportedKeywords.some((k) => candidate.includes(k));

      if (!isSupported) {
        unsupported.push({
          bank: bank || 'UnknownBank',
          project: name || 'UnknownProject',
          pages,
          reason: 'Unsupported bank discovered during harvest'
        });
      }
    }

    console.log(`Unsupported banks found: ${unsupported.length}`);

    if (process.env.HARVEST_DEBUG_ROWS === '1') {
      const pagerHtml = await page.evaluate(() => {
        const pager = document.querySelector('.k-pager-wrap, .k-pager, [class*="pager"]');
        return pager ? pager.outerHTML.slice(0, 4000) : null;
      });
      console.log(`Pager HTML: ${pagerHtml}`);
    }

    // The grid renders every row in one table (pager next/last is non-functional, data-kendo-page="NaN"),
    // so locate rows directly via DOM text search instead of clicking pagination controls.
    async function locateProjectRow(projectName) {
      const handle = await page.evaluateHandle((targetName) => {
        const isVisibleDataRow = (tr) => {
          const style = window.getComputedStyle(tr);
          return style.display !== 'none'
            && style.visibility !== 'hidden'
            && !tr.classList.contains('k-footer-template')
            && !tr.classList.contains('k-group-footer')
            && !tr.classList.contains('k-grouping-row');
        };

        const rowTables = Array.from(document.querySelectorAll('table'))
          .map((table) => ({ table, rows: Array.from(table.querySelectorAll('tbody tr')).filter(isVisibleDataRow) }))
          .filter((entry) => entry.rows.length > 0)
          .sort((left, right) => right.rows.length - left.rows.length);

        const rows = rowTables[0]?.rows || [];
        const needle = targetName.toLowerCase();
        return rows.find((tr) => (tr.textContent || '').toLowerCase().includes(needle)) || null;
      }, projectName);

      const element = handle.asElement();
      if (!element) {
        await handle.dispose();
        return null;
      }
      return element;
    }

    const manifestItems = [];
    for (const item of unsupported) {
      const bankDir = path.join(pdfRoot, sanitize(item.bank));
      fs.mkdirSync(bankDir, { recursive: true });

      let savedPdfPath = null;

      // Re-establish the filtered grid fresh for every project; a prior detail-page visit
      // plus history navigation can otherwise leave the date filter cleared or reset.
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
      await page.waitForSelector(`text=${report}`, { timeout: 60000 }).catch(() => {});
      await openFilteredDigitalReport();

      const row = await locateProjectRow(item.project);

      if (row) {
        await row.click({ timeout: 20000 });
        await page.waitForTimeout(3000);

        const downloadPromise = page.waitForEvent('download', { timeout: 60000 }).catch(() => null);

        const button = page.locator('button, a, [role="button"]').filter({
          hasText: /download|pdf|export/i
        }).first();

        const buttonVisible = await button.isVisible().catch(() => false);

        if (buttonVisible) {
          await button.click({ timeout: 20000 });
          const download = await downloadPromise;
          if (download) {
            const actualPath = path.join(bankDir, download.suggestedFilename() || `${sanitize(item.project)}.pdf`);
            await download.saveAs(actualPath);
            savedPdfPath = actualPath;
            console.log(`Saved PDF: ${actualPath}`);
          }
        } else {
          console.warn(`PDF button not found for project: ${item.project}`);
        }

        await row.dispose().catch(() => {});
      } else {
        console.warn(`Project row not found in report grid: ${item.project}`);
      }

      manifestItems.push({
        bank: item.bank,
        project: item.project,
        pages: item.pages,
        pdf_saved: savedPdfPath ? savedPdfPath.replace(process.cwd() + '\\', '').replace(/\\/g, '/') : null,
        reason: item.reason
      });
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const manifestPath = path.join(outputDir, `new_banks_manifest_${timestamp}.json`);

    const manifest = {
      stage: 'statement-harvester',
      runtime: 'github-copilot',
      status: 'COMPLETED',
      source: url,
      report,
      report_date: EFFECTIVE_DATE,
      excel_saved: excelPath.replace(process.cwd() + '\\', '').replace(/\\/g, '/'),
      extracted_at: new Date().toISOString(),
      total_projects_reviewed: rows.length,
      unsupported_banks_count: manifestItems.length,
      unsupported_banks: manifestItems,
      generated_at: new Date().toISOString()
    };

    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    console.log(`Manifest created: ${manifestPath}`);

    console.log('Stage 1 complete.');
  } catch (err) {
    console.error('Stage 1 failed.');
    console.error(err.message || err);
    process.exit(1);
  } finally {
    if (browser) {
      console.log('Browser remains open for you to inspect. Press Ctrl+C to close it.');
      // Keep it open so you can manually approve the Cloudflare/MFA flow if needed.
      // Uncomment below if you want the script to close immediately:
      // await browser.close();
    }
  }
})();

function sanitize(value) {
  return String(value || 'Unknown')
    .replace(/[<>:"/\\|?*]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 80) || 'Unknown';
}