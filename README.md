# Multi-Agent Research System

A LangGraph research pipeline that fans out web research, critiques its analysis, and streams a cited report over FastAPI.

[![CI](https://github.com/mariamneffeti/Multi_Agent_Search_System/actions/workflows/ci.yml/badge.svg)](https://github.com/mariamneffeti/Multi_Agent_Search_System/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)
![Docker](https://img.shields.io/badge/Docker-supported-2496ED)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

## Demo

<!-- Add a demo recording at docs/demo.gif. -->

![Demo recording placeholder](docs/demo.gif)

## Screenshots

<!-- Add screenshots when available. -->

| Research in progress | Final report |
| --- | --- |
| ![Research UI placeholder](docs/screenshots/research.png) | ![Report placeholder](docs/screenshots/report.png) |

## Features

- Orchestrator breaks a query into focused, searchable subtasks.
- Parallel research mode dispatches one research worker per subtask with LangGraph `Send()`.
- Analysis organizes findings and evidence; a critique agent identifies gaps and unsupported claims.
- Synthesizer produces a structured report with references and limitations.
- FastAPI streams progress and the final report to clients using Server-Sent Events.
- LangGraph supports `interrupt_before` and checkpointed thread state when a checkpointer is configured; see [Human review](#human-review).
- A shared LangChain rate limiter controls model request pace.

## Architecture

```mermaid
flowchart LR
    U[User Query] --> O[Orchestrator]
    O --> R[Parallel Research Agents]
    R --> A[Analysis]
    A --> C[Critique]
    C --> S[Synthesis]
    S --> P[Report]
```

## Stack

Python 3.11, LangGraph, LangChain, FastAPI, Docker, Groq (Llama 3.3) for language model calls, and Tavily for web search.

## Quickstart

### Docker

```bash
cp .env.example .env
# Set GROQ_API_KEY and TAVILY_API_KEY in .env
docker compose up --build
```

Open `http://localhost:8000`. The service listens on port 8000.

### Manual

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # Add your keys to .env
uvicorn api:app --reload --port 8000
```

For a command-line report, run `python main.py "Your research question" --parallel`.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Serves the research interface. |
| `GET` | `/history` | Serves the history page. |
| `GET` | `/about` | Serves the about page. |
| `GET` | `/api/health` | Reports service status and whether provider keys are configured. |
| `POST` | `/research` | Starts research and streams status, then a `done` event with report, flags, citations, and subtasks. Body: `{"query":"...","parallel":true}`. |

## Configuration

Copy `.env.example` to `.env` and provide:

| Variable | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Groq chat model access. |
| `TAVILY_API_KEY` | Tavily web search access. |

Keep `.env` local; it is ignored by Git.

## Testing

Install the project dependencies and pytest, then run `pytest`. GitHub Actions runs the test suite on pushes and pull requests.

## Project structure

| Path | Responsibility |
| --- | --- |
| `api.py` | FastAPI routes and SSE research endpoint. |
| `agents.py` | Orchestrator, research, analysis, critique, and synthesis nodes. |
| `state.py` | Shared Pydantic graph state and list reducers. |
| `graph.py` | Sequential LangGraph workflow. |
| `parallel_graph.py` | Parallel research workflow using `Send()`. |
| `tools.py` | Tavily search and HTTP page fetch tools. |
| `main.py` | Command-line entry point. |
| `static/` | HTML pages served by the API. |
| `tests/` | Automated tests with mocked external calls. |
| `.github/workflows/` | CI and deployment workflows. |

## Key technical decisions

- **LangGraph** models the pipeline as explicit stateful nodes and edges, which makes execution and checkpointing inspectable.
- **`Send()` and `operator.add` reducers** fan out one research task per worker and merge each worker's research results and sources into shared state.
- **`interrupt_before`** provides a review point before synthesis. The application can resume a checkpoint after a person approves or edits state.
- **Rate limiting** spaces shared Groq model requests to reduce bursts against provider limits. The current limiter is in-memory and process-local.

### Human review

The graph definitions can be compiled with `interrupt_before=["synthesizer"]` and a LangGraph checkpointer. Invoke with a stable `thread_id`, inspect or update the checkpointed state, then resume the same thread. The default API and CLI do not enable review or persistent storage; choose and configure a durable checkpointer before relying on state across restarts.

## Results

Example query: **[add query]**  
Report: **[add report link or excerpt]**  
Tokens: **[add measured input/output tokens]** · Latency: **[add measured duration]**

## Roadmap

- Add representative demo media and measured end-to-end results.
- Add durable checkpoint configuration for long-running, reviewable research threads.
- Improve observability for agent steps, provider latency, and token usage.

## Deployment

The repository's deployment is currently inactive. To reactivate automated Render deployment, configure a `RENDER_DEPLOY_HOOK` GitHub Actions secret, confirm the Render service and environment variables (`GROQ_API_KEY`, `TAVILY_API_KEY`) are configured, then push to `main`. The workflow builds and publishes the container to GHCR before calling the Render hook. The deploy hook alone does not create or configure a Render service.

## License

MIT. See [LICENSE](LICENSE).

## Contact

Open an issue in this repository for questions or suggestions.
