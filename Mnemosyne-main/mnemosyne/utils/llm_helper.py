import os
from typing import Optional, Dict, Any

def summarize_diff_with_llm(diff_text: str) -> Dict[str, str]:
    """
    Summarizes a git diff into a structured root cause and fix summary.
    Falls back to smart static analysis if no LLM backend is available.

    Uses whatever provider configure_llm_env() sets up — Ollama (local & free)
    by default, or OpenAI if configured.
    """
    from mnemosyne.config import configure_llm_env
    configure_llm_env()

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    model = os.getenv("MNEMOSYNE_LLM_MODEL", "gpt-4o-mini")
    if api_key and len(diff_text.strip()) > 10:
        try:
            import openai
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a code memory assistant. Analyze the diff and output JSON with keys: title, root_cause, fix_description."},
                    {"role": "user", "content": f"Analyze this diff:\n\n{diff_text[:2000]}"}
                ],
                response_format={"type": "json_object"}
            )
            import json
            data = json.loads(response.choices[0].message.content)
            return {
                "title": data.get("title", "Code modification"),
                "root_cause": data.get("root_cause", "Unchecked condition in changed code"),
                "fix_description": data.get("fix_description", "Updated logic to validate conditions")
            }
        except Exception:
            pass

    # Fallback pattern summarizer
    title = "Bug fix patch"
    root_cause = "Potential unhandled edge case or missing validation"
    fix_description = "Applied defensive check and validated response fields"
    
    if "None" in diff_text or "null" in diff_text or "if not" in diff_text:
        title = "Unchecked response / null handling fix"
        root_cause = "Missing null-check on external object return value"
        fix_description = "Added guard clause verifying return value is not None before property access"

    return {
        "title": title,
        "root_cause": root_cause,
        "fix_description": fix_description
    }
