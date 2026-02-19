# Developed by Nayan
# --- Standard library imports ---
import json
import mimetypes
import os
import re
import tempfile
import time
import argparse
import threading
from urllib.request import Request, urlopen
from urllib.parse import quote, parse_qs, urlparse
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# --- Third-party and local imports ---
import pandas as pd
from apex_client import send_bank_eligibility

try:
    from scraper import score_field_value
except Exception:
    def score_field_value(*_args, **_kwargs):
        return None

# --- App paths and runtime config ---
ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "ui"
OUTPUT_DIR = ROOT / "output"
SOURCES_PATH = ROOT / "config" / "sources.json"
SCRAPER_ENTRY = "scraper.py"
ELIGIBILITY_SCRAPER_ENTRY = "eligible_scraper.py"
ELIGIBILITY_OUTPUT_DIR = ROOT / "eligible_output"
ELIGIBLE_DOWNLOADS_DIR = ROOT / "eligible_downloads"
ELIGIBLE_WORKLIST_API = "http://103.163.96.251:8282/ords/cpa_invst/banks/worklist"

RUN_STATES = {
    "extraction": {
        "running": False,
        "proc": None,
        "started_at": None,
        "current_bank": None,
        "completed_banks": 0,
        "total_banks": 0,
        "records": {},
        "record_order": [],
    },
    "eligibility": {
        "running": False,
        "proc": None,
        "started_at": None,
        "current_bank": None,
        "completed_banks": 0,
        "total_banks": 0,
        "records": {},
        "record_order": [],
    },
}
RUN_STATE_LOCK = threading.Lock()
LAST_EXTRACTION_LOCK = threading.Lock()
LAST_EXTRACTION_RECORDS = {}
LAST_EXTRACTION_ORDER = []


def _acquire_run_slot(run_type):
    with RUN_STATE_LOCK:
        state = RUN_STATES.get(run_type)
        if not state:
            return False

        # Self-heal stale locks if process already exited or was never tracked.
        if state["running"]:
            proc = state.get("proc")
            if proc is None or proc.poll() is not None:
                state["running"] = False
                state["proc"] = None
                state["started_at"] = None

        if state["running"]:
            return False

        state["running"] = True
        state["started_at"] = time.time()
        state["proc"] = None
        state["current_bank"] = None
        state["completed_banks"] = 0
        state["total_banks"] = 0
        state["records"] = {}
        state["record_order"] = []
        return True


def _attach_run_process(run_type, proc):
    with RUN_STATE_LOCK:
        state = RUN_STATES.get(run_type)
        if not state:
            return
        state["proc"] = proc


def _release_run_slot(run_type):
    with RUN_STATE_LOCK:
        state = RUN_STATES.get(run_type)
        if not state:
            return
        state["running"] = False
        state["proc"] = None
        state["started_at"] = None
        state["current_bank"] = None
        state["completed_banks"] = 0
        state["total_banks"] = 0
        state["records"] = {}
        state["record_order"] = []


def _set_run_total(run_type, total_banks):
    with RUN_STATE_LOCK:
        state = RUN_STATES.get(run_type)
        if not state:
            return
        state["total_banks"] = max(0, int(total_banks or 0))


def _set_current_bank(run_type, bank_name):
    with RUN_STATE_LOCK:
        state = RUN_STATES.get(run_type)
        if not state:
            return
        state["current_bank"] = str(bank_name).strip() if bank_name else None


def _increment_completed(run_type, bank_name=None):
    with RUN_STATE_LOCK:
        state = RUN_STATES.get(run_type)
        if not state:
            return
        state["completed_banks"] = int(state.get("completed_banks") or 0) + 1
        if bank_name:
            state["current_bank"] = str(bank_name).strip()


def _upsert_run_record(run_type, record):
    if not isinstance(record, dict):
        return
    record_key = record.get("key")
    if not record_key:
        record_key = slugify(str(record.get("name") or record.get("bank") or ""))
    if not record_key:
        return
    with RUN_STATE_LOCK:
        state = RUN_STATES.get(run_type)
        if not state:
            return
        records = state.setdefault("records", {})
        order = state.setdefault("record_order", [])
        records[record_key] = record
        if record_key not in order:
            order.append(record_key)
    if run_type == "extraction":
        with LAST_EXTRACTION_LOCK:
            LAST_EXTRACTION_RECORDS[record_key] = record
            if record_key not in LAST_EXTRACTION_ORDER:
                LAST_EXTRACTION_ORDER.append(record_key)


