"""
prompt.py — Prompt Templates (Phase 3)

Defines the system prompt and user prompt template used for LLM inference.
Prompt design enforces:
  - Facts-only answers (no prior knowledge)
  - Maximum 3 sentences
  - Exactly one citation link
  - No investment advice, opinions, or comparisons
  - Graceful fallback when answer is not in context
"""

SYSTEM_PROMPT = """You are a facts-only mutual fund FAQ assistant.

Rules you MUST follow:
1. Answer ONLY using the provided context. Do NOT use prior knowledge.
2. Limit your response to a MAXIMUM of 3 sentences.
3. Include EXACTLY ONE source citation link from the context metadata.
4. Do NOT provide investment advice, opinions, recommendations, or comparisons.
5. Do NOT perform or reference return calculations or performance comparisons.
6. If the answer is not in the context, respond EXACTLY:
   "I could not find this information in the official documents."
7. Respond in English only.
"""

USER_PROMPT_TEMPLATE = """Context:
{context}

Question: {question}

Answer (max 3 sentences, include one source link):"""


def build_prompt(context: str, question: str) -> str:
    """Format the user prompt with retrieved context and user question."""
    q_lower = question.lower()
    # Handle known historical scheme renames (e.g. Parag Parikh Long Term Value -> Flexi Cap)
    if "parag parikh" in q_lower and "long term" in q_lower:
        context = "(Note: Parag Parikh Flexi Cap Fund Direct Growth was formerly known as Parag Parikh Long Term Value Fund.)\n\n" + context

    return USER_PROMPT_TEMPLATE.format(context=context, question=question)

