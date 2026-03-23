"""
Agent node functions. Each recieves ResearchState, return a dict of updates.
LangGraph merges the returned dict back into the shared state.
"""
import json
import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from state import ResearchState
from tools import get_search_tool, web_fetch

# Shared Model Instances

def get_llm(model: str = "llama-3.3-70b-versatile") -> ChatGroq :
    global _llm
    if _llm is None :
        _llm = ChatGroq(model=model,temperature =0, max_tokens = 4096)
    return _llm

# Orchestrator
"""
Decomposses the user query into subtasks ->writes an agent plan.
output : subtasks, agent_plan
the brain of the agent
"""

llm = get_llm()
prompt = f"""You are a research orchestrator. Your job is to break a complex question into specific,independently searchable subtasks.
Query : {state.query}
Return ONLY valid JSON with this exact shema:
{{
    "subtasks" : [
    "specific searchable question 1",
    "specific searchable question 2",
    "specific searchable question 3",
    "specific searchable question 4"
    ],
    "agent_plan" : "One paragraph describing the research strategy."
}}
Rules :
- 3-5 subtasks maximum
- Each subtask should be a concrete, searchable question
- Cover different facets : factual data, economic/environmental context, expert opinion, future outlook
- Do NOT include preamble - output raw JSON only
"""
result = llm.invoke([HumanMessage(context= prompt)])
try:
    return {
        "subtasks": parsed.get("subtasks",[]),
        "agent_plan": parsed.get("agent_plan",""),
    }
except json.JSONDecodeError: # Fallback : we treat the query as a single subtask
    return {
            "subtasks": [state.query],
            "agent_plan": "Direct search approach.",
        }


# Research Agent : runs twice in parrarel via Send API
"""
Takes the first half of subtasks, searches the web, and accumulates results.
In the graph this node is dispatched multiple times via send() for parallelism.
output : research_results (accumulated) and raw_sources (accumulated)
"""
def research_agent(state : ResearchState) -> dict :
    search = get_search_tool(max_results = 4)
    results = []
    sources = []
    for subtask in state.subtasks :
        print(f"[research] searching : {subtask[:60]}...")
        hits = search.invoke(subtask)
        for hit in hits:
            results.append({
                "subtask": subtask,
                "url": hit.get("url",""),
                "title": hit.get("title",""),
                "content": hit.get("content",""), 
            })
            if hit.get("url"):
                sources.append(hit["url"])
    return {
        "research_results": results,
        "raw_sources": sources,
    }
