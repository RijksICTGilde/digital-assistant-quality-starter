"""LangChain @tool definitions and execute_tools graph node."""

from __future__ import annotations

from typing import Any, List

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from loguru import logger

# Prompt-based fallback description (when the API doesn't support tools param)
TOOLS_PROMPT_FALLBACK = """
You have access to the following tools. To call a tool, respond ONLY with a JSON block:
{"tool": "<name>", "arguments": {<args>}}

Tools:
1. search_knowledge_base(query: str) – Search 350+ government documents for facts.
2. retrieve_past_answer(exchange_id: str) – Get full text of a previous answer.
3. lookup_past_conversation(topic: str) – Search past Q&A by topic keyword.

If you do NOT need a tool, just answer directly (no JSON).
"""


def create_tools(enhanced_rag: Any, session_getter, captured_sources: list):
    """Factory: creates tool instances with dependencies bound.

    Args:
        enhanced_rag: EnhancedRAGServiceWrapper instance for RAG search.
        session_getter: Callable that returns the current SessionMemory dict.
        captured_sources: Mutable list where search_knowledge_base appends
                          source metadata. The execute_tools node drains this
                          list after each invocation to populate retrieved_sources.
    """

    @tool
    def search_knowledge_base(query: str) -> str:
        """Search the RAG knowledge base of 350+ government documents. Use this when the user asks a factual question about regulations, guidelines, or best practices."""
        logger.info(f"[RAG-SEARCH] query='{query}'")
        results = enhanced_rag.search_documents(query, max_results=3)
        logger.info(f"[RAG-SEARCH] Found {len(results)} results")
        if not results:
            return "No relevant documents found."
        parts = []
        for i, doc in enumerate(results):
            title = doc.get("title", "Untitled")
            score = doc.get("relevance_score", 0)
            content = doc.get("content", doc.get("content_snippet", doc.get("summary", "")))
            logger.info(f"[RAG-SEARCH] #{i+1}: '{title}' (score={score:.3f}, content_len={len(content)})")
            parts.append(f"### {title} (relevance {score:.2f})\n{content}")

            # Capture structured source metadata (same search, no double call)
            captured_sources.append({
                "title": title,
                "document_id": doc.get("document_id", ""),
                "snippet": content[:200],
                "relevance_score": score,
                "url": doc.get("source_url", doc.get("url", "")),
                "file_path": doc.get("file_path", ""),
                "section_title": doc.get("section_title", ""),
                "chunk_index": doc.get("chunk_index", 0),
                "total_chunks": doc.get("total_chunks", 0),
                "document_title": doc.get("document_title", ""),
            })

        return "\n\n".join(parts)

    @tool
    def retrieve_past_answer(exchange_id: str) -> str:
        """Retrieve the full text of a previous answer from this conversation session. Use when the user refers to something discussed earlier and you need the exact details."""
        logger.info(f"[TOOL:retrieve_past_answer] ▶ exchange_id='{exchange_id}'")
        session = session_getter()
        full_answers = session.get("full_answers", {})
        entry = full_answers.get(exchange_id)
        if not entry:
            logger.info(f"[TOOL:retrieve_past_answer] ✗ not found")
            return f"No answer found for exchange_id '{exchange_id}'."
        if isinstance(entry, str):
            logger.info(f"[TOOL:retrieve_past_answer] ✓ legacy entry, {len(entry)} chars")
            return entry
        text = entry.get("text", "")
        sources = entry.get("sources", [])
        logger.info(f"[TOOL:retrieve_past_answer] ✓ {len(text)} chars, {len(sources)} sources")
        if sources:
            source_lines = []
            for s in sources:
                title = s.get("title", s.get("document_title", "?"))
                url = s.get("url", "")
                doc_id = s.get("document_id", "")
                line = f"- {title}"
                if url:
                    line += f" | URL: {url}"
                if doc_id:
                    line += f" | doc_id: {doc_id}"
                source_lines.append(line)
                # Capture into structured sources so they appear in the API response
                captured_sources.append({
                    "title": title,
                    "document_id": doc_id,
                    "snippet": s.get("snippet", ""),
                    "relevance_score": s.get("relevance_score", 0),
                    "url": url,
                    "file_path": s.get("file_path", ""),
                    "section_title": s.get("section_title", ""),
                    "chunk_index": s.get("chunk_index", 0),
                    "total_chunks": s.get("total_chunks", 0),
                    "document_title": s.get("document_title", ""),
                })
            text += "\n\n**Bronnen gebruikt voor dit antwoord:**\n" + "\n".join(source_lines)
        return text

    @tool
    def lookup_past_conversation(topic: str) -> str:
        """Search the Q&A index of this conversation by topic. Use when the user asks about something discussed earlier in the session, including questions about sources or URLs of previous answers."""
        logger.info(f"[TOOL:lookup_past_conversation] ▶ topic='{topic}'")
        session = session_getter()
        qa_index = session.get("qa_index", [])
        full_answers = session.get("full_answers", {})
        topic_lower = topic.lower()
        matches = []
        for entry in qa_index:
            entry_text = f"{entry.get('question_summary', '')} {entry.get('answer_summary', '')} {' '.join(entry.get('topics', []))}".lower()
            if topic_lower in entry_text:
                eid = entry.get('exchange_id', '')
                source_count = len(entry.get('source_ids', []))
                line = (
                    f"- [{eid}] Q: {entry.get('question_summary', '')} "
                    f"| A: {entry.get('answer_summary', '')} "
                    f"| topics: {', '.join(entry.get('topics', []))}"
                    f" | sources: {source_count}"
                )
                # Include source URLs/titles from full_answers if available
                fa = full_answers.get(eid, {})
                if isinstance(fa, dict):
                    sources = fa.get("sources", [])
                    if sources:
                        for s in sources:
                            title = s.get("title", s.get("document_title", ""))
                            url = s.get("url", "")
                            doc_id = s.get("document_id", "")
                            if title or url:
                                line += f"\n    - {title}"
                                if url:
                                    line += f" | URL: {url}"
                            # Capture into structured sources for the API response
                            captured_sources.append({
                                "title": title,
                                "document_id": doc_id,
                                "snippet": s.get("snippet", ""),
                                "relevance_score": s.get("relevance_score", 0),
                                "url": url,
                                "file_path": s.get("file_path", ""),
                                "section_title": s.get("section_title", ""),
                                "chunk_index": s.get("chunk_index", 0),
                                "total_chunks": s.get("total_chunks", 0),
                                "document_title": s.get("document_title", ""),
                            })
                matches.append(line)
        if matches:
            logger.info(f"[TOOL:lookup_past_conversation] ✓ {len(matches)} matches")
            return "\n".join(matches)
        logger.info(f"[TOOL:lookup_past_conversation] ✗ no matches for '{topic}'")
        return f"No past exchanges found matching topic '{topic}'."

    return [search_knowledge_base, retrieve_past_answer, lookup_past_conversation]


