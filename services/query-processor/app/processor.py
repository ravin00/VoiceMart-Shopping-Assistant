# services/query-processor/app/processor.py
from __future__ import annotations
import os
import re
from typing import Dict, Any, Optional, Tuple

# ===============================
# Optional feature flags (env)
# ===============================
USE_SPACY = os.getenv("QP_USE_SPACY", "0") == "1"   # pip install spacy && python -m spacy download en_core_web_sm
SPACY_MODEL = os.getenv("QP_SPACY_MODEL", "en_core_web_sm")
USE_LLM    = os.getenv("QP_USE_LLM", "0") == "1"    # if you wire an LLM clarifier later

# Lazy spaCy load
_nlp = None
if USE_SPACY:
    try:
        import spacy  # type: ignore
        _nlp = spacy.load(SPACY_MODEL)
    except Exception:
        _nlp = None
        USE_SPACY = False  # fail-closed

# ===============================
# Guardrails / sanitation
# ===============================
_MAX_TEXT_LEN = 600
def _sanitize(text: str) -> str:
    text = (text or "")[:_MAX_TEXT_LEN]
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", text)  # strip control chars
    text = re.sub(r"(?:```|</?script>|@everyone|@here)", " ", text, flags=re.I)  # basic prompt-injection tokens
    return text.strip()

# ===============================
# Lexicons & heuristics
# ===============================
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

# Common STT slips you want to autocorrect
TERM_FIXES = {
    r"\bshows\b": "shoes",
    r"\bmellow\b": "milo",
    r"\bcocks\b": "coke",
}

# Currency utils
CURRENCY_SYMBOLS = r"[\$£€]|Rs\.?|LKR|USD|EUR|GBP|rs|lkr|usd|eur|gbp"
CURRENCY_WORDS = {
    "dollar":"USD","dollars":"USD","$":"USD","usd":"USD",
    "rupee":"LKR","rupees":"LKR","rs":"LKR","lkr":"LKR",
    "euro":"EUR","euros":"EUR","€":"EUR","eur":"EUR",
    "gbp":"GBP","pound":"GBP","pounds":"GBP","£":"GBP",
}
CURRENCY_SYMBOL_FOR = {"USD":"$", "LKR":"Rs", "EUR":"€", "GBP":"£"}

# ===============================
# Regex extractors
# ===============================
COLOR_RE = re.compile(rf"\b{COLORS}\b", re.I)
SIZE_RE  = re.compile(rf"\b{SIZES}\b", re.I)
BRAND_RE = re.compile(rf"\b{BRANDS}\b", re.I)

PRICE_UNDER_RE = re.compile(rf"(?:under|below|less\s*than)\s*(?P<cur>{CURRENCY_SYMBOLS})?\s*(?P<val>[\d,]+(?:\.\d+)?)", re.I)
PRICE_OVER_RE  = re.compile(rf"(?:over|above|more\s*than|at\s*least)\s*(?P<cur>{CURRENCY_SYMBOLS})?\s*(?P<val>[\d,]+(?:\.\d+)?)", re.I)
PRICE_BETWEEN_RE = re.compile(
    rf"(?:between|from)\s*(?P<cur1>{CURRENCY_SYMBOLS})?\s*(?P<min>[\d,]+(?:\.\d+)?)\s*(?:and|to|-)\s*(?P<cur2>{CURRENCY_SYMBOLS})?\s*(?P<max>[\d,]+(?:\.\d+)?)",
    re.I,
)

# strip trailing price phrases from product (polish)
PRICE_PHRASE_RE = re.compile(
    r"\s*(?:under|below|less\s*than|over|above|more\s*than|at\s*least|between|from)\b.*$",
    re.I,
)

# ===============================
# Intent patterns (non-greedy product + filters)
# ===============================
INTENT_PATTERNS: Dict[str, re.Pattern] = {
    "add_to_cart": re.compile(
        rf"\b(add|buy|put)\b\s+"
        rf"(?P<qty_num>\d+|{'|'.join(WORD_NUM.keys())})?\s*"
        rf"(?P<uom>{UOMS})?\s*(?:of\s+)?"
        rf"(?P<product>.+?)"
        rf"(?:\s+(?P<size>{SIZES}))?"
        rf"(?:\s+(?P<color>{COLORS}))?"
        rf"(?:\s+(?:from|by)\s+(?P<brand>{BRANDS}))?"
        rf"(?:\s+(?:under|below|less\s*than)\s*(?P<cur1>{CURRENCY_SYMBOLS})?\s*(?P<price_max>[\d,]+(?:\.\d+)?))?"
        rf"(?:\s+(?:over|above|more\s*than|at\s*least)\s*(?P<cur2>{CURRENCY_SYMBOLS})?\s*(?P<price_min>[\d,]+(?:\.\d+)?))?"
        rf"\s*$",
        re.I,
    ),
    "remove_from_cart": re.compile(
        rf"\b(remove|delete|take\s*out)\b\s+(?P<product>.+?)"
        rf"(?:\s+(?P<size>{SIZES}))?"
        rf"(?:\s+(?P<color>{COLORS}))?"
        rf"(?:\s+(?:from|by)\s+(?P<brand>{BRANDS}))?"
        rf"\s*$",
        re.I,
    ),
    "search_product": re.compile(
        rf"\b(find|search|show|look\s*for)\b\s+(?:me\s+|some\s+)?"
        rf"(?P<product>.+?)\s*"
        rf"(?:(?:under|below|less\s*than)\s*(?P<cur1>{CURRENCY_SYMBOLS})?\s*(?P<price_max>[\d,]+(?:\.\d+)?))?\s*"
        rf"(?:(?:over|above|more\s*than|at\s*least)\s*(?P<cur2>{CURRENCY_SYMBOLS})?\s*(?P<price_min>[\d,]+(?:\.\d+)?))?\s*$",
        re.I,
    ),
    "show_cart": re.compile(r"\b(show|view|see|what'?s|whats)\b.*\bcart\b", re.I),
    "checkout": re.compile(r"\b(checkout|place\s+order|pay)\b", re.I),
    "greeting": re.compile(r"\b(hi|hello|hey)\b", re.I),
}

