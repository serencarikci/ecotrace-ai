# EcoTrace AI

**Version:** `0.7.1`  
**Status:** Complete through Phase 7 (final development phase)

**Carbon, LCA and Sustainability Intelligence Platform**

EcoTrace AI is a production-conscious reference implementation for corporate carbon accounting, product LCA / product carbon footprints, Digital Product Passports, analytics and targets, grounded AI assistance with RAG, and intelligent automation (agents, anomalies, forecasts, scheduled reports).

It is designed as a senior engineering portfolio and deployable modular monolith — not as a certified compliance product and not as an unrestricted autonomous agent platform.

## Business problem

Organizations need a trustworthy system of record for environmental performance: multi-tenant identity, auditable calculations, evidence-backed AI answers, and operational automation with human approval for high-impact actions.

## Main capabilities

- Authentication (JWT + refresh rotation), organization tenancy, RBAC, audit logging
- Facilities / assets, activity data, CSV imports, attachments
- Carbon inventories, emission factors, calculation snapshots
- Analytics, targets, scenarios
- Products, BOM/LCA, product carbon footprints, Digital Product Passports
- AI Sustainability Copilot with hybrid RAG, citations, document ingestion
- Safe agents with allowlisted tools and human-in-the-loop approvals
- Automation rules, scheduler/job tracking, anomaly detection, forecasting
- Data quality monitoring, alerts, in-app notifications, scheduled reports
- Supplier monitoring (internal scores), regulatory intelligence (demo / non-legal)
- Observability hooks, backup scripts, production configuration validation

## Architecture

Modular monolith:

- **API:** FastAPI (`apps/api`) — domain modules, application services, repositories, thin routers
- **Web:** Angular 19 standalone (`apps/web`) — lazy routes, role guards
- **Data:** PostgreSQL (+ pgvector for embeddings when available)
- **Jobs:** Separate Compose `scheduler` process using the same codebase (no Kafka/Celery)

LLM providers never access the database. Agent tools call application services only.

See [docs/architecture.md](docs/architecture.md) and [docs/final-system-overview.md](docs/final-system-overview.md).

## Technology stack

- Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic, structlog
- Angular 19, Angular Material
- PostgreSQL 16, Docker Compose
- GitHub Actions CI
- Deterministic local AI providers for development/CI (`local_grounded`, `local_hash`)

## Module list (high level)

Identity · Organizations · Facilities · Operational assets · Reference data · Reporting periods · Activity data · Imports · Attachments · Emission factors · Carbon inventory · Analytics · Targets · Scenarios · Products · Materials · Suppliers · LCA · Product carbon footprint · Digital Product Passport · Knowledge · Retrieval · AI Copilot · Enterprise search · Agents · Automation · Job execution · Anomaly detection · Forecasting · Data quality · Alerts · Notifications · Scheduled reports · Supplier monitoring · Regulatory intelligence · Production operations

## Local installation

```bash
cp .env.example .env
docker compose up --build
```

API: `http://localhost:8000` · Web: `http://localhost:4200` · Docs: `http://localhost:8000/docs`

### Migrations and seed

```bash
cd apps/api
alembic upgrade head
python -m ecotrace.db.seed
```

### Demo users (from seed)

| Role | Email | Password (dev defaults) |
|------|-------|-------------------------|
| System admin | `admin@ecotrace.dev` | from `.env` `INITIAL_ADMIN_PASSWORD` |
| Org admin | `orgadmin@ecotrace.dev` | `EcoTraceOrgAdmin!2024` |
| Analyst | `analyst@ecotrace.dev` | `EcoTraceAnalyst!2024` |
| Viewer | `viewer@ecotrace.dev` | `EcoTraceViewer!2024` |

## Tests and quality

```bash
# Backend
cd apps/api
ruff format --check src tests && ruff check src tests
mypy src
pytest tests/ -v

# Frontend
cd apps/web
npm test -- --watch=false
npm run build

# Performance (optional)
python scripts/perf/health_burst.py --url http://localhost:8000/health --concurrency 100
```

## Backup and restore

```bash
export POSTGRES_HOST=... POSTGRES_DB=... POSTGRES_USER=... POSTGRES_PASSWORD=...
./scripts/backup.sh
./scripts/verify-backup.sh ./backups/<timestamp>
# ./scripts/restore.sh ./backups/<timestamp>
```

Details: [docs/backup-and-restore.md](docs/backup-and-restore.md)

## Production deployment

Use `.env.production.example` and `docker-compose.prod.yml` as starting points.  
Production startup **fails** on weak secrets / debug mode. See [docs/deployment.md](docs/deployment.md) and [docs/production-readiness.md](docs/production-readiness.md).

## Security model

