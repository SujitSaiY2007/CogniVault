# Current Objective — Final Integration, Free Cloud Deployment, Live Acceptance & Release

**Status:** Final safe integration active; cloud deployment, live acceptance, and hackathon packaging underway.  
**Canonical Plan:** [docs/FINAL_OVERHAUL_PLAN.md](docs/FINAL_OVERHAUL_PLAN.md)  
**Implementation Base:** `overhaul/chat-03-evaluation-submission` (`0e1b0552da1676ff4f77d1108966a05b3fd2efbe`)  
**Canonical Branch:** `main` (`8a852cabf605235a0759c84195277d3ddb2cb765`)  
**Dedicated Integration Branch:** `integration/final-safe-integration`  

---

## Required Exit Criteria

1. **Safe Integration:** Safely integrate Chat 01–03 implementation into `main` without destructive operations. Keep PR #1 open and untouched; merge PR #2 once verified.
2. **Cloud Model Provider Configuration:** Implement dual model support: preserve local Ollama for local development, and enable cloud model provider (Google Gemini free tier) when configured in hosted environments with server-side API keys.
3. **Free Cloud Deployment:**
   - Frontend: Vercel deployment of Next.js frontend with `NEXT_PUBLIC_API_URL` pointing to backend HTTPS.
   - Backend: Render deployment of FastAPI/Agno service on free tier, listening on `0.0.0.0:$PORT` with CORS enabled.
   - Zero hosting charges: strictly free plans only.
4. **Persistence & Free-Tier Boundaries:** Address Render ephemeral disk boundaries, document storage lifecycle, and avoid large repeated model downloads.
5. **Live Acceptance:** Verify the public frontend and backend end-to-end: health, ingestion, citation drawer, fail-closed abstention, assessment with BKT update, and restart resilience.
6. **Documentation & Release:** Update README, documentation, and create `docs/FINAL_VERIFICATION_AND_SUBMISSION_REPORT.md` with real public URLs, exact test outputs, and a 3–5 minute video recording script.
