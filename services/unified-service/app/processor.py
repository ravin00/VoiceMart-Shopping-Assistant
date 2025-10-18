# services/query-processor/app/processor.py
from __future__ import annotations
import os
import re
import json
from typing import Dict, Any, Optional, Tuple, List
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# =========================================================
# Feature flags (env)
# =========================================================
USE_SPACY = os.getenv("QP_USE_SPACY", "0") == "1"
SPACY_MODEL = os.getenv("QP_SPACY_MODEL", "en_core_web_sm")

USE_LLM = True
LLM_MODEL_NAME = os.getenv("QP_LLM_MODEL", "google/flan-t5-base")
LLM_MAX_NEW_TOKENS = int(os.getenv("QP_LLM_MAX_NEW_TOKENS", "256"))

print(f"[AGENT INIT] Query Processing Agent starting...")
print(f"[AGENT INIT] LLM Enabled: {USE_LLM}")
print(f"[AGENT INIT] LLM Model: {LLM_MODEL_NAME}")
print(f"[AGENT INIT] Agent Mode: ACTIVE")

# =========================================================
# Agent Memory & Reasoning Tracker
# =========================================================
class AgentMemory:
    """Tracks agent's reasoning process and decisions"""
    def __init__(self):
        self.reasoning_steps: List[str] = []
        self.decisions: List[Dict[str, Any]] = []
        self.observations: List[str] = []
        self.timestamp = datetime.now().isoformat()
    
    def add_reasoning(self, step: str):
        """Log a reasoning step"""
        self.reasoning_steps.append(step)
        print(f"[AGENT REASONING] {step}")
    
    def add_decision(self, decision: str, confidence: float, basis: str):
        """Log an agent decision"""
        self.decisions.append({
            "decision": decision,
            "confidence": confidence,
            "basis": basis,
            "timestamp": datetime.now().isoformat()
        })
        print(f"[AGENT DECISION] {decision} (confidence: {confidence:.2f}) - {basis}")
    
    def add_observation(self, observation: str):
        """Log an observation from processing"""
        self.observations.append(observation)
        print(f"[AGENT OBSERVATION] {observation}")
    
    def get_trace(self) -> Dict[str, Any]:
        """Get complete reasoning trace"""
        return {
            "reasoning_steps": self.reasoning_steps,
            "decisions": self.decisions,
            "observations": self.observations,
            "agent_session": self.timestamp
        }

_current_memory: Optional[AgentMemory] = None

def _get_memory() -> AgentMemory:
    """Get or create agent memory for current processing"""
    global _current_memory
    if _current_memory is None:
        _current_memory = AgentMemory()
    return _current_memory

def _reset_memory():
    """Reset memory for new query"""
    global _current_memory
    _current_memory = AgentMemory()

# =========================================================
# Lazy spaCy load
# =========================================================
_nlp = None
if USE_SPACY:
    try:
        import spacy
        _nlp = spacy.load(SPACY_MODEL)
    except Exception:
        _nlp = None
        USE_SPACY = False

# =========================================================
# LLM: lazy pipeline cache
# =========================================================
_llm_pipe = None
_llm_error: Optional[str] = None

def _get_llm():
    """Create and cache a small instruction model (FLAN-T5) when enabled."""
    global _llm_pipe, _llm_error
    if not USE_LLM:
        return None
    if _llm_pipe is not None:
        return _llm_pipe
    try:
        from transformers import pipeline
        _llm_pipe = pipeline("text2text-generation", model=LLM_MODEL_NAME, device=-1)
        return _llm_pipe
    except Exception as e:
        _llm_error = f"LLM init failed: {e}"
        return None

# =========================================================
# Guardrails / sanitation
# =========================================================
_MAX_TEXT_LEN = 600
def _sanitize(text: str) -> str:
    text = (text or "")[:_MAX_TEXT_LEN]
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", text)
    text = re.sub(r"(?:```|</?script>|@everyone|@here)", " ", text, flags=re.I)
    return text.strip()

# =========================================================
# Lexicons & patterns
# =========================================================
WORD_NUM = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "dozen": 12, "pair": 2, "pairs": 2,
}

