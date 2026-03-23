"""
Entry point. Run:
    python main.py Query

Optional flags:
    --parallel   Use the parallel graph (one research agent per subtask)
    --output     Path to write the report markdown file
"""

import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from state import ResearchState

def run(query : str, parallel : bool = False, output: str | None = None) -> str:
    if parallel:
        from parallel_graph import parallel_research_graph as graph
        print("Using parallel research graph (one agent per subtask)\n")
    else:
        from graph import research_graph as graph
        print("Using sequential research graph\n")
    print(f"Query: {query}\n{'─'*60}")
    initial_state = ResearchState(query=query)
    result = graph.invoke(initial_state)
    report = result.get("final_report", "[no report generated]")
    print("\n" + "═"*60)
    print("FINAL REPORT")
    print("═"*60)
    print(report)
    if result.get("critique_flags"):
        print("\nFlags addressed in report:")
        for flag in result["critique_flags"]:
            print(f"  ⚠ {flag}")

    if output:
        Path(output).write_text(report, encoding="utf-8")
        print(f"\nReport saved to: {output}")

    return report
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Agent Research System")
    parser.add_argument("query", nargs="?",
                        default="What are the economic and environmental tradeoffs of nuclear vs solar energy in 2024?",
                        help="Research question to investigate")
    parser.add_argument("--parallel", action="store_true",
                        help="Use parallel research agents (faster for complex queries)")
    parser.add_argument("--output", type=str, default=None,
                        help="Write final report to this file path")
    args = parser.parse_args()

    run(args.query, parallel=args.parallel, output=args.output)