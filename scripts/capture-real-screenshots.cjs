#!/usr/bin/env node
/**
 * Capture REAL EcoTrace AI UI screenshots into docs/screenshots/.
 * Requires: web+api up, Playwright in NODE_PATH (e.g. /tmp/ecotrace-shots/node_modules).
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'docs', 'screenshots');
const WEB = process.env.WEB_URL || 'http://127.0.0.1:4200';
const API = process.env.API_URL || 'http://127.0.0.1:8000';
const EMAIL = process.env.DEMO_EMAIL || 'admin@ecotrace.dev';
const PASSWORD = process.env.DEMO_PASSWORD || 'EcoTraceAdmin!2024';
const VIEWPORT = { width: 1440, height: 900 };

const GROUPS = {
  '01-intro': 'Intro & Overview',
  '02-platform': 'Platform',
  '03-organization': 'Organization',
  '04-data-carbon': 'Data & Carbon',
  '05-analytics': 'Analytics',
  '06-product-lca': 'Product & LCA',
  '07-ai-automation': 'AI & Automation',
  '08-security-ops': 'Security & Ops',
  '09-infra-demo': 'Infrastructure & Demo',
};

/** @type {{ group: string, file: string, title: string, url: string, auth?: boolean }[]} */
const SHOTS = [
  { group: '01-intro', file: '01-sign-in.png', title: 'Sign In', url: `${WEB}/login`, auth: false },
  { group: '01-intro', file: '02-document-purpose.png', title: 'Document Purpose', url: `${WEB}/login`, auth: false },
  { group: '01-intro', file: '03-about-the-platform.png', title: 'About the Platform', url: `${WEB}/login`, auth: false },
  { group: '01-intro', file: '04-overview.png', title: 'Overview', url: `${WEB}/app/dashboard`, auth: true },

  { group: '02-platform', file: '01-platform-architecture.png', title: 'Platform Architecture', url: `${WEB}/app/dashboard`, auth: true },
  { group: '02-platform', file: '02-technology-stack.png', title: 'Technology Stack', url: `${WEB}/app/system/health`, auth: true },
  { group: '02-platform', file: '03-user-roles.png', title: 'User Roles', url: `${WEB}/app/profile`, auth: true },

  { group: '03-organization', file: '01-dashboard.png', title: 'Dashboard', url: `${WEB}/app/dashboard`, auth: true },
  { group: '03-organization', file: '02-organization-management.png', title: 'Organization Management', url: `${WEB}/app/organizations`, auth: true },
  { group: '03-organization', file: '03-users-and-roles.png', title: 'Users and Roles', url: `${WEB}/app/profile`, auth: true },
  { group: '03-organization', file: '04-facility-management.png', title: 'Facility Management', url: `${WEB}/app/facilities`, auth: true },
  { group: '03-organization', file: '05-operational-assets.png', title: 'Operational Assets', url: `${WEB}/app/equipment`, auth: true },

  { group: '04-data-carbon', file: '01-activity-data.png', title: 'Activity Data Management', url: `${WEB}/app/activity-data`, auth: true },
  { group: '04-data-carbon', file: '02-csv-import.png', title: 'CSV Data Import', url: `${WEB}/app/data-imports`, auth: true },
  { group: '04-data-carbon', file: '03-emission-factors.png', title: 'Emission Factor Management', url: `${WEB}/app/emission-factors`, auth: true },
  { group: '04-data-carbon', file: '04-carbon-inventory.png', title: 'Carbon Inventory', url: `${WEB}/app/carbon-inventories`, auth: true },
  { group: '04-data-carbon', file: '05-calculation-engine.png', title: 'Carbon Calculation Engine', url: `${WEB}/app/carbon-inventories`, auth: true },

  { group: '05-analytics', file: '01-analytics-reporting.png', title: 'Analytics and Reporting', url: `${WEB}/app/analytics`, auth: true },
  { group: '05-analytics', file: '02-sustainability-targets.png', title: 'Sustainability Targets', url: `${WEB}/app/planning/targets`, auth: true },
  { group: '05-analytics', file: '03-scenario-analysis.png', title: 'Scenario Analysis', url: `${WEB}/app/planning/scenarios`, auth: true },

  { group: '06-product-lca', file: '01-product-management.png', title: 'Product Management', url: `${WEB}/app/products`, auth: true },
  { group: '06-product-lca', file: '02-supplier-management.png', title: 'Supplier Management', url: `${WEB}/app/suppliers`, auth: true },
  { group: '06-product-lca', file: '03-material-management.png', title: 'Material Management', url: `${WEB}/app/materials`, auth: true },
  { group: '06-product-lca', file: '04-bill-of-materials.png', title: 'Bill of Materials (BOM)', url: `${WEB}/app/products`, auth: true },
  { group: '06-product-lca', file: '05-lca.png', title: 'Life Cycle Assessment (LCA)', url: `${WEB}/app/lca-studies`, auth: true },
  { group: '06-product-lca', file: '06-pcf.png', title: 'Product Carbon Footprint (PCF)', url: `${WEB}/app/product-carbon-footprints`, auth: true },
  { group: '06-product-lca', file: '07-dpp.png', title: 'Digital Product Passport (DPP)', url: `${WEB}/app/digital-product-passports`, auth: true },

  { group: '07-ai-automation', file: '01-ai-copilot.png', title: 'AI Sustainability Copilot', url: `${WEB}/app/ai`, auth: true },
  { group: '07-ai-automation', file: '02-enterprise-search.png', title: 'Enterprise Document Search', url: `${WEB}/app/ai/search`, auth: true },
  { group: '07-ai-automation', file: '03-document-management.png', title: 'Document Management', url: `${WEB}/app/ai/documents`, auth: true },
  { group: '07-ai-automation', file: '04-automation.png', title: 'Automation Management', url: `${WEB}/app/automation`, auth: true },
  { group: '07-ai-automation', file: '05-ai-agents.png', title: 'AI Agents', url: `${WEB}/app/agents`, auth: true },
  { group: '07-ai-automation', file: '06-forecasting.png', title: 'Forecasting', url: `${WEB}/app/forecasts`, auth: true },
  { group: '07-ai-automation', file: '07-anomaly-detection.png', title: 'Anomaly Detection', url: `${WEB}/app/anomalies`, auth: true },
  { group: '07-ai-automation', file: '08-data-quality.png', title: 'Data Quality Management', url: `${WEB}/app/data-quality`, auth: true },
  { group: '07-ai-automation', file: '09-alerts.png', title: 'Alert Center', url: `${WEB}/app/alerts`, auth: true },
  { group: '07-ai-automation', file: '10-notifications.png', title: 'Notification Center', url: `${WEB}/app/notifications`, auth: true },
  { group: '07-ai-automation', file: '11-scheduled-reports.png', title: 'Scheduled Reports', url: `${WEB}/app/scheduled-reports`, auth: true },
  { group: '07-ai-automation', file: '12-supplier-monitoring.png', title: 'Supplier Sustainability Monitoring', url: `${WEB}/app/supplier-monitoring`, auth: true },
  { group: '07-ai-automation', file: '13-regulatory.png', title: 'Regulatory Intelligence', url: `${WEB}/app/regulatory-intelligence`, auth: true },

  { group: '08-security-ops', file: '01-system-security.png', title: 'System Security', url: `${WEB}/app/profile`, auth: true },
  { group: '08-security-ops', file: '02-system-monitoring.png', title: 'System Monitoring and Operations', url: `${WEB}/app/system/health`, auth: true },

  { group: '09-infra-demo', file: '01-api-infrastructure.png', title: 'API Infrastructure', url: `${API}/docs`, auth: false },
  { group: '09-infra-demo', file: '02-backup-restore.png', title: 'Backup and Restore', url: `${WEB}/app/system/operations`, auth: true },
  { group: '09-infra-demo', file: '03-deployment.png', title: 'Deployment Architecture', url: `${WEB}/app/system/health`, auth: true },
  { group: '09-infra-demo', file: '04-demo-scenario.png', title: 'Demo Scenario', url: `${WEB}/app/dashboard`, auth: true },
  { group: '09-infra-demo', file: '05-conclusion.png', title: 'Conclusion', url: `${WEB}/app/dashboard`, auth: true },
];

