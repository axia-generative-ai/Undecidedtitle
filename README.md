# 🏭 FactoryGuard

> **Smart Factory Anomaly Detection & RAG-based Manual Retrieval AI Prototype**

[한국어 버전](./README.ko.md)

---

## 📖 Project Overview

FactoryGuard is an AI service that instantly retrieves the relevant manual via RAG when an equipment error code occurs on the factory floor, and automatically guides operators through diagnosis and corrective procedures by analyzing virtual sensor logs.

### Core Value

- 🔍 Manual search time reduced from 5–15 minutes → instant (within 10 seconds)
- 👷 Standardized action guides immediately available even for unskilled workers
- 📚 RAG-based source citation to prevent hallucination

---

## 🎯 Key Features

| Feature | Description |
|---|---|
| Error Code Search | Enter an error code → instantly retrieve relevant manual pages |
| Equipment Manual Lookup | Search manuals by equipment name or category |
| Anomaly Detection Demo | Input virtual logs → LLM analysis → estimate anomaly and root cause |
| Corrective Procedure Guide | Step-by-step corrective actions via RAG + LLM summarization |
| Manual Management | Upload PDF → automatic chunking & embedding (admin only) |

---

## 📂 Repository Structure

| Folder | Owner | Description |
|---|---|---|
| `frontend/` | Member A |  |
| `backend/` | Member B |  |
| `ai-service/` | Member C |  |
| `docs/` | Shared | Planning, design, architecture, and presentation documents |
| `shared/` | Shared | Environment variable templates, etc. |

For detailed setup instructions and folder structure, refer to the README inside each folder (written by each team member).

---

## 👥 Team

| Role | Owner |
|---|---|
| Frontend | Member A |
| Backend | Member B |
| AI · ML | Member C |

---

## 📅 Development Schedule

| Phase | Period | Key Deliverables |
|---|---|---|
| Phase 1 — Planning & Design | Apr 26 – Apr 29 | PRD, WBS, Wireframes, API Spec |
| Phase 2 — MVP Development | Apr 30 – May 4 | FE screens, BE APIs, AI RAG standalone |
| Phase 3 — AI Integration & Enhancement | May 5 – May 9 | Integration + anomaly detection + 80%+ accuracy |
| Phase 4 — QA & Demo Preparation | May 10 – May 13 | Testing, presentation materials, demo |

---

## 🛠️ Tech Stack

**Frontend** — React 18, TypeScript, Tailwind CSS
**Backend** — fast api, python 3.13
**AI/ML** — LangChain, FastAPI, OpenAI/Claude API, Chroma DB
**Database** — PostgreSQL (Relationship) + PGVector (Vector)
**DevOps** — GitHub Actions, Docker, Notion

---

## 📄 License

This project is a prototype built for portfolio purposes.

---


