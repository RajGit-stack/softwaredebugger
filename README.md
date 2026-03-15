## AI Software Debugger Agent

This repository contains a multi-service, zero-cost-friendly system that automates analysis, debugging, testing, and documentation for GitHub repositories using LangGraph agents.

### Services

- **frontend**: React + Vite UI (deployed on Vercel)
- **agent-service**: FastAPI + LangGraph (Python) orchestrator that runs the multi-agent graph against GitHub repos

### High-level architecture

- **React UI (Vercel)** → calls → **FastAPI + LangGraph Agent Service (Render)**
- **Agent service** talks to:
  - **GitHub API** (for repo read/write via GitHub App or PAT)
  - **Supabase Postgres** (task history, job status)
  - **Upstash Redis** (task queue / pub-sub between services)
  - **ChromaDB** (code embeddings on-disk in the agent container)
  - **Groq LLM API** (Llama 3.3 / Mixtral)

Detailed service READMEs live in the respective folders.

# softwaredebugger
