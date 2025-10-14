# services/query-processor/app/processor.py
from __future__ import annotations
import os
import re
import json
from typing import Dict, Any, Optional, Tuple

from dotenv import load_dotenv
load_dotenv()  # read QP_* vars from .env if present

# =========================================================
# Feature flags (env)
# =========================================================
USE_SPACY = os.getenv("QP_USE_SPACY", "0") == "1"
SPACY_MODEL = os.getenv("QP_SPACY_MODEL", "en_core_web_sm")

USE_LLM = os.getenv("QP_USE_LLM", "0") == "1"
LLM_MODEL_NAME = os.getenv("QP_LLM_MODEL", "google/flan-t5-small")
LLM_MAX_NEW_TOKENS = int(os.getenv("QP_LLM_MAX_NEW_TOKENS", "128"))

# =========================================================
# Lazy spaCy load
# =========================================================
_nlp = None
if USE_SPACY:
    try:
        import spacy  # type: ignore
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
        from transformers import pipeline  # type: ignore
        _llm_pipe = pipeline(
            "text2text-generation",
            model=LLM_MODEL_NAME,
            device=-1,  # CPU
        )
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

UOMS   = r"(packs?|packets?|pieces?|pcs?|bottles?|units?|cans?|bags?|boxes?|kg|g|lb|lbs|ml|l|liters?|litres?)"
COLORS = r"(black|white|red|blue|green|yellow|pink|purple|silver|gold|gray|grey|brown|beige|navy|orange)"
SIZES  = r"(xxs|xs|s|m|l|xl|xxl|xxxl|small|medium|large|\d+[x×]\d+|\d+(\.\d+)?(cm|mm|in|inch|inches))"
BRANDS = r"(nike|adidas|puma|reebok|samsung|apple|sony|dell|hp|lenovo|milo|nestle|coke|pepsi|asus|acer|msi)"

CATEGORY_KEYWORDS = {
    "shoes":   ["shoe", "shoes", "sneaker", "sneakers", "heels", "sandals", "boots"],
    "laptops": ["laptop", "notebook", "macbook", "chromebook"],
    "phones":  ["phone", "smartphone", "iphone", "android"],
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
    "dollar":"USD","dollars":"USD","$":"USD","usd":"USD",
    "rupee":"LKR","rupees":"LKR","rs":"LKR","lkr":"LKR",
    "euro":"EUR","euros":"EUR","€":"EUR","eur":"EUR",
    "gbp":"GBP","pound":"GBP","pounds":"GBP","£":"GBP",
}
CURRENCY_SYMBOL_FOR = {"USD":"$", "LKR":"Rs", "EUR":"€", "GBP":"£"}

# =========================================================
# Regex extractors
#   NOTE: allow k/m suffix via (?:[km])? and decimals via [\d,.]+
# =========================================================
COLOR_RE = re.compile(rf"\b{COLORS}\b", re.I)
SIZE_RE  = re.compile(rf"\b{SIZES}\b", re.I)
BRAND_RE = re.compile(rf"\b{BRANDS}\b", re.I)

PRICE_UNDER_RE = re.compile(
    rf"(?:under|below|less\s*than)\s*(?P<cur>{CURRENCY_SYMBOLS})?\s*(?P<val>[\d,.]+(?:[km])?)",
    re.I,
)
PRICE_OVER_RE  = re.compile(
    rf"(?:over|above|more\s*than|at\s*least)\s*(?P<cur>{CURRENCY_SYMBOLS})?\s*(?P<val>[\d,.]+(?:[km])?)",
    re.I,
)
PRICE_BETWEEN_RE = re.compile(
    rf"(?:between|from)\s*(?P<cur1>{CURRENCY_SYMBOLS})?\s*(?P<min>[\d,.]+(?:[km])?)\s*(?:and|to|-)\s*(?P<cur2>{CURRENCY_SYMBOLS})?\s*(?P<max>[\d,.]+(?:[km])?)",
    re.I,
)

PRICE_PHRASE_RE = re.compile(
    r"\s*(?:under|below|less\s*than|over|above|more\s*than|at\s*least|between|from)\b.*$",
    re.I,
)

