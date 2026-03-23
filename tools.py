"""
Tool definitons used by reseach agents.
"""
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
import httpx
from bs4 import BeautifulSoup
import re
def get_search_tool(max_results : int = 5) -> TavilySearchResults :
    # Travily web search - returns structured results with the URLs and snippets
    return TavilySearchResults(
        max_results = max_results,
        search_depth = "advanced",
        include_answer = True,
        include_raw_content = False,
    )

@tool
def web_fetch(url : str,max_chars : int = 4000) -> str :
    """
    Fetch and clean the text content of a web page.
    Strips HTML, scripts, and nav elements. Returns plain text up to max_chars.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (research bot)"}
        resp = httpx.get(url,headers=headers,timeout=10,follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text,"html.parser")
        # Remove Noise Elements
        for tag in soup(["script","style","nav","footer","header","aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip= True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:max_chars]
    except Exception as e:
        return f"[fetch error: {e}]"

@tool
def summarize_text(text: str, focus: str = "") -> str:
    """
    Placeholder for an LLM sub-call that summarizes a long passage.
    In production, invoke a cheap/fast model here ()
    """
    #Truncate as a stub - replace with real LLM call if desired
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 40]
    excerpt = "\n".join(lines[:12])
    return f"[summary stub - first 12 non empty lines]\n{excerpt}"
