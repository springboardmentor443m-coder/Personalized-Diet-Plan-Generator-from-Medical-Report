"""Generate a personalised diet plan using an LLM."""

from __future__ import annotations

import json
import logging
import re
import time

from groq import Groq

from config.settings import (
    GROQ_API_KEY,
    DIET_GENERATION_MODEL,
    DIET_GENERATION_MODEL_FALLBACK,
    RATE_LIMIT_RETRY_DELAY_SECONDS,
    MAX_DIET_GENERATION_RETRIES,
)
from modules.diet_prompt_builder import build_diet_prompt

logger = logging.getLogger(__name__)


def _is_rate_limit_error(exc: Exception) -> bool:
    """Detect 429 / rate-limit errors."""
    if "RateLimit" in type(exc).__name__:
        return True
    if hasattr(exc, "status_code") and getattr(exc, "status_code", None) == 429:
        return True
    return False


def _clean_json_response(text: str) -> str:
    """Strip markdown fences if present."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _validate_diet_plan_structure(plan: dict) -> list[str]:
    """
    Lightweight structural validation of the generated diet plan.
    Returns a list of warnings (empty = all good).
    """
    warnings: list[str] = []

    if "clinical_reasoning" not in plan:
        warnings.append("Missing 'clinical_reasoning' section")
    if "dietary_guidelines" not in plan:
        warnings.append("Missing 'dietary_guidelines' section")
    if "weekly_meal_plan" not in plan:
        warnings.append("Missing 'weekly_meal_plan' section")
    if "disclaimer" not in plan:
        warnings.append("Missing 'disclaimer' — will be injected")
        plan["disclaimer"] = (
            "This diet plan is AI-generated based on lab data and should not "
            "replace professional medical advice. Consult a registered "
            "dietitian or physician before making dietary changes."
        )
    if "confidence_assessment" not in plan:
        warnings.append("Missing 'confidence_assessment' section")

    # Check meal plan completeness
    meal_plan = plan.get("weekly_meal_plan", {})
    for day_num in range(1, 8):
        day_key = f"day_{day_num}"
        if day_key not in meal_plan:
            warnings.append(f"Missing {day_key} in weekly_meal_plan")

    return warnings


def generate_diet_plan(
    aggregated_state: dict,
    per_doc_results: list[dict] | None = None,
) -> dict:
    """Generate a diet plan from aggregated health data and safety checks."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured.")

    system_prompt, user_prompt = build_diet_prompt(
        aggregated_state, per_doc_results,
    )

    client = Groq(api_key=GROQ_API_KEY)
    last_error: Exception | None = None

    models = [DIET_GENERATION_MODEL] * min(2, MAX_DIET_GENERATION_RETRIES) + [
        DIET_GENERATION_MODEL_FALLBACK
    ] * max(0, MAX_DIET_GENERATION_RETRIES - 1)
    models = models[:MAX_DIET_GENERATION_RETRIES] if models else [DIET_GENERATION_MODEL]

    for attempt, model in enumerate(models, start=1):
        try:
            gen_start = time.time()

            response = client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_completion_tokens=16384,
            )

            raw = response.choices[0].message.content or ""
            cleaned = _clean_json_response(raw)
            plan = json.loads(cleaned)

            gen_time = round(time.time() - gen_start, 2)

            structural_warnings = _validate_diet_plan_structure(plan)

            if structural_warnings:
                logger.warning(
                    "Diet plan structural warnings: %s", structural_warnings,
                )

            logger.info(
                "Diet plan generated (attempt %d, model=%s, %.1fs, %d chars)",
                attempt, model, gen_time, len(raw),
            )

            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return {
                "diet_plan": plan,
                "generation_metadata": {
                    "model": model,
                    "attempt": attempt,
                    "generation_time_seconds": gen_time,
                    "temperature": 0.3,
                    "token_usage": usage,
                },
                "structural_warnings": structural_warnings,
            }

        except json.JSONDecodeError as exc:
            last_error = exc
            logger.warning(
                "Diet generation attempt %d JSON parse error: %s",
                attempt, exc,
            )
            time.sleep(1.0 * attempt)

        except Exception as exc:
            last_error = exc
            if _is_rate_limit_error(exc):
                wait = RATE_LIMIT_RETRY_DELAY_SECONDS
                logger.warning(
                    "Rate-limit hit on diet generation (attempt %d), "
                    "waiting %.1fs",
                    attempt, wait,
                )
            else:
                wait = 2.0 * attempt
                logger.warning(
                    "Diet generation attempt %d failed (model=%s): %s",
                    attempt, model, exc,
                )
            time.sleep(wait)

    raise RuntimeError(
        f"Diet plan generation failed after {MAX_DIET_GENERATION_RETRIES} "
        f"attempts. Last error: {last_error}"
    )
