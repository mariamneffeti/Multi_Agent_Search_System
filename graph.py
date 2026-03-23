""" Graph Assembly ------ wires agents into a LangGraph StateGraph.
Flow:
                        Orchestrator
                            |
                         Research <- single node( use Send() for true parallelism; see parallel_graph.py)
                            |
                         Analysis
                            |
                         Critique
                            |
                         Synthesizer
                            |
                            END
"""
from langgraph.graph import StateGraph, END
from state import ResearchState
from agents import(
    orchestrator,
    research_agent,
    analysis_agent,
    critique_agent,
    synthesizer,
)
def build_graph() -> StateGraph:
    workflow = StateGraph(ResearchState)
    # Register Nodes
    workflow.add_node("orchestrator",orchestrator)
    workflow.add_node("research",research_agent)
    workflow.add_node("analysis",analysis_agent)
    workflow.add_node("critique",critique_agent)
    workflow.add_node("synthesizer",synthesizer)
    #Define edges
    workflow.set_entry_point("orchestrator")
    workflow.add_edge("orchestrator", "research")
    workflow.add_edge("research",     "analysis")
    workflow.add_edge("analysis",     "critique")
    workflow.add_edge("critique",     "synthesizer")
    workflow.add_edge("synthesizer",  END)
    return workflow.compile()

# Compile once at import time for reuse
research_graph = build_graph()