Organization isolation, object-level RBAC, refresh rotation, password hashing, login lockout, security headers, CSP, trusted hosts, upload limits, CSV/formula injection defenses, agent tool allowlists, prompt-injection checks, RAG context isolation, audit logging. Details: [docs/security.md](docs/security.md), [docs/agent-security.md](docs/agent-security.md).

## AI and RAG

Hybrid retrieval with citations; default providers are local/deterministic for CI. Retrieved documents are untrusted. Citations are required for grounded answers. See Phase 6 docs and Phase 7 agent security.

## Automation / anomaly / forecast methodology

- **Automation:** validated templates/triggers; idempotent execution keys; pause/resume/manual run
- **Anomalies:** z-score, IQR, percentage change, missing-data checks; evidence + fingerprint dedup
- **Forecasts:** deterministic statistical methods; zero-safe MAPE; target trajectory labels (`likely_on_track`, `potentially_at_risk`, `likely_off_track`, `insufficient_data`) are projections, not guarantees

## Disclaimers

- **LCA / DPP:** calculation and passport features support decision-making; they do not constitute certification.
- **Regulatory intelligence:** document intelligence and internal decision support only. **It does not provide legal advice or guarantee regulatory compliance.** Seeded regulatory content is demo data.
- **Supplier scores:** internal and non-certified.

## Known limitations

- Minimal PDF report stub (not full PDF typography)
- Email defaults to logging provider unless SMTP is configured
- DB-polled scheduler (no Kafka/Celery)
- PITR not implemented in app scripts (infrastructure option)
- No unrestricted autonomous agents

## Project status

**Complete.** Phases 1–7 delivered. No Phase 8 roadmap.

## Dokümantasyon ekran görüntüleri

Kullanıcı kılavuzu başlıklarına göre gruplanmış görseller: [docs/screenshots](docs/screenshots/README.md).

### Giriş & Genel

#### Giriş

![Giriş](docs/screenshots/01-giris/01-giris.png)

#### Dokümanın Amacı

![Dokümanın Amacı](docs/screenshots/01-giris/02-dokumanin-amaci.png)

#### Platform Hakkında

![Platform Hakkında](docs/screenshots/01-giris/03-platform-hakkinda.png)

#### Genel Bakış

![Genel Bakış](docs/screenshots/01-giris/04-genel-bakis.png)

### Platform

#### Platform Mimarisi

![Platform Mimarisi](docs/screenshots/02-platform/01-platform-mimarisi.png)

#### Teknoloji Altyapısı

![Teknoloji Altyapısı](docs/screenshots/02-platform/02-teknoloji-altyapisi.png)

#### Kullanıcı Rolleri

![Kullanıcı Rolleri](docs/screenshots/02-platform/03-kullanici-rolleri.png)

### Organizasyon

#### Gösterge Paneli (Dashboard)

![Gösterge Paneli (Dashboard)](docs/screenshots/03-organizasyon/01-dashboard.png)

#### Organizasyon Yönetimi

![Organizasyon Yönetimi](docs/screenshots/03-organizasyon/02-organizasyon-yonetimi.png)

#### Kullanıcı ve Rol Yönetimi

![Kullanıcı ve Rol Yönetimi](docs/screenshots/03-organizasyon/03-kullanici-rol-yonetimi.png)

#### Tesis (Facility) Yönetimi

![Tesis (Facility) Yönetimi](docs/screenshots/03-organizasyon/04-tesis-yonetimi.png)

#### Operasyonel Varlık Yönetimi

![Operasyonel Varlık Yönetimi](docs/screenshots/03-organizasyon/05-operasyonel-varlik.png)

### Veri & Karbon

#### Aktivite Verisi Yönetimi

![Aktivite Verisi Yönetimi](docs/screenshots/04-veri-karbon/01-aktivite-verisi.png)

#### CSV Veri Aktarımı

![CSV Veri Aktarımı](docs/screenshots/04-veri-karbon/02-csv-veri-aktarimi.png)

#### Emisyon Faktörü Yönetimi

![Emisyon Faktörü Yönetimi](docs/screenshots/04-veri-karbon/03-emisyon-faktoru.png)

#### Karbon Envanteri

![Karbon Envanteri](docs/screenshots/04-veri-karbon/04-karbon-envanteri.png)

#### Karbon Hesaplama Motoru

![Karbon Hesaplama Motoru](docs/screenshots/04-veri-karbon/05-karbon-hesaplama-motoru.png)

### Analitik

#### Analitik ve Raporlama

![Analitik ve Raporlama](docs/screenshots/05-analitik/01-analitik-raporlama.png)

#### Sürdürülebilirlik Hedefleri

![Sürdürülebilirlik Hedefleri](docs/screenshots/05-analitik/02-surdurulebilirlik-hedefleri.png)