def make_execute_tools_node(tools: list, captured_sources: list):
    """Returns a graph node function that executes tool calls and captures sources.

    The node reads tool_calls from the last AIMessage, dispatches them,
    and returns ToolMessages + any new retrieved_sources (drained from
    the shared captured_sources list).
    """
    tool_map = {t.name: t for t in tools}

    def execute_tools(state: dict) -> dict:
        messages = state["messages"]
        # Find the last AIMessage with tool_calls
        last_ai: AIMessage = messages[-1]
        tool_calls = last_ai.tool_calls
        tool_names = [tc["name"] for tc in tool_calls]
        logger.info(f"[NODE:execute_tools] ▶ {len(tool_calls)} tool(s): {tool_names}")

        # Clear captured_sources before this round so we only get new ones
        captured_sources.clear()

        tool_messages: List[ToolMessage] = []

        for tc in tool_calls:
            name = tc["name"]
            args = tc["args"]
            tool_call_id = tc["id"]
            logger.info(f"[TOOL-CALL] {name}({args})")

            t = tool_map.get(name)
            if t is None:
                result = f"Unknown tool: {name}"
            else:
                try:
                    result = t.invoke(args)
                except Exception as e:
                    logger.error(f"Tool execution error ({name}): {e}")
                    result = f"Error executing {name}: {e}"

            logger.info(f"[TOOL-RESULT] {name} → {len(str(result))} chars")
            tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_call_id))

        # Drain captured sources into state (operator.add will accumulate)
        new_sources = list(captured_sources)
        captured_sources.clear()

        logger.info(f"[NODE:execute_tools] ✓ {len(tool_messages)} results, {len(new_sources)} new sources captured")
        return {"messages": tool_messages, "retrieved_sources": new_sources}

    return execute_tools
