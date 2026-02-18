# Developed by Nayan
import re

try:
    import requests  # type: ignore[import-not-found]
except Exception:
    requests = None

APEX_PERFORMANCE_URL = "http://103.163.96.251:8282/ords/cpa_invst/banks/performance"
EXCLUDED_INDICATOR_CODES = {"YIELD", "RC"}
MAX_SOURCE_URL_LEN = 500
MAX_SOURCE_TYPE_LEN = 30
MAX_PERIOD_LEN = 20


def normalize_bank_name(value):
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    text = re.sub(r"\b(19|20)\d{2}\b", "", text)
    text = re.sub(r"\s*\([^)]*\)\s*", " ", text)
    text = re.sub(r"\b(plc|ltd|limited)\b\.?", "", text, flags=re.IGNORECASE)
    return " ".join(text.split())


def normalize_indicator_code(value):
    if value is None:
        return ""
    return re.sub(r"[^A-Za-z0-9_]", "", str(value)).upper().strip()


def _safe_text(value, max_len):
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) > max_len:
        return text[:max_len]
    return text


def _post_payload(payload, use_json):
    if use_json:
        response = requests.post(APEX_PERFORMANCE_URL, json=payload, timeout=20)
    else:
        response = requests.post(APEX_PERFORMANCE_URL, data=payload, timeout=20)
    text = response.text or ""
    lowered = text.lower()
    has_error = "error" in lowered or "not found" in lowered or "exception" in lowered
    ok = response.status_code in (200, 201) and not has_error
    return response, text, ok


def send_bank_performance(
    bank_name,
    indicator_code,
    actual_value,
    score,
    year,
    period="Annual",
    source_url="",
    source_type="PDF",
):
    if requests is None:
        return {"error": "Missing dependency 'requests'."}

    bank_name = normalize_bank_name(bank_name)
    indicator_code = normalize_indicator_code(indicator_code)
    if indicator_code in EXCLUDED_INDICATOR_CODES:
        return {
            "ok": True,
            "status_code": 204,
            "response": f"Skipped excluded indicator code {indicator_code}",
            "mode": "skip",
            "url": APEX_PERFORMANCE_URL,
        }

    payload = {
        "bank_name": bank_name,
        "indicator_code": indicator_code,
        "actual_value": actual_value if actual_value is not None else "",
        "score": score,
        "year": year,
        "period": _safe_text(period, MAX_PERIOD_LEN),
        "source_url": _safe_text(source_url, MAX_SOURCE_URL_LEN),
        "source_type": _safe_text(source_type, MAX_SOURCE_TYPE_LEN),
    }

    try:
        # Prefer JSON first for consistent request parsing on ORDS endpoints.
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
            "url": APEX_PERFORMANCE_URL,
            "payload": payload,
            "content_type": response.headers.get("content-type"),
            "content_length": response.headers.get("content-length"),
        }
    except Exception as exc:
        return {"error": str(exc)}