def _estimate_total_for_eligibility():
    try:
        sources_payload = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
        sources = sources_payload.get("sources", []) if isinstance(sources_payload, dict) else []
    except Exception:
        sources = []
    if not sources:
        return 0
    try:
        eligible_banks = fetch_eligible_bank_names()
        filtered = filter_sources_by_bank_names({"sources": sources}, eligible_banks)
        if filtered:
            return len(filtered)
    except Exception:
        pass
    return len(sources)


def _snapshot_run_states():
    with RUN_STATE_LOCK:
        payload = {}
        for run_type, state in RUN_STATES.items():
            proc = state.get("proc")
            payload[run_type] = {
                "running": bool(state.get("running") and proc is not None and proc.poll() is None),
                "started_at": state.get("started_at"),
                "pid": proc.pid if proc and proc.poll() is None else None,
                "current_bank": state.get("current_bank"),
                "completed_banks": int(state.get("completed_banks") or 0),
                "total_banks": int(state.get("total_banks") or 0),
                "records": [
                    state.get("records", {}).get(key)
                    for key in state.get("record_order", [])
                    if state.get("records", {}).get(key)
                ],
            }
        return payload


def _terminate_process(proc):
    if not proc:
        return
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                if proc.poll() is None:
                    proc.kill()
    except Exception:
        pass

# --- Field name normalization map ---
FIELD_MAP = {
    "capital adequacy": "crar",
    "crar": "crar",
    "leverage ratio": "leverage",
    "non-performing": "npl",
    "non performing": "npl",
    "npl": "npl",
    "provision coverage": "provision",
    "loan to deposit": "ldr",
    "return on assets": "roa",
    "return on asset": "roa",
    "return on equity": "roe",
    "net interest margin": "nim",
    "liquidity coverage": "lcr",
    "net stable funding": "nsfr",
    "cash to deposit": "cdr",
    "credit rating": "creditRating",
    "regulatory compliance": "compliance",
}


# --- Text normalization helpers ---
def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return cleaned or "bank"


def sanitize_filename(value) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_\\-]+", "_", str(value).strip())
    cleaned = cleaned.strip("_")
    return cleaned or "Unknown"


def build_local_pdf_url(bank_name, year):
  bank_part = sanitize_filename(bank_name or "UnknownBank")
  year_part = sanitize_filename(year or "UnknownYear")
  filename = f"Annual_Report_{bank_part}_{year_part}.pdf"
  path = ROOT / "downloads" / filename
  if path.exists():
    return f"/downloads/{filename}"
  return None


def build_eligible_pdf_url(bank_name, year):
    bank_part = sanitize_filename(bank_name or "UnknownBank")
    year_part = sanitize_filename(year or "UnknownYear")
    filename = f"Annual_Report_{bank_part}_{year_part}.pdf"
    path = ELIGIBLE_DOWNLOADS_DIR / filename
    if path.exists():
        return f"/eligible_downloads/{filename}"
    return None


def build_pdf_viewer_url(file_url, page=None, value=None):
    if not file_url:
        return None
    fragment_parts = []
    if page not in ("", None):
        fragment_parts.append(f"page={page}")
    if value not in ("", None):
        fragment_parts.append(f"search={quote(str(value))}")
    fragment = "&".join(fragment_parts)
    viewer_url = f"/pdfjs/web/viewer.html?file={quote(str(file_url))}"
    if fragment:
        viewer_url = f"{viewer_url}#{fragment}"
    return viewer_url


def build_eligibility_record(payload):
    file_url = payload.get("pdf_url")
    pdf_path = payload.get("pdf_path")
    if not file_url and pdf_path:
        try:
            rel = os.path.relpath(pdf_path, ROOT).replace("\\", "/")
        except Exception:
            rel = None
        if rel:
            file_url = f"/{rel}"
    npl_source = build_pdf_viewer_url(
        file_url, page=payload.get("nplPage"), value=payload.get("npl")
    )
    rating_source = build_pdf_viewer_url(
        file_url, page=payload.get("ratingPage"), value=payload.get("rating")
    )
    return {
        "bank": payload.get("bank"),
        "year": payload.get("year"),
        "npl": payload.get("npl"),
        "nplPage": payload.get("nplPage"),
        "rating": payload.get("rating"),
        "ratingPage": payload.get("ratingPage"),
        "nplScore": payload.get("nplScore"),
        "ratingScore": payload.get("ratingScore"),
        "nplSource": npl_source,
        "ratingSource": rating_source,
    }