# =========================================================
# Intent patterns
# =========================================================
INTENT_PATTERNS: Dict[str, re.Pattern] = {
    "add_to_cart": re.compile(
        rf"\b(add|buy|put)\b\s+(?P<qty_num>\d+|{'|'.join(WORD_NUM.keys())})?\s*(?P<uom>{UOMS})?\s*(?:of\s+)?(?P<product>.+?)"
        rf"(?:\s+(?P<size>{SIZES}))?(?:\s+(?P<color>{COLORS}))?(?:\s+(?:from|by)\s+(?P<brand>{BRANDS}))?"
        rf"(?:\s+(?:under|below|less\s*than)\s*(?P<cur1>{CURRENCY_SYMBOLS})?\s*(?P<price_max>[\d,.]+(?:[km])?))?"
        rf"(?:\s+(?:over|above|more\s*than|at\s*least)\s*(?P<cur2>{CURRENCY_SYMBOLS})?\s*(?P<price_min>[\d,.]+(?:[km])?))?\s*$",
        re.I,
    ),
    "remove_from_cart": re.compile(
        rf"\b(remove|delete|take\s*out)\b\s+(?P<product>.+?)"
        rf"(?:\s+(?P<size>{SIZES}))?(?:\s+(?P<color>{COLORS}))?(?:\s+(?:from|by)\s+(?P<brand>{BRANDS}))?\s*$",
        re.I,
    ),
    "search_product": re.compile(
        rf"\b(find|search|show|look\s*for)\b\s+(?:me\s+|some\s+)?(?P<product>.+?)\s*"
        rf"(?:(?:under|below|less\s*than)\s*(?P<cur1>{CURRENCY_SYMBOLS})?\s*(?P<price_max>[\d,.]+(?:[km])?))?\s*"
        rf"(?:(?:over|above|more\s*than|at\s*least)\s*(?P<cur2>{CURRENCY_SYMBOLS})?\s*(?P<price_min>[\d,.]+(?:[km])?))?\s*$",
        re.I,
    ),
    "show_cart": re.compile(r"\b(show|view|see|what'?s|whats)\b.*\bcart\b", re.I),
    "checkout": re.compile(r"\b(checkout|place\s+order|pay)\b", re.I),
    "greeting": re.compile(r"\b(hi|hello|hey)\b", re.I),
}

# =========================================================
# Helpers
# =========================================================
def _fix_terms(text: str) -> str:
    for pat, repl in TERM_FIXES.items():
        text = re.sub(pat, repl, text, flags=re.I)
    return text

def _to_int(s: Optional[str]) -> Optional[int]:
    if not s: return None
    s = s.strip().lower()
    if s.isdigit(): return int(s)
    return WORD_NUM.get(s)

