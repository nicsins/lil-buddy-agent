# Lil Buddy – Product Requirements Document (PRD)

**Version**: 1.0
**Date**: 2026-06-24
**Owner**: domiNic / Grok Hybrid Agent

## 1. Purpose
Lil Buddy is the user's personal autonomous AI agent that interprets natural language instructions, executes code/actions safely, manages a dynamic model stack with auto-fallback, and enforces the user's exact model pasting checklist. It must be production-grade, deployable to Vercel (native performance) with optional Tailscale self-hosting and custom domain.

## 2. Core Features (from user's agent architecture spec)
- Real-time chat UI for instruction input and feedback
- Instruction parsing → code generation/execution or LLM response
- Secure code execution environment (VENV/Docker style, restricted)
- Dynamic model stack (Ollama local + OpenRouter cloud) with automatic iteration/fallback on failure
- Model addition UI that enforces the user's 5-point checklist (Accurate, Formatted Correctly, Available, Right Place, Restart)
- OpenRouter API key handling via secrets/env (prompt user with instructions + paste form)
- Production deployment: Vercel (primary) + Streamlit Cloud fallback + Docker/Tailscale option

## 3. Non-Functional Requirements
- Security: Least-privilege code execution, input validation, rate limiting, secrets never committed
- Performance: Low latency on Vercel edge where possible
- Maintainability: Clean Python/FastAPI backend + Next.js frontend, full Git history, CI/CD
- Symbiotic alignment: Golden Rule, minimal harm, user empowerment, Dragonscale-ready

## 4. Tech Stack Decision
- Backend: FastAPI (Python) – agent core, secure execution sandbox, OpenRouter client, model management
- Frontend: Next.js 14+ (App Router) + Tailwind + Vercel AI SDK or simple React chat – rich UI, model dashboard, checklist enforcement
- Deployment: Vercel (native) for frontend + API routes; optional Docker + Caddy + custom domain via custom-domain-helper
- Auth/Secrets: Vercel env vars + st.secrets equivalent
- Git: Existing lil-buddy-agent repo (evolved)

## 5. Risks & Mitigations
- Code execution safety: Use restricted subprocess + timeout + whitelist
- Ollama in cloud: Graceful degradation + clear messaging
- Vercel Streamlit limitations: Migrated to FastAPI + Next.js for native support

## 6. Success Metrics
- User can deploy in <10 minutes via Vercel import
- Full checklist enforcement in UI
- Auto-fallback works in production
- OpenRouter key prompted with easy instructions + paste box

## 7. Next Phases
Phase 2: Repo structure + initial scaffold
Phase 3: Backend (FastAPI agent core)
Phase 4: Frontend (Next.js chat + model UI)
Phase 5: Vercel deploy + custom domain option

Approved by user confirmation on 2026-06-24.