UOMS = r"(packs?|packets?|pieces?|pcs?|bottles?|units?|cans?|bags?|boxes?|kg|g|lb|lbs|ml|l|liters?|litres?)"
COLORS = r"(black|white|red|blue|green|yellow|pink|purple|silver|gold|gray|grey|brown|beige|navy|orange)"
SIZES = r"(xxs|xs|s|m|l|xl|xxl|xxxl|small|medium|large|\d+[x×]\d+|\d+(\.\d+)?(cm|mm|in|inch|inches))"
BRANDS = r"(nike|adidas|puma|reebok|samsung|apple|sony|dell|hp|lenovo|milo|nestle|coke|pepsi|asus|acer|msi)"

CATEGORY_KEYWORDS = {
    "shoes": ["shoe", "shoes", "sneaker", "sneakers", "heels", "sandals", "boots"],
    "laptops": ["laptop", "notebook", "macbook", "chromebook"],
    "phones": ["phone", "smartphone", "iphone", "android"],
    "tshirts": ["t-shirt", "t shirt", "tee", "tees"],
    "beverages": ["milo", "coke", "pepsi", "coffee", "tea", "juice", "soda"],
}

TERM_FIXES = {
    r"\bshows\b": "shoes",
    r"\bmellow\b": "milo",
    r"\bcocks\b": "coke",
}

CURRENCY_SYMBOLS = r"[\$£€]|Rs\.?|LKR|USD|EUR|GBP|rs|lkr|usd|eur|gbp"
CURRENCY_WORDS = {
    "dollar": "USD", "dollars": "USD", "$": "USD", "usd": "USD",
    "rupee": "LKR", "rupees": "LKR", "rs": "LKR", "lkr": "LKR",
    "euro": "EUR", "euros": "EUR", "€": "EUR", "eur": "EUR",
    "gbp": "GBP", "pound": "GBP", "pounds": "GBP", "£": "GBP",
}
CURRENCY_SYMBOL_FOR = {"USD": "$", "LKR": "Rs", "EUR": "€", "GBP": "£"}

# =========================================================
# Intent patterns - IMPROVED V2
# =========================================================
INTENT_PATTERNS = {
    "greeting": re.compile(r"^(hi|hello|hey|greetings|good\s*(morning|afternoon|evening))\b", re.I),
    
    "search_product": re.compile(
        rf"(?:find|search|show|looking\s*for|need|want|get)\s+(?:me\s+)?(?P<product>[\w\s]+?)(?:\s+(?P<brand>{BRANDS}))?(?:\s+between|under|over|from|and|\s*$)",
        re.I
    ),
    
    "add_to_cart": re.compile(
        rf"(?:add|put|place)\s+(?P<qty_num>\d+|\w+)?\s*(?P<uom>{UOMS})?\s*(?:of\s+)?(?P<product>[\w\s]+?)(?=\s+to\s+(?:my\s*)?(?:cart|basket))",
        re.I
    ),
    
    "remove_from_cart": re.compile(
        r"(?:remove|delete|take\s*out)\s+(?P<product>[\w\s]+?)\s*(?:from\s*(?:my\s*)?(?:cart|basket))",
        re.I
    ),
    
    "show_cart": re.compile(r"(?:show|view|display|what'?s?\s*in)\s*(?:my\s*)?(?:cart|basket)", re.I),
    
    "checkout": re.compile(r"(?:checkout|proceed\s*to\s*checkout|place\s*order|buy\s*now)", re.I),
}

# =========================================================
# Regex extractors
# =========================================================
COLOR_RE = re.compile(rf"\b{COLORS}\b", re.I)
SIZE_RE = re.compile(rf"\b{SIZES}\b", re.I)
BRAND_RE = re.compile(rf"\b{BRANDS}\b", re.I)
PRICE_UNDER_RE = re.compile(
    rf"(?:under|below|less\s*than)\s*(?P<cur>{CURRENCY_SYMBOLS})?\s*(?P<val>[\d,.]+(?:[km])?)", re.I
)
PRICE_OVER_RE = re.compile(
    rf"(?:over|above|more\s*than|at\s*least)\s*(?P<cur>{CURRENCY_SYMBOLS})?\s*(?P<val>[\d,.]+(?:[km])?)", re.I
)
PRICE_BETWEEN_RE = re.compile(
    rf"(?:between|from)\s*(?P<cur1>{CURRENCY_SYMBOLS})?\s*(?P<min>[\d,.]+(?:[km])?)\s*(?:and|to|-)\s*(?P<cur2>{CURRENCY_SYMBOLS})?\s*(?P<max>[\d,.]+(?:[km])?)", re.I
)
PRICE_PHRASE_RE = re.compile(
    r"\s*(?:under|below|less\s*than|over|above|more\s*than|at\s*least|between|from)\b.*$", re.I
)

