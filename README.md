🔍 BiasLens - Search Auditor for India
[live link- https://bias-lens-ochre.vercel.app/]

Audit how Google search results differ across Indian cities and languages.

Two people search the *same* question: one in Chennai in Tamil, one in Delhi in Hindi. Do they see the same web? BiasLens runs the same query across multiple Indian cities and languages, compares the results with transparent, reproducible math, and reports one **Information Inequality Score (0–100)** per query.

Built for the **SerpApi India Hackathon 2026**.

⚠️ BiasLens is **descriptive, not causal**. It shows *what* differs ("Chennai's top 10 overlapped 38% with Delhi's on this date"), not *why*, and never claims a city is being "discriminated against."

✨ Features

- Multi-city, multi-language audits**: run one query across Chennai, Delhi, Bengaluru, Mumbai, Kolkata, Hyderabad, Ahmedabad in each city's own language (Tamil, Hindi, Kannada, Marathi, Bengali, Telugu, Gujarati, English).
- Four bias signals + one headline score**: result overlap, source quality, language match, and source diversity, combined into the Information Inequality Score.
- No LLM in the math**: every number comes from plain Python formulas documented in [`docs/methodology.md`](docs/methodology.md). Domain classification is an editable YAML file, so any miscategorization is a one-line fix.
- Reliability checks**: each variant is fetched multiple times to separate real cross-city bias from Google's own result churn.
- Credit guard**: estimates SerpApi cost *before* spending anything and refuses to exceed `max_credits`.
- Demo mode**: works with zero API credits using bundled fixtures for six real-world queries (diabetes home remedy, best crop loan, how to file RTI, PM Kisan eligibility, and more). The dashboard never errors out because a key is missing.
- Dashboard extras**: India map preview, voice input for queries, "Read aloud" explanations, and export to **JSON** or **PNG**.
  -Three ways to use it**: web dashboard, REST API, or a standalone Python library + CLI.

---

## 📐 How the score works

```
score = 100 × (0.40·overlap + 0.20·quality + 0.25·language + 0.15·diversity)
```

| Component | What it measures | Weight |
|---|---|---|
| **Overlap** | How different the actual result sets are (`1 − mean pairwise RBO`) | 0.40 |
| **Language** | How unevenly results match the query's language | 0.25 |
| **Quality** | How unevenly trustworthy the sources are across cities | 0.20 |
| **Diversity** | How unevenly varied the source mix is (Shannon entropy) | 0.15 |

The weights are a documented editorial judgment and are configurable via `weights=` on `information_inequality_score()`. Full formulas, known limitations, and sample-size notes live in [`docs/methodology.md`](docs/methodology.md).

---

## 🧱 Project structure

```
biaslens/
├── apps/
│   └── web/                  # React + TypeScript dashboard (Vite)
├── packages/
│   ├── biaslens/             # Core Python library + CLI (the metrics engine)
│   │   └── src/biaslens/
│   │       ├── auditor.py        # High-level Auditor entry point
│   │       ├── client.py         # Async SerpApi client
│   │       ├── cache.py          # SQLite response cache
│   │       ├── credit_guard.py   # Cost estimation & budget enforcement
│   │       ├── domain_tiers.yaml # Editable source-quality tiers
│   │       ├── report.py         # AuditReport (JSON / HTML)
│   │       └── metrics/          # overlap, quality, language, diversity,
│   │                             # reliability, score
│   └── backend/              # FastAPI server wrapping the library
│       └── app/
│           ├── routers/          # health, locations, featured, estimate, audits
│           └── fixtures/         # Demo-mode audit results
└── docs/
    └── methodology.md        # Source of truth for every metric
```

---

## 🛠️ Tech stack

| Layer | Tools |
|---|---|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS v4, React Router, Recharts, Framer Motion, D3-geo + TopoJSON (India map), html-to-image, Lucide icons |
| **Backend** | Python 3.10+, FastAPI, Uvicorn, Pydantic |
| **Core library** | httpx (async), Pydantic, PyYAML, SQLite cache |
| **Data source** | [SerpApi](https://serpapi.com) Google Search API |
| **Testing & quality** | pytest, respx, Vitest, Testing Library, Playwright (e2e), mypy (strict), Ruff, Oxlint |

---

## 🚀 Getting started

### Prerequisites

- Python 3.10+
- Node.js 18+
- *(Optional)* a [SerpApi](https://serpapi.com) key for live audits. Without one, the app runs in demo mode.

### 1. Clone

```bash
git clone https://github.com/codewithparveen/BiasLens.git
cd BiasLens
```

### 2. Start the backend

```bash
cd packages
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e biaslens
pip install -e "backend[dev]"

cd backend
uvicorn app.main:app --reload --port 8000
```

API docs will be at `http://localhost:8000/docs`.

### 3. Start the frontend

```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to the backend on port 8000.

### 4. Enable live mode *(optional)*

```bash
export SERPAPI_KEY="your_serpapi_key"     # set before starting the backend
```

With a key set, audits call SerpApi for real (and are cached in SQLite). Without one, they replay the bundled demo fixtures.

### Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `SERPAPI_KEY` | backend / CLI | Enables live mode. Also read from a `.env` file. |
| `BIASLENS_CORS_ORIGINS` | backend | Comma-separated allowed origins (default: `http://localhost:5173,http://localhost:3000`). |
| `VITE_API_BASE_URL` | frontend | API base URL (default: `/api`). |

---

## 💻 Using the library & CLI

BiasLens also works without the web app:

```bash
# 1. See what an audit would cost, spending nothing
biaslens estimate \
  --queries "diabetes home remedy" \
  --cities "Chennai,Delhi,Mumbai" \
  --languages "ta,hi,en"

# 2. Run a real audit (capped at 40 credits)
biaslens audit \
  --queries "diabetes home remedy" \
  --cities "Chennai,Delhi,Mumbai" \
  --languages "ta,hi,en" \
  --runs 2 --max-credits 40 \
  --output report.json

# 3. Render a saved report
biaslens report report.json --format html > report.html
biaslens report report.json --format summary

# 4. Inspect the cache
biaslens cache-stats
```

Or from Python:

```python
from biaslens import Auditor

auditor = Auditor(api_key="YOUR_SERPAPI_KEY")

estimate = auditor.estimate(
    queries=["how to file RTI"],
    cities=["Chennai", "Delhi"],
    languages=["ta", "hi", "en"],
)
print(estimate.budget.total_credits)

report = auditor.audit(
    queries=["how to file RTI"],
    cities=["Chennai", "Delhi"],
    languages=["ta", "hi", "en"],
    max_credits=30,
)
print(report.summary())
```

---

## 🔌 REST API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Status + whether live mode is available |
| `GET` | `/api/locations` | Supported cities and languages |
| `GET` | `/api/featured` | Headline scores for the demo queries |
| `POST` | `/api/estimate` | Credit cost of a plan (no spend) |
| `POST` | `/api/audits` | Start an audit job, returns a job `id` |
| `GET` | `/api/audits/{id}` | Poll job status, progress, and result |

All errors share one shape: `{ "code", "message", "hint" }`.

---

## 🧪 Testing

```bash
# Python library
cd packages/biaslens && pip install -e ".[dev]" && pytest

# Backend
cd packages/backend && pytest

# Frontend
cd apps/web
npm test            # unit tests (Vitest)
npm run lint        # Oxlint
npm run test:e2e    # Playwright smoke tests
```

---

## ⚠️ Limitations

- Results are a **snapshot in time**; Google's SERPs change continuously.
- Language detection uses a **Unicode-script heuristic**, so Hindi and Marathi (both Devanagari) can't be told apart, and transliterated text won't match.
- The source-quality tier list reflects editorial judgment for Indian contexts and is intentionally incomplete.
- SerpApi's free plan (~250 searches/month) limits audit breadth.
- Findings are **descriptive only**, never causal.

See [`docs/methodology.md`](docs/methodology.md) for the full discussion.

---

## 🗺️ Roadmap

- [ ] LLM-written plain-language explanations (prose only, never altering computed numbers)
- [ ] More cities and languages
- [ ] Larger audit runs with published findings and sample sizes
- [ ] Hosted live demo

---

## 👤 Author

**Parveen** · [@codewithparveen](https://github.com/codewithparveen)

## 📄 License

MIT
