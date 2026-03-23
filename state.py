"""
Shared state schema for the multi-agent research system.
"""

from typing import Annotated
import operator
from pydantic import BaseModel , Field

class ResearchState(BaseModel):
    """
    Typed state passed through every node in the graph.
    Fields marked with operator.add are lists tthat accumulate across agents.
    """
    #input
    query: str = ""

    #Orchestrator outputs
    subtasks: list[str] = Field(default_factory=list)
    agent_plan: str =""
    # Research Outputs : accumulated from parallel agents
    research_results: Annotated[list[dict],operator.add] = Field(default_factory=list)
    raw_sources: Annotated[list[str],operator.add] = Field(default_factory=list)
    # Analysis + critique
    analysis: str =""
    critique: str =""
    critique_flags: list[str] = Field(default_factory=list)
    #Final output
    final_report: str =""
    citations: list[dict] = Field(default_factory=list)
    # Bookkeeping
    iteration: int =0
    errors: Annotated[list[str],operator.add] = Field(default_factory=list)
    class Config:
        arbitrary_types_allowed = True