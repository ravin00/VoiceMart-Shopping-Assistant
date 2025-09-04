# app/query_engine/processor.py
import re
from typing import Dict, Any, Optional, Tuple

INTENT_PATTERNS = {
    "add_to_cart": re.compile(r"(add|buy|put)\s+(?P<qty>\d+)?\s*(?P<product>.+)", re.I),
    "remove_from_cart": re.compile(r"(remove|delete|take\s*out)\s+(?P<product>.+)", re.I),
    "search_product": re.compile(r"(find|search|show|look\s*for)\s+(?P<product>.+)", re.I),
    "show_cart": re.compile(r"\b(show|view).*\bcart\b", re.I),
    "checkout": re.compile(r"\b(checkout|place\s+order|pay)\b", re.I),
    "greeting": re.compile(r"\b(hi|hello|hey)\b", re.I),
}

def _detect(text: str) -> Tuple[str, Optional[re.Match]]:
    for intent, pattern in INTENT_PATTERNS.items():
        m = pattern.search(text)
        if m:
            return intent, m
    return "unknown", None

def process_query(
    text: str,
    user_id: Optional[str] = None,
    locale: Optional[str] = "en-US",
) -> Dict[str, Any]:
    """Return a JSON-serializable dict matching QueryResponse."""
    intent, m = _detect(text or "")
    slots: Dict[str, Any] = {"raw": text or ""}

    if m:
        gd = m.groupdict() or {}
        # clean values & convert qty to int when possible
        for k, v in gd.items():
            if not v:
                continue
            if k == "qty":
                try:
                    slots["qty"] = int(v)
                except:
                    pass
            else:
                slots[k] = v.strip()

    if intent == "add_to_cart":
        reply = f"Adding {slots.get('qty', 1)} of {slots.get('product','item')} to your cart…"
    elif intent == "remove_from_cart":
        reply = f"Removing {slots.get('product','item')} from your cart…"
    elif intent == "search_product":
        reply = f"Searching for {slots.get('product','item')}…"
    elif intent == "show_cart":
        reply = "Here’s what’s in your cart…"
    elif intent == "checkout":
        reply = "Proceeding to checkout…"
    elif intent == "greeting":
        reply = "Hello! How can I help you with shopping today?"
    else:
        reply = "Sorry, I didn’t understand that."

    return {
        "intent": intent,
        "confidence": 0.9 if intent != "unknown" else 0.3,
        "slots": slots,
        "reply": reply,
        "action": {"type": intent, "params": slots},
        "user_id": user_id,
        "locale": locale or "en-US",
    }
