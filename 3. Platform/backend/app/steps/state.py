"""Shared state definition and constants for the chat pipeline.

Every step module reads from / writes to ``ChatState``.  Keeping the
type in a single place avoids circular imports between step modules
and the graph wiring file.
"""

from __future__ import annotations

import operator
from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# Maximum tool-call rounds before forcing a text reply
MAX_TOOL_ROUNDS = 3

# Unique markers for user vs. assistant attribution in memory.
M_USR = "[§USR]"
M_BOT = "[§BOT]"


class ChatState(TypedDict, total=False):
    # --- Input (set at invocation) ---
    message: str
    session_id: str
    user_context: dict
    use_memory: bool

    # --- Session (set by load_session) ---
    session: dict  # SessionMemory.model_dump()

    # --- LLM messages (managed by add_messages reducer) ---
    messages: Annotated[list[BaseMessage], add_messages]

    # --- Sources (accumulated by execute_tools via operator.add) ---
    retrieved_sources: Annotated[list, operator.add]

    # --- Output (set by later nodes) ---
    assistant_text: str
    exchange_id: str
    unique_sources: list
    source_ids: list
    response: dict

    # --- Triage (set by triage validators, before LLM) ---
    triage: dict  # {route, skip_llm, early_response, triage_log}

    # --- Validation (set by validator nodes, after LLM) ---
    source_validation: dict   # {grounded, issues, confidence}
    tone_validation: dict     # {appropriate, original_text, adjustments}
    output_guardrail: dict    # {safe, issues, original_text}
    answer_evaluation: dict   # {overall, relevance, tone, policy_compliance, groundedness, completeness, notes}
    answer_evaluation_before: dict  # evaluation snapshot before refinement
    refine_decision: dict     # {should_refine, reasons, thresholds, scores_used}
    refined_once: bool

    # --- Internal: track tool rounds ---
    tool_rounds: int
