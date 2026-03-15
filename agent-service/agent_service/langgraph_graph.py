import os
import re
from typing import TypedDict, Literal

import requests
from groq import Groq
from langgraph.graph import StateGraph, END


class GraphState(TypedDict):
    repo_url: str
    task_type: str
    branch: str
    description: str
    custom_question: str
    result: str
    quality_score: float
    repo_overview: str
    architecture_summary: str
    architecture_diagram: str
    custom_answer: str


def _get_groq_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")
    return Groq(api_key=api_key)


GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def _groq_complete(system_prompt: str, user_prompt: str) -> str:
    client = _get_groq_client()
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return completion.choices[0].message.content or ""


def _parse_github_repo(repo_url: str) -> tuple[str | None, str | None]:
    """
    Extract owner and repo from a GitHub URL like https://github.com/owner/repo[.git].
    """
    m = re.match(r"https?://github.com/([^/]+)/([^/]+)", repo_url.rstrip("/"))
    if not m:
        return None, None
    owner, repo = m.group(1), m.group(2)
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


def _fetch_repo_overview(repo_url: str, branch: str) -> str:
    """
    Fetch a lightweight overview of a public GitHub repo: top-level tree + README, if present.
    """
    owner, repo = _parse_github_repo(repo_url)
    if not owner or not repo:
        return ""

    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-software-debugger-agent",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        tree_resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}",
            params={"recursive": "1"},
            headers=headers,
            timeout=15,
        )
        tree_text = ""
        if tree_resp.ok:
            data = tree_resp.json()
            entries = data.get("tree", [])[:150]
            lines = [f"{e.get('type','blob'):4} {e.get('path','')}" for e in entries]
            tree_text = "\n".join(lines)

        readme_resp = requests.get(
            f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md",
            timeout=15,
        )
        readme_text = readme_resp.text if readme_resp.ok else ""

        parts = []
        if tree_text:
            parts.append("REPO TREE (truncated):\n" + tree_text)
        if readme_text:
            parts.append("\nREADME:\n" + readme_text)
        return "\n\n".join(parts)
    except Exception:
        return ""


def supervisor(state: GraphState) -> GraphState:
    # Attach lightweight repo overview (tree + README) so downstream agents can "see" the code.
    overview = _fetch_repo_overview(state["repo_url"], state["branch"])
    state["repo_overview"] = overview
    return state


def repo_analyser_agent(state: GraphState) -> GraphState:
    prompt = (
        f"Repository URL: {state['repo_url']}\n"
        f"Branch: {state['branch']}\n\n"
        f"User description: {state['description']}\n\n"
        "You are given a partial view of the repository (tree + README):\n\n"
        f"{state.get('repo_overview','')}\n\n"
        "From this, describe the code architecture and flow:\n"
        "- What the project does overall\n"
        "- Main modules / layers and how they interact\n"
        "- Important entrypoints (CLI, HTTP handlers, jobs, etc.)\n"
        "- Any obvious patterns (DDD, hexagonal, clean architecture, monolith, microservices, etc.)."
    )
    result = _groq_complete(
        "You are a senior software engineer performing repository analysis. "
        "Return clear, concise markdown.",
        prompt,
    )
    state["result"] = result
    state["architecture_summary"] = result

    diagram = _groq_complete(
        "You create SIMPLE high-level architecture diagrams as plain text box-and-arrow flows for developers.\n"
        "Use at most 6 boxes. Use this style, one per line:\n"
        "[User] -> [Frontend] -> [Backend API] -> [Database]\n"
        "Do NOT add explanations, only the diagram lines.",
        f"Repository URL: {state['repo_url']}\nBranch: {state['branch']}\n\n"
        f"REPO OVERVIEW:\n{state.get('repo_overview','')}\n\n"
        "Create a high-level architecture / data-flow diagram for this project.",
    )
    state["architecture_diagram"] = diagram

    if state.get("custom_question"):
        qa = _groq_complete(
            "You answer specific developer questions about a codebase, using the repository structure and README as context.",
            f"Repository URL: {state['repo_url']}\nBranch: {state['branch']}\n\n"
            f"REPO OVERVIEW:\n{state.get('repo_overview','')}\n\n"
            f"QUESTION:\n{state['custom_question']}",
        )
        state["custom_answer"] = qa
    state["quality_score"] = 0.0
    return state


def bug_fixer_agent(state: GraphState) -> GraphState:
    prompt = (
        f"Repository URL: {state['repo_url']}\n"
        f"Branch: {state['branch']}\n\n"
        f"User description (bugs/issues): {state['description']}\n\n"
        "You are given a partial view of the repository (tree + README):\n\n"
        f"{state.get('repo_overview','')}\n\n"
        "Use this structure to ground your reasoning. "
        "For each proposed bug, return a markdown section with:\n"
        "- A plausible file path and area (based on the tree)\n"
        "- A short explanation of the bug\n"
        "- A code block with the corrected code snippet the user can paste."
    )
    result = _groq_complete(
        "You are a senior debugging assistant. "
        "Explain likely root causes and propose concrete code-level changes in markdown.",
        prompt,
    )
    state["result"] = result

    if state.get("custom_question"):
        qa = _groq_complete(
            "You answer specific debugging questions about a codebase, using the repository structure and README as context.",
            f"Repository URL: {state['repo_url']}\nBranch: {state['branch']}\n\n"
            f"REPO OVERVIEW:\n{state.get('repo_overview','')}\n\n"
            f"QUESTION:\n{state['custom_question']}",
        )
        state["custom_answer"] = qa
    state["quality_score"] = 0.0
    return state


