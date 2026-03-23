# Multi-Agent Research System

A LangGraph-based research pipeline that decomposes complex questions,
dispatches specialist agents, and synthesizes a structured final report.

## Architecture

```
User Query
    │
    ▼
Orchestrator          Decomposes query into 3-5 subtasks
    │
    ▼
Research Agent(s)     Web search + page fetch (parallel via Send API)
    │
    ▼
Analysis Agent        Synthesizes evidence, maps tradeoffs
    │
    ▼
Critique Agent        Flags bias, gaps, unsupported claims
    │
    ▼
Synthesizer           Writes final structured report with citations
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

You also need `beautifulsoup4` for `web_fetch`:

```bash
pip install beautifulsoup4
```

### 2. Set API keys

```bash
cp .env.example .env
# Edit .env and fill in:
#   GROQ_API_KEY=...
#   TAVILY_API_KEY=...      (get a free key at tavily.com)
```

### 3. Run

```bash
# Default query
python main.py

# Custom query
python main.py "What are the geopolitical risks in semiconductor supply chains?"

# Parallel mode (faster — one research agent per subtask)
python main.py "Impact of GLP-1 drugs on obesity treatment" --parallel

# Save report to file
python main.py "AI impact on software jobs" --output report.md
```

## Files

| File | Purpose |
|------|---------|
| `state.py` | Typed `ResearchState` Pydantic model — shared across all agents |
| `tools.py` | Tool definitions: `web_search`, `web_fetch`, `summarize_text` |
| `agents.py` | 5 agent functions: orchestrator, research, analysis, critique, synthesizer |
| `graph.py` | Sequential LangGraph StateGraph |
| `parallel_graph.py` | Parallel variant using `Send()` API for concurrent research |
| `main.py` | CLI entry point |

## Customisation

### Swap the LLM

In `agents.py`, change the model string in `get_llm()`:

```python
def get_llm(model: str = "llama-3.3-70b-versatile") -> ChatGroq:
```

Use `llama-3.3-70b-versatile` for cheaper/faster runs, `llama-3.3-70b-versatile` for highest quality.

### Add tools

In `tools.py`, decorate any function with `@tool` and import it into
the relevant agent in `agents.py`.

### Add a new agent node

1. Write the function in `agents.py` — takes `ResearchState`, returns `dict`
2. Register it in `graph.py` with `workflow.add_node("name", fn)`
3. Wire it with `workflow.add_edge()`

### Enable human-in-the-loop

LangGraph supports interrupt points. Add before any node:

```python
workflow.add_node("human_review", lambda s: s)  # passthrough
workflow.interrupt_before(["synthesizer"])
```

Then resume with `graph.invoke(state, config={"configurable": {"thread_id": "1"}})`.

## Notes

- `research_results` and `raw_sources` use `operator.add` — they accumulate
  across parallel agent invocations without overwriting each other.
- The critique agent does not block synthesis — its flags are passed as context,
  not as a hard gate. Add a conditional edge if you want blocking critique.
- Tavily's free tier gives 1,000 searches/month. For higher volume, consider
  SerpAPI or Exa as drop-in replacements in `tools.py`.