# =========================================================
# Helpers
# =========================================================
def _fix_terms(text: str) -> str:
    for pat, repl in TERM_FIXES.items():
        text = re.sub(pat, repl, text, flags=re.I)
    return text

def _to_float(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    s = s.strip().lower().replace(",", "")
    try:
        if s.endswith("k"):
            return float(s[:-1]) * 1000
        if s.endswith("m"):
            return float(s[:-1]) * 1_000_000
        return float(s)
    except Exception:
        return None

def _to_int(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    s = s.strip().lower()
    if s in WORD_NUM:
        return WORD_NUM[s]
    try:
        return int(s)
    except Exception:
        return None

def _normalize_product(text: str) -> str:
    """Strip extra words and normalize product name."""
    text = re.sub(r"\b(find|search|show|get|need|want|looking\s+for)\b", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _strip_price_phrases(text: str) -> str:
    """Remove price-related phrases from product name."""
    return PRICE_PHRASE_RE.sub("", text).strip()

def _currency_code(cur_str: str) -> Optional[str]:
    """Convert currency string/symbol to standard code."""
    cur_str = cur_str.strip().lower()
    return CURRENCY_WORDS.get(cur_str)

def _infer_category(product: str) -> Optional[str]:
    """Infer category from product name."""
    product_lower = product.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in product_lower:
                return cat
    return None

def _ner_pass(text: str, slots: Dict[str, Any]) -> None:
    """Use spaCy NER to enrich slots if available."""
    if not _nlp:
        return
    try:
        doc = _nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PRODUCT" and "product" not in slots:
                slots["product"] = ent.text.strip()
            elif ent.label_ == "ORG" and "brand" not in slots:
                slots["brand"] = ent.text.strip()
            elif ent.label_ == "MONEY":
                val = _to_float(re.sub(r"[^\d.,km]", "", ent.text, flags=re.I))
                if val and "price_max" not in slots:
                    slots["price_max"] = val
    except Exception:
        pass

# =========================================================
# LLM Clarifier
# =========================================================
def _clarify_with_llm(text: str) -> Dict[str, Any]:
    pipe = _get_llm()
    if pipe is None:
        return {}

    prompt = f"""Extract e-commerce query information and return ONLY valid JSON.

Required fields:
- intent: one of [search_product, add_to_cart, remove_from_cart, show_cart, checkout, greeting, unknown]
- product: the main product name (e.g., "gaming laptop", "shoes", "milo")
- brand: brand name if mentioned (e.g., "asus", "nike")
- category: product category if clear (e.g., "laptops", "shoes", "beverages")
- price_min: minimum price as number (extract from "over", "above", "at least")
- price_max: maximum price as number (extract from "under", "below", "budget", "around")
- currency: currency code (LKR, USD, EUR, GBP)

Examples:
Input: "I need a gaming laptop maybe Asus, budget around 300k"
Output: {{"intent":"search_product","product":"gaming laptop","brand":"asus","price_max":300000,"currency":"LKR"}}

Input: "find nike shoes under $100"
Output: {{"intent":"search_product","product":"shoes","brand":"nike","price_max":100,"currency":"USD"}}

Input: "add 2 packs of milo"
Output: {{"intent":"add_to_cart","product":"milo","quantity":2}}

Now process this query and return ONLY the JSON object, no other text:
Query: {text}
JSON:"""

    try:
        response = pipe(prompt, max_new_tokens=LLM_MAX_NEW_TOKENS)[0]["generated_text"]
        print(f"[LLM] Clarifier triggered for: {text}")
        print(f"[LLM] Raw model output: {response}")

        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response.strip()
            if not json_str.startswith('{'):
                json_str = '{' + json_str + '}'

        json_str = re.sub(r'(\w+):', r'"\1":', json_str)
        json_str = re.sub(r':"(\d+)"', r':\1', json_str)
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        print(f"[LLM] Cleaned JSON candidate: {json_str}")

        result = json.loads(json_str)

        for key in ["price_min", "price_max"]:
            if key in result and isinstance(result[key], str):
                val_str = str(result[key]).lower().replace(",", "")
                if val_str.endswith("k"):
                    result[key] = float(val_str[:-1]) * 1000
                else:
                    result[key] = float(val_str)

        if result.get("intent"):
            info = f"[LLM OK] Parsed: {result.get('intent')} | Product: {result.get('product')} | Brand: {result.get('brand')} | Price: {result.get('price_max')}"
            print(info)

        return result

    except Exception as e:
        print(f"[LLM clarifier failed] {e}")
        import traceback
        traceback.print_exc()
        return {}

def _validate_structured(d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if isinstance(d.get("brand"), str) and 0 < len(d["brand"]) <= 50:
        out["brand"] = d["brand"].strip()
    if isinstance(d.get("product"), str) and 0 < len(d["product"]) <= 120:
        out["product"] = d["product"].strip()
    for k in ("price_limit", "price_max", "price_min"):
        if k in d:
            try:
                out[k] = float(str(d[k]).replace(",", ""))
            except Exception:
                pass
    if isinstance(d.get("intent"), str) and d["intent"]:
        out["intent"] = d["intent"].strip().lower()
    if isinstance(d.get("category"), str) and d["category"]:
        out["category"] = d["category"].strip().lower()
    if isinstance(d.get("currency"), str) and d["currency"]:
        out["currency"] = d["currency"].strip()
    return out

# =========================================================
# Intent detection helper
# =========================================================
def _detect(text: str) -> Tuple[str, Optional[re.Match]]:
    """Detect user intent from text using regex patterns."""
    for intent, pat in INTENT_PATTERNS.items():
        m = pat.search(text)
        if m:
            return intent, m
    return "unknown", None

# =========================================================
# Public entry point
# =========================================================
def process_query(
    text: str,
    user_id: Optional[str] = None,
    locale: Optional[str] = "en-US",
) -> Dict[str, Any]:
    """
    INTELLIGENT AGENT: Query Processing with Reasoning
    
    Agent Capabilities:
    1. Perceives: Receives and sanitizes natural language input
    2. Reasons: Uses LLM to understand intent and entities
    3. Decides: Determines best extraction strategy
    4. Acts: Structures data for downstream services
    5. Evaluates: Calculates confidence and adjusts behavior
    """
    
    _reset_memory()
    memory = _get_memory()
    
    print(f"\n{'='*60}")
    print(f"[AGENT START] Processing query: '{text}'")
    print(f"[AGENT START] User: {user_id or 'anonymous'}")
    print(f"{'='*60}\n")
    
    memory.add_reasoning("Step 1: Perceiving input - sanitizing and normalizing text")
    text = _sanitize(text)
    text = _fix_terms(text)
    memory.add_observation(f"Cleaned text: '{text}'")
    
    memory.add_reasoning("Step 2: Initial analysis - detecting intent patterns")
    intent, m = _detect(text)
    memory.add_observation(f"Pattern matching found: intent='{intent}'")
    
    slots: Dict[str, Any] = {"raw": text}

    memory.add_reasoning("Step 3: Entity extraction - identifying attributes from text")
    
    if (c := COLOR_RE.search(text)): 
        slots["color"] = c.group(1).lower()
        memory.add_observation(f"Extracted color: {slots['color']}")
    if (s := SIZE_RE.search(text)):  
        slots["size"]  = s.group(1).lower()
        memory.add_observation(f"Extracted size: {slots['size']}")
    if (b := BRAND_RE.search(text)): 
        slots["brand"] = b.group(1).lower()
        memory.add_observation(f"Extracted brand: {slots['brand']}")

    memory.add_reasoning("Step 4: Price analysis - detecting budget constraints")
    
    if (rng := PRICE_BETWEEN_RE.search(text)):
        mn, mx = _to_float(rng.group("min")), _to_float(rng.group("max"))
        if mn is not None: 
            slots["price_min"] = mn
            memory.add_observation(f"Extracted min price: {mn}")
        if mx is not None: 
            slots["price_max"] = mx
            memory.add_observation(f"Extracted max price: {mx}")
        if (rng.group("cur1") or rng.group("cur2")):
            slots["currency"] = (rng.group("cur1") or rng.group("cur2"))

    if (mxm := PRICE_UNDER_RE.search(text)) and "price_max" not in slots:
        val = _to_float(mxm.group("val"))
        if val is not None:
            slots["price_max"] = val
            memory.add_observation(f"Extracted max price: {val}")
            if mxm.group("cur"): slots["currency"] = mxm.group("cur")

    if (mnp := PRICE_OVER_RE.search(text)) and "price_min" not in slots:
        val = _to_float(mnp.group("val"))
        if val is not None:
            slots["price_min"] = val
            memory.add_observation(f"Extracted min price: {val}")
            if mnp.group("cur"): slots["currency"] = mnp.group("cur")

    if m:
        memory.add_reasoning("Step 5: Intent-specific processing - extracting context")
        gd = m.groupdict() or {}
        if intent == "add_to_cart":
            if (q := _to_int(gd.get("qty_num"))) is not None:
                slots["qty"] = q
                memory.add_observation(f"Quantity: {q}")
            if gd.get("uom"):
                slots["uom"] = gd["uom"].lower()

        pmx = _to_float(gd.get("price_max"))
        pmn = _to_float(gd.get("price_min"))
        if pmx is not None: slots["price_max"] = pmx
        if pmn is not None: slots["price_min"] = pmn
        if gd.get("cur1"): slots["currency"] = gd["cur1"]
        if gd.get("cur2"): slots["currency"] = gd["cur2"]

        if gd.get("color"): slots["color"] = gd["color"].lower()
        if gd.get("size"):  slots["size"]  = gd["size"].lower()
        if gd.get("brand"): slots["brand"] = gd["brand"].lower()

        if (p := gd.get("product")):
            p = _normalize_product(p)
            p = _strip_price_phrases(p)
            slots["product"] = p
            memory.add_observation(f"Product identified: {p}")

    memory.add_reasoning("Step 6: NER enrichment - using spaCy for entity recognition")
    _ner_pass(text, slots)

    if "product" in slots:
        memory.add_reasoning("Step 7: Category inference - mapping product to category")
        if (cat := _infer_category(slots["product"])):
            slots["category"] = cat
            memory.add_observation(f"Inferred category: {cat}")

    if "currency" in slots:
        memory.add_reasoning("Step 8: Currency normalization - standardizing currency format")
        code = _currency_code(slots["currency"])
        if code:
            slots["currency"] = CURRENCY_SYMBOL_FOR.get(code, slots["currency"])
            memory.add_observation(f"Normalized currency: {slots['currency']}")

    if "price_max" in slots and "price_min" not in slots:
        slots["price_limit"] = slots["price_max"]

    llm_used = False
    clarified: Dict[str, Any] = {}
    
    memory.add_reasoning("Step 10: LLM Agent activation - applying language model intelligence")
    memory.add_decision(
        "Activating LLM for deep understanding",
        confidence=0.9,
        basis="Agent mode enabled for all queries"
    )
    
    if USE_LLM:
        print(f"[AGENT LLM] Triggering language model for: {text}")
        clarified = _validate_structured(_clarify_with_llm(text))
        if clarified:
            llm_used = True
            memory.add_observation(f"LLM extracted: {list(clarified.keys())}")
            print(f"[AGENT LLM] Successfully extracted: {clarified}")

            intent_map = {
                "buy": "search_product",
                "purchase": "search_product",
                "order": "add_to_cart",
            }
            if "intent" in clarified:
                clarified_intent = clarified["intent"].lower()
                normalized_intent = intent_map.get(clarified_intent, clarified_intent)
                clarified["intent"] = normalized_intent
                if intent == "unknown":
                    intent = normalized_intent
                    memory.add_decision(
                        f"Intent resolved to: {intent}",
                        confidence=0.8,
                        basis="LLM understanding"
                    )

            for k in ("product", "brand", "category", "price_min", "price_max", "currency"):
                if k in clarified:
                    old_val = slots.get(k)
                    slots[k] = clarified[k]
                    if old_val != clarified[k]:
                        memory.add_observation(f"LLM corrected {k}: {old_val} → {clarified[k]}")

            if "currency" in slots:
                code = _currency_code(slots["currency"])
                if code:
                    slots["currency"] = CURRENCY_SYMBOL_FOR.get(code, slots["currency"])

            if "category" not in slots and "product" in slots:
                cat = _infer_category(slots["product"])
                if cat:
                    slots["category"] = cat

    memory.add_reasoning("Step 11: Confidence evaluation - assessing understanding quality")
    
    if llm_used:
        slots["__llm_used"] = True
        slots["__llm_model"] = LLM_MODEL_NAME
        slots["__llm_raw"] = clarified
    elif USE_LLM and _llm_error:
        slots["__llm_error"] = _llm_error

    if "price_min" in slots and "price_max" in slots and slots["price_min"] == slots["price_max"]:
        slots.pop("price_min")

    memory.add_reasoning("Step 12: Response generation - creating user-friendly reply")
    
    if intent == "greeting":
        reply = "Hi! Try: 'find Nike shoes under $100', 'add 2 packs of Milo', 'show cart', or 'checkout'."
    elif intent == "search_product":
        p = slots.get("product", "the item")
        bits = []
        if "brand" in slots: 
            bits.append(slots["brand"])
        if "color" in slots: 
            bits.append(slots["color"])
        if "size" in slots:  
            bits.append(slots["size"])
        if "price_min" in slots: 
            bits.append(f"over {slots.get('currency', '$')}{slots['price_min']}")
        if "price_max" in slots: 
            bits.append(f"under {slots.get('currency', '$')}{slots['price_max']}")
        suffix = f" ({', '.join(bits)})" if bits else ""
        reply = f"Searching for {p}{suffix}…"
    elif intent == "add_to_cart":
        qty = slots.get("qty", 1)
        uom = f" {slots['uom']}" if "uom" in slots else ""
        prod = slots.get("product", "item")
        reply = f"Adding {qty}{uom} of {prod} to your cart…"
    elif intent == "remove_from_cart":
        reply = f"Removing {slots.get('product','that item')} from your cart…"
    elif intent == "show_cart":
        reply = "Here's what's in your cart…"
    elif intent == "checkout":
        reply = "Proceeding to checkout…"
    else:
        reply = "Sorry, I didn't understand that."
        memory.add_decision(
            "Requesting clarification",
            confidence=0.3,
            basis="Unable to determine clear intent"
        )

    confidence = 0.9 if intent in {
        "add_to_cart","remove_from_cart","search_product","show_cart","checkout","greeting"
    } else 0.3
    if llm_used and confidence < 0.8:
        confidence = 0.8
    
    memory.add_decision(
        f"Final confidence: {confidence}",
        confidence=confidence,
        basis=f"{'LLM-enhanced' if llm_used else 'Pattern-based'} extraction with {len(slots)} entities"
    )
    
    agent_trace = memory.get_trace()
    
    print(f"\n[AGENT COMPLETE] Processed successfully")
    print(f"[AGENT COMPLETE] Intent: {intent} | Confidence: {confidence}")
    print(f"[AGENT COMPLETE] Entities extracted: {len(slots)}")
    print(f"{'='*60}\n")

    return {
        "intent": intent,
        "confidence": round(confidence, 2),
        "slots": slots,
        "reply": reply,
        "action": {"type": intent, "params": slots},
        "user_id": user_id,
        "locale": locale or "en-US",
        
        "agent_metadata": {
            "is_agent": True,
            "agent_type": "query_understanding_agent",
            "reasoning_trace": agent_trace["reasoning_steps"],
            "decisions_made": agent_trace["decisions"],
            "observations": agent_trace["observations"],
            "processing_timestamp": agent_trace["agent_session"],
            "llm_powered": llm_used,
            "model": LLM_MODEL_NAME if llm_used else "rule-based"
        }
    }