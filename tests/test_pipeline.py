import json
import operator

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langchain_core.messages import HumanMessage

import agents
from graph import build_graph
from parallel_graph import parallel_research_graph
from state import ResearchState
import tools


class FakeLLM:
    def invoke(self, messages):
        prompt = messages[0].content if isinstance(messages[0], HumanMessage) else str(messages[0])
        if "research orchestrator" in prompt:
            return type("Reply", (), {"content": json.dumps({"subtasks": ["topic one", "topic two"], "agent_plan": "cover both topics"})})()
        if "research analyst" in prompt:
            return type("Reply", (), {"content": "Analysis with evidence."})()
        if "fact-checker" in prompt:
            return type("Reply", (), {"content": "Review complete. FLAGS: [check date]"})()
        return type("Reply", (), {"content": "## Executive Summary\nMock report."})()


class FakeSearch:
    def invoke(self, query):
        return [{"url": f"https://example.test/{query.replace(' ', '-')}", "title": query, "content": f"Evidence for {query}"}]


def mock_external_services(monkeypatch):
    monkeypatch.setattr(agents, "get_llm", lambda: FakeLLM())
    monkeypatch.setattr(agents, "get_search_tool", lambda max_results=4: FakeSearch())


def test_state_reducer_appends_parallel_updates():
    graph = StateGraph(ResearchState)
    graph.add_node("first", lambda state: {"raw_sources": ["one"]})
    graph.add_node("second", lambda state: {"raw_sources": ["two"]})
    graph.set_entry_point("first")
    graph.add_edge("first", "second")
    graph.add_edge("second", END)

    result = graph.compile().invoke(ResearchState(query="q"))

    assert ResearchState.model_fields["raw_sources"].metadata[0] is operator.add
    assert result["raw_sources"] == ["one", "two"]


def test_graph_routes_through_all_nodes_with_mocked_llm(monkeypatch):
    mock_external_services(monkeypatch)
    from graph import research_graph

    result = research_graph.invoke(ResearchState(query="test question"))

    assert len(result["subtasks"]) == 2
    assert result["analysis"] == "Analysis with evidence."
    assert result["critique"] == "Review complete."
    assert result["final_report"].startswith("## Executive Summary")


def test_parallel_dispatch_collects_each_worker_output(monkeypatch):
    mock_external_services(monkeypatch)

    result = parallel_research_graph.invoke(ResearchState(query="test question"))

    assert {row["subtask"] for row in result["research_results"]} == {"topic one", "topic two"}
    assert len(result["raw_sources"]) == 2
    assert result["final_report"]


def test_human_review_interrupt_checkpoints_and_resumes(monkeypatch):
    mock_external_services(monkeypatch)
    graph = build_graph(checkpointer=MemorySaver(), interrupt_before=["synthesizer"])
    config = {"configurable": {"thread_id": "review-test"}}

    paused = graph.invoke(ResearchState(query="review this"), config)

    snapshot = graph.get_state(config)
    assert "synthesizer" in snapshot.next
    assert not paused.get("final_report")

    resumed = graph.invoke(None, config)
    assert resumed["final_report"].startswith("## Executive Summary")


def test_web_fetch_uses_mocked_http(monkeypatch):
    class Response:
        text = "<html><script>ignore()</script><main>Useful page text</main></html>"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(tools.httpx, "get", lambda *args, **kwargs: Response())

    result = tools.web_fetch.invoke({"url": "https://example.test/page"})

    assert "Useful page text" in result
    assert "ignore" not in result
