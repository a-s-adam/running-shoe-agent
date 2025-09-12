# app/llm.py
from __future__ import annotations
import os
import json
import httpx
from typing import List, Dict, Any

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

def build_prompt(inputs: Dict[str, Any], candidates: List[Dict[str, Any]]) -> tuple[str, str]:
    """
    Render system and user prompts from templates.
    For simplicity we read files here (tiny project). In a larger app, cache them.
    """
    here = os.path.dirname(__file__)
    with open(os.path.join(here, "prompts", "system.txt"), "r", encoding="utf-8") as f:
        system_str = f.read().strip()

    with open(os.path.join(here, "prompts", "user_template.txt"), "r", encoding="utf-8") as f:
        user_tmpl = f.read()

    # Small, readable candidate table; include critical fields and richer specs when available
    lines = []
    for c in candidates:
        cat = ",".join(c.get('category', []))
        price = c.get('price_usd', '?')
        plate = c.get('plate', 'none')
        drop = c.get('drop_mm', '?')
        weight = c.get('weight_g', None)
        cushioning = c.get('cushioning_level', None)
        support = c.get('support_type', None)
        heel_stack = c.get('heel_stack_mm', None)
        fore_stack = c.get('forefoot_stack_mm', None)

        parts = [
            f"- {c['brand']} {c['model']}",
            f"cat={cat}",
            f"price=${price}",
            f"plate={plate}",
            f"drop={drop}mm"
        ]
        if weight is not None:
            parts.append(f"weight={weight}g")
        if cushioning:
            parts.append(f"cushioning={cushioning}")
        if support:
            parts.append(f"support={support}")
        if heel_stack is not None and fore_stack is not None:
            parts.append(f"stack={heel_stack}/{fore_stack}mm")

        lines.append(" | ".join(parts))
    candidate_table = "\n".join(lines)

    user_str = user_tmpl.replace(
        "{{inputs_json}}", json.dumps(inputs, ensure_ascii=False)
    ).replace(
        "{{candidate_table}}", candidate_table
    )
    return system_str, user_str

def complete(system_str: str, user_str: str, timeout_s: float = 30.0) -> List[str]:
    """
    Call Ollama /api/chat with a small message array.
    Expect the model to return a JSON array of strings (justifications).
    Fallback: if parsing fails, return generic justifications of equal length to candidates (handled by caller).
    """
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_str},
            {"role": "user", "content": user_str}
        ],
        "stream": False,
        # Keep it lightweight; adjust as needed
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
            "num_ctx": 2048
        }
    }

    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    text = data.get("message", {}).get("content", "").strip()

    # The prompt asks for a JSON array of strings. Try to parse directly first.
    try:
        justifications = json.loads(text)
        # Ensure list[str]
        if isinstance(justifications, list) and all(isinstance(x, str) for x in justifications):
            return justifications
    except Exception:
        pass

    # Best-effort recovery: handle code fences (```json ... ```)
    if "```" in text:
        try:
            # Split by code fences and find the JSON content
            parts = text.split("```")
            for part in parts:
                part = part.strip()
                # Skip if it's just "json" or empty
                if part.lower() == "json" or not part:
                    continue
                # Try to parse this part as JSON
                try:
                    justifications = json.loads(part)
                    if isinstance(justifications, list) and all(isinstance(x, str) for x in justifications):
                        return justifications
                except:
                    continue
        except Exception:
            pass

    # Try to extract JSON from the text using regex or other methods
    import re
    try:
        # Look for array patterns like [..., ..., ...]
        array_match = re.search(r'\[.*?\]', text, re.DOTALL)
        if array_match:
            array_text = array_match.group(0)
            justifications = json.loads(array_text)
            if isinstance(justifications, list) and all(isinstance(x, str) for x in justifications):
                return justifications
    except Exception:
        pass

    # As a last resort, return a single generic line; caller should duplicate per candidate length if needed.
    return ["Solid fit for the stated use; consider feel and budget tradeoffs."]


def complete_text(system_str: str, user_str: str, timeout_s: float = 30.0) -> str:
    """
    Call Ollama /api/chat and return the raw assistant text content.
    This is suitable for standard prose answers (not JSON lists).
    """
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_str},
            {"role": "user", "content": user_str},
        ],
        "stream": False,
        "options": {
            "temperature": float(os.getenv("OLLAMA_TEMPERATURE", 0.5)),
            "top_p": 0.9,
            "num_ctx": 2048,
        },
    }

    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        text = data.get("message", {}).get("content", "").strip()
        if text:
            return text
    except Exception:
        pass

    # Fallback textual response
    return "This shoe aligns with your stated needs; consider fit preference and budget."
