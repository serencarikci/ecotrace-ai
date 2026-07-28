#!/usr/bin/env python3
"""Generate EcoTrace docs screenshots as styled HTML mockups via Chrome headless."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

GROUPS = {
    "01-giris": "Giriş & Genel",
    "02-platform": "Platform",
    "03-organizasyon": "Organizasyon",
    "04-veri-karbon": "Veri & Karbon",
    "05-analitik": "Analitik",
    "06-urun-lca": "Ürün & LCA",
    "07-ai-otomasyon": "AI & Otomasyon",
    "08-guvenlik-ops": "Güvenlik & Ops",
    "09-altyapi-demo": "Altyapı & Demo",
}

# (group, filename, title, kind, blurb, nav_hint)
SHOTS: list[tuple[str, str, str, str, str, str]] = [
    ("01-giris", "01-giris.png", "Giriş", "login", "Güvenli oturum açma: e-posta ve parola ile JWT + refresh token.", "Sign in"),
    ("01-giris", "02-dokumanin-amaci.png", "Dokümanın Amacı", "doc", "Platform yeteneklerini, ekranlarını ve operasyonel kullanımı açıklar. Portföy / referans uygulama; sertifikasyon ürünü değildir.", "Docs"),
    ("01-giris", "03-platform-hakkinda.png", "Platform Hakkında", "doc", "Karbon muhasebesi, LCA/PCF, DPP, analitik, hedefler, grounded AI ve onaylı otomasyonu birleştiren modüler monolith.", "Overview"),
    ("01-giris", "04-genel-bakis.png", "Genel Bakış", "app", "Operasyonlardan karbon envanterine, ürün LCA’sından AI ve otomasyona tek sistem kaydı.", "Dashboard"),
    ("02-platform", "01-platform-mimarisi.png", "Platform Mimarisi", "arch", "FastAPI API · Angular 19 Web · PostgreSQL (+ pgvector) · Scheduler. LLM’ler veritabanına erişmez.", "Architecture"),
    ("02-platform", "02-teknoloji-altyapisi.png", "Teknoloji Altyapısı", "doc", "Python 3.12, FastAPI, SQLAlchemy, Alembic · Angular Material · PostgreSQL 16 · Docker Compose · GitHub Actions.", "Stack"),
    ("02-platform", "03-kullanici-rolleri.png", "Kullanıcı Rolleri", "app", "system_admin · organization_admin · analyst · viewer — organizasyon kapsamlı RBAC.", "Profile"),
    ("03-organizasyon", "01-dashboard.png", "Gösterge Paneli (Dashboard)", "app", "Komuta merkezi: tesisler, karbon, ürünler ve zekâ yollarına hızlı erişim.", "Dashboard"),
    ("03-organizasyon", "02-organizasyon-yonetimi.png", "Organizasyon Yönetimi", "app", "Çok kiracılı organizasyonlar, üyelikler ve seçili org bağlamı.", "Organizations"),
    ("03-organizasyon", "03-kullanici-rol-yonetimi.png", "Kullanıcı ve Rol Yönetimi", "app", "Kimlik, roller ve profil; oturum ve yetki sınırları.", "Profile"),
    ("03-organizasyon", "04-tesis-yonetimi.png", "Tesis (Facility) Yönetimi", "app", "Üretim sahaları, depolar ve operasyonel tesis kayıtları.", "Facilities"),
    ("03-organizasyon", "05-operasyonel-varlik.png", "Operasyonel Varlık Yönetimi", "app", "Ekipman, üretim hatları ve veri kaynakları.", "Equipment"),
    ("04-veri-karbon", "01-aktivite-verisi.png", "Aktivite Verisi Yönetimi", "app", "Denetlenebilir aktivite kayıtları, dönemler ve onay akışları.", "Activity Data"),
    ("04-veri-karbon", "02-csv-veri-aktarimi.png", "CSV Veri Aktarımı", "app", "CSV içe aktarım sihirbazı, doğrulama ve satır hataları.", "Data Imports"),
    ("04-veri-karbon", "03-emisyon-faktoru.png", "Emisyon Faktörü Yönetimi", "app", "Faktör kaynakları, tercihler ve eşleştirme kuralları.", "Emission Factors"),
    ("04-veri-karbon", "04-karbon-envanteri.png", "Karbon Envanteri", "app", "Organizasyon emisyon envanterleri, kapsamlar ve snapshot’lar.", "Carbon Inventories"),
    ("04-veri-karbon", "05-karbon-hesaplama-motoru.png", "Karbon Hesaplama Motoru", "doc", "Aktivite × faktör → Scope sonuçları; doğrulama ve tekrarlanabilir hesaplama motoru.", "Engine"),
    ("05-analitik", "01-analitik-raporlama.png", "Analitik ve Raporlama", "app", "Yönetici analitiği, trendler, kategoriler ve karar desteği.", "Analytics"),
    ("05-analitik", "02-surdurulebilirlik-hedefleri.png", "Sürdürülebilirlik Hedefleri", "app", "Baseline’lar, mutlak/yoğunluk hedefleri ve girişimler.", "Targets"),
    ("05-analitik", "03-senaryo-analizi.png", "Senaryo Analizi", "app", "What-if senaryoları ve yol haritası karşılaştırmaları.", "Scenarios"),
    ("06-urun-lca", "01-urun-yonetimi.png", "Ürün Yönetimi", "app", "Ürünler, varyantlar ve parti (batch) kayıtları.", "Products"),
    ("06-urun-lca", "02-tedarikci-yonetimi.png", "Tedarikçi Yönetimi", "app", "Tedarikçi master data ve bağlantılar.", "Suppliers"),
    ("06-urun-lca", "03-malzeme-yonetimi.png", "Malzeme Yönetimi", "app", "Malzeme kataloğu ve özellikler.", "Materials"),
    ("06-urun-lca", "04-urun-recetesi-bom.png", "Ürün Reçetesi (Bill of Materials)", "app", "BOM satırları ile ürün bileşen ağacı.", "BOM"),
    ("06-urun-lca", "05-lca.png", "Yaşam Döngüsü Analizi (LCA)", "app", "LCA çalışmaları, envanter ve sonuç ekranları.", "LCA Studies"),
    ("06-urun-lca", "06-pcf.png", "Ürün Karbon Ayak İzi (PCF)", "app", "Ürün bazlı karbon ayak izi hesapları.", "PCF"),
    ("06-urun-lca", "07-dpp.png", "Dijital Ürün Pasaportu (DPP)", "app", "Pasaport sürümleri, önizleme ve genel yayın.", "Passports"),
    ("07-ai-otomasyon", "01-ai-copilot.png", "Yapay Zekâ Asistanı (AI Copilot)", "app", "Grounded RAG yanıtları, alıntılar ve güven skorları.", "AI Copilot"),
    ("07-ai-otomasyon", "02-enterprise-search.png", "Kurumsal Doküman Arama", "app", "Hibrit arama: anahtar kelime + vektör.", "Enterprise Search"),
    ("07-ai-otomasyon", "03-dokuman-yonetimi.png", "Doküman Yönetimi", "app", "Bilgi bankası yükleme, chunking ve yetkilendirme.", "Knowledge Docs"),
    ("07-ai-otomasyon", "04-otomasyon.png", "Otomasyon Yönetimi", "app", "Kurallar, tetikleyiciler, duraklat/çalıştır.", "Automation"),
    ("07-ai-otomasyon", "05-ai-ajanlari.png", "Yapay Zekâ Ajanları", "app", "Allowlist tool’lar ve insan onaylı yazma işlemleri.", "AI Agents"),
    ("07-ai-otomasyon", "06-tahminleme.png", "Tahminleme (Forecasting)", "app", "İstatistiksel projeksiyonlar ve hedef yörüngesi etiketleri.", "Forecasts"),
    ("07-ai-otomasyon", "07-anomali-tespiti.png", "Anomali Tespiti", "app", "Z-score, IQR, yüzde değişim ve eksik veri kontrolleri.", "Anomalies"),
    ("07-ai-otomasyon", "08-veri-kalitesi.png", "Veri Kalitesi Yönetimi", "app", "Kalite kuralları, bulgular ve izleme.", "Data Quality"),
    ("07-ai-otomasyon", "09-uyari-merkezi.png", "Uyarı Merkezi (Alerts)", "app", "Operasyonel uyarılar ve önem seviyeleri.", "Alerts"),
    ("07-ai-otomasyon", "10-bildirim-merkezi.png", "Bildirim Merkezi", "app", "Uygulama içi bildirimler ve tercihler.", "Notifications"),
    ("07-ai-otomasyon", "11-zamanlanmis-raporlar.png", "Zamanlanmış Raporlar", "app", "Planlı rapor üretimi ve dağıtım.", "Scheduled Reports"),
    ("07-ai-otomasyon", "12-tedarikci-takibi.png", "Tedarikçi Sürdürülebilirlik Takibi", "app", "İç skorlar (sertifikalı değil) ve izleme.", "Supplier Monitoring"),
    ("07-ai-otomasyon", "13-regulasyon.png", "Regülasyon Yönetimi", "app", "Regülasyon istihbaratı — hukuki tavsiye değildir.", "Regulatory"),
    ("08-guvenlik-ops", "01-sistem-guvenligi.png", "Sistem Güvenliği", "doc", "Org izolasyonu, RBAC, CSP, refresh rotasyonu, agent allowlist, audit log.", "Security"),
    ("08-guvenlik-ops", "02-sistem-izleme.png", "Sistem İzleme ve Operasyon", "app", "Sağlık, job monitoring ve operasyon panelleri.", "Health"),
    ("09-altyapi-demo", "01-api-altyapisi.png", "API Altyapısı", "api", "OpenAPI / Swagger, versioned /api/v1, camelCase sözleşmesi.", "API Docs"),
    ("09-altyapi-demo", "02-yedekleme.png", "Yedekleme ve Geri Yükleme", "doc", "backup.sh · verify-backup.sh · restore.sh — PostgreSQL yedekleri.", "Backup"),
    ("09-altyapi-demo", "03-dagitim.png", "Dağıtım Mimarisi (Deployment)", "arch", "Compose (dev/prod) · API + Web + Postgres + Scheduler · zayıf secret reddi.", "Deploy"),
    ("09-altyapi-demo", "04-demo-senaryosu.png", "Demo Senaryosu", "doc", "Seed: admin/orgadmin/analyst/viewer · demo org · EcoBottle · DPP · AI knowledge.", "Demo"),
    ("09-altyapi-demo", "05-sonuc.png", "Sonuç", "doc", "Phase 1–7 tamamlandı. Uçtan uca sürdürülebilirlik zekâsı referans platformu.", "Complete"),
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
        return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"/>
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
        return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"/>
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
  <p class="brand">EcoTrace AI · Dokümantasyon</p>
  <h1>{esc(title)}</h1>
  <p>{esc(blurb)}</p>
  {chips}
  <p class="foot">v0.7.1 · {esc(nav)}</p>
</article>
</body></html>"""

    # app shell mock
    rows = "".join(
        f"<div class='row'><strong>{esc(title.split('(')[0].strip())} #{i}</strong><span>Active</span><span>Demo Org</span></div>"
        for i in range(1, 5)
    )
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"/>
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
