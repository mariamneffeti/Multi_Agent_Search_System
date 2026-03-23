"""
Paralle variant - uses LnagGraph's Send() API to dispatch research agents concurrently,one per subtask. Faster for queries with many subtasks.
Requires langgraph >= 0.2.0
"""
from langgraph.graph import StateGraph, END
from langgraph.types import Send
from state import ResearchState
from agents import(
    orchestrator,
    research_agent,
    analysis_agent,
    critique_agent,
    synthesizer,
)
def dispatch_research(state: ResearchState) -> list[Send]:
    """
    Fan-out : spawn one research_agent per subtask.
    Each Send() creates an independent invocation with a cloned state.
    where subtasks = [single_subtask]. Results accumulate via operator.add .
    """
    return [
        Send("research", ResearchState(
            query = state.query,
            subtasks = [task],
            iteration = i,
        ))
        for i,task in enumerate(state.subtasks)
    ]
def build_parallel_graph() -> StateGraph:
    workflow = StateGraph(ResearchState)

    workflow.add_node("orchestrator", orchestrator)
    workflow.add_node("research",     research_agent)
    workflow.add_node("analysis",     analysis_agent)
    workflow.add_node("critique",     critique_agent)
    workflow.add_node("synthesizer",  synthesizer)

    workflow.set_entry_point("orchestrator")

    # Fan-out: orchestrator → multiple parallel research agents
    workflow.add_conditional_edges(
        "orchestrator",
        dispatch_research,
        ["research"],  # all Sends go to this node
    )
    # Fan-in: all research results accumulate before analysis runs
    workflow.add_edge("research",    "analysis")
    workflow.add_edge("analysis",    "critique")
    workflow.add_edge("critique",    "synthesizer")
    workflow.add_edge("synthesizer", END)

    return workflow.compile()


parallel_research_graph = build_parallel_graph()