def test_generator_agent(state: GraphState) -> GraphState:
    prompt = (
        f"Repository URL: {state['repo_url']}\n"
        f"Branch: {state['branch']}\n\n"
        f"User description: {state['description']}\n\n"
        "You are given a partial view of the repository (tree + README):\n\n"
        f"{state.get('repo_overview','')}\n\n"
        "Identify the main language and testing framework if possible. "
        "Generate real test code (not just descriptions) for the key functions implied by the structure or mentioned above. "
        "Return copy-pasteable test code blocks grouped by file."
    )
    result = _groq_complete(
        "You are an expert in automated testing. "
        "Return tests in markdown with sections per area/component.",
        prompt,
    )
    state["result"] = result

    if state.get("custom_question"):
        qa = _groq_complete(
            "You answer questions about testing strategies for a codebase, using the repository structure and README as context.",
            f"Repository URL: {state['repo_url']}\nBranch: {state['branch']}\n\n"
            f"REPO OVERVIEW:\n{state.get('repo_overview','')}\n\n"
            f"QUESTION:\n{state['custom_question']}",
        )
        state["custom_answer"] = qa
    state["quality_score"] = 0.0
    return state


def doc_generator_agent(state: GraphState) -> GraphState:
    prompt = (
        f"Repository URL: {state['repo_url']}\n"
        f"Branch: {state['branch']}\n\n"
        f"User description: {state['description']}\n\n"
        "You are given a partial view of the repository (tree + README):\n\n"
        f"{state.get('repo_overview','')}\n\n"
        "Write README-style documentation that explains:\n"
        "- What the project does\n"
        "- How it is structured\n"
        "- How to run it\n"
        "- Any important configuration or extension points."
    )
    result = _groq_complete(
        "You write clear, production-quality developer documentation.",
        prompt,
    )
    state["result"] = result

    if state.get("custom_question"):
        qa = _groq_complete(
            "You answer documentation-related questions about a codebase, using the repository structure and README as context.",
            f"Repository URL: {state['repo_url']}\nBranch: {state['branch']}\n\n"
            f"REPO OVERVIEW:\n{state.get('repo_overview','')}\n\n"
            f"QUESTION:\n{state['custom_question']}",
        )
        state["custom_answer"] = qa
    state["quality_score"] = 0.0
    return state


def code_search_agent(state: GraphState) -> GraphState:
    query = state["description"] or state["custom_question"]
    prompt = (
        f"Repository URL: {state['repo_url']}\n"
        f"Branch: {state['branch']}\n\n"
        f"Code search query: {query}\n\n"
        "You are given a partial view of the repository (tree + README):\n\n"
        f"{state.get('repo_overview','')}\n\n"
        "Act as an AI code search assistant. "
        "Based on the tree and README, identify the most relevant files and directories for this query. "
        "Return markdown with:\n"
        "- A bullet list of likely file paths\n"
        "- Short explanation why each file matches\n"
        "- If applicable, a small example snippet showing how the symbol or feature is likely used."
    )
    result = _groq_complete(
        "You are an AI code search assistant that helps developers navigate a repository using its structure.",
        prompt,
    )
    state["result"] = result
    state["quality_score"] = 0.0
    return state


def validator(state: GraphState) -> GraphState:
    grading_prompt = (
        "You are grading the quality of an LLM-generated answer on a scale from 0.0 to 1.0.\n"
        "Consider clarity, usefulness, and alignment with the requested task type "
        f"('{state['task_type']}').\n\n"
        "Return ONLY a numeric score, for example: 0.82"
    )
    score_str = _groq_complete(
        grading_prompt,
        f"Repo URL: {state['repo_url']}\n\nUser description:\n{state['description']}\n\nModel answer:\n{state['result']}",
    )
    try:
        state["quality_score"] = float(score_str.strip())
    except Exception:
        state["quality_score"] = 0.5
    return state


def router(state: GraphState) -> Literal[
    "repo_analyser_agent",
    "bug_fixer_agent",
    "test_generator_agent",
    "doc_generator_agent",
    "code_search_agent",
]:
    mapping = {
        "repo_analyser": "repo_analyser_agent",
        "bug_fixer": "bug_fixer_agent",
        "test_generator": "test_generator_agent",
        "doc_generator": "doc_generator_agent",
        "code_search": "code_search_agent",
    }
    return mapping.get(state["task_type"], "repo_analyser_agent")  # type: ignore[return-value]


def create_graph():
    builder = StateGraph(GraphState)

    builder.add_node("supervisor", supervisor)
    builder.add_node("repo_analyser_agent", repo_analyser_agent)
    builder.add_node("bug_fixer_agent", bug_fixer_agent)
    builder.add_node("test_generator_agent", test_generator_agent)
    builder.add_node("doc_generator_agent", doc_generator_agent)
    builder.add_node("code_search_agent", code_search_agent)
    builder.add_node("validator", validator)

    builder.set_entry_point("supervisor")

    builder.add_conditional_edges(
        "supervisor",
        router,
        {
            "repo_analyser_agent": "repo_analyser_agent",
            "bug_fixer_agent": "bug_fixer_agent",
            "test_generator_agent": "test_generator_agent",
            "doc_generator_agent": "doc_generator_agent",
            "code_search_agent": "code_search_agent",
        },
    )

    for node in [
        "repo_analyser_agent",
        "bug_fixer_agent",
        "test_generator_agent",
        "doc_generator_agent",
        "code_search_agent",
    ]:
        builder.add_edge(node, "validator")

    builder.add_edge("validator", END)

    return builder.compile()