#### Senaryo Analizi

![Senaryo Analizi](docs/screenshots/05-analitik/03-senaryo-analizi.png)

### Ürün & LCA

#### Ürün Yönetimi

![Ürün Yönetimi](docs/screenshots/06-urun-lca/01-urun-yonetimi.png)

#### Tedarikçi Yönetimi

![Tedarikçi Yönetimi](docs/screenshots/06-urun-lca/02-tedarikci-yonetimi.png)

#### Malzeme Yönetimi

![Malzeme Yönetimi](docs/screenshots/06-urun-lca/03-malzeme-yonetimi.png)

#### Ürün Reçetesi (Bill of Materials)

![Ürün Reçetesi (Bill of Materials)](docs/screenshots/06-urun-lca/04-urun-recetesi-bom.png)

#### Yaşam Döngüsü Analizi (LCA)

![Yaşam Döngüsü Analizi (LCA)](docs/screenshots/06-urun-lca/05-lca.png)

#### Ürün Karbon Ayak İzi (PCF)

![Ürün Karbon Ayak İzi (PCF)](docs/screenshots/06-urun-lca/06-pcf.png)

#### Dijital Ürün Pasaportu (DPP)

![Dijital Ürün Pasaportu (DPP)](docs/screenshots/06-urun-lca/07-dpp.png)

### AI & Otomasyon

#### Yapay Zekâ Asistanı (AI Copilot)

![Yapay Zekâ Asistanı (AI Copilot)](docs/screenshots/07-ai-otomasyon/01-ai-copilot.png)

#### Kurumsal Doküman Arama

![Kurumsal Doküman Arama](docs/screenshots/07-ai-otomasyon/02-enterprise-search.png)

#### Doküman Yönetimi

![Doküman Yönetimi](docs/screenshots/07-ai-otomasyon/03-dokuman-yonetimi.png)

#### Otomasyon Yönetimi

![Otomasyon Yönetimi](docs/screenshots/07-ai-otomasyon/04-otomasyon.png)

#### Yapay Zekâ Ajanları

![Yapay Zekâ Ajanları](docs/screenshots/07-ai-otomasyon/05-ai-ajanlari.png)

#### Tahminleme (Forecasting)

![Tahminleme (Forecasting)](docs/screenshots/07-ai-otomasyon/06-tahminleme.png)

#### Anomali Tespiti

![Anomali Tespiti](docs/screenshots/07-ai-otomasyon/07-anomali-tespiti.png)

#### Veri Kalitesi Yönetimi

![Veri Kalitesi Yönetimi](docs/screenshots/07-ai-otomasyon/08-veri-kalitesi.png)

#### Uyarı Merkezi (Alerts)

![Uyarı Merkezi (Alerts)](docs/screenshots/07-ai-otomasyon/09-uyari-merkezi.png)

#### Bildirim Merkezi

![Bildirim Merkezi](docs/screenshots/07-ai-otomasyon/10-bildirim-merkezi.png)

#### Zamanlanmış Raporlar

![Zamanlanmış Raporlar](docs/screenshots/07-ai-otomasyon/11-zamanlanmis-raporlar.png)

#### Tedarikçi Sürdürülebilirlik Takibi

![Tedarikçi Sürdürülebilirlik Takibi](docs/screenshots/07-ai-otomasyon/12-tedarikci-takibi.png)

#### Regülasyon Yönetimi

![Regülasyon Yönetimi](docs/screenshots/07-ai-otomasyon/13-regulasyon.png)

### Güvenlik & Ops

#### Sistem Güvenliği

![Sistem Güvenliği](docs/screenshots/08-guvenlik-ops/01-sistem-guvenligi.png)

#### Sistem İzleme ve Operasyon

![Sistem İzleme ve Operasyon](docs/screenshots/08-guvenlik-ops/02-sistem-izleme.png)

### Altyapı & Demo

#### API Altyapısı

![API Altyapısı](docs/screenshots/09-altyapi-demo/01-api-altyapisi.png)

#### Yedekleme ve Geri Yükleme

![Yedekleme ve Geri Yükleme](docs/screenshots/09-altyapi-demo/02-yedekleme.png)

#### Dağıtım Mimarisi (Deployment)

![Dağıtım Mimarisi (Deployment)](docs/screenshots/09-altyapi-demo/03-dagitim.png)

#### Demo Senaryosu

![Demo Senaryosu](docs/screenshots/09-altyapi-demo/04-demo-senaryosu.png)

#### Sonuç

![Sonuç](docs/screenshots/09-altyapi-demo/05-sonuc.png)

## License

See repository license file if present; otherwise treat as private/portfolio source unless otherwise stated.