def _to_float(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    s = s.strip().lower().replace(",", "")
    try:
        # Handle "k" and "m" shorthand (e.g., 200k = 200000; 1.5m = 1_500_000)
        if s.endswith("k"):
            return float(s[:-1]) * 1000
        if s.endswith("m"):
            return float(s[:-1]) * 1_000_000
        return float(s)
    except Exception:
        return None

def _clean(s: Optional[str]) -> Optional[str]:
    if not s: return s
    return re.sub(r"\s+", " ", s).strip().rstrip(".,!?")

def _normalize_product(p: Optional[str]) -> Optional[str]:
    if not p: return p
    p = _clean(p)
    p = re.sub(r"^\bme\b\s+", "", p, flags=re.I)
    p = re.sub(rf"^(?:{UOMS})\s+of\s+", "", p, flags=re.I)
    return p

def _strip_price_phrases(p: str) -> str:
    p = PRICE_PHRASE_RE.sub("", p)
    return p.strip()

def _infer_category(product: Optional[str]) -> Optional[str]:
    if not product: return None
    pl = product.lower()
    for cat, words in CATEGORY_KEYWORDS.items():
        for w in words:
            if w in pl: return cat
    return None

def _detect(text: str) -> Tuple[str, Optional[re.Match]]:
    for intent, pat in INTENT_PATTERNS.items():
        m = pat.search(text)
        if m: return intent, m
    return "unknown", None

def _currency_code(tok: Optional[str]) -> Optional[str]:
    if not tok: return None
    t = tok.strip().lower().replace(".", "")
    return CURRENCY_WORDS.get(t) or CURRENCY_WORDS.get(t.upper()) or None

# =========================================================
# spaCy NER enrichment
# =========================================================
def _ner_pass(text: str, slots: Dict[str, Any]) -> None:
    if not (USE_SPACY and _nlp): return
    try:
        doc = _nlp(text)
        for ent in doc.ents:
            label = ent.label_.lower()
            val = ent.text.strip()
            if label in ("org", "product", "brand"):
                if "brand" not in slots:
                    slots["brand"] = val.lower()
            elif label == "money":
                amt = re.findall(r"[\d,]+(?:\.\d+)?", val)
                if amt:
                    v = _to_float(amt[0])
                    if v is not None:
                        slots.setdefault("price_seen", v)
    except Exception:
        pass

# =========================================================
# LLM Clarifier with JSON repair
# =========================================================
def _clarify_with_llm(text: str) -> Dict[str, Any]:
    pipe = _get_llm()
    if pipe is None:
        return {}

    prompt = f"""
You are a JSON generator for e-commerce queries.
Read the user query and output ONLY valid JSON with the following fields:
intent, product, brand, category, price_min, price_max, currency.
Do not include any explanations or other text. 
Intent must be one of: search_product, add_to_cart, remove_from_cart, show_cart, checkout, greeting.
If any field is not applicable, OMIT it.

### EXAMPLE ###
User query: "I want a Dell laptop under 120k LKR"
JSON:
{{"intent":"search_product","product":"laptop","brand":"dell","price_max":120000,"currency":"LKR"}}

### INPUT ###
User query: "{text}"
JSON:
""".strip()

    try:
        out = pipe(prompt, max_new_tokens=LLM_MAX_NEW_TOKENS)[0]["generated_text"]
        print("[LLM] Clarifier triggered for:", text)
        print("[LLM] Raw model output:", out)

        cleaned = out.strip()

        # 1) Wrap with braces if missing
        if not cleaned.startswith("{") and re.match(r'^"[^"]+":', cleaned):
            cleaned = "{" + cleaned + "}"

        # 2) Fix duplicated intent separators
        cleaned = re.sub(r'""intent"', '","intent"', cleaned)

        # 3) Fix stray quotes before numbers or commas
        cleaned = re.sub(r'":(\d+)"', r'":\1', cleaned)

        # 4) Remove any extra quotes before commas
        cleaned = re.sub(r'"\s*,', '",', cleaned)

        # 5) Strip trailing commas / spaces
        cleaned = cleaned.strip().rstrip(",")

        # 6) If still no leading '{', try extracting JSON block
        if not cleaned.startswith("{"):
            m = re.search(r"\{.*\}", cleaned, re.S)
            if m:
                cleaned = m.group(0)

        print("[LLM] Cleaned JSON candidate:", cleaned)
        return json.loads(cleaned)
    except Exception as e:
        print(f"[LLM clarifier failed] {e}")
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
# Public entry point
# =========================================================
def process_query(
    text: str,
    user_id: Optional[str] = None,
    locale: Optional[str] = "en-US",
) -> Dict[str, Any]:
    # 1) sanitize + normalize
    text = _sanitize(text)
    text = _fix_terms(text)

    # 2) detect intent via regex
    intent, m = _detect(text)
    slots: Dict[str, Any] = {"raw": text}

    # 3) global attribute sniffs
    if (c := COLOR_RE.search(text)): slots["color"] = c.group(1).lower()
    if (s := SIZE_RE.search(text)):  slots["size"]  = s.group(1).lower()
    if (b := BRAND_RE.search(text)): slots["brand"] = b.group(1).lower()

    # 4) price phrases anywhere
    if (rng := PRICE_BETWEEN_RE.search(text)):
        mn, mx = _to_float(rng.group("min")), _to_float(rng.group("max"))
        if mn is not None: slots["price_min"] = mn
        if mx is not None: slots["price_max"] = mx
        if (rng.group("cur1") or rng.group("cur2")):
            slots["currency"] = (rng.group("cur1") or rng.group("cur2"))

    if (mxm := PRICE_UNDER_RE.search(text)) and "price_max" not in slots:
        val = _to_float(mxm.group("val"))
        if val is not None:
            slots["price_max"] = val
            if mxm.group("cur"): slots["currency"] = mxm.group("cur")

    if (mnp := PRICE_OVER_RE.search(text)) and "price_min" not in slots:
        val = _to_float(mnp.group("val"))
        if val is not None:
            slots["price_min"] = val
            if mnp.group("cur"): slots["currency"] = mnp.group("cur")

    # 5) intent-specific fields
    if m:
        gd = m.groupdict() or {}
        if intent == "add_to_cart":
            if (q := _to_int(gd.get("qty_num"))) is not None:
                slots["qty"] = q
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

    # 6) NER enrichment
    _ner_pass(text, slots)

    # 7) infer category
    if "product" in slots:
        if (cat := _infer_category(slots["product"])):
            slots["category"] = cat

    # 8) currency polish
    if "currency" in slots:
        code = _currency_code(slots["currency"])
        if code:
            slots["currency"] = CURRENCY_SYMBOL_FOR.get(code, slots["currency"])

    # 9) convenience: price_limit = price_max
    if "price_max" in slots and "price_min" not in slots:
        slots["price_limit"] = slots["price_max"]

    # 10) LLM clarifier
    llm_used = False
    clarified: Dict[str, Any] = {}
    if USE_LLM and (os.getenv("QP_LLM_ALWAYS") == "1" or intent == "unknown" or "product" not in slots):
        clarified = _validate_structured(_clarify_with_llm(text))
        if clarified:
            llm_used = True

            # Normalize LLM intent synonyms
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

            for k in ("product", "brand", "category", "price_min", "price_max", "currency"):
                if k in clarified and k not in slots:
                    slots[k] = clarified[k]

            if "currency" in slots:
                code = _currency_code(slots["currency"])
                if code:
                    slots["currency"] = CURRENCY_SYMBOL_FOR.get(code, slots["currency"])

            if "category" not in slots and "product" in slots:
                cat = _infer_category(slots["product"])
                if cat:
                    slots["category"] = cat

    # Debug breadcrumbs
    if llm_used:
        slots["__llm_used"] = True
        slots["__llm_model"] = LLM_MODEL_NAME
        slots["__llm_raw"] = clarified
    elif USE_LLM and _llm_error:
        slots["__llm_error"] = _llm_error

    # 10.5) Cosmetic: clean price_min == price_max to avoid awkward reply text
    if "price_min" in slots and "price_max" in slots and slots["price_min"] == slots["price_max"]:
        # keep only max for "under X" phrasing (feel free to flip if you prefer)
        slots.pop("price_min")

    # 11) reply + confidence
    if intent == "greeting":
        reply = "Hi! Try: 'find Nike shoes under $100', 'add 2 packs of Milo', 'show cart', or 'checkout'."
    elif intent == "search_product":
        p = slots.get("product", "the item")
        bits = []
        if "brand" in slots: bits.append(slots["brand"])
        if "color" in slots: bits.append(slots["color"])
        if "size" in slots:  bits.append(slots["size"])
        if "price_min" in slots: bits.append(f"over {slots.get('currency', '$')}{slots['price_min']}")
        if "price_max" in slots: bits.append(f"under {slots.get('currency', '$')}{slots['price_max']}")
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
        reply = "Here’s what’s in your cart…"
    elif intent == "checkout":
        reply = "Proceeding to checkout…"
    else:
        reply = "Sorry, I didn’t understand that."

    confidence = 0.9 if intent in {
        "add_to_cart","remove_from_cart","search_product","show_cart","checkout","greeting"
    } else 0.3
    if llm_used and confidence < 0.8:
        confidence = 0.8

    return {
        "intent": intent,
        "confidence": round(confidence, 2),
        "slots": slots,
        "reply": reply,
        "action": {"type": intent, "params": slots},
        "user_id": user_id,
        "locale": locale or "en-US",
    }
