# Upsum — Project Nexus

> *A sovereign Swedish knowledge platform designed to replace generic encyclopedias with a fast, fact‑centric experience built for Swedish language and intent.*

---

## 🎲 Overview

**Codename:** Nexus  
**Project name:** Upsum  

Upsum is the next generation of Swedish knowledge — an independent and privacy‑minded platform built around the idea of *Swedish linguistic sovereignty*.  
It combines the reliability of Wikipedia's factual backbone with a modern, Nordic‑themed design and a clean, dark-native interface.

The goal: to create **the next Wikipedia for Sweden**, purpose-built for Swedish readers, dialects, and expressions.

---

## 🚀 Getting Started

### Quick Start (Windows)

To install dependencies and launch both backend and frontend automatically, run:

```cmd
RUNME.bat
```

This will:
- Set up Python virtual environment and install backend dependencies
- Install Wikipedia API integration (wikipediaapi)
- Start backend (http://localhost:8000) and frontend (http://localhost:5173) in new terminals
- Open the application in your browser

If you encounter permission issues, right-click and run as administrator or check your Python installation.

### Manual Setup

For detailed setup instructions, deployment guides, and troubleshooting, see [SETUP.md](SETUP.md).

#### Frontend (Standalone HTML)

1. The frontend is automatically served by the backend at http://localhost:8000
2. Alternatively, open `frontend/frontend.html` directly in your browser

#### Backend (FastAPI)

1. Open a terminal in `backend/`
2. Create a virtual environment:
  ```sh
  python -m venv .venv
  source .venv/bin/activate  # On Windows: .venv\Scripts\activate
  ```
3. Install dependencies:
  ```sh
  pip install -r requirements.txt
  ```
4. Test Wikipedia integration (optional):
  ```sh
  python test_wikipedia.py
  ```
5. Start the backend server:
  ```sh
  uvicorn main:app --reload
  ```
6. The API will be available at [http://localhost:8000](http://localhost:8000)

---

## 🏛️ Project Structure

```
Upsum/
├── backend/           # FastAPI backend (Python)
│   ├── main.py         # FastAPI application
│   ├── search.py       # Wikipedia search integration
│   ├── requirements.txt # Python dependencies
│   └── test_wikipedia.py # Integration test script
├── frontend/          # Frontend interface
│   └── frontend.html  # Standalone Nordic-themed UI
├── RUNME.bat          # Windows quick start script
├── SETUP.md           # Detailed setup and deployment guide
└── README.md          # This file
```

---

## 🌐 What is Project Nexus?

### Swedish‑First
Upsum treats Swedish as a first‑class citizen. Its knowledge model is tuned to understand Swedish grammar, nuance, and dialects — including compound words, regional phrasing, and idiomatic structures.

### Fact‑Centric
Every topic and claim is backed by traceable, verifiable sources from Swedish Wikipedia. Upsum emphasizes accuracy and transparency — *no distractions, no bias, no noise.*

### Privacy‑Focused
Your curiosity should never come at the cost of your privacy.  
No ads, no tracking, no profiling — just **pure knowledge** at incredible speed.

---

## 🕯️ Why It Matters

### Language Sovereignty
- Swedish nuance is interpreted correctly.  
- Dialect and colloquial input are recognized.  
- Compounds and definiteness are resolved naturally.

### Trustworthy by Design
- Citation‑first presentation of facts.  
- Transparent provenance for all data.  
- Ad‑free reading, no interruptions.

### Built for Speed
- Extremely lightweight interface.  
- Fast Wikipedia API integration.  
- Real-time search results.

---

## ⚙️ How It Works

### Natural Swedish Input
Upsum's parser understands:
- Complex compounds and declension patterns.  
- Automatic normalization of definiteness and context.  
- Mapping of informal phrasing to formal semantic intent.

### Wikipedia Integration (ACTIVE)
- **Live Swedish Wikipedia API integration** via `wikipediaapi` library
- Real-time article search and retrieval
- Automatic snippet extraction and formatting
- Direct links to source articles for full reading

### Sovereign Data Layer (Planned)
- Local Wikipedia dump processing for offline capability
- Planned integrations with official Swedish data sources:  
  *SCB, Bolagsverket, Lantmäteriet, Språkbanken.*  
- Transparent citations displayed alongside every claim.

### Oscyra Design System
- Minimalist, Nordic-inspired interface.  
- **Dark-first UX** — no light mode.  
- Built for clarity, speed, and calm visual focus.  
- Inspired by the Klar design language.

---

## 🛠️ Technology & Architecture

- **Backend**: Python + FastAPI (API orchestration + Wikipedia integration)
- **Search**: Wikipedia API (wikipediaapi + MediaWiki OpenSearch)
- **Frontend**: Standalone HTML/CSS/JavaScript (no framework overhead)
- **Deployment**: Uvicorn (development) / Gunicorn (production)
- **Privacy**: Zero analytics, no tracking, no external dependencies

### API Endpoints

- `GET /` - Serve frontend interface
- `GET /health` - Health check endpoint
- `GET /search?q={query}` - Search Swedish Wikipedia
- `GET /api/docs` - Interactive API documentation (Swagger UI)

---

## 🔮 Roadmap

| Phase | Goal | Status |
|-------|------|--------|
| Alpha | Core Wikipedia integration + Swedish NLP | 🟢 **COMPLETE** |
| Beta  | Interface with Oscyra design system | 🟢 **COMPLETE** |
| 1.0   | Production deployment on oscyra.solutions | 🟡 In Progress |
| 1.1   | Local Wikipedia dump processing | ⚪ Planned |
| 2.0   | Sovereign data integration (SCB, etc.) | ⚪ Planned |

---

## 🧪 Testing

To verify Wikipedia integration is working:

```bash
cd backend
python test_wikipedia.py
```

Expected output will show successful connection to Swedish Wikipedia API and sample search results.

To test the API manually:
```bash
curl "http://localhost:8000/search?q=Stockholm"
```

---

## 🧭 Vision

Upsum's mission is **to give Sweden back its knowledge — in its own language, on its own terms.**  
By merging verified information with linguistic precision, Upsum becomes more than an encyclopedia.  
It becomes **a national knowledge core**, sovereign, neutral, and enduring.

---

## 🧩 License and Attribution

- Built upon open data contributions from [Wikipedia](https://www.wikipedia.org) under the Creative Commons Attribution‑ShareAlike License.  
- Planned integrations with public datasets under compatible open licenses.
- Original code: MIT License (see LICENSE file)

---

## 🌒 Design Reference

> "Form follows clarity."  
> — Oscyra Design Philosophy

Dark, minimal, and purely functional — Upsum reflects Swedish calm.  
Every pixel serves comprehension, never distraction.

---

## 💬 Contact & Contribution

**Website**: [oscyra.solutions/upsum](https://oscyra.solutions/upsum)  
**Developer**: Alex Jonsson / Oscyra Solutions  
**GitHub**: [CKCHDX/upsum](https://github.com/CKCHDX/upsum)

Contributions welcome! See [SETUP.md](SETUP.md) for development guidelines.

---

*Ett svenskt kunskapslager — byggt på svensk Wikipedia, för svensk språkrytm och svensk integritet.*
