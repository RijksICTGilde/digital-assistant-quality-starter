"""Prompt-building step node."""

from __future__ import annotations

from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from loguru import logger

from app.steps.state import ChatState

SYSTEM_PROMPT = """Je bent Kletsmajoor, AI-assistent voor Nederlandse overheden. Antwoord in het Nederlands.

KERNREGEL: Baseer je antwoord op de tool-resultaten van search_knowledge_base. Citeer specifieke feiten, datums en artikelnummers uit de gevonden documenten. Verzin niets. Als de gevonden documenten geen antwoord geven op de specifieke vraag van de gebruiker, zeg dan eerlijk dat je de gevraagde informatie niet hebt kunnen vinden in de kennisbank.

TOOL-KEUZE:
- Nieuwe feitelijke vraag → gebruik search_knowledge_base.
- Vraag over bronnen, URLs, documenten van een eerder antwoord → gebruik lookup_past_conversation (om het exchange_id te vinden) en daarna retrieve_past_answer (om de volledige bronnen inclusief URLs op te halen). Gebruik NIET search_knowledge_base voor dit soort meta-vragen.
- Verwijzing naar iets specifieks dat eerder in het gesprek is besproken → gebruik lookup_past_conversation met het onderwerp als zoekterm.
- Vraag om samenvatting/overzicht van DIT GESPREK → gebruik get_conversation_summary (geen parameters). Dit geeft alle besproken onderwerpen terug.

GEHEUGEN:
- Hieronder staat "Wat je AL hebt beantwoord" met een SAMENVATTING van vorige antwoorden.
- Je ziet ook welke bronnen je al hebt geciteerd.
- Je kunt lookup_past_conversation gebruiken om een exchange_id te vinden, en retrieve_past_answer om de volledige tekst op te halen als je die nodig hebt.

BELANGRIJK – GEEN HERHALING:
- Bekijk de "Eerdere vragen" sectie hieronder. De "answer_summary" toont wat je AL hebt gezegd.
- HERHAAL NIET wat in de answer_summary staat. De gebruiker kan je vorige antwoord nog zien.
- Bij "vertel me meer" of vervolgvragen: geef ALLEEN NIEUWE informatie uit de bronnen.
- Begin NOOIT met dezelfde definitie of uitleg die je eerder gaf.
- Start vervolgantwoorden met iets als: "Aanvullend op wat ik eerder noemde..." of "Daarnaast is belangrijk dat..."
- Haal je eerdere antwoord ALLEEN op via retrieve_past_answer als je een specifiek feit moet verifiëren — niet om te kopiëren.

STIJL:
- Wees concreet. Noem datums, artikelnummers, namen als die in de bronnen staan.
- Gebruik markdown headers (##, ###) en opsommingen om het antwoord te structureren.
- Gebruik korte alinea's (2-4 zinnen) met een witregel ertussen. Geen lange lappen tekst.
- Blijf zo dicht mogelijk bij de originele formulering uit de bronnen. Parafraseer alleen waar nodig voor leesbaarheid.

ANTWOORDLENGTE:
- Geef een volledig en informatief antwoord met alle relevante details uit de bronnen.
- Citeer concrete feiten, datums, artikelnummers en namen uit de documenten.
- Structureer lange antwoorden met headers en opsommingen voor leesbaarheid.
"""


def build_prompt(state: ChatState) -> dict:
    """Build the 3-layer system prompt + conversation messages."""
    session = state["session"]
    message = state["message"]
    user_context = state.get("user_context", {})
    use_memory = state.get("use_memory", True)

    logger.info(f"[NODE:build_prompt] ▶ message='{message[:80]}...'" if len(message) > 80 else f"[NODE:build_prompt] ▶ message='{message}'")

    # Build system prompt parts
    parts: List[str] = [SYSTEM_PROMPT]

    if use_memory:
        # Layer 2: session summary
        summary = session.get("summary", "")
        if summary:
            parts.append(f"\n## Sessie-samenvatting\n{summary}")
            logger.debug(f"[NODE:build_prompt] Layer 2: summary ({len(summary)} chars)")

        # Layer 3: Q&A index (last 10) - simplified format
        qa_index = session.get("qa_index", [])
        if qa_index:
            logger.debug(f"[NODE:build_prompt] Layer 3: qa_index ({len(qa_index)} entries)")
            index_lines = []
            all_used_source_ids = []
            for entry in qa_index[-10:]:
                source_ids = entry.get("source_ids", [])
                all_used_source_ids.extend(source_ids)
                # Simplified format: just what's needed to avoid repetition
                index_lines.append(
                    f"- [{entry.get('exchange_id', '')}] "
                    f"Vraag: {entry.get('question_summary', '')} → "
                    f"Antwoord: {entry.get('answer_summary', '')}"
                )
            parts.append(
                "\n## Wat je AL hebt beantwoord (NIET HERHALEN)\n"
                + "\n".join(index_lines)
            )
            # Add used source IDs so LLM knows what was already cited
            if all_used_source_ids:
                unique_sources = list(dict.fromkeys(all_used_source_ids))  # preserve order, remove dupes
                logger.debug(f"[NODE:build_prompt] Layer 3b: {len(unique_sources)} used source IDs")
                parts.append(
                    f"\n## Bronnen die je AL hebt geciteerd\n"
                    f"Als dezelfde bronnen terugkomen in search_knowledge_base, "
                    f"focus dan op ANDERE informatie uit die bronnen.\n"
                    f"Gebruikte bron-IDs: {', '.join(unique_sources[:10])}"  # max 10 to avoid clutter
                )

    # User context
    if user_context:
        ctx_str = ", ".join(f"{k}: {v}" for k, v in user_context.items() if v)
        if ctx_str:
            parts.append(f"\n## Gebruikerscontext\n{ctx_str}")

    system_content = "\n".join(parts)
    logger.debug(f"[NODE:build_prompt] Full system prompt:\n{system_content}")
    msgs: List[BaseMessage] = [SystemMessage(content=system_content)]

    # Layer 1: recent USER messages only (not assistant responses)
    # This prevents the LLM from copy-pasting its previous answers.
    # The LLM can retrieve full answers via retrieve_past_answer tool if needed.
    # The Q&A index in the system prompt shows exchange_ids for retrieval.
    if use_memory:
        recent = session.get("recent_messages", [])[-10:]
        user_msg_count = 0
        for msg in recent:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if content.strip():
                    msgs.append(HumanMessage(content=content))
                    # Placeholder so LLM knows it responded (without copy-paste material)
                    msgs.append(AIMessage(content="[Antwoord gegeven]"))
                    user_msg_count += 1
        logger.debug(f"[NODE:build_prompt] Layer 1: {user_msg_count} user messages (no assistant content)")

    # Current user message
    msgs.append(HumanMessage(content=message))

    recent_count = len([m for m in msgs if not isinstance(m, SystemMessage)]) - 1  # exclude current user msg
    logger.info(
        f"[NODE:build_prompt] ✓ {len(msgs)} messages "
        f"(system: {len(system_content)} chars, history: {recent_count} msgs, "
        f"user_context: {bool(user_context)})"
    )

    return {"messages": msgs, "retrieved_sources": [], "tool_rounds": 0}
