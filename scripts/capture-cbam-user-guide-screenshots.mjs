#!/usr/bin/env node
/**
 * Capture real CBAM/SKDM User Guide screenshots from the local review app.
 * Credentials via env only — never written to docs.
 * Optional API_REWRITE redirects localhost:8000 API calls without editing environment.ts.
 */
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'docs', 'cbam', 'user-guide', 'assets');
const WEB = process.env.WEB_URL || 'http://127.0.0.1:4201';
const API_REWRITE = (process.env.API_REWRITE || '').replace(/\/$/, '');
const EMAIL = process.env.CBAM_REVIEW_EMAIL || 'cbam.reviewer@ecotrace.dev';
const PASSWORD = process.env.CBAM_REVIEW_PASSWORD || '';
const BINDING =
  process.env.CBAM_REVIEW_BINDING_ID || '0d79daa8-9fdc-40ea-8e60-2e8430d98fa1';
const EMPTY_BINDING =
  process.env.CBAM_EMPTY_BINDING_ID || '8123d235-63d4-489a-ae49-5bb2b85ff03a';
const LOCKED_BINDING = process.env.CBAM_LOCKED_BINDING_ID || '';
const VIEWPORT = { width: 1440, height: 900 };

if (!PASSWORD) {
  console.error('Set CBAM_REVIEW_PASSWORD');
  process.exit(1);
}

fs.mkdirSync(OUT, { recursive: true });

const PERIOD_TABS = [
  ['overview', '07-reporting-period-detail'],
  ['Product Profiles', '04-product-profiles'],
  ['Production', '05-production'],
  ['Monthly allocation data', '05b-monthly-allocation-data'],
  ['Activities', '06-activities'],
  ['Direct Emissions', '07-direct-emissions'],
  ['Indirect Emissions', '08-indirect-emissions'],
  ['Processes', '09-processes'],
  ['Purchased Inputs', '10-purchased-inputs'],
  ['Purchased Precursors', '10b-purchased-precursors'],
  ['Product Results', '11-product-results'],
  ['Allocation', '12-allocation'],
  ['Direct Emissions Allocation', '12b-direct-emissions-allocation'],
  ['Indirect Emissions Allocation', '12c-indirect-emissions-allocation'],
  ['Factors', '13-factors'],
  ['Calculation', '13b-calculation'],
  ['Report / Excel', '14-report-excel'],
];

async function shot(page, name) {
  const file = path.join(OUT, `${name}.png`);
  await page.waitForTimeout(500);
  await page.screenshot({ path: file, fullPage: false });
  console.log('saved', name, fs.statSync(file).size);
}