# ===============================
# Helpers
# ===============================
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
    if not s: return None
    try: return float(s.replace(",", ""))
    except Exception: return None

def _clean(s: Optional[str]) -> Optional[str]:
    if not s: return s
    return re.sub(r"\s+", " ", s).strip().rstrip(".,!?")

def _normalize_product(p: Optional[str]) -> Optional[str]:
    if not p: return p
    p = _clean(p)
    p = re.sub(r"^\bme\b\s+", "", p, flags=re.I)                 # drop leading "me"
    p = re.sub(rf"^(?:{UOMS})\s+of\s+", "", p, flags=re.I)       # drop leading "packs of ..."
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

# ===============================
# Optional: spaCy NER enrichment
# ===============================
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
        pass  # fail-quiet

# ===============================
# (Optional) LLM clarifier stub
# ===============================
def _clarify_with_llm(_text: str) -> Dict[str, Any]:
    # Wire your LLM client here and return validated dict, e.g. {"product":"laptop","price_max":600}
    return {}

def _validate_structured(d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if isinstance(d.get("brand"), str) and 0 < len(d["brand"]) <= 50:
        out["brand"] = d["brand"].strip()
    if isinstance(d.get("product"), str) and 0 < len(d["product"]) <= 120:
        out["product"] = d["product"].strip()
    for k in ("price_limit", "price_max", "price_min"):
        if k in d:
            try: out[k] = float(d[k])
            except Exception: pass
    return out

# ===============================
# Public entry point
# ===============================
def process_query(
    text: str,
    user_id: Optional[str] = None,
    locale: Optional[str] = "en-US",
) -> Dict[str, Any]:
    # 1) sanitize + normalize
    text = _sanitize(text)
    text = _fix_terms(text)

    # 2) detect intent
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

        # inline price overrides (specific beats global)
        pmx = _to_float(gd.get("price_max"))
        pmn = _to_float(gd.get("price_min"))
        if pmx is not None: slots["price_max"] = pmx
        if pmn is not None: slots["price_min"] = pmn
        if gd.get("cur1"): slots["currency"] = gd["cur1"]
        if gd.get("cur2"): slots["currency"] = gd["cur2"]

        # inline attrs
        if gd.get("color"): slots["color"] = gd["color"].lower()
        if gd.get("size"):  slots["size"]  = gd["size"].lower()
        if gd.get("brand"): slots["brand"] = gd["brand"].lower()

        # product
        if (p := gd.get("product")):
            p = _normalize_product(p)
            p = _strip_price_phrases(p)  # keep product clean (no price fragments)
            slots["product"] = p

    # 6) NER enrichment (optional)
    _ner_pass(text, slots)

    # 7) infer category
    if "product" in slots:
        if (cat := _infer_category(slots["product"])):
            slots["category"] = cat

    # 8) map currency tokens → codes/symbols (polish)
    if "currency" in slots:
        code = _currency_code(slots["currency"])
        if code:
            slots["currency"] = CURRENCY_SYMBOL_FOR.get(code, slots["currency"])

    # 9) convenience: price_limit == price_max when only max given
    if "price_max" in slots and "price_min" not in slots:
        slots["price_limit"] = slots["price_max"]

    # 10) (optional) LLM clarifier for ambiguous phrases
    if USE_LLM:
        clarified = _validate_structured(_clarify_with_llm(text))
        for k, v in clarified.items():
            slots.setdefault(k, v)

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

    return {
        "intent": intent,
        "confidence": round(confidence, 2),
        "slots": slots,  # contains brand, product, price_limit/max/min, etc.
        "reply": reply,
        "action": {"type": intent, "params": slots},
        "user_id": user_id,
        "locale": locale or "en-US",
    }
