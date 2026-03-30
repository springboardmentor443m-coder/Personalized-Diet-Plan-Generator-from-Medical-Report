"""
core/chat.py
Step 7: Context-aware AI Chat Assistant (Llama 3.3 70B Versatile on Groq)
Uses the extracted report data + diet plan as context — no RAG/ChromaDB required.
"""

import os
import json
from typing import Dict, List, Optional

from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CHAT_SYSTEM_TEMPLATE = """You are AI-NutriCare, a friendly and knowledgeable medical nutrition assistant.
You have access to the patient's medical report data and their personalised diet plan.

PATIENT MEDICAL REPORT (JSON):
{report_json}

PERSONALISED DIET PLAN (JSON):
{diet_json}

INSTRUCTIONS:
- Answer questions about the patient's lab results clearly in plain language.
- Explain what abnormal values mean and how they relate to diet.
- Refer specifically to the patient's actual values when answering.
- If asked about the diet plan, explain recommendations with reasons.
- Keep answers concise, warm, and practical.
- Always remind the user to consult a doctor for medical decisions.
- Never fabricate lab values — only use data from the report above."""


def build_context(extracted_data: Dict, diet_plan: Optional[Dict]) -> str:
    """Serialize context into a system prompt."""
    report_json = json.dumps(extracted_data, indent=2)[:6000]   # keep within token limits
    diet_json   = json.dumps(diet_plan,      indent=2)[:3000] if diet_plan else "Not generated yet."
    return CHAT_SYSTEM_TEMPLATE.format(report_json=report_json, diet_json=diet_json)


def chat_with_report(
    question: str,
    extracted_data: Dict,
    diet_plan: Optional[Dict],
    chat_history: List[Dict],
) -> str:
    """
    Send a question to Llama 3.3 70B with full report context.
    chat_history is a list of {"role": "user"/"assistant", "content": "..."} dicts.
    Returns the assistant's reply as a plain string.
    """
    system_prompt = build_context(extracted_data, diet_plan)

    # Build messages: system + history + new question
    messages = [{"role": "system", "content": system_prompt}]

    # Include last 6 turns of history to keep context window manageable
    for msg in chat_history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1024,
        temperature=0.3,
    )

    return response.choices[0].message.content