async function clickTab(page, label) {
  const tab = page.getByRole('tab', { name: label, exact: true });
  if (await tab.count()) {
    await tab.first().click({ timeout: 8000 });
    await page.waitForTimeout(800);
    return true;
  }
  const link = page.getByRole('link', { name: label, exact: true });
  if (await link.count()) {
    await link.first().click({ timeout: 8000 });
    await page.waitForTimeout(800);
    return true;
  }
  const text = page.locator(`text=${label}`).first();
  if (await text.count()) {
    await text.click({ timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(800);
    return true;
  }
  console.warn('tab_missing', label);
  return false;
}

async function ensureOrgContext(page) {
  // Full page reload can trip orgContextGuard; seed org via SPA nav when possible.
  await page.goto(`${WEB}/app/organizations`, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(600);
  const row = page.locator('table tbody tr, .mat-mdc-row, a[href*="organizations"]').first();
  if (await row.count()) {
    await row.click({ timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(500);
  }
}

async function gotoCbam(page, route) {
  await ensureOrgContext(page);
  // Prefer in-app navigation via SKDM link when present
  const skdm = page.getByRole('link', { name: /SKDM|CBAM/i }).first();
  if (await skdm.count()) {
    await skdm.click().catch(() => {});
    await page.waitForTimeout(500);
  }
  await page.goto(`${WEB}${route}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1200);
}

async function main() {
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.PW_CHANNEL || undefined,
  });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();

  if (API_REWRITE) {
    await page.route('**/localhost:8000/**', async (route) => {
      const url = route.request().url().replace('http://localhost:8000', API_REWRITE);
      await route.continue({ url });
    });
    await page.route('**/127.0.0.1:8000/**', async (route) => {
      const url = route.request().url().replace('http://127.0.0.1:8000', API_REWRITE);
      await route.continue({ url });
    });
    console.log('api_rewrite', API_REWRITE);
  }

  // Login
  await page.goto(`${WEB}/login`, { waitUntil: 'networkidle' });
  await page.getByLabel('Email').fill(EMAIL);
  await page.getByLabel('Password').fill(PASSWORD);
  await shot(page, '01-login');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL(/\/app\//, { timeout: 30000 });
  await page.waitForTimeout(1000);
  await shot(page, '02-dashboard');

  await ensureOrgContext(page);
  await shot(page, '03-organizations');

  await gotoCbam(page, '/app/cbam');
  await shot(page, '02b-skdm-shell');

  await gotoCbam(page, '/app/cbam/installations');
  await shot(page, '04-installations-list');

  const instLink = page.locator('a[href*="/app/cbam/installations/"]').first();
  if (await instLink.count()) {
    await instLink.click();
    await page.waitForTimeout(1000);
    await shot(page, '05-installation-detail');
  }

  await gotoCbam(page, '/app/cbam/periods');
  await shot(page, '06-reporting-periods-list');

  await gotoCbam(page, `/app/cbam/periods/${BINDING}`);
  await shot(page, '07-reporting-period-detail');

  for (const [label, file] of PERIOD_TABS) {
    if (label === 'overview') continue;
    const ok = await clickTab(page, label);
    if (!ok) {
      if (label.includes('Monthly')) {
        await clickTab(page, 'Production');
        await clickTab(page, label);
      } else if (label.includes('Precursor')) {
        await clickTab(page, 'Purchased Inputs');
        await page.waitForTimeout(500);
        // scroll precursors panel if present
        const prec = page.locator('text=Precursor').first();
        if (await prec.count()) await prec.scrollIntoViewIfNeeded().catch(() => {});
      } else if (
        label.includes('Direct Emissions Allocation') ||
        label.includes('Indirect Emissions Allocation')
      ) {
        await clickTab(page, 'Allocation');
        await page.waitForTimeout(500);
        const sub = page.locator(`text=${label}`).first();
        if (await sub.count()) await sub.scrollIntoViewIfNeeded().catch(() => {});
      }
    }
    await shot(page, file);
  }

  // Official Excel sections
  await clickTab(page, 'Report / Excel');
  await page.waitForTimeout(800);
  const official = page.locator('text=/Official Excel|Official SEE|Readiness/i').first();
  if (await official.count()) {
    await official.scrollIntoViewIfNeeded();
    await shot(page, '14b-official-excel-readiness');
  }
  const history = page.locator('text=/History|Previous exports|Export history/i').first();
  if (await history.count()) {
    await history.scrollIntoViewIfNeeded().catch(() => {});
    await shot(page, '14c-official-excel-history');
  }
  const completed = page.locator('text=/Download|COMPLETED|Completed|formula parity/i').first();
  if (await completed.count()) {
    await completed.scrollIntoViewIfNeeded().catch(() => {});
    await shot(page, '14e-official-excel-completed-download');
  } else {
    // Still capture readiness area as best-effort completed/downloadable evidence when history has a row
    const histRow = page.locator('table tbody tr, .mat-mdc-row').first();
    if (await histRow.count()) {
      await histRow.scrollIntoViewIfNeeded().catch(() => {});
      await shot(page, '14e-official-excel-completed-download');
    }
  }
  const internal = page.locator('text=/Internal Excel|Internal workbook/i').first();
  if (await internal.count()) {
    await internal.scrollIntoViewIfNeeded().catch(() => {});
    await shot(page, '14d-internal-excel');
  }

  // Empty period
  await gotoCbam(page, `/app/cbam/periods/${EMPTY_BINDING}`);
  await shot(page, '15-period-empty-state');
  await shot(page, '17-state-empty');

  // Incomplete (review period still in data_collection)
  await gotoCbam(page, `/app/cbam/periods/${BINDING}`);
  await shot(page, '17-state-incomplete');

  // Ready-ish: Official readiness panel
  await clickTab(page, 'Report / Excel');
  await page.waitForTimeout(600);
  await shot(page, '17-state-ready');

  // Current/history
  const hist2 = page.locator('text=/History|Export history/i').first();
  if (await hist2.count()) {
    await hist2.scrollIntoViewIfNeeded().catch(() => {});
    await shot(page, '17-state-history');
  }

  // Try open a create/edit dialog to capture validation error (required field empty)
  await clickTab(page, 'Activities');
  const addBtn = page.getByRole('button', { name: /Add|New|Create/i }).first();
  if (await addBtn.count()) {
    await addBtn.click().catch(() => {});
    await page.waitForTimeout(500);
    const save = page.getByRole('button', { name: /Save|Create|Add/i }).last();
    if (await save.count()) {
      await save.click().catch(() => {});
      await page.waitForTimeout(700);
      await shot(page, '17-state-validation-error');
      await page.keyboard.press('Escape').catch(() => {});
    }
  }

  // Unbalanced / stale / failed — capture visible banners/chips if present on Product Results / Allocation / Report
  for (const [tab, file, re] of [
    ['Product Results', '17-state-unbalanced', /unbalanc|balance|not balanced/i],
    ['Product Results', '17-state-stale', /stale|out of date|recalculate/i],
    ['Report / Excel', '17-state-failed-execution', /failed|error|unavailable|RECALCULATION/i],
  ]) {
    await clickTab(page, tab);
    await page.waitForTimeout(600);
    const el = page.locator(`text=${re}`).first();
    if (await el.count()) {
      await el.scrollIntoViewIfNeeded().catch(() => {});
    }
    await shot(page, file);
  }

  // Locked period (disposable binding if provided)
  if (LOCKED_BINDING) {
    await gotoCbam(page, `/app/cbam/periods/${LOCKED_BINDING}`);
    await shot(page, '17-state-locked');
  } else {
    // Look for Lock action on current period and capture locked chip if already locked
    await gotoCbam(page, `/app/cbam/periods/${BINDING}`);
    const lockChip = page.locator('text=/Locked|lock/i').first();
    if (await lockChip.count()) {
      await shot(page, '17-state-locked');
    }
  }

  // View-only: viewer login
  const viewerPass = process.env.CBAM_VIEWER_PASSWORD || PASSWORD;
  const viewerEmail = process.env.CBAM_VIEWER_EMAIL || 'cbam.viewer@ecotrace.dev';
  await context.clearCookies();
  await page.evaluate(() => localStorage.clear());
  await page.goto(`${WEB}/login`, { waitUntil: 'networkidle' });
  await page.getByLabel('Email').fill(viewerEmail);
  await page.getByLabel('Password').fill(viewerPass);
  await page.getByRole('button', { name: 'Sign in' }).click();
  try {
    await page.waitForURL(/\/app\//, { timeout: 20000 });
    await gotoCbam(page, `/app/cbam/periods/${BINDING}`);
    await shot(page, '16-view-only-period');
    await shot(page, '17-state-view-only');
  } catch (e) {
    console.warn('viewer_login_skipped', String(e).slice(0, 160));
  }

  await browser.close();
  const files = fs.readdirSync(OUT).filter((f) => f.endsWith('.png'));
  const sizes = files.map((f) => ({ f, kb: Math.round(fs.statSync(path.join(OUT, f)).size / 1024) }));
  console.log(JSON.stringify({ captured: files.length, sizes }, null, 2));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
