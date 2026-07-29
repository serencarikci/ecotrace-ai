#!/usr/bin/env python3
"""Generate EcoTrace docs screenshots (English UI mockups) via Chrome headless."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

GROUPS = {
    "01-intro": "Intro & Overview",
    "02-platform": "Platform",
    "03-organization": "Organization",
    "04-data-carbon": "Data & Carbon",
    "05-analytics": "Analytics",
    "06-product-lca": "Product & LCA",
    "07-ai-automation": "AI & Automation",
    "08-security-ops": "Security & Ops",
    "09-infra-demo": "Infrastructure & Demo",
}

# (group, filename, title, kind, blurb, nav_hint)
SHOTS: list[tuple[str, str, str, str, str, str]] = [
    ("01-intro", "01-sign-in.png", "Sign In", "login", "Secure sign-in with email and password. Uses JWT and refresh tokens.", "Sign in"),
    ("01-intro", "02-document-purpose.png", "Document Purpose", "doc", "This guide explains EcoTrace AI features and screens. It is a reference portfolio app, not a certification product.", "Docs"),
    ("01-intro", "03-about-the-platform.png", "About the Platform", "doc", "EcoTrace AI combines carbon accounting, LCA/PCF, digital product passports, analytics, targets, grounded AI, and approved automation.", "Overview"),
    ("01-intro", "04-overview.png", "Overview", "app", "One system of record from operations to carbon inventories, product LCA, AI, and automation.", "Dashboard"),
    ("02-platform", "01-platform-architecture.png", "Platform Architecture", "arch", "FastAPI API · Angular 19 Web · PostgreSQL (+ pgvector) · Scheduler. LLMs never access the database.", "Architecture"),
    ("02-platform", "02-technology-stack.png", "Technology Stack", "doc", "Python 3.12, FastAPI, SQLAlchemy, Alembic · Angular Material · PostgreSQL 16 · Docker Compose · GitHub Actions.", "Stack"),
    ("02-platform", "03-user-roles.png", "User Roles", "app", "system_admin · organization_admin · analyst · viewer — organization-scoped RBAC.", "Profile"),
    ("03-organization", "01-dashboard.png", "Dashboard", "app", "Command center with quick links to facilities, carbon, products, and intelligence.", "Dashboard"),
    ("03-organization", "02-organization-management.png", "Organization Management", "app", "Multi-tenant organizations, memberships, and selected org context.", "Organizations"),
    ("03-organization", "03-users-and-roles.png", "Users and Roles", "app", "Identity, roles, and profile. Session and permission boundaries.", "Profile"),
    ("03-organization", "04-facility-management.png", "Facility Management", "app", "Production sites, warehouses, and operational facilities.", "Facilities"),
    ("03-organization", "05-operational-assets.png", "Operational Assets", "app", "Equipment, production lines, and data sources.", "Equipment"),
    ("04-data-carbon", "01-activity-data.png", "Activity Data Management", "app", "Auditable activity records, reporting periods, and approval flows.", "Activity Data"),
    ("04-data-carbon", "02-csv-import.png", "CSV Data Import", "app", "CSV import wizard with validation and row-level errors.", "Data Imports"),
    ("04-data-carbon", "03-emission-factors.png", "Emission Factor Management", "app", "Factor sources, preferences, and matching rules.", "Emission Factors"),
    ("04-data-carbon", "04-carbon-inventory.png", "Carbon Inventory", "app", "Organization emission inventories, scopes, and snapshots.", "Carbon Inventories"),
    ("04-data-carbon", "05-calculation-engine.png", "Carbon Calculation Engine", "doc", "Activity × factor → scope results. Validation and repeatable calculation runs.", "Engine"),
    ("05-analytics", "01-analytics-reporting.png", "Analytics and Reporting", "app", "Executive analytics, trends, categories, and decision support.", "Analytics"),
    ("05-analytics", "02-sustainability-targets.png", "Sustainability Targets", "app", "Baselines, absolute/intensity targets, and initiatives.", "Targets"),
    ("05-analytics", "03-scenario-analysis.png", "Scenario Analysis", "app", "What-if scenarios and roadmap comparisons.", "Scenarios"),
    ("06-product-lca", "01-product-management.png", "Product Management", "app", "Products, variants, and batch records.", "Products"),
    ("06-product-lca", "02-supplier-management.png", "Supplier Management", "app", "Supplier master data and links.", "Suppliers"),
    ("06-product-lca", "03-material-management.png", "Material Management", "app", "Material catalog and attributes.", "Materials"),
    ("06-product-lca", "04-bill-of-materials.png", "Bill of Materials (BOM)", "app", "BOM lines that describe the product component tree.", "BOM"),
    ("06-product-lca", "05-lca.png", "Life Cycle Assessment (LCA)", "app", "LCA studies, inventory, and results screens.", "LCA Studies"),
    ("06-product-lca", "06-pcf.png", "Product Carbon Footprint (PCF)", "app", "Product-level carbon footprint calculations.", "PCF"),
    ("06-product-lca", "07-dpp.png", "Digital Product Passport (DPP)", "app", "Passport versions, preview, and public publish.", "Passports"),
    ("07-ai-automation", "01-ai-copilot.png", "AI Sustainability Copilot", "app", "Grounded RAG answers with citations and confidence scores.", "AI Copilot"),
    ("07-ai-automation", "02-enterprise-search.png", "Enterprise Document Search", "app", "Hybrid search: keywords plus vectors.", "Enterprise Search"),
    ("07-ai-automation", "03-document-management.png", "Document Management", "app", "Knowledge upload, chunking, and access control.", "Knowledge Docs"),
    ("07-ai-automation", "04-automation.png", "Automation Management", "app", "Rules, triggers, pause, and run actions.", "Automation"),
    ("07-ai-automation", "05-ai-agents.png", "AI Agents", "app", "Allowlisted tools and human-approved write actions.", "AI Agents"),
    ("07-ai-automation", "06-forecasting.png", "Forecasting", "app", "Statistical projections and target trajectory labels.", "Forecasts"),
    ("07-ai-automation", "07-anomaly-detection.png", "Anomaly Detection", "app", "Z-score, IQR, percent change, and missing-data checks.", "Anomalies"),
    ("07-ai-automation", "08-data-quality.png", "Data Quality Management", "app", "Quality rules, findings, and monitoring.", "Data Quality"),
    ("07-ai-automation", "09-alerts.png", "Alert Center", "app", "Operational alerts and severity levels.", "Alerts"),
    ("07-ai-automation", "10-notifications.png", "Notification Center", "app", "In-app notifications and preferences.", "Notifications"),
    ("07-ai-automation", "11-scheduled-reports.png", "Scheduled Reports", "app", "Planned report generation and delivery.", "Scheduled Reports"),
    ("07-ai-automation", "12-supplier-monitoring.png", "Supplier Sustainability Monitoring", "app", "Internal scores (not certified) and monitoring.", "Supplier Monitoring"),
    ("07-ai-automation", "13-regulatory.png", "Regulatory Intelligence", "app", "Regulatory document support — not legal advice.", "Regulatory"),
    ("08-security-ops", "01-system-security.png", "System Security", "doc", "Org isolation, RBAC, CSP, refresh rotation, agent allowlists, audit log.", "Security"),
    ("08-security-ops", "02-system-monitoring.png", "System Monitoring and Operations", "app", "Health checks, job monitoring, and operations panels.", "Health"),
    ("09-infra-demo", "01-api-infrastructure.png", "API Infrastructure", "api", "OpenAPI / Swagger, versioned /api/v1, camelCase contracts.", "API Docs"),
    ("09-infra-demo", "02-backup-restore.png", "Backup and Restore", "doc", "backup.sh · verify-backup.sh · restore.sh — PostgreSQL backups.", "Backup"),
    ("09-infra-demo", "03-deployment.png", "Deployment Architecture", "arch", "Compose (dev/prod) · API + Web + Postgres + Scheduler · weak secrets rejected.", "Deploy"),
    ("09-infra-demo", "04-demo-scenario.png", "Demo Scenario", "doc", "Seed users: admin / orgadmin / analyst / viewer · demo org · EcoBottle · DPP · AI knowledge.", "Demo"),
    ("09-infra-demo", "05-conclusion.png", "Conclusion", "doc", "The platform is complete. An end-to-end sustainability intelligence reference platform.", "Complete"),
]


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def html_for(title: str, kind: str, blurb: str, nav: str) -> str:
    nav_items = [
        "Dashboard",
        "Organizations",
        "Facilities",
        "Activity Data",
        "Carbon Inventories",
        "Analytics",
        "Products",
        "AI Copilot",
        "Agents",
        "Alerts",
    ]
    nav_html = "".join(
        f'<a class="{"active" if n.lower() in nav.lower() or title.lower().find(n.split()[0].lower())>=0 else ""}">{esc(n)}</a>'
        for n in nav_items
    )

    if kind == "login":
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&display=swap');
*{{box-sizing:border-box}} body{{margin:0;font-family:Sora,system-ui,sans-serif;min-height:100vh;display:grid;place-items:center;
background:linear-gradient(120deg,rgba(15,42,31,.88),rgba(27,67,50,.72)),#0f2a1f;color:#f4faf6;padding:32px}}
.stage{{width:min(440px,100%);display:grid;gap:20px}}
.brand{{font-size:28px;font-weight:700;letter-spacing:-.04em;margin:0}}
.h{{font-size:18px;font-weight:500;margin:0;opacity:.92}}
.lede{{margin:0;opacity:.78;font-size:14px;line-height:1.55}}
.form{{background:#fff;color:#14212b;border-radius:20px;padding:22px;display:grid;gap:12px}}
.form h2{{margin:0;font-size:16px;color:#0f2a1f}}
.field{{border:1px solid #d5e0da;border-radius:10px;padding:12px 14px;color:#5c6b73;font-size:14px}}
.btn{{background:#2d6a4f;color:#fff;border:0;border-radius:12px;height:48px;font-weight:600;font-size:15px}}
.tag{{font-size:11px;letter-spacing:.08em;text-transform:uppercase;opacity:.7}}
</style></head><body>
<div class="stage">
  <p class="tag">EcoTrace AI</p>
  <p class="brand">{esc(title)}</p>
  <p class="h">Sustainability intelligence, grounded in your data.</p>
  <p class="lede">{esc(blurb)}</p>
  <div class="form">
    <h2>Sign in</h2>
    <div class="field">admin@ecotrace.dev</div>
    <div class="field">••••••••••••</div>
    <button class="btn">Sign in</button>
  </div>
</div>
</body></html>"""

    if kind in {"doc", "arch", "api"}:
        chips = ""
        if kind == "arch":
            chips = """
            <div class="chips">
              <span>API · FastAPI</span><span>Web · Angular 19</span><span>DB · PostgreSQL</span><span>Jobs · Scheduler</span>
            </div>"""
        elif kind == "api":
            chips = """
            <div class="chips">
              <span>GET /health</span><span>POST /api/v1/auth/login</span><span>OpenAPI</span><span>camelCase</span>
            </div>"""
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&display=swap');
*{{box-sizing:border-box}} html,body{{margin:0;height:100%;font-family:Sora,system-ui,sans-serif}}
body{{background:radial-gradient(ellipse 80% 55% at 0% -10%,rgba(149,213,178,.28),transparent 55%),
linear-gradient(160deg,#f7faf8,#eef4f0 45%,#e7efea);display:grid;place-items:center;padding:40px}}
.card{{width:min(960px,100%);background:rgba(255,255,255,.94);border:1px solid #d5e0da;border-radius:16px;
box-shadow:0 18px 50px rgba(15,42,31,.1);padding:48px 52px}}
.brand{{font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#2d6a4f;margin:0 0 14px}}
h1{{margin:0 0 16px;font-size:34px;letter-spacing:-.03em;color:#0f2a1f}}
p{{margin:0;font-size:17px;line-height:1.65;color:#5c6b73;max-width:64ch}}
.chips{{display:flex;flex-wrap:wrap;gap:10px;margin-top:28px}}
.chips span{{background:rgba(45,106,79,.1);color:#1b4332;padding:8px 12px;border-radius:999px;font-size:13px;font-weight:600}}
.foot{{margin-top:28px;font-size:12px;color:#95d5b2;font-weight:600}}
</style></head><body>
<article class="card">
  <p class="brand">EcoTrace AI · Documentation</p>
  <h1>{esc(title)}</h1>
  <p>{esc(blurb)}</p>
  {chips}
  <p class="foot">v0.7.1 · {esc(nav)}</p>
</article>
</body></html>"""

    rows = "".join(
        f"<div class='row'><strong>{esc(title.split('(')[0].strip())} #{i}</strong><span>Active</span><span>Demo Org</span></div>"
        for i in range(1, 5)
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&display=swap');
*{{box-sizing:border-box}} body{{margin:0;font-family:Sora,system-ui,sans-serif;background:#eef4f0;color:#14212b;min-height:100vh;display:grid;grid-template-columns:272px 1fr}}
.side{{background:linear-gradient(175deg,#0f2a1f,#1b4332 55%,#2d6a4f);color:#f4faf6;padding:18px 0}}
.side .logo{{padding:8px 18px 18px;font-weight:700;font-size:18px;letter-spacing:-.03em;border-bottom:1px solid rgba(255,255,255,.08)}}
.side .ver{{opacity:.65;font-size:11px;margin-top:4px;letter-spacing:.06em;text-transform:uppercase}}
.side a{{display:block;margin:4px 10px;padding:10px 12px;border-radius:10px;color:rgba(244,250,246,.9);text-decoration:none;font-size:13px}}
.side a.active{{background:rgba(149,213,178,.18);box-shadow:inset 3px 0 0 #95d5b2}}
.main{{display:flex;flex-direction:column;min-height:100vh}}
.top{{height:64px;background:rgba(255,255,255,.8);border-bottom:1px solid #d5e0da;display:flex;align-items:center;padding:0 20px;gap:10px;backdrop-filter:blur(12px)}}
.top .name{{font-weight:700;color:#0f2a1f}}
.top .badge{{font-size:11px;font-weight:600;color:#2d6a4f;background:rgba(45,106,79,.1);padding:4px 8px;border-radius:999px}}
.spacer{{flex:1}}
.content{{padding:28px 28px 40px;max-width:1100px}}
.eyebrow{{font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#2d6a4f;margin:0 0 8px}}
h1{{margin:0 0 8px;font-size:30px;letter-spacing:-.03em;color:#0f2a1f}}
.sub{{margin:0 0 22px;color:#5c6b73;max-width:60ch;line-height:1.55}}
.card{{background:rgba(255,255,255,.92);border:1px solid #d5e0da;border-radius:16px;box-shadow:0 8px 24px rgba(15,42,31,.06);padding:8px 0;overflow:hidden}}
.row{{display:grid;grid-template-columns:2fr 1fr 1fr;gap:12px;padding:14px 18px;border-top:1px solid #e7efea;font-size:14px}}
.row:first-child{{border-top:0}}
.row span{{color:#5c6b73}}
</style></head><body>
<aside class="side">
  <div class="logo">EcoTrace AI<div class="ver">v0.7.1</div></div>
  {nav_html}
</aside>
<div class="main">
  <header class="top"><span class="name">EcoTrace AI</span><span class="badge">v0.7.1</span><span class="spacer"></span><span style="color:#5c6b73;font-size:14px">EcoTrace Demo Industries</span></header>
  <main class="content">
    <p class="eyebrow">EcoTrace AI</p>
    <h1>{esc(title)}</h1>
    <p class="sub">{esc(blurb)}</p>
    <div class="card">{rows}</div>
  </main>
</div>
</body></html>"""


def capture(html: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        html_path = f.name
    file_url = Path(html_path).resolve().as_uri()
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--screenshot={dest}",
        "--window-size=1440,900",
        "--virtual-time-budget=5000",
        file_url,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    Path(html_path).unlink(missing_ok=True)


def main() -> None:
    if OUT.exists():
        for child in OUT.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            elif child.name in {"index.json", "README.md"}:
                child.unlink()
    index = []
    for group, filename, title, kind, blurb, nav in SHOTS:
        out = OUT / group / filename
        print(f"→ {group}/{filename}", flush=True)
        capture(html_for(title, kind, blurb, nav), out)
        index.append(
            {
                "group": group,
                "groupTitle": GROUPS[group],
                "file": filename,
                "title": title,
                "rel": f"docs/screenshots/{group}/{filename}",
            }
        )
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done: {len(index)} → {OUT}")


if __name__ == "__main__":
    main()
