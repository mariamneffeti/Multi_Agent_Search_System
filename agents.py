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
_llm = None
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
def orchestrator(state: ResearchState) -> dict:
    llm = get_llm()
    prompt = f"""You are a research orchestrator. Your job is to break a complex question into specific,independently searchable subtasks.
    Query : {state.query}
    Return ONLY valid JSON with this exact schema:
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
    result = llm.invoke([HumanMessage(content= prompt)])
    try:
        parsed = json.loads(result.content)
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

# Analysis Agent

def analysis_agent(state: ResearchState) -> dict :
    """
    Synthesizes all gathered research into a structured analysis.
    outputs : analysis
    """
    llm = get_llm()
    context_parts = []
    for r in state.research_results[:12]: #cap context size
        context_parts.append(
            f"Source: {r.get('title','untitled')} {r.get('url','')}\n{r.get('content','')}"
        )
    context = "\n\n---\n\n".join(context_parts)
    prompt = f"""You are an expert research analyst. Synthesize the following research results into a coherent analysis adressing the original query.
    Original query: {state.query}
    Researcg finding:
    {context}
    Write a structured analysis with:
    1. Key findings (bullet points with source attribution)
    2. Major tradeoffs or tensions in the evidence
    3. Areas of consensus vs. disagreement
    4. Confidence assessment (high / medium / low) with reasoning
    
    Be specific and data-driven. Cite sources by title when referencing specific claims.
    """
    result = llm.invoke([HumanMessage(content=prompt)])
    return {"analysis": result.content}
# Critique Agent
def critique_agent(state : ResearchState) -> dict :
    """
    Reviews the analysis for bias,gaps,and unsupported claims.
    outputs : critique, critique_flags
    """
    llm = get_llm()
    prompt = f"""You are a rigorous fact-checker and research critic.
    Review the following analysis for quality issues.
    Original query : {state.query}
    Analysis to review:
    {state.analysis}
    Identify:
    1. Any claims that appear unsupported or overstated
    2. Important perspectives or data sources that are missing
    3. Potential bias in framing or source selection
    4. Geographic, temporal, or demographic blind spots
    
    Return your critique as plain prose, then list specific flags as:
    FLAGS: [flag1] | [flag2] | [flag3]
    
    Be constructive — the goal is a stronger final report, not rejection.
    """
    result = llm.invoke([HumanMessage(content=prompt)])
    content = result.content
    #Parse flags from the response
    flags = []
    if "FLAGS:" in content:
        flag_line = content.split("FLAGS:")[-1].strip()
        flags = [f.strip("[]") for f in flag_line.split("|") if f.strip()]
        content = content.split("FLAGS:")[0].strip()
    return {"critique": content,"critique_flags": flags}


# Synthesizer
"""
Write the final structured reseach report incorprating all prior worj.
output : final resport, citations"""
def synthesizer(state: ResearchState) -> dict:
    llm = get_llm()
    sources_block = "\n".join(
        f"[{i+1}] {url}" for i, url in enumerate(set(state.raw_sources[:10]))
    )
    flag_block = "\n".join(f"- {f}" for f in state.critique_flags) or "None identified."
    prompt = f"""You are a senior research writer. Produce a final, publication-ready
    research report based on the analysis and critique below.
    
    Original query: {state.query}
    
    Analysis:
    {state.analysis}
    
    Critique and flags to address:
    {state.critique}
    
    Known limitations flagged:
    {flag_block}
    
    Available sources:
    {sources_block}
    
    Write the report in this structure:
    ## Executive Summary
    (2-3 sentences, key takeaway)
    
    ## Key Findings
    (Numbered list, each finding with inline citation [N])
    
    ## Tradeoffs & Tensions
    (Prose, balanced perspective)
    
    ## Limitations & Caveats
    (Address the critique flags honestly)
    
    ## Conclusion
    (Actionable synthesis, 1-2 paragraphs)
    
    ## References
    (Numbered list matching inline citations)
    
    Use precise language. Do not hedge excessively. Acknowledge uncertainty where real.
    """
    result = llm.invoke([HumanMessage(content=prompt)])
    # Build structured citations list
    citations = [
        {"index": i+1, "url": url}
        for i, url in enumerate(set(state.raw_sources[:10]))
    ]
    return {"final_report": result.content, "citations": citations}