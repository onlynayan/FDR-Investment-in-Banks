# Developed by Nayan
import re

try:
    import requests  # type: ignore[import-not-found]
except Exception:
    requests = None

APEX_URL = "http://103.163.96.251:8282/ords/cpa_invst/banks/insert"


def normalize_bank_name(value):
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    
    text = re.sub(r"\b(19|20)\d{2}\b", "", text)
    text = re.sub(r"\s*\([^)]*\)\s*", " ", text)
    # Remove common corporate suffixes.
    text = re.sub(r"\b(plc|ltd|limited)\b\.?", "", text, flags=re.IGNORECASE)
    text = " ".join(text.split())
    return text


def normalize_credit_rating(value):
    if value is None:
        return ""
    text = str(value).strip().upper()
    if not text:
        return ""
    text = re.sub(r"\s+", "", text)
    text = text.replace("AA-1", "AA1").replace("AA-2", "AA2").replace("AA-3", "AA3")
    text = text.replace("A-1", "A1").replace("A-2", "A2").replace("A-3", "A3")
    if text == "AAA":
        return "AAA"
    if text.startswith("AA"):
        return "AA"
    if text.startswith("A"):
        return "A"
    if text.startswith("BBB"):
        return "BBB"
    if text.startswith("BB"):
        return "BB"
    if text.startswith("B"):
        return "B"
    if text.startswith("CCC"):
        return "CCC"
    if text.startswith("CC"):
        return "CC"
    if text.startswith("C"):
        return "C"
    if text.startswith("D"):
        return "D"
    return ""


def _post_payload(payload, use_json):
    if use_json:
        response = requests.post(APEX_URL, json=payload, timeout=20)
    else:
        response = requests.post(APEX_URL, data=payload, timeout=20)
    text = response.text or ""
    lowered = text.lower()
    has_error = "error" in lowered or "not found" in lowered or "exception" in lowered
    ok = response.status_code in (200, 201) and not has_error
    return response, text, ok


def send_bank_eligibility(bank_name, fiscal_year, fin_period, npl, pcr, rating):
    if requests is None:
        return {"error": "Missing dependency 'requests'."}
    bank_name = normalize_bank_name(bank_name)
    normalized_rating = normalize_credit_rating(rating)
    payload = {
        "bank_name": bank_name,
        "fiscal_year": fiscal_year,
        "fin_period": fin_period,
        "npl": npl,
        "pcr": pcr,
        # Keep both keys to tolerate backend handlers that bind one naming style only.
        "credit_rating": normalized_rating,
        "rating": normalized_rating,
    }

    try:
        # Prefer JSON because ORDS handlers commonly bind JSON payloads more reliably.
        response, text, ok = _post_payload(payload, use_json=True)
        mode = "json"
        if not ok:
            retry_response, retry_text, retry_ok = _post_payload(payload, use_json=False)
            if retry_ok or retry_response.status_code != response.status_code:
                response, text, ok = retry_response, retry_text, retry_ok
                mode = "form"
        return {
            "status_code": response.status_code,
            "response": text,
            "ok": ok,
            "mode": mode,
            "url": APEX_URL,
            "payload": payload,
            "content_type": response.headers.get("content-type"),
            "content_length": response.headers.get("content-length"),
        }
    except Exception as exc:
        return {"error": str(exc)}