# --- Data cleaning helpers ---
def clean_cell(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


# --- Numeric parsing helpers ---
def clean_number(value):
    value = clean_cell(value)
    if value == "":
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("%", "")
        if cleaned == "":
            return None
        value = cleaned
    try:
        num = float(value)
    except Exception:
        return None
    if num.is_integer():
        return int(num)
    return num


def normalize_bank_name(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\b(plc|ltd|limited|bank)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _extract_list_payload(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "data", "rows", "result", "worklist", "banks", "sources"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return candidate
    return []


def _entry_bank_name(entry):
    if isinstance(entry, str):
        return entry
    if not isinstance(entry, dict):
        return None
    for key in ("bank", "bank_name", "bankName", "BANK_NAME", "name", "BANK"):
        value = entry.get(key)
        if value:
            return value
    return None


def fetch_eligible_bank_names():
    req = Request(
        ELIGIBLE_WORKLIST_API,
        headers={"Accept": "application/json", "User-Agent": "fdr-investment-in-banks-ui-server/1.0"},
    )
    with urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    payload = json.loads(raw)
    items = _extract_list_payload(payload)
    names = []
    seen = set()
    for item in items:
        name = _entry_bank_name(item)
        if not name:
            continue
        normalized = normalize_bank_name(name)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        names.append(str(name).strip())
    return names


def filter_sources_by_bank_names(sources_payload, bank_names):
    sources = sources_payload.get("sources", []) if isinstance(sources_payload, dict) else []
    if not bank_names:
        return []
    by_norm = {}
    for entry in sources:
        bank = entry.get("bank")
        norm = normalize_bank_name(bank)
        if norm:
            by_norm[norm] = entry

    filtered = []
    selected_norm = set()
    for raw_name in bank_names:
        norm = normalize_bank_name(raw_name)
        if not norm:
            continue
        chosen = by_norm.get(norm)
        if not chosen:
            for key, value in by_norm.items():
                if norm in key or key in norm:
                    chosen = value
                    break
        if not chosen:
            continue
        key = normalize_bank_name(chosen.get("bank"))
        if key in selected_norm:
            continue
        selected_norm.add(key)
        filtered.append(chosen)
    return filtered


def filter_scorecards_by_bank_names(scorecards, bank_names):
    if not scorecards or not bank_names:
        return []
    allowed = [normalize_bank_name(name) for name in bank_names if normalize_bank_name(name)]
    if not allowed:
        return []
    filtered = []
    for card in scorecards:
        card_name = normalize_bank_name(card.get("name"))
        if not card_name:
            continue
        for norm in allowed:
            if card_name == norm or card_name in norm or norm in card_name:
                filtered.append(card)
                break
    return filtered


def _snapshot_last_extraction_scorecards():
    with LAST_EXTRACTION_LOCK:
        return [
            LAST_EXTRACTION_RECORDS.get(key)
            for key in LAST_EXTRACTION_ORDER
            if LAST_EXTRACTION_RECORDS.get(key)
        ]


# --- File and field matching helpers ---
def bank_name_from_filename(path: Path) -> str:
    name = path.stem
    if name.lower().startswith("annual_report_"):
        name = name[len("annual_report_") :]
    name = re.sub(r"\b20\d{2}\b", "", name).strip("_ ")
    return name.replace("_", " ").strip()


def match_field_key(field: str):
    field_lower = field.lower()
    for needle, key in FIELD_MAP.items():
        if needle in field_lower:
            return key
    return None


# --- Summary field mappings ---
SUMMARY_FIELD_MAP = {
    "capital to risk weighted assets ratio": ("crar", "Capital Adequacy Ratio (CRAR)"),
    "leverage ratio": ("leverage", "Leverage Ratio (LR)"),
    "non performing loan ratio": ("npl", "Non-Performing Loan Ratio (NPL)"),
    "provision coverage ratio": ("provision", "Provision Coverage Ratio (PCR)"),
    "loan to deposit ratio": ("ldr", "Loan to Deposit Ratio (LDR)"),
    "return on assets": ("roa", "Return on Assets (ROA)"),
    "return on equity": ("roe", "Return on Equity (ROE)"),
    "net interest margin": ("nim", "Net Interest Margin (NIM)"),
    "liquidity coverage ratio": ("lcr", "Liquidity Coverage Ratio (LCR)"),
    "net stable funding ratio": ("nsfr", "Net Stable Funding Ratio (NSFR)"),
    "cash to deposit ratio": ("cdr", "Cash to Deposit Ratio (CDR)"),
    "credit rating": ("creditRating", "Credit Rating (CR)"),
}

def feature_label_to_key(label: str):
    if not label:
        return None
    normalized = str(label).strip().lower()
    mapped = SUMMARY_FIELD_MAP.get(normalized)
    if mapped:
        return mapped[0]
    return match_field_key(normalized)

def load_developer_links():
    if not OUTPUT_DIR.exists():
        return {}
    links = {}
    for path in sorted(OUTPUT_DIR.glob("*.xlsx")):
        if path.name.startswith("~$"):
            continue
        if "developer" not in path.stem.lower():
            continue
        try:
            df = pd.read_excel(path)
        except Exception:
            continue
        df.columns = [str(col).strip().lower() for col in df.columns]
        if "feature" not in df.columns or "bank name" not in df.columns:
            continue
        mtime = path.stat().st_mtime
        for _, row in df.iterrows():
            feature = clean_cell(row.get("feature"))
            bank_name = clean_cell(row.get("bank name"))
            if not feature or not bank_name:
                continue
            if str(feature).strip().lower() == "total score":
                continue
            key = feature_label_to_key(feature)
            if not key:
                continue
            page = clean_cell(row.get("page"))
            source_url = clean_cell(row.get("source_url"))
            value = clean_cell(row.get("value"))
            year = clean_cell(row.get("year"))
            bank_key = slugify(str(bank_name))
            local_pdf_url = build_local_pdf_url(bank_name, year)
            file_url = None
            if local_pdf_url:
                file_url = local_pdf_url
            elif source_url and "<" not in str(source_url):
                file_url = source_url
            viewer_url = build_pdf_viewer_url(file_url, page=page, value=value)

            bank_links = links.setdefault(bank_key, {})
            existing = bank_links.get(key)
            if not existing or mtime > existing.get("mtime", 0):
                bank_links[key] = {
                    "page": page,
                    "sourceUrl": viewer_url or source_url,
                    "mtime": mtime,
                }
    return links


# --- Field-based scorecard parser ---
def read_field_scorecard(df: pd.DataFrame, path: Path):
    if "field" not in df.columns:
        return None

    bank_name = None
    indicators = {}
    total_score = None

    for _, row in df.iterrows():
        if bank_name is None and "bank" in df.columns:
            bank_name = clean_cell(row.get("bank")) or None

        field = clean_cell(row.get("field"))
        if not field:
            continue

        field_norm = str(field).strip().lower()
        if field_norm.replace(" ", "_") == "total_score":
            total_score = clean_number(row.get("score"))
            continue

        key = match_field_key(field_norm)
        if not key:
            continue

        indicators[key] = {
            "value": clean_cell(row.get("value")),
            "score": clean_number(row.get("score")),
            "page": clean_cell(row.get("page")),
            "confidence": clean_number(row.get("confidence")),
            "validation": clean_cell(row.get("validation")),
        }

    if not bank_name:
        bank_name = bank_name_from_filename(path)

    if not bank_name:
        bank_name = path.stem

    if total_score is None:
        total_score = 0
        for indicator in indicators.values():
            score = clean_number(indicator.get("score"))
            total_score += score or 0

    return {
        "key": slugify(str(bank_name)),
        "name": str(bank_name),
        "totalScore": total_score,
        "indicators": indicators,
    }


# --- Summary-based scorecard parser ---
def normalize_summary_value(field_name, value):
    if value is None or value == "":
        return None
    if field_name == "Credit Rating (CR)":
        return str(value).strip().upper()
    return clean_number(value)


def read_summary_scorecards(df: pd.DataFrame, developer_links=None):
    cards = []
    if "bank name" not in df.columns:
        return cards

    for _, row in df.iterrows():
        bank_name = clean_cell(row.get("bank name"))
        if not bank_name:
            continue
        indicators = {}
        total_score = clean_number(row.get("total score"))

        for column, (key, field_name) in SUMMARY_FIELD_MAP.items():
            raw_value = clean_cell(row.get(column))
            value = raw_value if raw_value != "" else None
            score_value = normalize_summary_value(field_name, value)
            score = score_field_value(field_name, score_value)
            indicators[key] = {
                "value": value,
                "score": clean_number(score),
                "page": None,
                "confidence": None,
                "validation": None,
                "sourceUrl": None,
            }
            if developer_links:
                bank_key = slugify(str(bank_name))
                link_entry = developer_links.get(bank_key, {}).get(key)
                if link_entry:
                    indicators[key]["page"] = link_entry.get("page")
                    indicators[key]["sourceUrl"] = link_entry.get("sourceUrl")

        if total_score is None:
            total_score = 0
            for indicator in indicators.values():
                score = clean_number(indicator.get("score"))
                total_score += score or 0

        cards.append(
            {
                "key": slugify(str(bank_name)),
                "name": str(bank_name),
                "totalScore": total_score,
                "indicators": indicators,
            }
        )

    return cards


# --- Scorecard file loader ---
def read_scorecards_from_file(path: Path):
    try:
        df = pd.read_excel(path)
    except Exception:
        return []

    df.columns = [str(col).strip().lower() for col in df.columns]
    if "field" in df.columns:
        card = read_field_scorecard(df, path)
        return [card] if card else []
    if "bank name" in df.columns:
        return read_summary_scorecards(df, developer_links=None)
    return []


# --- Scorecard aggregation across XLSX outputs ---
def build_scorecards():
    if not OUTPUT_DIR.exists():
        return []

    developer_links = load_developer_links()
    scorecards = {}
    for path in sorted(OUTPUT_DIR.glob("*.xlsx")):
        if path.name.startswith("~$"):
            continue
        if "developer" in path.stem.lower():
            continue
        try:
            df = pd.read_excel(path)
        except Exception:
            continue
        df.columns = [str(col).strip().lower() for col in df.columns]
        if "bank name" in df.columns:
            cards = read_summary_scorecards(df, developer_links=developer_links)
        elif "field" in df.columns:
            card = read_field_scorecard(df, path)
            cards = [card] if card else []
        else:
            cards = []
        if not cards:
            continue
        mtime = path.stat().st_mtime
        for card in cards:
            if not card:
                continue
            key = card["key"]
            existing = scorecards.get(key)
            if not existing or mtime > existing["mtime"]:
                scorecards[key] = {"card": card, "mtime": mtime}

    ordered = sorted(
        (entry["card"] for entry in scorecards.values()),
        key=lambda item: item["name"].lower(),
    )
    return ordered


ELIGIBILITY_FIELD_MAP = {
    "non performing loan ratio": ("npl", "Non-Performing Loan Ratio (NPL)", "npl page"),
    "provision coverage ratio": ("provision", "Provision Coverage Ratio (PCR)", "pcr page"),
    "credit rating": ("creditRating", "Credit Rating (CR)", "credit rating page"),
}


def normalize_column_names(columns):
    return {str(col).strip().lower(): col for col in columns}


def find_column_name(col_map, *candidates):
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in col_map:
            return col_map[key]
    return None


def build_eligibility_scorecards():
    if not ELIGIBILITY_OUTPUT_DIR.exists():
        return []

    scorecards = {}
    for path in sorted(ELIGIBILITY_OUTPUT_DIR.glob("*.xlsx")):
        if path.name.startswith("~$"):
            continue
        try:
            df = pd.read_excel(path)
        except Exception:
            continue
        df.columns = [str(col).strip() for col in df.columns]
        col_map = normalize_column_names(df.columns)
        bank_col = find_column_name(col_map, "bank name", "bank")
        if not bank_col:
            continue
        year = extract_eligibility_year(path.name) or ""
        mtime = path.stat().st_mtime

        npl_col = find_column_name(col_map, "non performing loan ratio", "npl ratio", "npl")
        npl_page_col = find_column_name(col_map, "npl page", "non performing loan ratio page")
        pcr_col = find_column_name(col_map, "provision coverage ratio", "pcr", "pcr ratio")
        pcr_page_col = find_column_name(col_map, "pcr page", "provision coverage ratio page")
        rating_col = find_column_name(col_map, "credit rating", "rating")
        rating_page_col = find_column_name(col_map, "credit rating page", "rating page")

        for _, row in df.iterrows():
            bank_name = clean_cell(row.get(bank_col))
            if not bank_name:
                continue
            bank_name = str(bank_name).strip()
            if not bank_name:
                continue

            indicators = {}
            local_pdf_url = build_eligible_pdf_url(bank_name, year)

            npl_value = clean_number(row.get(npl_col)) if npl_col else None
            npl_page = clean_number(row.get(npl_page_col)) if npl_page_col else None
            npl_score = score_field_value("Non-Performing Loan Ratio (NPL)", npl_value)
            indicators["npl"] = {
                "value": npl_value,
                "score": clean_number(npl_score),
                "page": npl_page,
                "sourceUrl": build_pdf_viewer_url(local_pdf_url, page=npl_page, value=npl_value),
            }

            pcr_value = clean_number(row.get(pcr_col)) if pcr_col else None
            pcr_page = clean_number(row.get(pcr_page_col)) if pcr_page_col else None
            pcr_score = score_field_value("Provision Coverage Ratio (PCR)", pcr_value)
            indicators["provision"] = {
                "value": pcr_value,
                "score": clean_number(pcr_score),
                "page": pcr_page,
                "sourceUrl": build_pdf_viewer_url(local_pdf_url, page=pcr_page, value=pcr_value),
            }

            rating_value = clean_cell(row.get(rating_col)) if rating_col else None
            rating_value = str(rating_value).strip().upper() if rating_value not in (None, "") else None
            rating_page = clean_number(row.get(rating_page_col)) if rating_page_col else None
            rating_score = score_field_value("Credit Rating (CR)", rating_value)
            indicators["creditRating"] = {
                "value": rating_value,
                "score": clean_number(rating_score),
                "page": rating_page,
                "sourceUrl": build_pdf_viewer_url(local_pdf_url, page=rating_page, value=rating_value),
            }

            total_score = 0
            for indicator in indicators.values():
                score = clean_number(indicator.get("score"))
                total_score += score or 0

            key = slugify(str(bank_name))
            existing = scorecards.get(key)
            if not existing or mtime > existing["mtime"]:
                scorecards[key] = {
                    "card": {
                        "key": key,
                        "name": str(bank_name),
                        "totalScore": total_score,
                        "indicators": indicators,
                    },
                    "mtime": mtime,
                }

    ordered = sorted(
        (entry["card"] for entry in scorecards.values()),
        key=lambda item: item["name"].lower(),
    )
    return ordered


def extract_eligibility_year(filename):
    match = re.search(r"Eligible_Bank_Lists_(\d{4})", filename)
    return match.group(1) if match else None


def eligibility_files_since(since):
    if not ELIGIBILITY_OUTPUT_DIR.exists():
        return []
    recent = []
    for path in ELIGIBILITY_OUTPUT_DIR.glob("*.xlsx"):
        if path.name.startswith("~$"):
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime >= since:
            recent.append((path, mtime))
    recent.sort(key=lambda entry: entry[1])
    return [entry[0] for entry in recent]


# --- HTTP handler for UI + API endpoints ---
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        parsed = urlparse(self.path)
        raw_path = parsed.path or "/"
        path = raw_path.rstrip("/") or "/"
        if not path.startswith("/"):
            path = f"/{path}"
        path_parts = [part for part in path.split("/") if part]
        tail = "/".join(path_parts[-2:]) if len(path_parts) >= 2 else (path_parts[0] if path_parts else "")
        query = parse_qs(parsed.query)
        if path in {"/api/scorecards", "/scorecards"}:
            return self.handle_scorecards()
        if path in {"/api/eligibility-scorecards", "/eligibility-scorecards"}:
            return self.handle_eligibility_scorecards()
        if path in {"/api/sources", "/sources"}:
            return self.handle_sources()
        if path in {"/api/run", "/run"}:
            return self.handle_run()
        if path in {"/api/eligibility-run", "/eligibility-run"}:
            return self.handle_eligibility_run()
        if path in {"/api/stop-run", "/stop-run"}:
            return self.handle_stop_run(query)
        if path in {"/api/run-status", "/run-status"}:
            return self.handle_run_status()
        # Support reverse-proxy path prefixes (e.g. /fdr/api/run-status).
        if tail in {"api/run-status", "run-status"}:
            return self.handle_run_status()
        if tail in {"api/stop-run", "stop-run"}:
            return self.handle_stop_run(query)
        return self.handle_static(path)

    def handle_scorecards(self):
        cards = _snapshot_last_extraction_scorecards()
        if not cards:
            cards = build_scorecards()
        try:
            eligible_banks = fetch_eligible_bank_names()
            filtered = filter_scorecards_by_bank_names(cards, eligible_banks)
            cards = filtered
        except Exception:
            pass
        payload = {"banks": cards}
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_sources(self):
        try:
            sources_payload = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
        except Exception:
            sources_payload = {"sources": []}
        all_sources = sources_payload.get("sources", []) if isinstance(sources_payload, dict) else []
        eligible_sources = []
        api_available = False
        try:
            eligible_banks = fetch_eligible_bank_names()
            eligible_sources = filter_sources_by_bank_names(sources_payload, eligible_banks)
            api_available = True
        except Exception:
            pass
        payload = {
            "sources": all_sources,
            "eligible_sources": eligible_sources,
            "eligible_api_available": api_available,
        }
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_eligibility_scorecards(self):
        payload = {"banks": build_eligibility_scorecards()}
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_run(self):
        return self._start_run_process("extraction", SCRAPER_ENTRY)

    def handle_eligibility_run(self):
        return self._start_run_process("eligibility", ELIGIBILITY_SCRAPER_ENTRY, self._sync_eligibility_to_apex)

    def handle_run_status(self):
        payload = {"runs": _snapshot_run_states()}
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_stop_run(self, query):
        requested = (query.get("type") or ["all"])[0].strip().lower()
        if requested not in {"all", "extraction", "eligibility"}:
            payload = {"ok": False, "error": "Invalid type. Use all, extraction, or eligibility."}
            data = json.dumps(payload).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        targets = ["extraction", "eligibility"] if requested == "all" else [requested]
        stopped = []
        for run_type in targets:
            proc = None
            with RUN_STATE_LOCK:
                state = RUN_STATES.get(run_type)
                if state:
                    proc = state.get("proc")
            if proc and proc.poll() is None:
                _terminate_process(proc)
                stopped.append(run_type)
            _release_run_slot(run_type)

        payload = {
            "ok": True,
            "stopped": stopped,
            "runs": _snapshot_run_states(),
        }
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _start_run_process(self, run_type, script_entry, post_complete=None):
        if not _acquire_run_slot(run_type):
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                message = f"{run_type} already in progress."
                self.send_event({"type": "error", "message": message})
                self.send_event({"type": "complete", "returncode": 1, "run": run_type})
            except Exception:
                pass
            return
        run_start = time.time()
        temp_sources_path = None
        client_connected = True
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            env = dict(os.environ)
            env["PYTHONUNBUFFERED"] = "1"
            cmd = [sys.executable, "-u"]
            if run_type == "extraction":
                try:
                    sources_payload = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
                except Exception:
                    sources_payload = {"sources": []}
                try:
                    eligible_banks = fetch_eligible_bank_names()
                    filtered_sources = filter_sources_by_bank_names(sources_payload, eligible_banks)
                except Exception as exc:
                    client_connected = self.send_event(
                        {
                            "type": "log",
                            "line": f"Eligible API unavailable, using local sources: {exc}",
                        }
                    )
                    filtered_sources = sources_payload.get("sources", [])
                if not filtered_sources:
                    self.send_event(
                        {
                            "type": "error",
                            "message": "No eligible bank source matched config/sources.json",
                        }
                    )
                    return
                _set_run_total(run_type, len(filtered_sources))
                tmp = tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    delete=False,
                    suffix=".json",
                    prefix="eligible_sources_",
                    dir=str(ROOT),
                )
                json.dump({"sources": filtered_sources}, tmp, ensure_ascii=False, indent=2)
                tmp.flush()
                tmp.close()
                temp_sources_path = tmp.name
                cmd.extend(["scraper.py", "--sources", temp_sources_path])
                client_connected = self.send_event(
                    {
                        "type": "log",
                        "line": f"Loaded {len(filtered_sources)} eligible banks from final worklist.",
                    }
                )
            else:
                _set_run_total(run_type, _estimate_total_for_eligibility())
                cmd.append(script_entry)
            proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
            _attach_run_process(run_type, proc)
            if not proc.stdout:
                self.send_event({"type": "error", "message": "Unable to read scraper output."})
                return

            for line in proc.stdout:
                text = line.rstrip()
                if text.startswith("Processing "):
                    m = re.match(r"^Processing\s+(.+?)\s+\d{4}\s*$", text)
                    if m:
                        _set_current_bank(run_type, m.group(1))
                if text.startswith("EXTRACTION_DATA "):
                    try:
                        payload = json.loads(text.split(" ", 1)[1])
                        record = payload.get("record") if isinstance(payload, dict) and "record" in payload else payload
                        if isinstance(record, dict):
                            _upsert_run_record(run_type, record)
                            _increment_completed(run_type, record.get("name") or record.get("bank"))
                        if client_connected:
                            client_connected = self.send_event({"type": "extraction", "record": record or payload})
                    except Exception:
                        if client_connected:
                            client_connected = self.send_event({"type": "log", "line": text})
                    continue
                if text.startswith("ELIGIBILITY_DATA "):
                    try:
                        payload = json.loads(text.split(" ", 1)[1])
                        record = build_eligibility_record(payload)
                        _upsert_run_record(run_type, record)
                        _increment_completed(run_type, record.get("bank"))
                        if client_connected:
                            client_connected = self.send_event({"type": "eligibility", "record": record})
                    except Exception:
                        if client_connected:
                            client_connected = self.send_event({"type": "log", "line": text})
                    continue
                if client_connected:
                    client_connected = self.send_event({"type": "log", "line": text})

            proc.wait()
            if client_connected:
                self.send_event({"type": "complete", "returncode": proc.returncode, "run": run_type})
            if post_complete:
                try:
                    post_complete(run_start)
                except Exception as exc:
                    self.send_event(
                        {
                            "type": "log",
                            "line": f"Post-run step failed: {exc}",
                        }
                    )
        except Exception as exc:
            try:
                self.send_event({"type": "error", "message": str(exc)})
                self.send_event({"type": "complete", "returncode": 1, "run": run_type})
            except Exception:
                pass
        finally:
            if temp_sources_path:
                try:
                    os.remove(temp_sources_path)
                except OSError:
                    pass
            _release_run_slot(run_type)

    def _sync_eligibility_to_apex(self, since):
        files = eligibility_files_since(since)
        if not files:
            self.send_event(
                {"type": "log", "line": "No new eligibility output files were produced."}
            )
            return

        synced = 0
        for path in files:
            year = extract_eligibility_year(path.name) or ""
            try:
                df = pd.read_excel(path)
            except Exception as exc:
                self.send_event(
                    {
                        "type": "log",
                        "line": f"APEX skipped {path.name}: {exc}",
                    }
                )
                continue
            for record in df.to_dict("records"):
                bank_name = clean_cell(record.get("Bank Name"))
                if not bank_name:
                    continue
                bank_name = str(bank_name).strip()
                if not bank_name:
                    continue
                npl_value = clean_number(record.get("Non Performing Loan Ratio"))
                pcr_value = clean_number(record.get("Provision Coverage Ratio"))
                if pcr_value is None:
                    pcr_value = ""
                if npl_value is None:
                    npl_value = ""
                rating_value = clean_cell(record.get("Credit Rating"))
                if rating_value not in (None, ""):
                    rating_value = str(rating_value).strip()
                else:
                    rating_value = ""
                result = send_bank_eligibility(
                    bank_name=bank_name,
                    fiscal_year=year,
                    fin_period="Annual",
                    npl=npl_value,
                    pcr=pcr_value,
                    rating=rating_value,
                )
                if result.get("error"):
                    self.send_event(
                        {
                            "type": "log",
                            "line": f"APEX error {bank_name} {year}: {result['error']}",
                        }
                    )
                    continue
                status = result.get("status_code")
                response_text = result.get("response") or "(empty)"
                self.send_event(
                    {
                        "type": "log",
                        "line": f"APEX response {bank_name} {year}: {response_text}",
                    }
                )
                if result.get("payload"):
                    self.send_event(
                        {
                            "type": "log",
                            "line": f"APEX payload {bank_name} {year}: {result.get('payload')}",
                        }
                    )
                if result.get("content_type") or result.get("content_length"):
                    self.send_event(
                        {
                            "type": "log",
                            "line": f"APEX meta {bank_name} {year}: status={status} content-type={result.get('content_type')} content-length={result.get('content_length')}",
                        }
                    )
                if not result.get("ok"):
                    self.send_event(
                        {
                            "type": "log",
                            "line": f"APEX rejected {bank_name} {year} -> {status}",
                        }
                    )
                    continue
                self.send_event(
                    {
                        "type": "log",
                        "line": f"APEX sent {bank_name} {year} -> {status}",
                    }
                )
                synced += 1

        if synced:
            self.send_event(
                {
                    "type": "log",
                    "line": f"APEX sync completed ({synced} record{'s' if synced != 1 else ''}).",
                }
            )
        else:
            self.send_event(
                {
                    "type": "log",
                    "line": "APEX sync completed (no valid records were sent).",
                }
            )

    def handle_static(self, path):
        if path == "/":
            path = "/index.html"
        if path.startswith("/downloads/"):
            file_path = (ROOT / path.lstrip("/")).resolve()
            if not str(file_path).startswith(str((ROOT / "downloads").resolve())):
                self.send_error(403, "Forbidden")
                return
        elif path.startswith("/eligible_downloads/"):
            file_path = (ROOT / path.lstrip("/")).resolve()
            if not str(file_path).startswith(str(ELIGIBLE_DOWNLOADS_DIR.resolve())):
                self.send_error(403, "Forbidden")
                return
        else:
            file_path = (UI_DIR / path.lstrip("/")).resolve()
            if not str(file_path).startswith(str(UI_DIR.resolve())):
                self.send_error(403, "Forbidden")
                return
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "Not found")
            return

        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_event(self, payload):
        try:
            data = json.dumps(payload)
            message = f"data: {data}\n\n".encode("utf-8")
            self.wfile.write(message)
            self.wfile.flush()
            return True
        except BrokenPipeError:
            return False
        except ConnectionResetError:
            return False

    def log_message(self, format, *args):
        return


# --- Server bootstrapping ---
def run_server(host: str = "0.0.0.0", port: int = 8000):
    ports = [port, 8080, 8001, 5000, 0]
    tried = set()
    last_error = None

    for candidate in ports:
        if candidate in tried:
            continue
        tried.add(candidate)
        try:
            server = ThreadingHTTPServer((host, candidate), Handler)
            actual_port = server.server_address[1]
            if candidate and candidate != actual_port:
                print(f"Requested port {candidate} unavailable; using {actual_port}.")
            print(f"Serving UI on http://{host}:{actual_port}")
            server.serve_forever()
            return
        except PermissionError as exc:
            last_error = exc
            print(f"Port {candidate} unavailable ({exc}). Trying next port.")
        except OSError as exc:
            last_error = exc
            print(f"Port {candidate} unavailable ({exc}). Trying next port.")

    if last_error:
        raise last_error


# --- CLI entrypoint ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FDR Investment in Banks UI server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host, e.g. 0.0.0.0 or 127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="Preferred port")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
