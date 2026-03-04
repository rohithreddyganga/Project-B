# AutoApply Agent v2.0

**Fully autonomous job application system for F1-STEM OPT candidates.**

Scrapes from ATS portals (Workday, Greenhouse, Lever, etc.), filters by sponsorship eligibility, optimizes LaTeX resumes via a tiered ATS strategy, auto-applies end-to-end, and reports everything on a 7-section dashboard — all under $100/month.

## Quick Start

### 1. Clone & Configure

```bash
cp .env.example .env
# Edit .env with your API keys (Anthropic, Adzuna, JSearch, etc.)

# Edit your profile
nano config/profile.json

# Edit your master resume
nano src/optimizer/templates/master.tex

# Add priority companies
nano config/priority_companies.yaml
```

### 2. Run with Docker (Recommended)

```bash
docker-compose up -d
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 3. Run Locally (Development)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Start the server (includes scheduler)
python run.py serve

# Or run pipeline manually
python run.py pipeline

# Or just test scraping
python run.py scrape
```

### 4. API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `POST /api/pipeline/trigger` | Manually trigger the daily pipeline |
| `GET /api/jobs/` | List scraped jobs (with filters) |
| `GET /api/jobs/{id}` | Get job details + JD |
| `GET /api/applications/` | List all applications |
| `GET /api/applications/queue` | Current application queue |
| `GET /api/applications/pipeline` | Interview pipeline (Kanban data) |
| `PUT /api/applications/{id}/stage` | Update interview stage |
| `POST /api/applications/manual` | Add manual application |
| `POST /api/resume/score` | Score resume against JD |
| `POST /api/resume/optimize` | Optimize LaTeX resume for JD |
| `GET /api/stats/overview` | Dashboard overview stats |
| `GET /api/stats/costs` | Cost breakdown |
| `GET /api/stats/daily` | Daily application chart |
| `GET /api/settings/rules` | Get current rules |
| `PUT /api/settings/rules` | Update rules |
| `PUT /api/settings/blacklist` | Update blacklist |
| `PUT /api/settings/priority` | Update priority companies |

## Architecture

```
Pipeline: Scrape → Visa Filter → Gates → Score → Tier → Optimize → Archive → Apply → Dashboard → Gmail
```

See `autoapply-v2-architecture.html` for the full interactive architecture document.

## Project Structure

```
src/
├── scraper/          # Adzuna, JSearch, RemoteOK, ATS feeds
├── filters/          # visa_filter, gate_checker, freshness
├── scorer/           # ats_scorer, jd_analyzer, tier_classifier
├── optimizer/        # latex_optimizer, compiler, cover_letter
├── applicant/        # engine, stealth, handlers/
├── archive/          # DB-indexed flat storage
├── email/            # Phase 2: Gmail monitor
├── outreach/         # Phase 3: Network outreach
├── pipeline/         # Scheduler, orchestrator
├── api/              # FastAPI backend + routes
├── db/               # SQLAlchemy models
└── notifications/    # Telegram bot
```

## Configuration

- `config/profile.json` — Your personal info + form answers
- `config/settings.yaml` — All rules, schedule, scoring weights, etc.
- `config/priority_companies.yaml` — Top-tier company whitelist
- `config/blacklist.yaml` — Companies to never apply to
- `src/optimizer/templates/master.tex` — Your master LaTeX resume

## Cost: ~$55-75/month

| Category | Cost |
|----------|------|
| Hetzner VPS (CX32) | $14/mo |
| Claude API (Haiku + Sonnet) | ~$20/mo |
| Webshare Proxies | $10/mo |
| CapSolver | ~$5/mo |
| Everything else (free tiers) | $0 |
| **Total** | **~$55-75/mo** |

## Build Timeline

- **Days 1-3:** Scraper + DB + Dashboard skeleton
- **Days 4-6:** ATS scorer + LaTeX optimizer
- **Days 7-10:** Playwright auto-applicant (Greenhouse + Lever)
- **Days 11-14:** Full integration + go live at 50/day
- **Week 3-4:** Gmail Monitor + more ATS handlers
- **Month 2+:** Network outreach + AI agent pattern