async function apiLogin() {
  const res = await fetch(`${API}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  });
  if (!res.ok) {
    throw new Error(`API login failed: ${res.status} ${await res.text()}`);
  }
  return res.json();
}

async function fetchOrgId(accessToken) {
  const res = await fetch(`${API}/api/v1/auth/me/organizations`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    throw new Error(`orgs failed: ${res.status}`);
  }
  const orgs = await res.json();
  return orgs[0]?.organizationId || null;
}

async function injectSession(page, tokens, orgId) {
  const me = {
    id: tokens.user.id,
    email: tokens.user.email,
    fullName: tokens.user.fullName,
    isActive: true,
    isVerified: true,
    roles: tokens.user.roles,
    lastLoginAt: null,
  };
  await page.goto(`${WEB}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.evaluate(
    ({ access, refresh, user, orgId: oid }) => {
      localStorage.setItem('ecotrace.accessToken', access);
      localStorage.setItem('ecotrace.refreshToken', refresh);
      localStorage.setItem('ecotrace.user', JSON.stringify(user));
      if (oid) localStorage.setItem('ecotrace.selectedOrganizationId', oid);
    },
    { access: tokens.accessToken, refresh: tokens.refreshToken, user: me, orgId },
  );
}

async function settle(page) {
  await page.waitForLoadState('domcontentloaded', { timeout: 30000 }).catch(() => null);
  await page.waitForTimeout(1200);
  await page
    .waitForFunction(
      () => {
        const spinners = document.querySelectorAll(
          'mat-spinner, mat-progress-spinner, .mat-mdc-progress-spinner',
        );
        return [...spinners].every((el) => {
          const style = window.getComputedStyle(el);
          return (
            style.display === 'none' ||
            style.visibility === 'hidden' ||
            Number(style.opacity) === 0 ||
            el.getAttribute('mode') === 'determinate'
          );
        });
      },
      { timeout: 12000 },
    )
    .catch(() => null);
  await page.waitForTimeout(900);
}

async function main() {
  for (const g of Object.keys(GROUPS)) {
    fs.mkdirSync(path.join(OUT, g), { recursive: true });
  }

  const tokens = await apiLogin();
  const orgId = await fetchOrgId(tokens.accessToken);
  console.log('API login ok:', tokens.user.email, 'org:', orgId);

  const browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.CHROME_PATH ||
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 1,
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();

  let authed = false;
  const index = [];

  for (const shot of SHOTS) {
    process.stdout.write(`→ ${shot.group}/${shot.file} ... `);
    try {
      if (shot.auth) {
        if (!authed) {
          await injectSession(page, tokens, orgId);
          await page.goto(`${WEB}/app/dashboard`, { waitUntil: 'domcontentloaded', timeout: 60000 });
          await settle(page);
          if (!page.url().includes('/app')) {
            throw new Error(`session inject failed, url=${page.url()}`);
          }
          authed = true;
        }
        await page.goto(shot.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      } else if (shot.url.includes('/docs')) {
        await page.goto(shot.url, { waitUntil: 'load', timeout: 60000 });
        await page.waitForTimeout(4000);
      } else {
        await page.goto(shot.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      }
      await settle(page);
      const dest = path.join(OUT, shot.group, shot.file);
      await page.screenshot({ path: dest, fullPage: false });
      console.log('ok');
      index.push({
        group: shot.group,
        groupTitle: GROUPS[shot.group],
        file: shot.file,
        title: shot.title,
        rel: `docs/screenshots/${shot.group}/${shot.file}`,
      });
    } catch (err) {
      console.log('FAIL', err.message);
    }
  }

  fs.writeFileSync(path.join(OUT, 'index.json'), JSON.stringify(index, null, 2));
  await browser.close();
  console.log(`\nDone: ${index.length}/${SHOTS.length} real screenshots → ${OUT}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
