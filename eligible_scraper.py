# Developed by Nayan
# --- Standard library imports ---
import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from urllib.parse import unquote, urljoin, urlparse, quote

# --- Third-party imports ---
import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from apex_client import send_bank_eligibility

# --- Optional PDF/OCR backends ---
try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

_OCR_MODULES = None
OCR_ZOOM = 3.0
OCR_CONFIG = "--oem 3 --psm 6"

# --- Shared constants and field definitions ---
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)
FIELD_ORDER = [
    "Capital Adequacy Ratio (CRAR)",
    "Leverage Ratio (LR)",
    "Non-Performing Loan Ratio (NPL)",
    "Provision Coverage Ratio (PCR)",
    "Loan to Deposit Ratio (LDR)",
    "Return on Assets (ROA)",
    "Return on Equity (ROE)",
    "Net Interest Margin (NIM)",
    "Liquidity Coverage Ratio (LCR)",
    "Net Stable Funding Ratio (NSFR)",
    "Cash to Deposit Ratio (CDR)",
    "Credit Rating (CR)",
]
FIELD_TYPES = {
    "Capital Adequacy Ratio (CRAR)": "numeric",
    "Leverage Ratio (LR)": "numeric",
    "Non-Performing Loan Ratio (NPL)": "numeric",
    "Provision Coverage Ratio (PCR)": "numeric",
    "Loan to Deposit Ratio (LDR)": "numeric",
    "Return on Assets (ROA)": "numeric",
    "Return on Equity (ROE)": "numeric",
    "Net Interest Margin (NIM)": "numeric",
    "Liquidity Coverage Ratio (LCR)": "numeric",
    "Net Stable Funding Ratio (NSFR)": "numeric",
    "Cash to Deposit Ratio (CDR)": "numeric",
    "Credit Rating (CR)": "text",
}

# --- Regex patterns for label detection and cleanup ---
CRAR_PRIMARY_LABEL_RE = re.compile(
    r"(?:Capital\s*[-\s]*To\s*[-\s]*Risk\s*[-\s]*Weighted\s*[-\s]*Asset(?:s)?\s*[-\s]*Ratio|Risk\s*[-\s]*Weighted\s*[-\s]*Asset(?:s)?\s*[-\s]*Ratio)",
    flags=re.IGNORECASE,
)
CRAR_SECONDARY_LABEL_RE = re.compile(
    r"(?:Capital\s*[-\s]*Adequacy\s*[-\s]*Ratio|\bCRAR\b)",
    flags=re.IGNORECASE,
)
CLASSIFIED_LOAN_PATTERN = r"(?<!un)(?<!non[-\\s])classified\\s+loan(?:s)?(?:\\s*ratio)?"
NPL_PRIMARY_LABEL_RE = re.compile(
    rf"(?<!Net\s)(?<!Gross\s)(?:Non Performing Loan Ratio|Non-performing Loan Ratio|Non-Performing Loan Ratio|Non Performing Loans?|Non-performing Loans?|Non-Performing Loans?|NPL Ratio|NPLs to total loans and advances(?:\s*\((?:percent|percentage)\))?|Ratio of classified loans against total loans and advances|Classified Loans against total loans and advances|{CLASSIFIED_LOAN_PATTERN}|Classified Loan Ratio|CL Ratio|% CL to total loans & advances|Percentage of Classified Loans against total loans and advances)",
    flags=re.IGNORECASE,
)
NPL_SECONDARY_LABEL_RE = re.compile(
    r"(?:Gross\s+(?:NPL Ratio|Non Performing Loan Ratio|Non-performing Loan Ratio|Non-Performing Loan Ratio)|Percentage\s+of\s+Classified\s+Loans?\s+against\s+total\s+loans?\s*(?:and|&)\s*advances|Class\.?\s*Advance\s*/\s*Total\s*Advance|Classified\s+Advance\s*/\s*Total\s*Advance|Classified\s+Advances?\s*/\s*Total\s*Advances?)",
    flags=re.IGNORECASE,
)
NPL_THRESHOLD_RE = re.compile(
    r"\b(within|below|less than|under|not more than|at most|maximum|max(?:imum)?|cap(?:ped)?|target|aim|goal|not exceed|<=)\b",
    re.I,
)
NPL_EXACT_VALUE_RE = re.compile(
    r"\b(stood at|stands at|was|were|remained at|contained at|ratio (?:stood|stands|was|is)|as of|as at|as on|i\.e\.)\b",
    re.I,
)
GENERIC_EXACT_VALUE_RE = re.compile(
    r"\b(stood at|stands at|was|were|remained at|as of|as at|as on|recorded at)\b",
    re.I,
)
GENERIC_TARGET_RE = re.compile(
    r"\b(target|aim|goal|planned|plan|planning|expected|forecast|projected|projection|aspiration)\b",
    re.I,
)
GENERIC_BENCHMARK_RE = re.compile(
    r"\b(benchmark|peer|industry average|sector average|system average|market average)\b",
    re.I,
)
GENERIC_DEFINITION_RE = re.compile(
    r"\b(defined as|definition|formula|calculation|calculated as|computed as|measured as)\b",
    re.I,
)
NPL_INDUSTRY_RE = re.compile(
    r"\bbanking\b.{0,40}\b(?:sector|industry)\b|\bindustry average\b|\bindustry\b",
    re.I,
)
BANK_POSSESSIVE_RE = re.compile(
    r"\b(?:bank|tbl|bbplc)(?:'s|’s)\b|\b[A-Za-z]{2,}\s+Bank(?:'s|’s)\b",
    re.I,
)
BANK_NAME_RE = re.compile(r"\b([A-Za-z]{2,})\s+Bank\b", re.I)
BANK_ABBR_RE = re.compile(r"\b(?:BBPLC|TBL)\b", re.I)
WHEREAS_RE = re.compile(r"\bwhereas|while\b", re.I)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
NUMERIC_RE = re.compile(r"-?[0-9]+(?:\.[0-9]+)?%?")
MONTH_TOKEN_RE = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-–']?\d{2}\b",
    re.I,
)

DATE_RATING_RE_1 = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2}),\s*(20\d{2})\b",
    re.I,
)
DATE_RATING_RE_2 = re.compile(
    r"\b(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(20\d{2})\b",
    re.I,
)
DATE_RATING_RE_3 = re.compile(
    r"\b(\d{1,2})[-/](Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[-/](\d{2,4})\b",
    re.I,
)

GENERIC_LABEL_RE = re.compile(
    r"\b[A-Za-z][A-Za-z/&\-\s]{0,40}\b(?:Ratio|Margin|Coverage|Return|Payout|NPL|ROA|ROE|NIM)\b",
    re.I,
)
GENERIC_LABEL_TOKEN_RE = re.compile(
    r"\b(?:ratio|margin|coverage|return|payout|npl|roa|roe|nim)\b", re.I
)
STANDALONE_TOKENS = (
    "standalone",
    "stand-alone",
    "stand alone",
    "solo",
    "solo basis",
    "separate",
    "bank only",
    "bank-only",
    "bank basis",
    "bank-basis",
    "standalone basis",
    "stand-alone basis",
    "stand alone basis",
)
CONSOLIDATED_TOKENS = ("consolidated", "consolidate", "group")
REQUIREMENT_TOKENS = ("requirement", "minimum")
GROUP_BANK_TOKENS = ("group", "bank")
PERCENT_REQUIRED_FIELDS = {
    name for name, field_type in FIELD_TYPES.items() if field_type == "numeric"
}
RATING_TOKEN_RE = re.compile(
    r"(?<![A-Z0-9])("
    r"A\s*A\s*A|"
    r"A\s*A\s*[-]?\s*[123]|"
    r"A\s*A\s*[+-]|"
    r"A\s*A|"
    r"A\s*[-]?\s*[123]|"
    r"A\s*[+-]|"
    r"A|"
    r"B\s*B\s*B\s*[+-]|"
    r"B\s*B\s*B|"
    r"B\s*B\s*[+-]|"
    r"B\s*B|"
    r"B\s*[+-]|"
    r"B|"
    r"C\s*C\s*C|"
    r"C\s*C|"
    r"C|"
    r"D"
    r")(?![A-Z0-9])"
)
LONG_TERM_RATING_RE = re.compile(r"\blong\s*-\s*term\b|\blong\s+term\b", re.I)
SHORT_TERM_RATING_RE = re.compile(r"\bshort\s*-\s*term\b|\bshort\s+term\b", re.I)
EXPLICIT_RATING_TERM_RE = re.compile(
    r"\blong\s*-\s*term\s+rating\b|\blong\s+term\s+rating\b|\bshort\s*-\s*term\s+rating\b|\bshort\s+term\s+rating\b",
    re.I,
)
SURVEILLANCE_RATING_RE = re.compile(r"\bsurveillance\s+ratings?\b", re.I)
BASIC_RATING_CONTEXT_RE = re.compile(
    r"\b(outlook|rating by|rated by|credit rating of|entity rating|issuer rating|national rating|surveillance rating)\b",
    re.I,
)
BASIC_RATING_LINE_RE = re.compile(
    r"\b(credit rating|rating summary|ratings?:|long\s*term|short\s*term|outlook)\b",
    re.I,
)
CREDIT_RATING_VALUE_CONTEXT_RE = re.compile(
    r"\b(date of rating|surveillance rating|long\s*-\s*term|long\s+term|short\s*-\s*term|short\s+term|ratings?\s+have\s+been\s+awarded|outlook|stable|negative|positive)\b",
    re.I,
)
RATING_ADDRESS_CONTEXT_RE = re.compile(
    r"\b(flat|suite|level|floor|tower|road|rd\b|avenue|ave\b|house|plot|block|dhaka|chattogram|ctg|tejgaon)\b",
    re.I,
)
CREDIT_RATING_SECTION_RE = re.compile(
    r"\bcredit\s+rating\s+of\b|\bcredit\s+rating\s+of\s+the\s+bank\b|\bcredit\s+rating\s+of\s+[A-Za-z]{2,}\s+bank\b",
    re.I,
)
BOND_RATING_CONTEXT_RE = re.compile(
    r"\b(perpetual|subordinated|bond|debenture|sukuk|tier\s*(?:ii|2|iii|3)|hyb(?:rid)?)\b",
    re.I,
)
PENALTY_TOKEN_RE = re.compile(
    r"\b(penalt(?:y|ies)?|fine(?:s)?|non[- ]?compliance|violation|breach)\b", re.I
)
# --- Canonical field label regexes ---
FIELD_LABELS = {
    "Capital Adequacy Ratio (CRAR)": re.compile(
        r"(?:Capital\s*[-\s]*To\s*[-\s]*Risk\s*[-\s]*Weighted\s*[-\s]*Asset(?:s)?\s*[-\s]*Ratio|Risk\s*[-\s]*Weighted\s*[-\s]*Asset(?:s)?\s*[-\s]*Ratio|Capital\s*[-\s]*Adequacy\s*[-\s]*Ratio|\bCRAR\b)",
        re.I,
    ),
    "Leverage Ratio (LR)": re.compile(
        r"(?:Leverage Ratio|Leverage-Ratio|Tier\s*[-\s]*1\s*Leverage\s*Ratio|Basel\s*III\s*Leverage\s*Ratio|\bLR\b)",
        re.I,
    ),
    "Non-Performing Loan Ratio (NPL)": re.compile(
        rf"(?:(?<!Net\s)(?<!Gross\s)(?:Non Performing Loan Ratio|Non-performing Loan Ratio|Non-Performing Loan Ratio|Non Performing Loans?|Non-performing Loans?|Non-Performing Loans?|NPL Ratio|NPLs to total loans and advances(?:\s*\((?:percent|percentage)\))?|Ratio of classified loans against total loans and advances|Classified Loans against total loans and advances|{CLASSIFIED_LOAN_PATTERN}|Classified Loan Ratio|CL Ratio|% CL to total loans & advances|Percentage of Classified Loans against total loans and advances)|Gross\s+(?:NPL Ratio|Non Performing Loan Ratio|Non-performing Loan Ratio|Non-Performing Loan Ratio))",
        re.I,
    ),
    "Provision Coverage Ratio (PCR)": re.compile(
        r"(?:Provision Coverage Ratio|Provision-Coverage Ratio|Provision Coverage|\bPCR\b|NPL Coverage Ratio|NPL Coverage)",
        re.I,
    ),
    "Loan to Deposit Ratio (LDR)": re.compile(
        r"(?:Loan To Deposit Ratio|Loan-To-Deposit Ratio|Advance Deposit Ratio|Advance-Deposit Ratio|Advance to Deposit Ratio|\bAD Ratio\b|\bADR\b)",
        re.I,
    ),
    "Return on Assets (ROA)": re.compile(
        r"(?:Return on Asset|Return on Assets|Return-on-Asset|Return-on-Assets|\bROA\b|PAT\s*/\s*Average\s*Assets?|Return\s+on\s+Average\s+Assets)",
        re.I,
    ),
    "Return on Equity (ROE)": re.compile(
        r"(?:Return on Equity|Return-on-Equity|Return on Shareholders'?\s*Equity|Return on Average Equity|\bROE\b|PAT\s*/\s*Average\s*Equity)",
        re.I,
    ),
    "Net Interest Margin (NIM)": re.compile(
        r"(?:Net Interest Margin|Net-Interest-Margin|\bNIM\b|Net Interest Income\s*(?:as\s*)?%?\s*of\s*Working\s*Fund|Net Interest Income\s*(?:%|percent|percentage)\b)",
        re.I,
    ),
    "Liquidity Coverage Ratio (LCR)": re.compile(
        r"(?:Liquidity Coverage Ratio|Liquidity-Coverage Ratio|\bLCR\b)", re.I
    ),
    "Net Stable Funding Ratio (NSFR)": re.compile(
        r"(?:Net Stable Funding Ratio|Net-Stable-Funding Ratio|\bNSFR\b)", re.I
    ),
    "Cash to Deposit Ratio (CDR)": re.compile(
        r"(?:Cash to Deposit Ratio|Cash-To-Deposit Ratio)", re.I
    ),
}
ALL_LABEL_REGEXES = list(FIELD_LABELS.values())

# --- Label routing helpers ---
def target_label_regexes(field_name):
    if field_name == "Capital Adequacy Ratio (CRAR)":
        return [CRAR_PRIMARY_LABEL_RE, CRAR_SECONDARY_LABEL_RE]
    if field_name == "Non-Performing Loan Ratio (NPL)":
        return [NPL_PRIMARY_LABEL_RE, NPL_SECONDARY_LABEL_RE]
    label = FIELD_LABELS.get(field_name)
    return [label] if label else []


def field_keyword_match(field_name, patterns, page_text):
    if not page_text:
        return False
    for label in target_label_regexes(field_name):
        if label and label.search(page_text):
            return True
    for pattern in patterns or []:
        if re.search(pattern, page_text, flags=re.IGNORECASE):
            return True
    return False


def has_other_ratio_label(text, target_labels):
    if not text:
        return False
    target_spans = []
    for label in target_labels or []:
        if not label:
            continue
        for match in label.finditer(text):
            target_spans.append(match.span())

    def overlaps(span):
        for start, end in target_spans:
            if not (span[1] <= start or span[0] >= end):
                return True
        return False

    for label in ALL_LABEL_REGEXES:
        if label in (target_labels or []):
            continue
        if label.search(text):
            return True
    for match in GENERIC_LABEL_RE.finditer(text):
        if target_spans and overlaps(match.span()):
            continue
        return True
    return False


def other_label_between(text, start, end, exclude_labels=None):
    if not text or start is None or end is None or end <= start:
        return False
    for label in ALL_LABEL_REGEXES:
        if exclude_labels and label in exclude_labels:
            continue
        if label.search(text, pos=start, endpos=end):
            return True
    generic = GENERIC_LABEL_RE.search(text, pos=start, endpos=end)
    return bool(generic)


# --- File and text normalization utilities ---
def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path):
    if path:
        os.makedirs(path, exist_ok=True)


def normalize_text(text):
    if text is None:
        return ""
    # Normalize common unicode dashes/minus to ASCII for consistent parsing.
    text = (
        str(text)
        .replace("\u2212", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("â€“", "-")
        .replace("â€”", "-")
        .replace("â€-", "-")
        .replace("â€\x93", "-")
        .replace("â€\x94", "-")
    )
    return " ".join(text.split())


def sanitize_filename(value):
    cleaned = re.sub(r"[^A-Za-z0-9_\\-]+", "_", str(value).strip())
    cleaned = cleaned.strip("_")
    return cleaned or "Unknown"


def parse_numeric(value):
    if value is None:
        return None
    text = str(value).replace("\u2212", "-")
    # Treat parenthesized values as negative.
    negative = bool(re.search(r"\(\s*-?\d", text))
    match = re.search(r"-?[0-9]+(?:\.[0-9]+)?", text)
    if not match:
        return None
    number = float(match.group(0))
    if negative and number > 0:
        number = -number
    return number



MONTH_INDEX = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def parse_year_token(value):
    if value is None:
        return None
    year = int(value)
    if year < 100:
        year += 2000
    return year


def month_number(token):
    if not token:
        return None
    key = str(token).strip().lower()[:3]
    return MONTH_INDEX.get(key)


def extract_latest_rating_date(text):
    if not text:
        return None
    candidates = []
    for match in DATE_RATING_RE_1.finditer(text):
        month = month_number(match.group(1))
        day = int(match.group(2))
        year = parse_year_token(match.group(3))
        if month and year:
            candidates.append((year, month, day))
    for match in DATE_RATING_RE_2.finditer(text):
        day = int(match.group(1))
        month = month_number(match.group(2))
        year = parse_year_token(match.group(3))
        if month and year:
            candidates.append((year, month, day))
    for match in DATE_RATING_RE_3.finditer(text):
        day = int(match.group(1))
        month = month_number(match.group(2))
        year = parse_year_token(match.group(3))
        if month and year:
            candidates.append((year, month, day))
    return max(candidates) if candidates else None


def normalize_credit_rating(text):
    cleaned = re.sub(r"[^A-Z0-9+/\- ]", " ", str(text).upper())
    cleaned = re.sub(r"\bA\s+A\s+A\b", "AAA", cleaned)
    cleaned = re.sub(r"\bA\s+A\b", "AA", cleaned)
    cleaned = re.sub(r"\bB\s+B\s+B\b", "BBB", cleaned)
    cleaned = re.sub(r"\bB\s+B\b", "BB", cleaned)
    cleaned = re.sub(r"\bC\s+C\s+C\b", "CCC", cleaned)
    cleaned = re.sub(r"\bC\s+C\b", "CC", cleaned)
    cleaned = re.sub(r"\bAA\s*-\s*([123])\b", r"AA\1", cleaned)
    cleaned = re.sub(r"\bA\s*-\s*([123])\b", r"A\1", cleaned)
    cleaned = cleaned.replace("AA-1", "AA1").replace("AA-2", "AA2").replace("AA-3", "AA3")
    cleaned = cleaned.replace("A-1", "A1").replace("A-2", "A2").replace("A-3", "A3")
    cleaned = re.sub(r"AA\s*([123])", r"AA\1", cleaned)
    cleaned = re.sub(r"AA\s*([+-])", r"AA\1", cleaned)
    cleaned = re.sub(r"A\s*([123])", r"A\1", cleaned)
    cleaned = re.sub(r"A\s*([+-])", r"A\1", cleaned)
    cleaned = re.sub(r"BBB\s*([+-])", r"BBB\1", cleaned)
    cleaned = re.sub(r"BB\s*([+-])", r"BB\1", cleaned)
    cleaned = re.sub(r"B\s*([+-])", r"B\1", cleaned)
    cleaned = normalize_text(cleaned)
    matches = RATING_TOKEN_RE.findall(cleaned)
    if not matches:
        return None
    token = matches[0]
    if token == "AAA":
        return "AAA"
    if token.startswith("AA"):
        return "AA"
    if token.startswith("A"):
        return "A"
    if token.startswith("BBB"):
        return "BBB"
    if token.startswith("BB"):
        return "BB"
    if token.startswith("B"):
        return "B"
    if token.startswith("CCC"):
        return "CCC"
    if token.startswith("CC"):
        return "CC"
    if token.startswith("C"):
        return "C"
    if token.startswith("D"):
        return "D"
    return None


def normalize_regulatory_compliance(text):
    lower = str(text).lower()
    if "no penalt" in lower:
        return "No Penalty"
    if "penalt" in lower:
        return "Penalty"
    return None


def normalize_field_value(field_name, raw_value):
    field_type = FIELD_TYPES.get(field_name, "text")
    if field_type == "numeric":
        return parse_numeric(raw_value)
    if field_name == "Credit Rating (CR)":
        return normalize_credit_rating(raw_value)
    if field_name == "Regulatory Compliance (RC)":
        return normalize_regulatory_compliance(raw_value)
    cleaned = re.sub(r"[^A-Za-z ]", " ", str(raw_value))
    cleaned = normalize_text(cleaned)
    return cleaned or None


# --- Year and table parsing helpers ---
def extract_year_tokens(text):
    return set(YEAR_RE.findall(text))


def extract_years_in_order(text):
    years = []
    for match in YEAR_RE.finditer(text or ""):
        year = match.group(0)
        if year not in years:
            years.append(year)
    return years


def is_table_context(line_text, context_text, current_years, current_columns):
    lower = (line_text or "").lower()
    context_lower = (context_text or "").lower()
    if current_columns:
        return True
    if re.search(r"\b20\d{2}\b.*\b20\d{2}\b", lower):
        return True
    if "particular" in lower or "key ratios" in lower or "ratio (%)" in lower:
        return True
    if "particular" in context_lower or "key ratios" in context_lower:
        return True
    return False


def extract_year_header(line_text):
    lower = line_text.lower()
    if "annual report" in lower:
        return None
    years = YEAR_RE.findall(line_text)
    if not years:
        return None
    unique_years = []
    for year in years:
        if year not in unique_years:
            unique_years.append(year)
    if len(unique_years) < 2:
        return None
    is_header = False
    if "particular" in lower or "year" in lower or "change" in lower:
        is_header = True
    if re.search(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-/]?\s*(?:19|20)\d{2}\b",
        lower,
    ):
        is_header = True
    tokens = re.findall(r"\b\w+\b", line_text)
    if tokens:
        year_tokens = sum(1 for token in tokens if YEAR_RE.fullmatch(token))
        if year_tokens / len(tokens) >= 0.5:
            is_header = True
    if not is_header:
        return None
    if len(years) > len(unique_years):
        return years
    return unique_years


def extract_column_labels(line_text):
    lower = line_text.lower()
    if not any(token in lower for token in STANDALONE_TOKENS + CONSOLIDATED_TOKENS + REQUIREMENT_TOKENS):
        return None
    positions = []
    for token in REQUIREMENT_TOKENS:
        for pos in keyword_positions(line_text, [token]):
            positions.append((pos, "requirement"))
    for token in STANDALONE_TOKENS:
        for pos in keyword_positions(line_text, [token]):
            positions.append((pos, "standalone"))
    for token in CONSOLIDATED_TOKENS:
        for pos in keyword_positions(line_text, [token]):
            positions.append((pos, "consolidated"))
    if not positions:
        return None
    positions.sort(key=lambda item: item[0])
    ordered = []
    for _, label in positions:
        if not ordered or ordered[-1] != label:
            ordered.append(label)
    if len(ordered) < 2:
        return None
    return ordered


def extract_group_bank_header(line_text):
    lower = line_text.lower()
    if "bank" not in lower:
        return None
    if "group" not in lower and not any(token in lower for token in CONSOLIDATED_TOKENS):
        return None
    positions = []
    for token in CONSOLIDATED_TOKENS:
        for pos in keyword_positions(line_text, [token]):
            positions.append((pos, "group"))
    for token in GROUP_BANK_TOKENS:
        for pos in keyword_positions(line_text, [token]):
            positions.append((pos, token))
    if not positions:
        return None
    positions.sort(key=lambda item: item[0])
    ordered = []
    for _, label in positions:
        if not ordered or ordered[-1] != label:
            ordered.append(label)
    if "group" in ordered and "bank" in ordered:
        return ordered
    return None


def is_year_value(value_text):
    if not value_text:
        return False
    cleaned = str(value_text).strip()
    if cleaned.endswith("%"):
        return False
    cleaned = cleaned.lstrip("-")
    cleaned = cleaned.strip("()")
    if re.fullmatch(r"\d{4}", cleaned):
        year_val = int(cleaned)
        return 1900 <= year_val <= 2100
    return False


def infer_value_column_from_tokens(line_text, value_span):
    if not line_text or not value_span:
        return None
    value_pos = value_span[0]
    standalone_positions = keyword_positions(line_text, STANDALONE_TOKENS)
    consolidated_positions = keyword_positions(line_text, CONSOLIDATED_TOKENS)
    if standalone_positions or consolidated_positions:
        bank_positions = []
        group_positions = []
    else:
        if extract_group_bank_header(line_text):
            bank_positions = keyword_positions(line_text, ["bank"])
            group_positions = keyword_positions(line_text, ["group"])
        else:
            bank_positions = []
            group_positions = []
    best = None
    best_dist = None
    for label, positions in (
        ("standalone", standalone_positions),
        ("consolidated", consolidated_positions),
        ("bank", bank_positions),
        ("group", group_positions),
    ):
        if not positions:
            continue
        dist = min_distance(value_pos, positions)
        if dist is None:
            continue
        if best_dist is None or dist < best_dist:
            best = label
            best_dist = dist
    return best


def percent_token_near_value(text, span, window=30):
    if not text or not span:
        return False
    s, e = span
    forward = text[e : min(len(text), e + window)]
    backward = text[max(0, s - window) : s]
    forward_match = re.search(
        r"%|\bpercent(?:age)?\b|\bper\s*cent\b", forward, flags=re.IGNORECASE
    )
    if forward_match:
        between = forward[: forward_match.start()]
        if not NUMERIC_RE.search(between):
            return True
    backward_match = re.search(
        r"%|\bpercent(?:age)?\b|\bper\s*cent\b", backward, flags=re.IGNORECASE
    )
    if backward_match:
        between = backward[backward_match.end() :]
        if not NUMERIC_RE.search(between):
            return True
    return False


def has_local_percent_indicator(line_text, context_text=None, value_span=None):
    if not value_span:
        return False
    start, _ = value_span
    header_window = line_text[max(0, start - 60) : start]
    if percent_token_near_value(line_text, value_span):
        return True
    if "(%)" in header_window or "%)" in header_window:
        return True
    if context_text:
        if "(%)" in context_text:
            return True
        if re.search(
            r"\bpercent(?:age)?\b|\bper\s*cent\b", context_text, flags=re.IGNORECASE
        ):
            return True
    return False


def has_percent_indicator(raw_value, line_text, context_text=None, value_span=None):
    if raw_value is None:
        return False
    if "%" in str(raw_value):
        return True
    if value_span:
        start, _ = value_span
        header_window = line_text[max(0, start - 60) : start]
        if percent_token_near_value(line_text, value_span):
            return True
        if "(%)" in header_window or "%)" in header_window:
            return True
        line_has_percent = "%" in line_text or re.search(
            r"\bpercent(?:age)?\b|\bper\s*cent\b", line_text, flags=re.IGNORECASE
        )
        if not line_has_percent and context_text:
            if "(%)" in context_text:
                return True
            if re.search(
                r"\bpercent(?:age)?\b|\bper\s*cent\b", context_text, flags=re.IGNORECASE
            ):
                return True
        return False
    if "%" in line_text:
        return True
    if context_text and "%" in context_text:
        return True
    if re.search(r"\bpercent(?:age)?\b|\bper\s*cent\b", line_text, flags=re.IGNORECASE):
        return True
    if context_text and re.search(
        r"\bpercent(?:age)?\b|\bper\s*cent\b", context_text, flags=re.IGNORECASE
    ):
        return True
    return False


def has_currency_marker(text, value_span):
    if not text or not value_span:
        return False
    start, end = value_span
    window = text[max(0, start - 10) : min(len(text), end + 10)]
    return bool(re.search(r"\b(BDT|TK|Taka|USD|\$)\b", window, flags=re.IGNORECASE))


def has_higher_percent_in_line(line_text, value):
    if not line_text or value is None:
        return False
    values = []
    for match in re.finditer(r"-?\d+(?:\.\d+)?%", line_text):
        parsed = parse_numeric(match.group(0))
        if parsed is not None:
            values.append(parsed)
    if not values:
        return False
    for other in values:
        if other > value + 5:
            return True
    return False


def is_axis_tick_line(line_text):
    percents = []
    for match in re.finditer(r"-?\d+(?:\.\d+)?%", line_text):
        parsed = parse_numeric(match.group(0))
        if parsed is not None:
            percents.append(parsed)
    if len(percents) < 3:
        return False
    rounded = [val for val in percents if abs(val - round(val)) < 0.01]
    if len(rounded) < 3:
        return False
    return (max(rounded) - min(rounded)) >= 40


def extract_label_order_value(candidate_text, target_field):
    first_num = NUMERIC_RE.search(candidate_text)
    if not first_num:
        return None
    first_num_pos = first_num.start()
    for label in ALL_LABEL_REGEXES:
        if label.search(candidate_text, pos=first_num_pos):
            return None
    if GENERIC_LABEL_TOKEN_RE.search(candidate_text, pos=first_num_pos):
        return None
    label_positions = []
    label_spans = []
    for field_name, label_re in FIELD_LABELS.items():
        if FIELD_TYPES.get(field_name) != "numeric":
            continue
        match = label_re.search(candidate_text)
        if match and match.start() < first_num_pos:
            label_positions.append((match.start(), field_name))
            label_spans.append(match.span())
    generic_positions = []
    for match in GENERIC_LABEL_TOKEN_RE.finditer(candidate_text[:first_num_pos]):
        span = match.span()
        overlaps = False
        for known_span in label_spans:
            if not (span[1] <= known_span[0] or span[0] >= known_span[1]):
                overlaps = True
                break
        if overlaps:
            continue
        generic_positions.append((span[0], None))
    combined_positions = label_positions + generic_positions
    if len(combined_positions) < 2:
        return None
    combined_positions.sort(key=lambda item: item[0])
    if len(combined_positions) > 4:
        return None
    if combined_positions[-1][0] - combined_positions[0][0] > 40:
        return None
    numbers = []
    percent_numbers = []
    tail = candidate_text[first_num_pos:]
    for num_match in NUMERIC_RE.finditer(tail):
        raw = num_match.group(0)
        if is_year_value(raw):
            continue
        span = (first_num_pos + num_match.start(), first_num_pos + num_match.end())
        numbers.append((raw, span))
        if "%" in raw:
            percent_numbers.append((raw, span))
    if target_field in PERCENT_REQUIRED_FIELDS and percent_numbers:
        numbers = percent_numbers
    if len(numbers) < len(combined_positions):
        return None
    ordered_fields = [field for _, field in combined_positions]
    if (
        target_field in ("Liquidity Coverage Ratio (LCR)", "Net Stable Funding Ratio (NSFR)")
        and "Liquidity Coverage Ratio (LCR)" in ordered_fields
        and "Net Stable Funding Ratio (NSFR)" in ordered_fields
        and len(numbers) > len(ordered_fields)
        and not extract_year_tokens(candidate_text)
    ):
        numbers = numbers[-len(ordered_fields) :]
    if target_field not in ordered_fields:
        return None
    target_index = ordered_fields.index(target_field)
    return numbers[target_index]


def should_fallback_full_line(candidate_text):
    if not candidate_text:
        return False
    if len(extract_year_tokens(candidate_text)) >= 2:
        return True
    if len(list(NUMERIC_RE.finditer(candidate_text))) >= 5:
        return True
    return False


def is_formula_multiplier(text, span):
    if not span:
        return False
    start, end = span
    prefix = text[max(0, start - 3) : start]
    if any(token in prefix for token in ("*", "x", "×")):
        return True
    if re.search(r"\b[A-Z]\s*/\s*B\)?\s*$", text[:start], flags=re.IGNORECASE):
        return True
    return False


def apply_negative_context(raw_value, line_text, value_span):
    if raw_value is None or not value_span:
        return raw_value
    if str(raw_value).lstrip().startswith("-"):
        return raw_value
    start, end = value_span
    prefix = line_text[:start]
    suffix = line_text[end:]
    if re.search(r"\(\s*$", prefix) and re.search(r"^\s*\)", suffix):
        return f"-{raw_value}"
    if re.search(r"\(\s*-\s*$", prefix):
        return f"-{raw_value}"
    if re.search(r"-\s*$", prefix):
        stripped = prefix.rstrip()
        if stripped.endswith("-"):
            before_dash = stripped[:-1].rstrip()
            if before_dash.endswith("%") and len(before_dash) >= 2 and before_dash[-2].isdigit():
                return raw_value
            if before_dash and before_dash[-1].isdigit():
                return raw_value
        return f"-{raw_value}"
    if start > 0 and line_text[start - 1] == "-":
        if start > 1 and line_text[start - 2].isdigit():
            return raw_value
        return f"-{raw_value}"
    return raw_value


def keyword_positions(text, tokens):
    lower = text.lower()
    positions = []
    for token in tokens:
        token_lower = token.lower()
        start = 0
        while True:
            idx = lower.find(token_lower, start)
            if idx == -1:
                break
            positions.append(idx)
            start = idx + len(token_lower)
    return positions


def min_distance(value_pos, positions):
    if value_pos is None or not positions:
        return None
    return min(abs(value_pos - pos) for pos in positions)


def extract_crar_values(candidate_text):
    label_match = CRAR_PRIMARY_LABEL_RE.search(candidate_text)
    if not label_match:
        label_match = CRAR_SECONDARY_LABEL_RE.search(candidate_text)
    if not label_match:
        return []
    tail = candidate_text[label_match.end() :]
    values = []
    for num_match in NUMERIC_RE.finditer(tail):
        raw = num_match.group(0)
        if is_year_value(raw):
            continue
        span = (
            label_match.end() + num_match.start(),
            label_match.end() + num_match.end(),
        )
        values.append((raw, span))
    return values


def extract_numeric_values_after_label(
    candidate_text, label_re, context_text=None, exclude_labels=None, max_distance=None
):
    label_match = label_re.search(candidate_text)
    if not label_match:
        return [], False
    exclude_patterns = set()
    if label_re:
        exclude_patterns.add(label_re.pattern)
    if exclude_labels:
        exclude_patterns.update(
            lbl.pattern for lbl in exclude_labels if lbl and getattr(lbl, "pattern", None)
        )
    start = label_match.end()
    # If the label omits "ratio" but it immediately follows, treat it as part of the label.
    ratio_tail = re.match(r"\s*ratio\b", candidate_text[start:], flags=re.IGNORECASE)
    if ratio_tail:
        start += ratio_tail.end()
    next_label_pos = None
    for other_label in ALL_LABEL_REGEXES:
        if exclude_labels and other_label in exclude_labels:
            continue
        if exclude_patterns and other_label.pattern in exclude_patterns:
            continue
        other_match = other_label.search(candidate_text, pos=start)
        if not other_match:
            continue
        if next_label_pos is None or other_match.start() < next_label_pos:
            next_label_pos = other_match.start()
    generic_match = GENERIC_LABEL_RE.search(candidate_text, pos=start)
    if generic_match:
        if next_label_pos is None or generic_match.start() < next_label_pos:
            next_label_pos = generic_match.start()
    if next_label_pos is not None:
        segment = candidate_text[start:next_label_pos]
    tail = candidate_text[start:next_label_pos] if next_label_pos else candidate_text[start:]
    values = []
    for num_match in NUMERIC_RE.finditer(tail):
        raw = num_match.group(0)
        if is_year_value(raw):
            continue
        abs_start = start + num_match.start()
        if max_distance is not None and abs_start - start > max_distance:
            continue
        if other_label_between(candidate_text, start, abs_start, exclude_labels):
            continue
        span = (abs_start, start + num_match.end())
        values.append((raw, span))
    used_context = False
    if context_text and len(values) <= 1:
        context_match = label_re.search(context_text)
        if context_match:
            cstart = context_match.end()
            ratio_tail = re.match(r"\s*ratio\b", context_text[cstart:], flags=re.IGNORECASE)
            if ratio_tail:
                cstart += ratio_tail.end()
            cnext_label_pos = None
            for other_label in ALL_LABEL_REGEXES:
                if exclude_labels and other_label in exclude_labels:
                    continue
                if exclude_patterns and other_label.pattern in exclude_patterns:
                    continue
                other_match = other_label.search(context_text, pos=cstart)
                if not other_match:
                    continue
                if cnext_label_pos is None or other_match.start() < cnext_label_pos:
                    cnext_label_pos = other_match.start()
            generic_match = GENERIC_LABEL_RE.search(context_text, pos=cstart)
            if generic_match:
                if cnext_label_pos is None or generic_match.start() < cnext_label_pos:
                    cnext_label_pos = generic_match.start()
            ctail = context_text[cstart:cnext_label_pos] if cnext_label_pos else context_text[cstart:]
            context_values = []
            for num_match in NUMERIC_RE.finditer(ctail):
                raw = num_match.group(0)
                if is_year_value(raw):
                    continue
                abs_start = cstart + num_match.start()
                if max_distance is not None and abs_start - cstart > max_distance:
                    continue
                if other_label_between(context_text, cstart, abs_start, exclude_labels):
                    continue
                span = (abs_start, cstart + num_match.end())
                context_values.append((raw, span))
            if len(context_values) > len(values):
                values = context_values
                used_context = True
    if values:
        return values, used_context
    # Fallback: if label exists but numbers are before it (common in charts/cards), scan full line.
    if should_fallback_full_line(candidate_text) and not has_other_ratio_label(
        candidate_text, exclude_labels
    ):
        for num_match in NUMERIC_RE.finditer(candidate_text):
            raw = num_match.group(0)
            if is_year_value(raw):
                continue
            span = (num_match.start(), num_match.end())
            values.append((raw, span))
    return values, False


def is_tier_ratio_value(line_text, value_span):
    if not line_text or not value_span:
        return False
    start, end = value_span
    window = line_text[max(0, start - 140) : min(len(line_text), end + 40)].lower()
    if re.search(r"\btier\s*[- ]?(?:1|2|i|ii)\b", window) or "common equity tier" in window or "cet1" in window:
        local = line_text[max(0, start - 40) : min(len(line_text), end + 20)].lower()
        if re.search(r"total\s+capital|total\s+capital\s+adequacy|total\s+capital\s+ratio", local):
            return False
        return True
    return False


def is_requirement_value(line_text, value_span):
    if not line_text or not value_span:
        return False
    start, end = value_span
    window_start = max(0, start - 80)
    window = line_text[window_start:start].lower()
    match = re.search(r"minimum requirement|required level|required|requirement", window)
    if not match:
        # Check for requirement tokens appearing after the value.
        end_window = line_text[end : min(len(line_text), end + 80)].lower()
        match_after = re.search(
            r"minimum requirement|required level|required|requirement", end_window
        )
        if not match_after:
            return False
        between = end_window[: match_after.start()]
        if NUMERIC_RE.search(between):
            return False
        return True
    between = window[match.end() :]
    if NUMERIC_RE.search(between):
        return False
    return True


def is_minimum_ratio_value(line_text, value_span):
    if not line_text or not value_span:
        return False
    start, end = value_span
    window_start = max(0, start - 80)
    window = line_text[window_start:start].lower()
    match = re.search(r"\bminimum\b|\bmin\b", window)
    if not match:
        end_window = line_text[end : min(len(line_text), end + 80)].lower()
        match_after = re.search(r"\bminimum\b|\bmin\b", end_window)
        if not match_after:
            return False
        between = end_window[: match_after.start()]
        if NUMERIC_RE.search(between):
            return False
        return True
    between = window[match.end() :]
    if NUMERIC_RE.search(between):
        return False
    return True


def is_day_in_date_context(line_text, value_span):
    if not line_text or not value_span:
        return False
    start, end = value_span
    window = line_text[max(0, start - 12) : min(len(line_text), end + 12)].lower()
    return bool(
        re.search(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\b", window)
    )


def basis_label_after_value(line_text, value_span):
    if not line_text or not value_span:
        return None
    _, end = value_span
    window = line_text[end : min(len(line_text), end + 90)].lower()
    if re.search(
        r"\bsolo\b|\bstandalone\b|\bstand[- ]?alone\b|\bbank\s*only\b|\bbank\s*basis\b",
        window,
    ):
        return "standalone"
    if re.search(r"\bconsolidated\b|\bconsolidate\b|\bgroup\b", window):
        return "consolidated"
    return None


def is_pre_total_capital_value(line_text, value_span):
    if not line_text or not value_span:
        return False
    lower = line_text.lower()
    if "total capital" not in lower:
        return False
    if "tier" not in lower and "cet1" not in lower and "common equity" not in lower:
        return False
    total_pos = lower.find("total capital")
    return value_span[0] < total_pos


# --- Heuristic filters for indicator lines ---
def is_crar_exclusion_line(line_text):
    lower = line_text.lower()
    if "shock" in lower or "stress" in lower or "scenario" in lower:
        return True
    if "minimum crar" in lower:
        return True
    if "minimum" in lower and "crar" in lower:
        return True
    if "requirement" in lower and ("crar" in lower or "capital adequacy" in lower):
        return True
    if "conservation buffer" in lower:
        return True
    return False


def is_comparison_line(line_text):
    lower = line_text.lower()
    if any(token in lower for token in ["<", ">", "\u2264", "\u2265"]):
        return True
    if "less than" in lower or "greater than" in lower:
        return True
    range_match = re.search(r"(\d{2,4})\s*%?\s*-\s*(\d{1,4})", lower)
    if range_match:
        numeric_count = len(NUMERIC_RE.findall(lower))
        if numeric_count > 2:
            return False
        left = range_match.group(1)
        if re.fullmatch(r"\d{4}", left):
            year_val = int(left)
            if 1900 <= year_val <= 2100:
                return False
        return True
    return False


def has_subcolumn_tokens(text):
    if not text:
        return False
    return bool(re.search(r"\b(required|held|maintained)\b", text, flags=re.IGNORECASE))


def has_threshold_marker(line_text):
    return bool(
        re.search(r"[<>≤≥]\s*\d", line_text)
        or re.search(r"\?\s*\d", line_text)
        or re.search(
            r"\b(?:at least|at most|not less than|not more than|threshold|required)\b",
            line_text,
            re.I,
        )
    )


def is_scoring_table_line(line_text):
    lower = line_text.lower()
    return "benchmark" in lower or "score" in lower or "indicator" in lower


def is_definition_context(line_text, context_text=None):
    combined = f"{line_text or ''} {context_text or ''}"
    combined_lower = combined.lower()
    if GENERIC_DEFINITION_RE.search(combined):
        if GENERIC_EXACT_VALUE_RE.search(combined):
            return False
        if extract_year_tokens(combined_lower):
            return False
        return True
    return False


def is_target_context(line_text, context_text=None):
    combined = f"{line_text or ''} {context_text or ''}"
    if GENERIC_TARGET_RE.search(combined):
        if GENERIC_EXACT_VALUE_RE.search(combined):
            return False
        if extract_year_tokens(combined):
            return False
        return True
    return False


def is_benchmark_context(line_text, context_text=None):
    combined = f"{line_text or ''} {context_text or ''}"
    if GENERIC_BENCHMARK_RE.search(combined):
        if GENERIC_EXACT_VALUE_RE.search(combined):
            return False
        if extract_year_tokens(combined):
            return False
        return True
    return False


def is_consolidated_line(line_text):
    lower = line_text.lower()
    return any(token in lower for token in CONSOLIDATED_TOKENS)


def is_standalone_line(line_text):
    lower = line_text.lower()
    return any(token in lower for token in STANDALONE_TOKENS)


def bank_mention_positions(text):
    if not text:
        return []
    positions = [m.start() for m in BANK_ABBR_RE.finditer(text)]
    for match in BANK_NAME_RE.finditer(text):
        lead = match.group(1).lower()
        if lead in {"the", "this", "that", "our", "your", "their", "a", "an"}:
            continue
        positions.append(match.start())
    for match in BANK_POSSESSIVE_RE.finditer(text):
        positions.append(match.start())
    return positions


def is_npl_coverage_line(line_text):
    lower = line_text.lower()
    return "coverage" in lower and "loan" in lower


def is_npl_exclusion_line(line_text):
    lower = line_text.lower()
    if "capital ratio" in lower or "capital adequacy" in lower or "crar" in lower:
        return True
    if ("unclassified" in lower or "sma" in lower) and "non performing" not in lower and "npl" not in lower:
        return True
    if "net" in lower and ("npl" in lower or "non performing loan" in lower) and "gross" not in lower:
        return True
    if "coverage" in lower and ("npl" in lower or "non performing" in lower or "loan" in lower):
        return True
    if "provision" in lower and "coverage" in lower:
        return True
    if "loss" in lower and ("npl" in lower or "non performing" in lower):
        return True
    return False


def is_npl_industry_only_line(line_text):
    if not line_text:
        return False
    if NPL_INDUSTRY_RE.search(line_text):
        return not bool(bank_mention_positions(line_text))
    return False


def is_portfolio_npl_line(line_text):
    if not line_text:
        return False
    lower = line_text.lower()
    if "citygem" in lower:
        return True
    if "portfolio" not in lower:
        return False
    if any(
        token in lower
        for token in (
            "card",
            "credit card",
            "retail",
            "consumer",
            "sme",
            "cmsme",
            "agri",
            "agriculture",
            "micro",
        )
    ):
        return True
    if not any(
        token in lower
        for token in ("bank", "overall", "total", "gross", "group", "consolidated")
    ):
        return True
    return False


def is_roaa_line(line_text):
    if not line_text:
        return False
    return bool(re.search(r"\broaa\b", line_text, flags=re.IGNORECASE))


def is_lcr_sector_line(line_text):
    if not line_text:
        return False
    lower = line_text.lower()
    return bool(
        re.search(
            r"banking\s+sector|banking\s+industry|banking\s+system|industry\s+average|sector\s+average",
            lower,
        )
    )


def is_lcr_nsfr_overlap_line(line_text):
    if not line_text:
        return False
    lower = line_text.lower()
    if "net stable funding" in lower or "nsfr" in lower:
        return "liquidity coverage" not in lower
    return False


def contains_rating_agency(line_text):
    lower = line_text.lower()
    return (
        "crab" in lower
        or "credit rating agency of bangladesh" in lower
        or "crisl" in lower
        or "s&p" in lower
        or "s&p global" in lower
        or "ecpl" in lower
        or "ecrl" in lower
        or "emerging credit rating" in lower
        or "moody" in lower
    )


def credit_rating_term(line_text, context_text=None):
    combined = f"{line_text or ''} {context_text or ''}".lower()
    has_long = bool(LONG_TERM_RATING_RE.search(combined))
    has_short = bool(SHORT_TERM_RATING_RE.search(combined))
    if has_long and not has_short:
        return "long_term"
    if has_short and not has_long:
        return "short_term"
    if has_long and has_short:
        return "mixed"
    return None


def is_credit_rating_context(line_text, context_text=None):
    line_lower = (line_text or "").lower()
    context_lower = (context_text or "").lower()
    if "credit rating" in line_lower:
        return True
    if contains_rating_agency(line_text):
        return True
    if BASIC_RATING_CONTEXT_RE.search(line_text or ""):
        if "outlook" in line_lower and "rating" not in line_lower and not contains_rating_agency(line_text):
            pass
        else:
            return True
    if EXPLICIT_RATING_TERM_RE.search(line_text or ""):
        return True
    if (
        "credit rating" in context_lower
        or contains_rating_agency(context_text or "")
        or BASIC_RATING_CONTEXT_RE.search(context_text or "")
    ):
        if "rating" in line_lower or EXPLICIT_RATING_TERM_RE.search(line_text or ""):
            return True
        if RATING_TOKEN_RE.search((line_text or "").upper()):
            return True
        if spelled_out_rating_matches(line_text):
            return True
    return False


def is_credit_rating_strict_context(line_text, context_text=None):
    combined = f"{line_text or ''} {context_text or ''}"
    combined_lower = combined.lower()
    if "credit rating" in combined_lower:
        return True
    if CREDIT_RATING_SECTION_RE.search(combined):
        return True
    if contains_rating_agency(combined):
        return True
    if EXPLICIT_RATING_TERM_RE.search(combined):
        return True
    if BASIC_RATING_LINE_RE.search(combined) and (
        LONG_TERM_RATING_RE.search(combined) or SHORT_TERM_RATING_RE.search(combined)
    ):
        return True
    return False


def is_strong_credit_rating_context(line_text, context_text=None):
    combined = f"{line_text or ''} {context_text or ''}"
    combined_lower = combined.lower()
    if contains_rating_agency(line_text) or (
        context_text and contains_rating_agency(context_text)
    ):
        return True
    if EXPLICIT_RATING_TERM_RE.search(combined):
        return True
    if (
        (LONG_TERM_RATING_RE.search(combined) or SHORT_TERM_RATING_RE.search(combined))
        and "rating" in combined_lower
    ):
        return True
    if SURVEILLANCE_RATING_RE.search(combined):
        return True
    if BASIC_RATING_CONTEXT_RE.search(combined):
        if "outlook" in combined_lower and "rating" not in combined_lower and not contains_rating_agency(combined):
            return False
        return True
    return False


def is_credit_rating_exclusion(line_text, context_text=None):
    combined = f"{line_text or ''} {context_text or ''}"
    combined_lower = combined.lower()
    if BOND_RATING_CONTEXT_RE.search(combined):
        return True
    if contains_rating_agency(combined):
        has_grade_token = bool(re.search(r"\b(?:AAA|AA|BBB|BB|CCC|CC|DD?|D)\b", combined, re.I))
        has_value_context = (
            CREDIT_RATING_VALUE_CONTEXT_RE.search(combined)
            or EXPLICIT_RATING_TERM_RE.search(combined)
            or LONG_TERM_RATING_RE.search(combined)
            or SHORT_TERM_RATING_RE.search(combined)
        )
        if RATING_ADDRESS_CONTEXT_RE.search(combined_lower) and not has_value_context and not has_grade_token:
            return True
    if re.search(r"\bcredit\s+risk\b", combined_lower):
        if not (
            contains_rating_agency(combined)
            or BASIC_RATING_CONTEXT_RE.search(combined)
            or EXPLICIT_RATING_TERM_RE.search(combined)
            or CREDIT_RATING_SECTION_RE.search(combined)
        ):
            return True
    if re.search(r"\bcredit\s+rating\b", combined_lower):
        if not is_strong_credit_rating_context(line_text, context_text):
            return True
    return False


def rating_term_for_span(line_text, value_span):
    if not line_text or not value_span:
        return None
    positions = []
    for match in LONG_TERM_RATING_RE.finditer(line_text):
        positions.append((match.start(), "long_term"))
    for match in SHORT_TERM_RATING_RE.finditer(line_text):
        positions.append((match.start(), "short_term"))
    if not positions:
        return None
    value_pos = value_span[0]
    best = None
    best_dist = None
    for pos, label in positions:
        dist = abs(value_pos - pos)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best = label
    return best


def contains_preferred_rating_agency(line_text):
    lower = line_text.lower()
    return (
        "crab" in lower
        or "credit rating agency of bangladesh" in lower
        or "s&p" in lower
        or "s&p global" in lower
        or "ecpl" in lower
        or "ecrl" in lower
        or "emerging credit rating" in lower
    )


def contains_crab_agency(line_text):
    lower = line_text.lower()
    return "crab" in lower or "credit rating agency of bangladesh" in lower


def has_rating_context_near(text, span, window=40):
    if not text or not span:
        return False
    start = max(0, span[0] - window)
    end = min(len(text), span[1] + window)
    snippet = text[start:end]
    snippet_lower = snippet.lower()
    if "rating" in snippet_lower:
        return True
    if contains_rating_agency(snippet):
        return True
    if EXPLICIT_RATING_TERM_RE.search(snippet):
        return True
    return False


def spelled_out_rating_matches(text):
    if not text:
        return []
    matches = []
    for pattern, token in (
        (r"\btriple\s*[-–]?\s*a\b", "AAA"),
        (r"\bdouble\s*[-–]?\s*a\b", "AA"),
    ):
        for match in re.finditer(pattern, text, flags=re.I):
            matches.append((token, match.span()))
    return matches


def rating_dates_with_positions(text):
    if not text:
        return []
    dates = []
    for match in DATE_RATING_RE_1.finditer(text):
        month = month_number(match.group(1))
        day = int(match.group(2))
        year = parse_year_token(match.group(3))
        if month and year:
            dates.append(((year, month, day), match.start()))
    for match in DATE_RATING_RE_2.finditer(text):
        day = int(match.group(1))
        month = month_number(match.group(2))
        year = parse_year_token(match.group(3))
        if month and year:
            dates.append(((year, month, day), match.start()))
    for match in DATE_RATING_RE_3.finditer(text):
        day = int(match.group(1))
        month = month_number(match.group(2))
        year = parse_year_token(match.group(3))
        if month and year:
            dates.append(((year, month, day), match.start()))
    return dates


def nearest_rating_date(text, value_span=None):
    dates = rating_dates_with_positions(text)
    if not dates:
        return None
    if not value_span:
        return max(date for date, _ in dates)
    value_pos = value_span[0]
    best_date = None
    best_dist = None
    for date_token, pos in dates:
        dist = abs(value_pos - pos)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_date = date_token
    return best_date


def count_rating_agencies(text):
    if not text:
        return 0
    lower = text.lower()
    agencies = {
        "crab": ["crab", "credit rating agency of bangladesh"],
        "crisl": ["crisl", "credit rating information and services"],
        "ecrl": ["ecrl", "emerging credit rating"],
        "ecpl": ["ecpl"],
        "moody": ["moody"],
        "s&p": ["s&p", "s&p global", "standard & poor", "standard and poor"],
    }
    found = set()
    for key, tokens in agencies.items():
        if any(token in lower for token in tokens):
            found.add(key)
    return len(found)


def credit_rating_rank(value):
    if not value:
        return None
    normalized = normalize_credit_rating(value)
    if not normalized:
        return None
    if normalized in ("AAA", "AA"):
        return 10
    return 0


def credit_rating_choice_rank(value):
    normalized = normalize_credit_rating(value)
    if not normalized:
        return -1
    order = {
        "AAA": 9,
        "AA": 8,
        "A": 7,
        "BBB": 6,
        "BB": 5,
        "B": 4,
        "CCC": 3,
        "CC": 2,
        "C": 1,
        "D": 0,
    }
    return order.get(normalized, -1)


def fallback_credit_rating_from_pdf(pdf_path, max_pages=None, year=None, page_text_cache=None):
    year_token = str(year) if year else None
    if isinstance(page_text_cache, dict) and page_text_cache:
        pages = sorted(page_text_cache.items(), key=lambda item: item[0])
    else:
        try:
            pages = iter_pdf_pages(pdf_path, max_pages)
        except Exception:
            return None
    candidates = []
    for page_num, text in pages:
        if not text:
            continue
        page_text = str(text)
        page_upper = page_text.upper()
        page_lower = page_text.lower()
        has_section = "credit rating of the bank" in page_lower
        has_rating_table = (
            "surveillance rating" in page_lower
            or "long term" in page_lower
            or "short term" in page_lower
            or "ratings have been awarded" in page_lower
        )
        if not (has_section or has_rating_table):
            continue
        if contains_rating_agency(page_text) and not has_rating_table:
            continue
        date_matches = []
        for m in DATE_RATING_RE_1.finditer(page_text):
            parsed_year = parse_year_token(m.group(3))
            if parsed_year:
                date_matches.append(str(parsed_year))
        for m in DATE_RATING_RE_2.finditer(page_text):
            parsed_year = parse_year_token(m.group(3))
            if parsed_year:
                date_matches.append(str(parsed_year))
        for m in DATE_RATING_RE_3.finditer(page_text):
            parsed_year = parse_year_token(m.group(3))
            if parsed_year:
                date_matches.append(str(parsed_year))
        year_bonus = 0
        if year_token and year_token in date_matches:
            year_bonus = 4
        elif year_token and date_matches:
            year_bonus = -2
        for m in RATING_TOKEN_RE.finditer(page_upper):
            raw = m.group(0)
            value = normalize_credit_rating(raw)
            if value not in ("AAA", "AA"):
                continue
            left = max(0, m.start() - 80)
            right = min(len(page_text), m.end() + 120)
            snippet = page_text[left:right]
            snippet_lower = snippet.lower()
            snippet_bonus = 0
            if re.search(r"\bst-?\s*[123]\b", snippet, re.I):
                snippet_bonus += 3
            if "long term" in snippet_lower or "surveillance rating" in snippet_lower:
                snippet_bonus += 3
            if "outlook" in snippet_lower or "stable" in snippet_lower:
                snippet_bonus += 1
            score = (credit_rating_choice_rank(value) * 100) + snippet_bonus + year_bonus
            if has_section:
                score += 3
            if has_rating_table:
                score += 2
            candidates.append((score, value, page_num))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[2]), reverse=True)
    _, value, page_num = candidates[0]
    return {"value": value, "page": page_num}


def is_comma_number(text, span):
    if not span:
        return False
    start, end = span
    if start > 0 and text[start - 1] == ",":
        return True
    if end < len(text) and text[end] == ",":
        return True
    return False


def has_trailing_words_after_numbers(line_text):
    matches = list(NUMERIC_RE.finditer(line_text))
    if not matches:
        return False
    tail = line_text[matches[-1].end() :].strip()
    if not tail:
        return False
    return bool(re.search(r"[A-Za-z]", tail))


def classify_regulatory_compliance(text):
    lower = text.lower()
    if not PENALTY_TOKEN_RE.search(lower):
        return None
    negation = re.search(
        r"\b(no|nil|none|without|zero)\b(?:\W+\w+){0,3}\W+\b(penalt(?:y|ies)?|fine(?:s)?|non[- ]?compliance|violation|breach)\b",
        lower,
    )
    negation = negation or re.search(
        r"\b(penalt(?:y|ies)?|fine(?:s)?|non[- ]?compliance|violation|breach)\b(?:\W+\w+){0,3}\W+\b(no|nil|none|without|zero)\b",
        lower,
    )
    if negation:
        return "No Penalty"
    risk_context = re.search(r"\b(risk|potential|could|may|might|expose|possible|likely|would)\b", lower)
    if risk_context:
        return None
    regulator_context = re.search(
        r"\b(regulator|regulators|bangladesh bank|bsec|central bank|bb)\b",
        lower,
    )
    action_context = re.search(
        r"\b(imposed|levied|fined|penalized|sanctioned|charged|paid|settlement|settled|appeal)\b",
        lower,
    )
    if regulator_context or action_context:
        return "Penalty"
    return None


def is_strong_penalty_context(text):
    lower = text.lower()
    if re.search(r"\b(no|nil|none|without|zero)\b(?:\W+\w+){0,3}\W+\b(penalt|fine)\b", lower):
        return False
    if re.search(r"\bno\b(?:\W+\w+){0,4}\W+\b(appeals?|actions?)\b", lower):
        return False
    if not PENALTY_TOKEN_RE.search(lower):
        return False
    if re.search(r"\b(imposed|levied|fined|penalized|sanctioned|charged|paid|settlement|settled)\b", lower):
        return True
    if re.search(r"\b(bangladesh bank|bsec|central bank|regulator|regulators|bb)\b", lower) and re.search(
        r"\b(penalt|fine|violation|breach|non[- ]?compliance)\b", lower
    ):
        return True
    return False


# --- PDF discovery and download ---
def score_pdf(url, anchor_text, keywords, year):
    score = 0
    hay = (url + " " + (anchor_text or "")).lower()
    for kw in keywords or []:
        if kw.lower() in hay:
            score += 2
    if year and str(year) in hay:
        score += 4
    if "annual" in hay:
        score += 2
    if "report" in hay:
        score += 1
    if "financial" in hay:
        score += 1
    return score


def is_pdf_url(url):
    return url.lower().split("?")[0].endswith(".pdf")


def same_domain(url, allowed_netlocs):
    if not allowed_netlocs:
        return True
    return urlparse(url).netloc in allowed_netlocs


def build_referer(url):
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/"


def base_headers():
    return {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "close",
    }


def html_headers():
    headers = base_headers()
    headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    return headers


def pdf_headers(url=None):
    headers = base_headers()
    headers["Accept"] = "application/pdf,application/octet-stream,*/*;q=0.8"
    referer = build_referer(url) if url else None
    if referer:
        headers["Referer"] = referer
        headers["Origin"] = referer.rstrip("/")
    return headers


def fetch_url(url, timeout):
    return requests.get(url, headers=html_headers(), timeout=timeout)


def crawl_for_pdf(start_urls, keywords=None, year=None, max_pages=200, timeout=15):
    queue = list(start_urls)
    visited = set()
    allowed_netlocs = {urlparse(u).netloc for u in start_urls if urlparse(u).netloc}
    candidates = []

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            resp = fetch_url(url, timeout)
        except Exception:
            continue

        content_type = resp.headers.get("content-type", "").lower()

        if "application/pdf" in content_type or is_pdf_url(url):
            candidates.append((score_pdf(url, "", keywords, year), url))
            continue

        if "text/html" not in content_type:
            continue

        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.select("a[href]"):
            href = a.get("href")
            if not href:
                continue
            if href.startswith("mailto:") or href.startswith("javascript:"):
                continue
            link = urljoin(url, href)
            if not same_domain(link, allowed_netlocs):
                continue
            anchor = normalize_text(a.get_text(" ", strip=True))
            if is_pdf_url(link):
                candidates.append((score_pdf(link, anchor, keywords, year), link))
            elif link not in visited:
                queue.append(link)

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def download_pdf(url, download_dir, timeout, filename=None):
    ensure_dir(download_dir)
    local_name = filename or os.path.basename(urlparse(url).path) or "annual_report.pdf"
    local_path = os.path.join(download_dir, local_name)
    headers = pdf_headers(url)
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        print(f"Downloading PDF (cached) to {local_path}")
        return local_path
    last_exc = None
    session = requests.Session()
    preflight_done = False
    for attempt in range(1, 4):
        try:
            response = session.get(url, stream=True, headers=headers, timeout=timeout)
            if response.status_code in (401, 403) and not preflight_done:
                response.close()
                referer = headers.get("Referer")
                if referer:
                    try:
                        session.get(referer, headers=html_headers(), timeout=timeout)
                    except requests.RequestException:
                        pass
                    preflight_done = True
                    response = session.get(
                        url, stream=True, headers=headers, timeout=timeout
                    )
            with response as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", "0")) or None
                print(f"Downloading PDF to {local_path}")
                with open(local_path, "wb") as f:
                    progress = tqdm(
                        total=total,
                        unit="B",
                        unit_scale=True,
                        desc="Download",
                        disable=not sys.stdout.isatty(),
                    )
                    try:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
                                progress.update(len(chunk))
                    finally:
                        progress.close()
            return local_path
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < 3:
                wait = min(2 ** attempt, 6)
                print(f"Download failed (attempt {attempt}): {exc}. Retrying in {wait}s.")
                time.sleep(wait)
            else:
                break

    if last_exc:
        raise last_exc
    raise RuntimeError("Download failed")


def normalize_name_hint(value):
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def find_cached_pdf(download_dir, bank_name=None, year=None, url=None):
    if not download_dir or not os.path.isdir(download_dir):
        return None
    if url:
        base = os.path.basename(urlparse(url).path)
        for candidate_name in filter(None, [base, unquote(base) if base else None]):
            candidate = os.path.join(download_dir, candidate_name)
            if os.path.exists(candidate):
                return candidate
    bank_hint = normalize_name_hint(bank_name)
    year_hint = str(year or "")
    for filename in os.listdir(download_dir):
        if not filename.lower().endswith(".pdf"):
            continue
        stem = os.path.splitext(filename)[0]
        stem_hint = normalize_name_hint(stem)
        if bank_hint and bank_hint in stem_hint:
            if not year_hint or year_hint in stem:
                return os.path.join(download_dir, filename)
        if year_hint and year_hint in stem and not bank_hint:
            return os.path.join(download_dir, filename)
    return None


# --- PDF page iterators and OCR helpers ---
def iter_pages_pdfplumber(pdf_path, max_pages):
    if not pdfplumber:
        raise RuntimeError("pdfplumber is not available")
    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            if max_pages and idx > max_pages:
                break
            text = page.extract_text() or ""
            yield idx, text


def iter_pages_pymupdf(pdf_path, max_pages):
    if not fitz:
        raise RuntimeError("PyMuPDF is not available")
    doc = fitz.open(pdf_path)
    try:
        for idx in range(len(doc)):
            page_num = idx + 1
            if max_pages and page_num > max_pages:
                break
            text = doc.load_page(idx).get_text("text") or ""
            yield page_num, text
    finally:
        doc.close()


def load_ocr_modules():
    global _OCR_MODULES
    if _OCR_MODULES is not None:
        return _OCR_MODULES
    try:
        import importlib

        pytesseract = importlib.import_module("pytesseract")
        image_module = importlib.import_module("PIL.Image")
    except Exception:
        _OCR_MODULES = (None, None)
        return _OCR_MODULES
    _OCR_MODULES = (pytesseract, image_module)
    return _OCR_MODULES


def ocr_available():
    pytesseract, _ = load_ocr_modules()
    if not pytesseract:
        return False
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        return False
    return True


def iter_pages_ocr(pdf_path, max_pages, zoom=OCR_ZOOM):
    pytesseract, image_module = load_ocr_modules()
    if not fitz or not pytesseract or image_module is None:
        raise RuntimeError("OCR dependencies are not available")
    doc = fitz.open(pdf_path)
    try:
        for idx in range(len(doc)):
            page_num = idx + 1
            if max_pages and page_num > max_pages:
                break
            page = doc.load_page(idx)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            mode = "RGBA" if pix.alpha else "RGB"
            image = image_module.frombytes(mode, [pix.width, pix.height], pix.samples)
            try:
                text = pytesseract.image_to_string(image, config=OCR_CONFIG) or ""
            except Exception as exc:
                raise RuntimeError(f"OCR failed: {exc}") from exc
            yield page_num, text
    finally:
        doc.close()


def iter_pages_ocr_selected(pdf_path, page_numbers, zoom=OCR_ZOOM, cache=None, max_pages=None):
    pytesseract, image_module = load_ocr_modules()
    if not fitz or not pytesseract or image_module is None:
        raise RuntimeError("OCR dependencies are not available")
    if not page_numbers:
        return
    doc = fitz.open(pdf_path)
    try:
        total_pages = len(doc)
        for page_num in page_numbers:
            if max_pages and page_num > max_pages:
                continue
            if page_num < 1 or page_num > total_pages:
                continue
            if cache is not None and page_num in cache:
                yield page_num, cache[page_num]
                continue
            page = doc.load_page(page_num - 1)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            mode = "RGBA" if pix.alpha else "RGB"
            image = image_module.frombytes(mode, [pix.width, pix.height], pix.samples)
            try:
                text = pytesseract.image_to_string(image, config=OCR_CONFIG) or ""
            except Exception as exc:
                raise RuntimeError(f"OCR failed: {exc}") from exc
            if cache is not None:
                cache[page_num] = text
            yield page_num, text
    finally:
        doc.close()


def iter_pdf_pages(pdf_path, max_pages):
    if pdfplumber is not None:
        return iter_pages_pdfplumber(pdf_path, max_pages)
    if fitz is not None:
        return iter_pages_pymupdf(pdf_path, max_pages)
    raise RuntimeError("No PDF parser available. Install pdfplumber or PyMuPDF.")


def nearest_year_for_value(line_text, value_pos):
    if value_pos is None:
        return None
    years = extract_year_tokens(line_text)
    if not years:
        return None
    best_year = None
    best_dist = None
    for year in years:
        positions = keyword_positions(line_text, [year])
        for pos in positions:
            dist = abs(value_pos - pos)
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_year = year
    return best_year


# --- Core field extraction pipeline ---
def iter_with_progress(pages, desc="Scanning pages", log_every=25):
    if sys.stdout.isatty():
        for page_num, text in tqdm(pages, desc=desc, unit="page"):
            yield page_num, text
        return
    start = time.time()
    count = 0
    for page_num, text in pages:
        count += 1
        if log_every and count % log_every == 0:
            elapsed = int(time.time() - start)
            print(f"{desc}: {count} pages scanned ({elapsed}s)")
        yield page_num, text


def extract_fields(
    pages,
    fields,
    scan_keywords=None,
    source="text",
    keyword_hits=None,
    page_text_cache=None,
):
    results = []
    keyword_set = [k.lower() for k in scan_keywords] if scan_keywords else None
    standalone_only = {
        "Capital Adequacy Ratio (CRAR)",
        "Leverage Ratio (LR)",
        "Return on Assets (ROA)",
        "Return on Equity (ROE)",
        "Liquidity Coverage Ratio (LCR)",
        "Net Stable Funding Ratio (NSFR)",
    }
    for page_num, text in iter_with_progress(pages, desc="Scanning pages"):
        if page_text_cache is not None:
            page_text_cache[page_num] = text or ""
        if not text:
            continue
        page_text = normalize_text(text)
        lower = page_text.lower()
        if keyword_hits is not None:
            for field in fields:
                name = field.get("name")
                if not name:
                    continue
                if field_keyword_match(name, field.get("patterns"), page_text):
                    keyword_hits.setdefault(name, set()).add(page_num)
        if keyword_set and not any(k in lower for k in keyword_set):
            continue
        lines = text.splitlines()
        current_years = None
        current_columns = None
        current_group_bank = None
        for line_idx, line in enumerate(lines):
            line_norm = normalize_text(line)
            if not line_norm:
                continue
            header_years = extract_year_header(line_norm)
            if header_years:
                current_years = header_years
            header_columns = extract_column_labels(line_norm)
            if header_columns:
                current_columns = header_columns
            header_group_bank = extract_group_bank_header(line_norm)
            if header_group_bank:
                current_group_bank = header_group_bank
            candidate_lines = []
            candidate_lines.append(line_norm)
            if line_idx + 1 < len(lines):
                combined_next = normalize_text(
                    f"{line_norm} {lines[line_idx + 1]}"
                )
                if combined_next and combined_next not in candidate_lines:
                    candidate_lines.append(combined_next)
            if line_idx + 2 < len(lines):
                combined_next_two = normalize_text(
                    f"{line_norm} {lines[line_idx + 1]} {lines[line_idx + 2]}"
                )
                if combined_next_two and combined_next_two not in candidate_lines:
                    candidate_lines.append(combined_next_two)
            if line_idx - 1 >= 0:
                combined_prev = normalize_text(
                    f"{lines[line_idx - 1]} {line_norm}"
                )
                if combined_prev and combined_prev not in candidate_lines:
                    candidate_lines.append(combined_prev)
            if line_idx - 2 >= 0:
                combined_prev_two = normalize_text(
                    f"{lines[line_idx - 2]} {lines[line_idx - 1]} {line_norm}"
                )
                if combined_prev_two and combined_prev_two not in candidate_lines:
                    candidate_lines.append(combined_prev_two)
            context_start = max(0, line_idx - 2)
            context_end = min(len(lines), line_idx + 3)
            context_text = normalize_text(" ".join(lines[context_start:context_end]))
            for field in fields:
                name = field.get("name")
                for candidate_text in candidate_lines:
                    if FIELD_TYPES.get(name) == "numeric":
                        label_priority = None
                        target_labels = target_label_regexes(name)
                        if name == "Capital Adequacy Ratio (CRAR)":
                            numeric_values, used_context = extract_numeric_values_after_label(
                                candidate_text,
                                CRAR_PRIMARY_LABEL_RE,
                                context_text,
                                exclude_labels=target_labels,
                            )
                            if numeric_values:
                                label_priority = 1
                            else:
                                numeric_values, used_context = extract_numeric_values_after_label(
                                    candidate_text,
                                    CRAR_SECONDARY_LABEL_RE,
                                    context_text,
                                    exclude_labels=target_labels,
                                )
                                if numeric_values:
                                    label_priority = 2
                        elif name == "Non-Performing Loan Ratio (NPL)":
                            numeric_values, used_context = extract_numeric_values_after_label(
                                candidate_text,
                                NPL_PRIMARY_LABEL_RE,
                                context_text,
                                exclude_labels=target_labels,
                                max_distance=50,
                            )
                            if numeric_values:
                                label_priority = 1
                            else:
                                numeric_values, used_context = extract_numeric_values_after_label(
                                    candidate_text,
                                    NPL_SECONDARY_LABEL_RE,
                                    context_text,
                                    exclude_labels=target_labels,
                                    max_distance=50,
                                )
                                if numeric_values:
                                    label_priority = 2
                            if numeric_values:
                                whereas_match = WHEREAS_RE.search(candidate_text)
                                if whereas_match and len(numeric_values) > 1:
                                    pivot = whereas_match.start()
                                    filtered = [
                                        item
                                        for item in numeric_values
                                        if item[1][0] >= pivot
                                    ]
                                    if filtered:
                                        numeric_values = filtered
                                    else:
                                        numeric_values = []
                                if NPL_INDUSTRY_RE.search(candidate_text):
                                    if not whereas_match and len(numeric_values) == 1:
                                        numeric_values = []
                        else:
                            label_re = FIELD_LABELS.get(name)
                            if not label_re:
                                continue
                            numeric_values, used_context = extract_numeric_values_after_label(
                                candidate_text,
                                label_re,
                                context_text,
                                exclude_labels=target_labels,
                            )
                        ordered_value = extract_label_order_value(candidate_text, name)
                        if (
                            ordered_value
                            and name == "Capital Adequacy Ratio (CRAR)"
                            and len(numeric_values) > 1
                            and (
                                is_standalone_line(candidate_text)
                                or is_consolidated_line(candidate_text)
                                or is_standalone_line(context_text)
                                or is_consolidated_line(context_text)
                            )
                        ):
                            ordered_value = None
                        ordered_span = ordered_value[1] if ordered_value else None
                        if ordered_value:
                            numeric_values = [ordered_value]
                        if used_context:
                            candidate_text = context_text
                        has_other_labels = has_other_ratio_label(candidate_text, target_labels)
                        has_other_labels_context = has_other_ratio_label(context_text, target_labels)
                        candidate_years = current_years or extract_years_in_order(
                            candidate_text
                        )
                        if not candidate_years:
                            candidate_years = extract_years_in_order(context_text)
                        if (
                            name == "Provision Coverage Ratio (PCR)"
                            and candidate_years
                            and len(numeric_values) >= len(candidate_years)
                        ):
                            numeric_values = numeric_values[: len(candidate_years)]
                        if not numeric_values:
                            continue
                        if name in ("Liquidity Coverage Ratio (LCR)", "Net Stable Funding Ratio (NSFR)"):
                            if re.search(r"regulatory|limit|minimum|plus", candidate_text, flags=re.IGNORECASE):
                                if len(numeric_values) > 1:
                                    first_value = numeric_values[0][0]
                                    if "%" in first_value:
                                        numeric_values = numeric_values[1:]
                        if (
                            name == "Return on Assets (ROA)"
                            and len(numeric_values) > 1
                            and re.search(r"\bfrom\b", candidate_text, flags=re.IGNORECASE)
                            and re.search(r"\bto\b", candidate_text, flags=re.IGNORECASE)
                        ):
                            numeric_values = [numeric_values[-1]]
                        if (
                            name == "Return on Equity (ROE)"
                            and len(numeric_values) > 1
                            and re.search(r"\bfrom\b", candidate_text, flags=re.IGNORECASE)
                            and re.search(r"\bto\b", candidate_text, flags=re.IGNORECASE)
                        ):
                            numeric_values = [numeric_values[-1]]
                        if (
                            name == "Net Stable Funding Ratio (NSFR)"
                            and len(numeric_values) > 1
                        ):
                            label_re = FIELD_LABELS.get(name)
                            label_match = label_re.search(candidate_text) if label_re else None
                            if label_match and label_match.start() > numeric_values[-1][1][1]:
                                closest_idx = min(
                                    range(len(numeric_values)),
                                    key=lambda idx: abs(
                                        label_match.start() - numeric_values[idx][1][0]
                                    ),
                                )
                                numeric_values = [numeric_values[closest_idx]]
                        numeric_values = [
                            item
                            for item in numeric_values
                            if not is_formula_multiplier(candidate_text, item[1])
                        ]
                        if not numeric_values:
                            continue
                        context_years = extract_year_tokens(context_text)
                        if not (current_years or current_columns or context_years):
                            if not extract_year_tokens(candidate_text):
                                numeric_values = numeric_values[:1]
                        if (
                            name in standalone_only
                            and is_consolidated_line(candidate_text)
                            and not is_standalone_line(candidate_text)
                        ):
                            continue
                        if name == "Non-Performing Loan Ratio (NPL)":
                            if is_npl_coverage_line(candidate_text) or is_npl_exclusion_line(
                                candidate_text
                            ):
                                continue
                            if is_portfolio_npl_line(candidate_text):
                                continue
                            if (
                                "ratio" not in candidate_text.lower()
                                and not is_table_context(
                                    candidate_text, context_text, current_years, current_columns
                                )
                                and len(numeric_values) <= 1
                            ):
                                continue
                        if name == "Return on Assets (ROA)" and is_roaa_line(candidate_text):
                            continue
                        if name in ("Liquidity Coverage Ratio (LCR)", "Net Stable Funding Ratio (NSFR)"):
                            if name == "Liquidity Coverage Ratio (LCR)":
                                if is_lcr_sector_line(candidate_text) or is_lcr_sector_line(
                                    context_text
                                ):
                                    continue
                                if is_lcr_nsfr_overlap_line(candidate_text):
                                    continue
                            if MONTH_TOKEN_RE.search(candidate_text) and not is_table_context(
                                candidate_text, context_text, current_years, current_columns
                            ):
                                continue
                            if is_axis_tick_line(candidate_text) and not is_table_context(
                                candidate_text, context_text, current_years, current_columns
                            ):
                                continue
                        if name == "Capital Adequacy Ratio (CRAR)" and (
                            is_crar_exclusion_line(candidate_text)
                            or is_crar_exclusion_line(context_text)
                        ):
                            continue
                        if FIELD_TYPES.get(name) == "numeric" and is_comparison_line(
                            candidate_text
                        ):
                            if name in (
                                "Liquidity Coverage Ratio (LCR)",
                                "Net Stable Funding Ratio (NSFR)",
                            ):
                                if has_higher_percent_in_line(candidate_text, 100):
                                    pass
                                elif re.search(
                                    r"regulatory|limit|minimum|requirement|bb limit|more than|less than|or more",
                                    candidate_text,
                                    flags=re.IGNORECASE,
                                ):
                                    if not (
                                        extract_year_tokens(candidate_text)
                                        or extract_year_tokens(context_text)
                                    ):
                                        continue
                                else:
                                    continue
                            else:
                                continue
                        value_column_overrides = {}
                        if (
                            name
                            in (
                                "Capital Adequacy Ratio (CRAR)",
                                "Leverage Ratio (LR)",
                                "Return on Equity (ROE)",
                            )
                            and len(numeric_values) > 1
                        ):
                            standalone_positions = keyword_positions(
                                candidate_text, STANDALONE_TOKENS
                            )
                            consolidated_positions = keyword_positions(
                                candidate_text, CONSOLIDATED_TOKENS
                            )
                            has_year_context = bool(candidate_years or context_years)
                            if standalone_positions and consolidated_positions:
                                for idx, (_, span) in enumerate(numeric_values):
                                    dist_standalone = min_distance(
                                        span[0], standalone_positions
                                    )
                                    dist_consolidated = min_distance(
                                        span[0], consolidated_positions
                                    )
                                    if dist_standalone is None and dist_consolidated is None:
                                        continue
                                    if dist_consolidated is None or (
                                        dist_standalone is not None
                                        and dist_standalone <= dist_consolidated
                                    ):
                                        value_column_overrides[idx] = "standalone"
                                    else:
                                        value_column_overrides[idx] = "consolidated"
                            elif standalone_positions and not consolidated_positions:
                                closest_idx = None
                                closest_dist = None
                                for idx, (_, span) in enumerate(numeric_values):
                                    dist = min_distance(span[0], standalone_positions)
                                    if dist is None:
                                        continue
                                    if closest_dist is None or dist < closest_dist:
                                        closest_dist = dist
                                        closest_idx = idx
                                if closest_idx is not None:
                                    value_column_overrides[closest_idx] = "standalone"
                                    if len(numeric_values) == 2 and not has_year_context:
                                        other_idx = 1 - closest_idx
                                        value_column_overrides[other_idx] = "consolidated"
                            elif consolidated_positions and not standalone_positions:
                                closest_idx = None
                                closest_dist = None
                                for idx, (_, span) in enumerate(numeric_values):
                                    dist = min_distance(span[0], consolidated_positions)
                                    if dist is None:
                                        continue
                                    if closest_dist is None or dist < closest_dist:
                                        closest_dist = dist
                                        closest_idx = idx
                                if closest_idx is not None:
                                    value_column_overrides[closest_idx] = "consolidated"
                                    if len(numeric_values) == 2 and not has_year_context:
                                        other_idx = 1 - closest_idx
                                        value_column_overrides[other_idx] = "standalone"
                        value_count = len(numeric_values)
                        lr_required_group = None
                        year_candidates = current_years or candidate_years
                        if (
                            name == "Leverage Ratio (LR)"
                            and year_candidates
                            and value_count > len(year_candidates)
                            and value_count % len(year_candidates) == 0
                            and (
                                has_subcolumn_tokens(candidate_text)
                                or has_subcolumn_tokens(context_text)
                            )
                        ):
                            lr_required_group = value_count // len(year_candidates)
                        for value_index, (raw_value, value_span) in enumerate(
                            numeric_values
                        ):
                            if is_formula_multiplier(candidate_text, value_span):
                                continue
                            if is_comma_number(candidate_text, value_span):
                                continue
                            raw_value = apply_negative_context(
                                raw_value, candidate_text, value_span
                            )
                            if (
                                name == "Leverage Ratio (LR)"
                                and lr_required_group
                                and re.search(
                                    r"\brequired\b", f"{candidate_text} {context_text}", re.IGNORECASE
                                )
                                and value_index % lr_required_group == 0
                            ):
                                continue
                            if name == "Leverage Ratio (LR)" and value_span:
                                day_value = parse_numeric(raw_value)
                                if (
                                    day_value is not None
                                    and day_value <= 31
                                    and "%" not in str(raw_value)
                                    and is_day_in_date_context(candidate_text, value_span)
                                ):
                                    continue
                            if (
                                name == "Capital Adequacy Ratio (CRAR)"
                                and is_tier_ratio_value(candidate_text, value_span)
                            ):
                                continue
                            if (
                                name == "Capital Adequacy Ratio (CRAR)"
                                and is_pre_total_capital_value(candidate_text, value_span)
                            ):
                                continue
                            if (
                                name == "Capital Adequacy Ratio (CRAR)"
                                and is_requirement_value(candidate_text, value_span)
                            ):
                                continue
                            if (
                                name == "Non-Performing Loan Ratio (NPL)"
                                and (
                                    is_requirement_value(candidate_text, value_span)
                                    or is_minimum_ratio_value(candidate_text, value_span)
                                )
                            ):
                                continue
                            if (
                                name == "Leverage Ratio (LR)"
                                and (
                                    is_requirement_value(candidate_text, value_span)
                                    or is_minimum_ratio_value(candidate_text, value_span)
                                )
                            ):
                                continue
                            if (
                                name in PERCENT_REQUIRED_FIELDS
                                and "%" not in str(raw_value)
                                and has_currency_marker(candidate_text, value_span)
                            ):
                                continue
                            if (
                                name == "Leverage Ratio (LR)"
                                and "%" not in str(raw_value)
                                and (
                                    "times" in candidate_text.lower()
                                    or not has_local_percent_indicator(
                                        candidate_text, context_text, value_span
                                    )
                                )
                            ):
                                continue
                            if name in PERCENT_REQUIRED_FIELDS and not has_percent_indicator(
                                raw_value, candidate_text, context_text, value_span
                            ):
                                continue
                            value = normalize_field_value(name, raw_value)
                            if value is None:
                                continue
                            if name == "Net Interest Margin (NIM)" and value > 20:
                                continue
                            if name == "Capital Adequacy Ratio (CRAR)" and value > 100:
                                continue
                            value_year = None
                            change_context = bool(
                                re.search(
                                    r"%\s*change|change over|percent change|%change",
                                    f"{candidate_text} {context_text}",
                                    flags=re.IGNORECASE,
                                )
                            )
                            table_context = is_table_context(
                                candidate_text, context_text, current_years, current_columns
                            )
                            exact_context = bool(
                                GENERIC_EXACT_VALUE_RE.search(candidate_text)
                                or GENERIC_EXACT_VALUE_RE.search(context_text)
                            )
                            if not table_context and not exact_context:
                                if is_definition_context(candidate_text, context_text):
                                    continue
                                if is_target_context(candidate_text, context_text):
                                    continue
                                if is_benchmark_context(candidate_text, context_text):
                                    continue
                            if current_years and not has_trailing_words_after_numbers(
                                candidate_text
                            ):
                                if value_count == len(current_years) and value_index < len(
                                    current_years
                                ):
                                    value_year = current_years[value_index]
                                elif (
                                    value_count > len(current_years)
                                    and value_count % len(current_years) == 0
                                    and (
                                        table_context
                                        or current_columns
                                        or current_group_bank
                                        or has_subcolumn_tokens(candidate_text)
                                        or has_subcolumn_tokens(context_text)
                                    )
                                ):
                                    group_size = value_count // len(current_years)
                                    if current_columns or current_group_bank:
                                        value_year = current_years[
                                            value_index % len(current_years)
                                        ]
                                    else:
                                        value_year = current_years[
                                            value_index // group_size
                                        ]
                                elif (
                                    value_index < len(current_years)
                                    and (change_context or table_context)
                                    and value_count >= len(current_years)
                                ):
                                    value_year = current_years[value_index]
                            elif candidate_years and not has_trailing_words_after_numbers(
                                candidate_text
                            ):
                                if value_count == len(candidate_years) and value_index < len(
                                    candidate_years
                                ):
                                    value_year = candidate_years[value_index]
                                elif (
                                    value_count > len(candidate_years)
                                    and value_count % len(candidate_years) == 0
                                    and (
                                        table_context
                                        or current_columns
                                        or current_group_bank
                                        or has_subcolumn_tokens(candidate_text)
                                        or has_subcolumn_tokens(context_text)
                                    )
                                ):
                                    group_size = value_count // len(candidate_years)
                                    if current_columns or current_group_bank:
                                        value_year = candidate_years[
                                            value_index % len(candidate_years)
                                        ]
                                    else:
                                        value_year = candidate_years[
                                            value_index // group_size
                                        ]
                                elif (
                                    value_index < len(candidate_years)
                                    and (change_context or table_context)
                                    and value_count >= len(candidate_years)
                                ):
                                    value_year = candidate_years[value_index]
                            if not value_year:
                                value_year = nearest_year_for_value(
                                    candidate_text, value_span[0]
                                )
                            if not value_year:
                                context_years = extract_year_tokens(context_text)
                                if len(context_years) == 1:
                                    value_year = next(iter(context_years))
                            value_column = None
                            if current_columns and value_count == len(current_columns):
                                if value_index < len(current_columns):
                                    value_column = current_columns[value_index]
                            elif (
                                current_columns
                                and value_count > len(current_columns)
                                and value_count % len(current_columns) == 0
                            ):
                                block_size = value_count // len(current_columns)
                                value_column = current_columns[value_index // block_size]
                            elif current_group_bank and value_count >= 2:
                                split = value_count // 2
                                first_label = (
                                    current_group_bank[0]
                                    if current_group_bank and len(current_group_bank) > 0
                                    else "group"
                                )
                                second_label = (
                                    current_group_bank[1]
                                    if current_group_bank and len(current_group_bank) > 1
                                    else "bank"
                                )
                                value_column = (
                                    first_label if value_index < split else second_label
                                )
                            if value_column_overrides and value_index in value_column_overrides:
                                value_column = value_column_overrides[value_index]
                            if name in (
                                "Capital Adequacy Ratio (CRAR)",
                                "Leverage Ratio (LR)",
                                "Return on Equity (ROE)",
                            ):
                                basis_label = basis_label_after_value(
                                    candidate_text, value_span
                                )
                                if basis_label:
                                    value_column = basis_label
                            if (
                                name
                                in (
                                    "Capital Adequacy Ratio (CRAR)",
                                    "Leverage Ratio (LR)",
                                    "Return on Equity (ROE)",
                                )
                                and not value_column
                            ):
                                if not current_columns and not current_group_bank:
                                    context_columns = extract_column_labels(context_text)
                                    if context_columns and value_count >= len(context_columns):
                                        if value_count == len(context_columns):
                                            if value_index < len(context_columns):
                                                value_column = context_columns[value_index]
                                        elif value_count % len(context_columns) == 0:
                                            block_size = value_count // len(context_columns)
                                            value_column = context_columns[
                                                value_index // block_size
                                            ]
                                    if not value_column:
                                        context_group_bank = extract_group_bank_header(
                                            context_text
                                        )
                                        if context_group_bank and value_count >= 2:
                                            split = value_count // 2
                                            first_label = (
                                                context_group_bank[0]
                                                if context_group_bank
                                                and len(context_group_bank) > 0
                                                else "group"
                                            )
                                            second_label = (
                                                context_group_bank[1]
                                                if context_group_bank
                                                and len(context_group_bank) > 1
                                                else "bank"
                                            )
                                            value_column = (
                                                first_label
                                                if value_index < split
                                                else second_label
                                            )
                                if value_column_overrides and value_index not in value_column_overrides:
                                    inferred = None
                                else:
                                    inferred = infer_value_column_from_tokens(
                                        candidate_text, value_span
                                    )
                                if inferred:
                                    value_column = inferred
                            if (
                                name == "Capital Adequacy Ratio (CRAR)"
                                and value_column == "requirement"
                            ):
                                continue
                            match_source = source
                            if source == "text" and is_table_context(
                                candidate_text, context_text, current_years, current_columns
                            ):
                                match_source = "table"
                            results.append(
                                {
                                    "field": name,
                                    "value": value,
                                    "page": page_num,
                                    "line": line_idx,
                                    "line_text": candidate_text,
                                    "context_text": context_text,
                                    "value_span": value_span,
                                    "value_index": value_index,
                                    "value_count": value_count,
                                    "value_year": value_year,
                                    "value_column": value_column,
                                    "raw_value": raw_value,
                                    "label_priority": label_priority,
                                    "source": match_source,
                                    "has_other_labels": has_other_labels,
                                    "has_other_labels_context": has_other_labels_context,
                                    "label_order_match": bool(
                                        ordered_span and value_span == ordered_span
                                    ),
                                }
                            )
                        continue
                    if name == "Regulatory Compliance (RC)":
                        compliance = classify_regulatory_compliance(candidate_text)
                        if not compliance:
                            continue
                        results.append(
                            {
                                "field": name,
                                "value": compliance,
                                "page": page_num,
                                "line": line_idx,
                                "line_text": candidate_text,
                                "context_text": context_text,
                                "value_span": None,
                                "value_index": 0,
                                "value_count": 1,
                                "value_year": None,
                                "value_column": None,
                                "raw_value": compliance,
                                "source": source,
                            }
                        )
                        continue
                    if name == "Credit Rating (CR)":
                        if not is_credit_rating_context(candidate_text, context_text):
                            continue
                        if is_credit_rating_exclusion(candidate_text, context_text):
                            continue
                        rating_term = credit_rating_term(candidate_text, context_text)
                        if rating_term == "short_term":
                            continue
                        rating_hits = []
                        source_text = candidate_text
                        context_for_match = context_text
                        rating_matches = list(RATING_TOKEN_RE.finditer(candidate_text.upper()))
                        if rating_matches:
                            rating_hits = [(m.group(0), m.span()) for m in rating_matches]
                        spelled_hits = spelled_out_rating_matches(source_text)
                        if spelled_hits:
                            rating_hits = spelled_hits
                        if not rating_hits:
                            rating_matches = list(
                                RATING_TOKEN_RE.finditer(context_text.upper())
                            )
                            if rating_matches:
                                source_text = context_text
                                context_for_match = candidate_text
                                rating_hits = [
                                    (m.group(0), m.span()) for m in rating_matches
                                ]
                            spelled_hits = spelled_out_rating_matches(source_text)
                            if spelled_hits:
                                rating_hits = spelled_hits
                        if not rating_hits:
                            rating_hits = spelled_out_rating_matches(candidate_text)
                        if not rating_hits:
                            rating_hits = spelled_out_rating_matches(context_text)
                            if rating_hits:
                                source_text = context_text
                                context_for_match = candidate_text
                        if not rating_hits:
                            continue
                        if not is_credit_rating_context(source_text, context_for_match):
                            continue
                        if not is_credit_rating_strict_context(
                            source_text, context_for_match
                        ):
                            continue
                        for idx, (token, span) in enumerate(rating_hits):
                            compact_token = re.sub(r"\s+", "", str(token).upper())
                            token_context = f"{source_text or ''} {context_for_match or ''}"
                            normalized_token = normalize_credit_rating(token)
                            if re.fullmatch(r"[ABCD]-?[123]", compact_token):
                                if RATING_ADDRESS_CONTEXT_RE.search(token_context) and not (
                                    LONG_TERM_RATING_RE.search(token_context)
                                    or SHORT_TERM_RATING_RE.search(token_context)
                                    or CREDIT_RATING_VALUE_CONTEXT_RE.search(token_context)
                                ):
                                    continue
                            if not has_rating_context_near(source_text, span):
                                table_rating_context = (
                                    bool(re.search(r"\bst-?\s*[123]\b", token_context, re.I))
                                    or "stable" in token_context.lower()
                                    or "outlook" in token_context.lower()
                                    or bool(is_table_context(source_text, context_for_match, current_years, current_columns))
                                )
                                if normalized_token in ("AAA", "AA", "A", "BBB", "BB", "B") and table_rating_context:
                                    pass
                                elif not (
                                    EXPLICIT_RATING_TERM_RE.search(context_for_match or "")
                                    or BASIC_RATING_LINE_RE.search(context_for_match or "")
                                    or contains_rating_agency(context_for_match or "")
                                ):
                                    continue
                            if len(token) == 1:
                                rating_context_text = f"{source_text} {context_for_match}"
                                if "rating" not in (source_text or "").lower():
                                    continue
                                if not (
                                    is_strong_credit_rating_context(
                                        source_text, context_for_match
                                    )
                                    and BASIC_RATING_LINE_RE.search(rating_context_text)
                                    and (
                                        LONG_TERM_RATING_RE.search(rating_context_text)
                                        or SHORT_TERM_RATING_RE.search(
                                            rating_context_text
                                        )
                                    )
                                ):
                                    continue
                            value = normalize_credit_rating(token)
                            if not value:
                                continue
                            value_year = nearest_year_for_value(source_text, span[0])
                            if not value_year and len(rating_hits) == 1:
                                context_years = extract_year_tokens(context_for_match)
                                if len(context_years) == 1:
                                    value_year = next(iter(context_years))
                            if not value_year and current_years:
                                if (
                                    len(current_years) == len(rating_hits)
                                    and idx < len(current_years)
                                ):
                                    value_year = current_years[idx]
                                elif (
                                    len(current_years) > 0
                                    and len(rating_hits) % len(current_years) == 0
                                ):
                                    block = len(rating_hits) // len(current_years)
                                    value_year = current_years[idx // block]
                            token_term = rating_term_for_span(source_text, span)
                            if token_term == "short_term":
                                continue
                            resolved_term = token_term or rating_term
                            rating_date = nearest_rating_date(source_text, span)
                            if not rating_date and context_for_match:
                                context_dates = rating_dates_with_positions(context_for_match)
                                unique_dates = {date for date, _ in context_dates}
                                if len(unique_dates) == 1:
                                    rating_date = next(iter(unique_dates))
                            match_source = source
                            if source == "text" and is_table_context(
                                source_text, context_for_match, current_years, current_columns
                            ):
                                match_source = "table"
                            results.append(
                                {
                                    "field": name,
                                    "value": value,
                                    "page": page_num,
                                    "line": line_idx,
                                    "line_text": source_text,
                                    "context_text": context_for_match,
                                    "value_span": span,
                                    "value_index": idx,
                                    "value_count": len(rating_hits),
                                    "value_year": value_year,
                                    "value_column": None,
                                    "raw_value": token,
                                    "rating_term": resolved_term,
                                    "rating_date": rating_date,
                                    "source": match_source,
                                }
                            )
                        continue
                    for pattern in field.get("patterns", []):
                        for match in re.finditer(
                            pattern, candidate_text, flags=re.IGNORECASE
                        ):
                            if match.groups():
                                raw_value = match.group(1)
                                value_span = match.span(1)
                            else:
                                raw_value = match.group(0)
                                value_span = match.span(0)
                            if (
                                name in standalone_only
                                and is_consolidated_line(candidate_text)
                                and not is_standalone_line(candidate_text)
                            ):
                                continue
                            if name == "Non-Performing Loan Ratio (NPL)":
                                if is_npl_coverage_line(candidate_text) or is_npl_exclusion_line(
                                    candidate_text
                                ):
                                    continue
                                if is_npl_industry_only_line(candidate_text):
                                    continue
                                if is_portfolio_npl_line(candidate_text):
                                    continue
                                if (
                                    is_requirement_value(candidate_text, value_span)
                                    or is_minimum_ratio_value(candidate_text, value_span)
                                ):
                                    continue
                            if name == "Return on Assets (ROA)" and is_roaa_line(candidate_text):
                                continue
                            if name == "Liquidity Coverage Ratio (LCR)":
                                if is_lcr_sector_line(candidate_text) or is_lcr_sector_line(
                                    context_text
                                ):
                                    continue
                                if is_lcr_nsfr_overlap_line(candidate_text):
                                    continue
                            if name == "Capital Adequacy Ratio (CRAR)" and (
                                is_crar_exclusion_line(candidate_text)
                                or is_crar_exclusion_line(context_text)
                            ):
                                continue
                            if FIELD_TYPES.get(name) == "numeric" and is_comparison_line(
                                candidate_text
                            ):
                                continue
                            if name in ("Credit Rating (CR)", "Regulatory Compliance (RC)"):
                                if is_scoring_table_line(candidate_text):
                                    continue
                            if FIELD_TYPES.get(name) == "numeric":
                                raw_value = apply_negative_context(
                                    raw_value, candidate_text, value_span
                                )
                                if is_formula_multiplier(candidate_text, value_span):
                                    continue
                                if name in PERCENT_REQUIRED_FIELDS and not has_percent_indicator(
                                    raw_value, candidate_text, context_text, value_span
                                ):
                                    continue
                            value = normalize_field_value(name, raw_value)
                            if value is None:
                                continue
                            match_source = source
                            if source == "text" and is_table_context(
                                candidate_text, context_text, current_years, current_columns
                            ):
                                match_source = "table"
                            results.append(
                                {
                                    "field": name,
                                    "value": value,
                                    "page": page_num,
                                    "line": line_idx,
                                    "line_text": candidate_text,
                                    "context_text": context_text,
                                    "value_span": value_span,
                                    "value_index": 0,
                                    "value_count": 1,
                                    "value_year": None,
                                    "value_column": None,
                                    "raw_value": raw_value,
                                    "source": match_source,
                                }
                            )

    return results


# --- Scoring and match evaluation ---
def compute_value_stats(matches):
    value_sources = {}
    value_counts = Counter()
    for match in matches:
        value = match.get("value")
        source = match.get("source", "text")
        if value is None:
            continue
        value_sources.setdefault(value, set()).add(source)
        value_counts[value] += 1
    return value_sources, value_counts


def format_value_for_reason(value):
    if value is None:
        return "None"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def summarize_distinct_values(value_counts, limit=3):
    values = []
    for value in value_counts.keys():
        if value is None:
            continue
        if value not in values:
            values.append(value)
    if not values:
        return ""
    display = ", ".join(format_value_for_reason(v) for v in values[:limit])
    if len(values) > limit:
        display = f"{display}, +{len(values) - limit} more"
    return display


def values_significantly_differ(value_a, value_b):
    if value_a is None or value_b is None:
        return False
    if isinstance(value_a, (int, float)) and isinstance(value_b, (int, float)):
        diff = abs(value_a - value_b)
        if diff >= 1:
            return True
        if value_b != 0 and diff / abs(value_b) >= 0.1:
            return True
        return False
    return value_a != value_b


def compute_match_score(match, year_token, field_name, value_sources, value_counts):
    line_text = match.get("line_text", "")
    context_text = match.get("context_text") or line_text
    combined_text = f"{line_text} {context_text}"
    value_span = match.get("value_span")
    value_pos = value_span[0] if value_span else None
    value_year = match.get("value_year")
    value_column = match.get("value_column")
    label_priority = match.get("label_priority")
    score = 0
    if year_token:
        if value_year:
            if value_year == year_token:
                score += 20
            else:
                score -= 20
        else:
            line_years = extract_year_tokens(line_text)
            context_years = extract_year_tokens(context_text)
            if year_token in line_years:
                score += 10
            elif year_token in context_years:
                score += 6
            elif not line_years and not context_years:
                score -= 4
            if year_token not in line_years and year_token not in context_years:
                other_years = line_years | context_years
                if other_years:
                    score -= 6
            if value_pos is not None and year_token in line_years:
                year_positions = keyword_positions(line_text, [year_token])
                dist_target = min_distance(value_pos, year_positions)
                if dist_target is not None:
                    if dist_target <= 8:
                        score += 8
                    elif dist_target <= 16:
                        score += 6
                    elif dist_target <= 24:
                        score += 4
                    elif dist_target <= 32:
                        score += 2
                other_years = [yr for yr in line_years if yr != year_token]
                if other_years:
                    other_positions = []
                    for yr in other_years:
                        other_positions.extend(keyword_positions(line_text, [yr]))
                    dist_other = min_distance(value_pos, other_positions)
                    if (
                        dist_other is not None
                        and dist_target is not None
                        and dist_other < dist_target
                    ):
                        score -= 2
    if field_name in (
        "Capital Adequacy Ratio (CRAR)",
        "Leverage Ratio (LR)",
        "Return on Assets (ROA)",
        "Return on Equity (ROE)",
    ):
        if value_column:
            if value_column == "standalone":
                score += 18
            elif value_column == "consolidated":
                score -= 18
    if field_name in ("Capital Adequacy Ratio (CRAR)", "Non-Performing Loan Ratio (NPL)") and label_priority:
        if label_priority == 1:
            score += 5 if field_name == "Capital Adequacy Ratio (CRAR)" else 4
        elif label_priority == 2:
            score -= 2
    if field_name == "Non-Performing Loan Ratio (NPL)":
        line_years = extract_year_tokens(line_text)
        context_years = extract_year_tokens(context_text)
        if match.get("value_count") == 2 and not line_years and context_years:
            if "2024" in context_years and "2023" in context_years:
                if match.get("value_index") == 0:
                    score += 6
                else:
                    score -= 6
        if match.get("value_count") == 2 and not line_years and not context_years:
            if match.get("value_index") == 0:
                score += 4
            else:
                score -= 4
    if field_name in (
        "Capital Adequacy Ratio (CRAR)",
        "Leverage Ratio (LR)",
        "Return on Equity (ROE)",
    ) and not value_column:
        standalone_positions = keyword_positions(line_text, STANDALONE_TOKENS)
        consolidated_positions = keyword_positions(line_text, CONSOLIDATED_TOKENS)
        if value_pos is not None:
            dist_standalone = min_distance(value_pos, standalone_positions)
            dist_consolidated = min_distance(value_pos, consolidated_positions)
            if dist_standalone is not None:
                score += 12 if dist_standalone <= 20 else 6
            if dist_consolidated is not None:
                score -= 12 if dist_consolidated <= 20 else 6
            if dist_standalone is not None and dist_consolidated is not None:
                if dist_standalone < dist_consolidated:
                    score += 3
                elif dist_consolidated < dist_standalone:
                    score -= 3
            if not standalone_positions and not consolidated_positions:
                if is_standalone_line(context_text):
                    score += 6
                if is_consolidated_line(context_text):
                    score -= 6
        else:
            if is_standalone_line(line_text) or is_standalone_line(context_text):
                score += 6
            if is_consolidated_line(line_text) or is_consolidated_line(context_text):
                score -= 6
    else:
        if is_standalone_line(line_text):
            score += 2
        if is_consolidated_line(line_text):
            score -= 5
    if field_name in ("Liquidity Coverage Ratio (LCR)", "Net Stable Funding Ratio (NSFR)"):
        if isinstance(match.get("value"), (int, float)):
            if match.get("value") >= 100:
                score += 6
            elif match.get("value") < 50:
                score -= 6
        if value_span:
            label_re = FIELD_LABELS.get(field_name)
            label_match = label_re.search(line_text) if label_re else None
            if label_match:
                dist = value_span[0] - label_match.end()
                if dist >= 0:
                    if dist <= 10:
                        score += 6
                    elif dist <= 20:
                        score += 3
                    elif dist >= 35:
                        score -= 4
                elif abs(dist) >= 10:
                    score -= 4
        if re.search(r"highlights|dashboard", line_text, flags=re.IGNORECASE) and (
            match.get("value_count") or 1
        ) >= 3:
            score -= 6
        if re.search(r"regulatory|limit|dbo", line_text, flags=re.IGNORECASE):
            score += 2
        if re.search(r"limit|minimum|requirement|more than|less than|or more", line_text, flags=re.IGNORECASE) or has_threshold_marker(line_text):
            if isinstance(match.get("value"), (int, float)) and match.get("value") <= 105:
                if has_higher_percent_in_line(line_text, match.get("value")):
                    score -= 20
                else:
                    score -= 8
            elif isinstance(match.get("value"), (int, float)) and match.get("value") <= 110:
                score -= 4
    if value_column == "bank":
        score += 8
    elif value_column == "group":
        score -= 6
    if field_name in PERCENT_REQUIRED_FIELDS:
        if GENERIC_EXACT_VALUE_RE.search(combined_text):
            score += 4
        if GENERIC_DEFINITION_RE.search(combined_text):
            score -= 12
        if GENERIC_TARGET_RE.search(combined_text):
            score -= 10
        if GENERIC_BENCHMARK_RE.search(combined_text):
            score -= 8
    if field_name == "Capital Adequacy Ratio (CRAR)":
        if year_token and re.search(
            r"\bas on\b|\bas at\b|\bas of\b",
            combined_text,
            flags=re.IGNORECASE,
        ):
            if year_token in line_text or year_token in context_text:
                score += 6
        if (
            re.search(r"consist|compris|made up", line_text, flags=re.IGNORECASE)
            and re.search(r"tier[- ]?1", line_text, flags=re.IGNORECASE)
            and re.search(r"tier[- ]?2", line_text, flags=re.IGNORECASE)
        ):
            score -= 20
        if isinstance(match.get("value"), (int, float)):
            if match.get("value") < 5 or match.get("value") > 40:
                score -= 30
        if value_span:
            window_start = max(0, value_span[0] - 25)
            window = line_text[window_start:value_span[0]].lower()
            if re.search(r"minimum requirement|required level|required|requirement", window):
                score -= 20
    if match.get("has_other_labels"):
        score -= 8
    if match.get("has_other_labels_context"):
        score -= 4
    if match.get("label_order_match"):
        score += 6
    if field_name == "Return on Equity (ROE)":
        if "roa" in line_text.lower() and "roe" in line_text.lower():
            if isinstance(match.get("value"), (int, float)) and match.get("value") < 5:
                score -= 12
    if field_name == "Return on Assets (ROA)":
        if "roa" in line_text.lower() and "roe" in line_text.lower():
            if isinstance(match.get("value"), (int, float)) and match.get("value") > 5:
                score -= 12
    if field_name == "Non-Performing Loan Ratio (NPL)":
        value_count = match.get("value_count") or 1
        lower = line_text.lower()
        if NPL_THRESHOLD_RE.search(lower):
            score -= 12
        if NPL_EXACT_VALUE_RE.search(lower):
            score += 6
        ie_match = re.search(r"\bi\.e\.\b|\bie\b", lower)
        if ie_match and value_span:
            if value_span[0] > ie_match.start():
                score += 18
            else:
                score -= 8
        if WHEREAS_RE.search(lower):
            score += 10
        if BANK_POSSESSIVE_RE.search(line_text):
            score += 8
        if "npl" in lower:
            score += 3
            if re.search(r"\bnpl\s*%\b", lower):
                score += 4
        if re.search(r"\b(movement|trend|graph|chart)\b", lower):
            score -= 10
        if NPL_THRESHOLD_RE.search(lower) and value_count >= 2:
            if match.get("value_index") == 0:
                score -= 6
            else:
                score += 4
        if NPL_INDUSTRY_RE.search(lower) or NPL_INDUSTRY_RE.search(
            (context_text or "").lower()
        ):
            bank_positions = bank_mention_positions(line_text)
            industry_positions = [m.start() for m in NPL_INDUSTRY_RE.finditer(line_text)]
            whereas_match = WHEREAS_RE.search(line_text)
            if value_span:
                value_pos = value_span[0]
                if whereas_match and value_pos < whereas_match.start():
                    score -= 120
                if bank_positions:
                    dist_bank = min_distance(value_pos, bank_positions)
                    if dist_bank is not None:
                        score += 16 if dist_bank <= 25 else 8 if dist_bank <= 40 else 2
                else:
                    score -= 40
                if industry_positions:
                    dist_industry = min_distance(value_pos, industry_positions)
                    if dist_industry is not None and dist_industry <= 20:
                        score -= 25
                    elif dist_industry is not None and dist_industry <= 40:
                        score -= 12
                if bank_positions and industry_positions:
                    if dist_bank is not None and dist_industry is not None:
                        if dist_bank <= dist_industry:
                            score += 8
                        else:
                            score -= 18
                if whereas_match:
                    score += 12 if value_pos >= whereas_match.start() else -40
            else:
                if not bank_positions:
                    score -= 10
            if " vs " in lower or " versus " in lower:
                score -= 12
    value_count = match.get("value_count") or 1
    if value_count >= 6:
        score -= 8
    elif value_count >= 4:
        score -= 6
    elif value_count >= 2:
        score -= 2
    if match.get("field") == "Credit Rating (CR)":
        rating_score = credit_rating_rank(match.get("value"))
        if rating_score is not None:
            score += rating_score
        rating_term = match.get("rating_term")
        if rating_term == "long_term":
            score += 8
        elif rating_term == "mixed":
            score += 3
        elif rating_term == "short_term":
            score -= 10
        if CREDIT_RATING_SECTION_RE.search(line_text) or CREDIT_RATING_SECTION_RE.search(
            context_text
        ):
            score += 30
        if SURVEILLANCE_RATING_RE.search(f"{line_text} {context_text}"):
            score -= 12
        if re.search(r"\bachievement|award", f"{line_text} {context_text}", re.I) and not CREDIT_RATING_SECTION_RE.search(
            f"{line_text} {context_text}"
        ):
            score -= 30
        agency_count = count_rating_agencies(f"{line_text} {context_text}")
        if agency_count >= 2:
            score -= 8
        has_preferred = contains_preferred_rating_agency(
            line_text
        ) or contains_preferred_rating_agency(context_text)
        has_any_agency = contains_rating_agency(line_text) or contains_rating_agency(
            context_text
        )
        has_crab = contains_crab_agency(line_text) or contains_crab_agency(context_text)
        if has_preferred:
            score += 6
        elif has_any_agency:
            score += 3
        if rating_term == "long_term" and has_crab:
            score += 4
    source_rank = {"text": 8, "table": 4, "ocr": 0}
    score += source_rank.get(match.get("source", "text"), 0)
    if has_trailing_words_after_numbers(line_text):
        score -= 4
    if isinstance(match.get("value"), (int, float)) and "%" in line_text:
        score += 1
    sources = value_sources.get(match.get("value"), set())
    if "text" in sources and "ocr" in sources:
        score += 6
    frequency = value_counts.get(match.get("value"), 0)
    if frequency > 1:
        score += min(6, 2 * (frequency - 1))
    if len(line_text) <= 120:
        score += 1
    return score


def compute_match_confidence(match, year, field_name, value_sources, value_counts):
    if not match:
        return None
    year_token = str(year) if year else None
    source = match.get("source", "text")
    base = {"text": 0.9, "table": 0.86, "ocr": 0.6}.get(source, 0.75)
    score = compute_match_score(match, year_token, field_name, value_sources, value_counts)
    adjust = max(-0.2, min(0.2, score / 100.0))
    conf = base + adjust
    count = value_counts.get(match.get("value"), 0)
    if count > 1:
        conf += min(0.05, 0.02 * (count - 1))
    sources = value_sources.get(match.get("value"), set())
    if len(sources) > 1:
        conf += 0.03
    conf = max(0.0, min(0.99, conf))
    return round(conf, 3)


def pick_best_match(matches, year=None, field_name=None):
    if not matches:
        return None
    all_matches = matches
    # Enforce source priority: text -> table -> ocr.
    if field_name == "Credit Rating (CR)":
        table_matches = [m for m in all_matches if m.get("source", "text") == "table"]
        if table_matches:
            matches = table_matches
        else:
            matches = all_matches
    elif field_name not in (
        "Capital Adequacy Ratio (CRAR)",
        "Leverage Ratio (LR)",
        "Return on Assets (ROA)",
        "Return on Equity (ROE)",
    ):
        sources_present = {m.get("source", "text") for m in all_matches}
        if "text" in sources_present:
            matches = [m for m in all_matches if m.get("source", "text") == "text"]
        elif "table" in sources_present:
            matches = [m for m in all_matches if m.get("source", "text") == "table"]
    year_token = str(year) if year else None
    if year_token:
        with_year = []
        undated_standalone = []
        for m in matches:
            line_text = m.get("line_text", "")
            context_text = m.get("context_text") or line_text
            line_years = extract_year_tokens(line_text)
            context_years = extract_year_tokens(context_text)
            value_year = m.get("value_year")
            if value_year:
                if value_year == year_token:
                    with_year.append(m)
                continue
            if year_token in line_years or year_token in context_years:
                with_year.append(m)
            elif (
                field_name in (
                    "Capital Adequacy Ratio (CRAR)",
                    "Leverage Ratio (LR)",
                    "Return on Assets (ROA)",
                    "Return on Equity (ROE)",
                )
                and m.get("value_column") in ("standalone", "bank")
                and not line_years
                and not context_years
            ):
                undated_standalone.append(m)
        if with_year:
            if field_name in (
                "Capital Adequacy Ratio (CRAR)",
                "Leverage Ratio (LR)",
                "Return on Assets (ROA)",
                "Return on Equity (ROE)",
            ):
                has_standalone = any(
                    m.get("value_column") in ("standalone", "bank") for m in with_year
                )
                if not has_standalone and undated_standalone:
                    for m in undated_standalone:
                        if m not in with_year:
                            with_year.append(m)
            matches = with_year
    if matches:
        with_column = [
            m for m in matches if m.get("value_column") in ("bank", "group")
        ]
        if with_column and len(with_column) == len(matches):
            bank_matches = [m for m in with_column if m.get("value_column") == "bank"]
            if bank_matches:
                matches = bank_matches
    if matches and field_name in (
        "Capital Adequacy Ratio (CRAR)",
        "Leverage Ratio (LR)",
        "Return on Assets (ROA)",
        "Return on Equity (ROE)",
        "Liquidity Coverage Ratio (LCR)",
        "Net Stable Funding Ratio (NSFR)",
    ):
        standalone_matches = [
            m for m in matches if m.get("value_column") in ("standalone", "bank")
        ]
        if standalone_matches:
            matches = standalone_matches
    if matches and field_name == "Credit Rating (CR)":
        section_matches = [
            m
            for m in matches
            if CREDIT_RATING_SECTION_RE.search(m.get("line_text", ""))
            or CREDIT_RATING_SECTION_RE.search(m.get("context_text", ""))
        ]
        if section_matches:
            matches = section_matches
        crab_line_matches = [
            m for m in matches if contains_crab_agency(m.get("line_text", ""))
        ]
        crab_context_matches = []
        if crab_line_matches:
            matches = crab_line_matches
        else:
            crab_context_matches = [
                m for m in matches if contains_crab_agency(m.get("context_text", ""))
            ]
        if crab_context_matches:
            matches = crab_context_matches
        if year_token:
            dated_year_matches = []
            for m in matches:
                date_token = m.get("rating_date")
                if date_token and str(date_token[0]) == year_token:
                    dated_year_matches.append(m)
            if dated_year_matches:
                matches = dated_year_matches
        long_term_matches = [m for m in matches if m.get("rating_term") == "long_term"]
        if long_term_matches:
            matches = long_term_matches
        table_matches = [m for m in matches if m.get("source", "text") == "table"]
        if table_matches:
            matches = table_matches
        dated_matches = []
        for m in matches:
            date_token = m.get("rating_date")
            if not date_token:
                line_text = m.get("line_text", "")
                date_token = extract_latest_rating_date(line_text)
            if date_token:
                dated_matches.append((date_token, m))
        if dated_matches:
            latest_date = max(date for date, _ in dated_matches)
            matches = [m for date, m in dated_matches if date == latest_date]
        if year_token and not dated_matches:
            year_matches = [m for m in matches if m.get("value_year") == year_token]
            if year_matches:
                matches = year_matches
            else:
                inferred_matches = []
                for m in matches:
                    if m.get("value_year"):
                        continue
                    value_count = m.get("value_count") or 0
                    value_index = m.get("value_index")
                    if value_index is None or value_count <= 0:
                        continue
                    context_years = extract_years_in_order(m.get("context_text", ""))
                    if not context_years:
                        continue
                    if len(context_years) == value_count and value_index < len(context_years):
                        inferred = context_years[value_index]
                    elif (
                        len(context_years) > 0
                        and value_count % len(context_years) == 0
                        and value_index < value_count
                    ):
                        block = value_count // len(context_years)
                        inferred = context_years[value_index // block]
                    else:
                        continue
                    if inferred == year_token:
                        inferred_matches.append(m)
                if inferred_matches:
                    matches = inferred_matches
        if matches:
            ranked_matches = []
            for m in matches:
                rank = credit_rating_choice_rank(m.get("value"))
                if rank >= 0:
                    ranked_matches.append((rank, m))
            if ranked_matches:
                best_rank = max(rank for rank, _ in ranked_matches)
                matches = [m for rank, m in ranked_matches if rank == best_rank]
    if matches and field_name == "Non-Performing Loan Ratio (NPL)" and year_token:
        year_matches = [m for m in matches if m.get("value_year") == year_token]
        if year_matches:
            matches = year_matches
        else:
            inferred_matches = []
            for m in matches:
                if m.get("value_year"):
                    continue
                value_count = m.get("value_count") or 0
                value_index = m.get("value_index")
                if value_index is None or value_count <= 0:
                    continue
                context_years = extract_years_in_order(m.get("context_text", ""))
                if not context_years:
                    continue
                if len(context_years) == value_count and value_index < len(context_years):
                    inferred = context_years[value_index]
                elif (
                    len(context_years) > 0
                    and value_count % len(context_years) == 0
                    and value_index < value_count
                ):
                    block = value_count // len(context_years)
                    inferred = context_years[value_index // block]
                else:
                    continue
                if inferred == year_token:
                    inferred_matches.append(m)
            if inferred_matches:
                matches = inferred_matches
    value_sources, value_counts = compute_value_stats(all_matches)
    if field_name == "Regulatory Compliance (RC)":
        penalty_matches = [m for m in matches if m.get("value") == "Penalty"]
        no_penalty_matches = [m for m in matches if m.get("value") == "No Penalty"]
        strong_penalty = [
            m
            for m in penalty_matches
            if is_strong_penalty_context(
                f"{m.get('line_text', '')} {m.get('context_text', '')}"
            )
        ]
        if no_penalty_matches:
            matches = no_penalty_matches
        elif strong_penalty:
            matches = strong_penalty
        elif penalty_matches:
            return {
                "field": field_name,
                "value": "No Penalty",
                "page": None,
                "line": None,
                "line_text": "",
                "context_text": "",
                "value_span": None,
                "value_index": 0,
                "value_count": 1,
                "value_year": None,
                "value_column": None,
                "raw_value": "No Penalty",
            }
    best = None
    best_score = None
    for match in matches:
        score = compute_match_score(match, year_token, field_name, value_sources, value_counts)
        rank = (score, -match.get("page", 0), -match.get("line", 0))
        if best is None or rank > best_score:
            best = match
            best_score = rank
    return best


def plan_selective_ocr(fields, grouped, year, keyword_hits):
    ocr_field_names = set()
    ocr_pages = set()
    ocr_reasons = {}
    pre_ocr_best = {}
    pre_ocr_conf = {}
    for field_name in FIELD_ORDER:
        matches = grouped.get(field_name, [])
        matches_tt = [
            m for m in matches if m.get("source", "text") in ("text", "table")
        ]
        best_tt = pick_best_match(matches_tt, year=year, field_name=field_name) if matches_tt else None
        pre_ocr_best[field_name] = best_tt
        if matches_tt:
            value_sources, value_counts = compute_value_stats(matches_tt)
            confidence = compute_match_confidence(
                best_tt, year, field_name, value_sources, value_counts
            )
            distinct_values = [v for v in value_counts.keys() if v is not None]
            if len(distinct_values) > 1:
                conflict_values = summarize_distinct_values(value_counts)
                confidence = min(confidence or 0.0, 0.74)
                pre_ocr_conf[field_name] = confidence
                reason = f"conflicting values ({conflict_values})"
                status = "conflicting"
            elif confidence is not None and confidence < 0.75:
                pre_ocr_conf[field_name] = confidence
                reason = f"low confidence ({confidence:.2f})"
                status = "low"
            else:
                pre_ocr_conf[field_name] = confidence
                reason = "not required"
                status = "ok"
        else:
            pre_ocr_conf[field_name] = None
            reason = "missing value"
            status = "missing"

        if FIELD_TYPES.get(field_name) != "numeric":
            if field_name != "Credit Rating (CR)":
                if status in ("missing", "low", "conflicting"):
                    ocr_reasons[field_name] = f"{reason}; not eligible (non-numeric)"
                else:
                    ocr_reasons[field_name] = reason
                continue

        if status in ("missing", "low", "conflicting"):
            pages = keyword_hits.get(field_name, set()) if keyword_hits else set()
            if pages:
                ocr_field_names.add(field_name)
                ocr_pages.update(pages)
                ocr_reasons[field_name] = reason
            else:
                ocr_reasons[field_name] = f"{reason}; no keyword page found"
        else:
            ocr_reasons[field_name] = reason

    return {
        "ocr_field_names": ocr_field_names,
        "ocr_pages": sorted(ocr_pages),
        "ocr_reasons": ocr_reasons,
        "pre_ocr_best": pre_ocr_best,
        "pre_ocr_conf": pre_ocr_conf,
    }


def select_best_match_with_confidence(field_name, matches, year):
    if not matches:
        return None, None, None, None, {}
    by_source = {"text": [], "table": [], "ocr": []}
    for match in matches:
        source = match.get("source", "text")
        by_source.setdefault(source, []).append(match)
    best_by_source = {}
    for source, source_matches in by_source.items():
        if source_matches:
            best_by_source[source] = pick_best_match(
                source_matches, year=year, field_name=field_name
            )
    if not best_by_source:
        return None, None, None, None, {}
    value_sources, value_counts = compute_value_stats(matches)
    conf_by_source = {}
    for source, match in best_by_source.items():
        conf_by_source[source] = compute_match_confidence(
            match, year, field_name, value_sources, value_counts
        )
    ocr_mismatch = False
    if "ocr" in best_by_source:
        ocr_value = best_by_source["ocr"].get("value")
        non_ocr_sources = [
            src
            for src in ("text", "table")
            if src in best_by_source and best_by_source[src] is not None
        ]
        if non_ocr_sources:
            best_non_ocr_source = max(
                non_ocr_sources, key=lambda src: conf_by_source.get(src, 0)
            )
            non_ocr_value = best_by_source[best_non_ocr_source].get("value")
            if values_significantly_differ(ocr_value, non_ocr_value):
                conf_by_source["ocr"] = max(0.0, conf_by_source["ocr"] - 0.15)
                ocr_mismatch = True
    priority = {"text": 2, "table": 1, "ocr": 0}
    best_source = max(
        conf_by_source.keys(),
        key=lambda src: (conf_by_source.get(src, 0), priority.get(src, -1)),
    )
    best_match = best_by_source[best_source]
    best_conf = conf_by_source.get(best_source)
    reason_parts = []
    for source in ("text", "table", "ocr"):
        if source in conf_by_source:
            reason_parts.append(f"{source}:{conf_by_source[source]:.2f}")
    if ocr_mismatch:
        reason_parts.append("ocr_mismatch_penalty")
    reason = "highest confidence (" + ", ".join(reason_parts) + ")"
    return best_match, best_conf, best_source, reason, conf_by_source


def score_field_value(field_name, value):
    if value is None:
        return None
    numeric_fields = {
        "Capital Adequacy Ratio (CRAR)",
        "Leverage Ratio (LR)",
        "Non-Performing Loan Ratio (NPL)",
        "Provision Coverage Ratio (PCR)",
        "Loan to Deposit Ratio (LDR)",
        "Return on Assets (ROA)",
        "Return on Equity (ROE)",
        "Net Interest Margin (NIM)",
        "Liquidity Coverage Ratio (LCR)",
        "Net Stable Funding Ratio (NSFR)",
        "Cash to Deposit Ratio (CDR)",
    }
    if field_name in numeric_fields:
        value = parse_numeric(value)
        if value is None:
            return 0
    if field_name == "Capital Adequacy Ratio (CRAR)":
        if value > 14:
            return 15
        if 12.5 <= value <= 13.9:
            return 10
        if 10 <= value <= 12.4:
            return 7
        return 0
    if field_name == "Leverage Ratio (LR)":
        return 5 if value >= 3 else 0
    if field_name == "Non-Performing Loan Ratio (NPL)":
        if value <= 3:
            return 15
        if 3.1 <= value <= 5:
            return 10
        if 5.1 <= value <= 8:
            return 5
        return 0
    if field_name == "Provision Coverage Ratio (PCR)":
        return 10 if value >= 100 else 0
    if field_name == "Loan to Deposit Ratio (LDR)":
        return 5 if 75 <= value <= 90 else 0
    if field_name == "Return on Assets (ROA)":
        return 5 if value >= 1 else 0
    if field_name == "Return on Equity (ROE)":
        return 5 if value >= 12 else 0
    if field_name == "Net Interest Margin (NIM)":
        return 5 if value >= 3 else 0
    if field_name == "Liquidity Coverage Ratio (LCR)":
        return 10 if value >= 110 else 0
    if field_name == "Net Stable Funding Ratio (NSFR)":
        return 10 if value > 100 else 0
    if field_name == "Cash to Deposit Ratio (CDR)":
        return 5 if value >= 10 else 0
    if field_name == "Credit Rating (CR)":
        normalized = normalize_credit_rating(value)
        if not normalized:
            return 0
        return 10 if normalized in ("AAA", "AA") else 0
    if field_name == "Regulatory Compliance (RC)":
        if value == "Penalty":
            return -5
        if value == "No Penalty":
            return 0
        return None
    return None


# --- Output and configuration helpers ---
def save_excel(rows, output_path):
    ensure_dir(os.path.dirname(output_path) or ".")
    df = pd.DataFrame(rows)
    df.to_excel(output_path, index=False)


def save_excel_df(df, output_path):
    ensure_dir(os.path.dirname(output_path) or ".")
    df.to_excel(output_path, index=False)


def load_bank_config(banks_path, bank_name):
    data = read_json(banks_path)
    for entry in data.get("banks", []):
        if entry.get("bank", "").lower() == bank_name.lower():
            return entry
    return None


def load_sources(sources_path):
    data = read_json(sources_path)
    return data.get("sources", [])


def push_eligibility_to_apex(bank_name, year, npl_value, rating_value, pcr=None):
    try:
        result = send_bank_eligibility(
            bank_name=bank_name,
            fiscal_year=str(year) if year is not None else "",
            fin_period="Annual",
            npl=npl_value,
            pcr=pcr,
            rating=rating_value,
        )
    except Exception as exc:
        print(f"APEX error for {bank_name} {year}: {exc}", file=sys.stderr)
        return
    if result.get("error"):
        print(
            f"APEX reported failure for {bank_name} {year}: {result['error']}",
            file=sys.stderr,
        )
        return
    status = result.get("status_code")
    response_text = result.get("response") or "(empty)"
    mode = result.get("mode") or "form"
    print(f"APEX response {bank_name} {year} [{mode}] -> {status}: {response_text}")
    if not result.get("ok"):
        print(f"APEX rejected {bank_name} {year} -> {status}", file=sys.stderr)
        return
    print(f"APEX sent {bank_name} {year} -> {status}")


def build_output_name(bank, year):
    bank_part = sanitize_filename(bank or "UnknownBank")
    year_part = sanitize_filename(year or "UnknownYear")
    return f"Annual_Report_{bank_part}_{year_part}.xlsx"


def build_pdf_name(bank, year):
    bank_part = sanitize_filename(bank or "UnknownBank")
    year_part = sanitize_filename(year or "UnknownYear")
    return f"Annual_Report_{bank_part}_{year_part}.pdf"


def build_summary_output_name(year):
    year_part = sanitize_filename(year or "UnknownYear")
    return f"Annual_Report_{year_part}.xlsx"


def build_developer_output_name(year):
    year_part = sanitize_filename(year or "UnknownYear")
    return f"Annual_Report_Developer_{year_part}.xlsx"


def build_eligible_output_name(year):
    year_part = sanitize_filename(year or "UnknownYear")
    return f"Eligible_Bank_Lists_{year_part}.xlsx"


def emit_eligibility_data(
    bank_name,
    year,
    npl_value,
    npl_page,
    pcr_value,
    pcr_page,
    rating_value,
    rating_page,
    pdf_path,
    npl_score=None,
    pcr_score=None,
    rating_score=None,
):
    payload = {
        "bank": bank_name,
        "year": year,
        "npl": npl_value,
        "nplPage": npl_page,
        "pcr": pcr_value,
        "pcrPage": pcr_page,
        "rating": rating_value,
        "ratingPage": rating_page,
        "nplScore": npl_score,
        "pcrScore": pcr_score,
        "ratingScore": rating_score,
        "pdf_path": pdf_path,
    }
    try:
        print("ELIGIBILITY_DATA " + json.dumps(payload, separators=(",", ":")))
    except Exception:
        pass


def derive_developer_path(summary_path):
    base, ext = os.path.splitext(summary_path)
    if not ext:
        ext = ".xlsx"
    return f"{base}_Developer{ext}"


def build_summary_row(bank_name, field_values, total_score):
    return {
        "Bank Name": bank_name,
        "Capital To Risk Weighted Assets Ratio": field_values.get(
            "Capital Adequacy Ratio (CRAR)"
        ),
        "Leverage Ratio": field_values.get("Leverage Ratio (LR)"),
        "Non Performing Loan Ratio": field_values.get("Non-Performing Loan Ratio (NPL)"),
        "Provision Coverage Ratio": field_values.get("Provision Coverage Ratio (PCR)"),
        "Loan To Deposit Ratio": field_values.get("Loan to Deposit Ratio (LDR)"),
        "Return on Assets": field_values.get("Return on Assets (ROA)"),
        "Return on Equity": field_values.get("Return on Equity (ROE)"),
        "Net Interest Margin": field_values.get("Net Interest Margin (NIM)"),
        "Liquidity Coverage Ratio": field_values.get("Liquidity Coverage Ratio (LCR)"),
        "Net Stable Funding Ratio": field_values.get("Net Stable Funding Ratio (NSFR)"),
        "Cash to Deposit Ratio": field_values.get("Cash to Deposit Ratio (CDR)"),
        "Credit Rating": field_values.get("Credit Rating (CR)"),
        "Total Score": total_score,
    }


def build_empty_result(bank_name, year, source_url=None, source_type=None, error=None):
    safe_bank = bank_name or "Unknown"
    safe_type = source_type or "unknown"
    field_values = {field: None for field in FIELD_ORDER}
    summary_row = build_summary_row(safe_bank, field_values, 0)
    best_matches = {field: None for field in FIELD_ORDER}
    developer_rows = build_developer_rows(
        safe_bank, year, source_url, safe_type, best_matches, 0
    )
    if error:
        print(f"Error processing {safe_bank} {year}: {error}", file=sys.stderr)
    return {
        "bank": safe_bank,
        "year": year,
        "summary_row": summary_row,
        "developer_rows": developer_rows,
    }


def build_developer_rows(
    bank_name,
    year,
    source_url,
    source_type,
    best_matches,
    total_score,
    field_metadata=None,
    ocr_triggered_fields=None,
):
    def build_source_url_for_match(base_url, match):
        if not base_url:
            return None
        parsed = urlparse(base_url)
        if parsed.scheme not in ("http", "https"):
            return base_url
        page = match.get("page") if match else None
        if page is None and not match:
            return base_url
        search_value = None
        if match:
            raw_value = match.get("raw_value")
            search_value = raw_value if raw_value not in (None, "") else match.get("value")
        if page is None and search_value in (None, ""):
            return base_url
        base_no_fragment = parsed._replace(fragment="").geturl()
        fragment_parts = []
        if page is not None:
            fragment_parts.append(f"page={page}")
        if search_value not in (None, ""):
            fragment_parts.append(f"search={quote(str(search_value))}")
        fragment = "&".join(fragment_parts)
        return f"{base_no_fragment}#{fragment}" if fragment else base_no_fragment

    display_names = {
        "Capital Adequacy Ratio (CRAR)": "Capital To Risk Weighted Assets Ratio",
        "Leverage Ratio (LR)": "Leverage Ratio",
        "Non-Performing Loan Ratio (NPL)": "Non Performing Loan Ratio",
        "Provision Coverage Ratio (PCR)": "Provision Coverage Ratio",
        "Loan to Deposit Ratio (LDR)": "Loan To Deposit Ratio",
        "Return on Assets (ROA)": "Return on Assets",
        "Return on Equity (ROE)": "Return on Equity",
        "Net Interest Margin (NIM)": "Net Interest Margin",
        "Liquidity Coverage Ratio (LCR)": "Liquidity Coverage Ratio",
        "Net Stable Funding Ratio (NSFR)": "Net Stable Funding Ratio",
        "Cash to Deposit Ratio (CDR)": "Cash to Deposit Ratio",
        "Credit Rating (CR)": "Credit Rating",
    }
    rows = []
    ocr_triggered_display = ", ".join(ocr_triggered_fields or []) if ocr_triggered_fields else ""
    for field_name in FIELD_ORDER:
        best = best_matches.get(field_name)
        meta = (field_metadata or {}).get(field_name, {})
        row_source_url = build_source_url_for_match(source_url, best)
        rows.append(
            {
                "Feature": display_names.get(field_name, field_name),
                "Bank Name": bank_name,
                "Year": year,
                "Value": best["value"] if best else None,
                "Page": best["page"] if best else None,
                "Confidence": meta.get("confidence"),
                "Winning_Source": meta.get("winning_source"),
                "Winning_Reason": meta.get("winning_reason"),
                "OCR_Triggered_Fields": ocr_triggered_display,
                "OCR_Reason": meta.get("ocr_reason"),
                "Source_Type": source_type,
                "Source_URL": row_source_url,
            }
        )
    rows.append(
        {
            "Feature": "Total Score",
            "Bank Name": bank_name,
            "Year": year,
            "Value": total_score,
            "Page": None,
            "Confidence": None,
            "Winning_Source": None,
            "Winning_Reason": None,
            "OCR_Triggered_Fields": ocr_triggered_display,
            "OCR_Reason": None,
            "Source_Type": source_type,
            "Source_URL": source_url,
        }
    )
    return rows


def write_year_outputs(results, year, output_dir, summary_output=None):
    ensure_dir(output_dir)
    summary_rows = [r["summary_row"] for r in results]
    developer_rows = []
    for result in results:
        developer_rows.extend(result["developer_rows"])
    summary_columns = [
        "Bank Name",
        "Capital To Risk Weighted Assets Ratio",
        "Leverage Ratio",
        "Non Performing Loan Ratio",
        "Provision Coverage Ratio",
        "Loan To Deposit Ratio",
        "Return on Assets",
        "Return on Equity",
        "Net Interest Margin",
        "Liquidity Coverage Ratio",
        "Net Stable Funding Ratio",
        "Cash to Deposit Ratio",
        "Credit Rating",
        "Total Score",
    ]
    developer_columns = [
        "Feature",
        "Bank Name",
        "Year",
        "Value",
        "Page",
        "Confidence",
        "Winning_Source",
        "Winning_Reason",
        "OCR_Triggered_Fields",
        "OCR_Reason",
        "Source_Type",
        "Source_URL",
    ]
    summary_df = pd.DataFrame(summary_rows, columns=summary_columns)
    developer_df = pd.DataFrame(developer_rows, columns=developer_columns)
    if summary_output:
        summary_path = summary_output
        developer_path = derive_developer_path(summary_output)
    else:
        summary_path = os.path.join(output_dir, build_summary_output_name(year))
        developer_path = os.path.join(output_dir, build_developer_output_name(year))
    save_excel_df(summary_df, summary_path)
    save_excel_df(developer_df, developer_path)
    print(f"Saved summary output to {summary_path}")
    print(f"Saved developer output to {developer_path}")


def infer_bank_name(bank_name, bank_cfg, pdf_path, pdf_url):
    if bank_name:
        return bank_name
    if bank_cfg and bank_cfg.get("bank"):
        return bank_cfg.get("bank")
    source = pdf_path or (urlparse(pdf_url).path if pdf_url else "")
    base = os.path.basename(source) if source else ""
    if base:
        name = re.sub(r"\.pdf$", "", base, flags=re.IGNORECASE)
        name = re.sub(r"annual[_ -]?report[_ -]?", "", name, flags=re.IGNORECASE)
        name = re.sub(r"(?<!\d)\d{4}(?!\d)", "", name)
        name = name.replace("_", " ").replace("-", " ")
        name = normalize_text(name)
        if name:
            return name
    return "Unknown"


def detect_source_type(url, pdf_path):
    if url and is_pdf_url(url):
        return "pdf"
    if pdf_path and pdf_path.lower().endswith(".pdf"):
        return "pdf"
    return "website"


def run_single_with_config(
    args,
    fields,
    pdf_url,
    pdf_path,
    bank_name,
    year,
    fields_override=None,
    eligibility_only=False,
):
    scan_fields = fields_override or fields
    scan_field_names = {field.get("name") for field in scan_fields}
    bank_cfg = None
    download_name = None
    if bank_name and year:
        download_name = build_pdf_name(bank_name, year)
    if not pdf_url and not pdf_path:
        if not bank_name:
            banks_cfg = read_json(args.banks)
            banks = banks_cfg.get("banks", [])
            if not banks:
                print("Provide --pdf-url, --pdf-path, or --bank", file=sys.stderr)
                return 2
            bank_cfg = banks[0]
            bank_name = bank_cfg.get("bank")
            print(
                f"No --bank provided; using first configured bank: {bank_name}",
                file=sys.stderr,
            )
        else:
            bank_cfg = load_bank_config(args.banks, bank_name)
            if not bank_cfg:
                print("Bank not found in config/bank_seeds.json", file=sys.stderr)
                return 2
        pdf_url = crawl_for_pdf(
            bank_cfg.get("seeds", []),
            keywords=bank_cfg.get("keywords", []),
            year=year,
            max_pages=args.max_crawl_pages,
            timeout=args.timeout,
        )
        if not pdf_url:
            print("Crawler could not find a PDF", file=sys.stderr)
            return 2

    if pdf_path:
        final_pdf_path = pdf_path
    else:
        if not pdf_url:
            print("No PDF URL available", file=sys.stderr)
            return 2
        try:
            final_pdf_path = download_pdf(
                pdf_url, args.download_dir, args.download_timeout, download_name
            )
        except Exception as exc:
            cached_pdf = find_cached_pdf(args.download_dir, bank_name, year, pdf_url)
            if cached_pdf:
                print(f"Using cached PDF at {cached_pdf}")
                final_pdf_path = cached_pdf
            else:
                if bank_name and not bank_cfg:
                    bank_cfg = load_bank_config(args.banks, bank_name)
                if bank_cfg:
                    pdf_url = crawl_for_pdf(
                        bank_cfg.get("seeds", []),
                        keywords=bank_cfg.get("keywords", []),
                        year=year,
                        max_pages=args.max_crawl_pages,
                        timeout=args.timeout,
                    )
                    if not pdf_url:
                        raise
                    final_pdf_path = download_pdf(
                        pdf_url,
                        args.download_dir,
                        args.download_timeout,
                        download_name,
                    )
                else:
                    raise RuntimeError(f"Download failed: {exc}")

    source_url = pdf_url or pdf_path
    source_type = detect_source_type(pdf_url, final_pdf_path)
    output_bank = infer_bank_name(bank_name, bank_cfg, final_pdf_path, pdf_url)
    print(f"Scanning PDF: {final_pdf_path}")

    def scan_pdf_for_fields(fields_to_scan):
        keyword_hits = {}
        page_text_cache = {}
        pages = iter_pdf_pages(final_pdf_path, args.max_pages)
        raw_matches = extract_fields(
            pages,
            fields_to_scan,
            scan_keywords=args.scan_keywords,
            source="text",
            keyword_hits=keyword_hits,
            page_text_cache=page_text_cache,
        )
        if not raw_matches and pdfplumber is not None and fitz is not None:
            print("No matches found. Retrying with alternate PDF parser.")
            keyword_hits = {}
            page_text_cache = {}
            pages = iter_pages_pymupdf(final_pdf_path, args.max_pages)
            raw_matches = extract_fields(
                pages,
                fields_to_scan,
                scan_keywords=args.scan_keywords,
                source="text",
                keyword_hits=keyword_hits,
                page_text_cache=page_text_cache,
            )
        return raw_matches, keyword_hits, page_text_cache

    if not eligibility_only and fields_override is None:
        eligibility_fields = [
            field
            for field in fields
            if field.get("name")
            in (
                "Non-Performing Loan Ratio (NPL)",
                "Provision Coverage Ratio (PCR)",
                "Credit Rating (CR)",
            )
        ]
        if eligibility_fields:
            print("Eligibility precheck: NPL + Credit Rating", file=sys.stderr)
            scan_pdf_for_fields(eligibility_fields)

    raw_matches, keyword_hits, page_text_cache = scan_pdf_for_fields(scan_fields)
    grouped = {}
    for match in raw_matches:
        grouped.setdefault(match["field"], []).append(match)

    ocr_plan = plan_selective_ocr(scan_fields, grouped, year, keyword_hits)
    ocr_field_names = ocr_plan["ocr_field_names"]
    ocr_pages = ocr_plan["ocr_pages"]
    ocr_reasons = ocr_plan["ocr_reasons"]
    ocr_triggered_fields = sorted(ocr_field_names)

    if ocr_field_names and ocr_pages and fitz is not None and ocr_available():
        print(
            f"Selective OCR on {len(ocr_pages)} pages for {len(ocr_field_names)} fields.",
            file=sys.stderr,
        )
        try:
            ocr_fields = [f for f in scan_fields if f.get("name") in ocr_field_names]
            ocr_cache = {}
            pages = iter_pages_ocr_selected(
                final_pdf_path, ocr_pages, max_pages=args.max_pages, cache=ocr_cache
            )
            ocr_matches = extract_fields(
                pages, ocr_fields, scan_keywords=None, source="ocr"
            )
        except Exception as exc:
            print(f"OCR fallback skipped: {exc}", file=sys.stderr)
            ocr_matches = []
            for field_name in ocr_field_names:
                base_reason = (ocr_reasons.get(field_name) or "").strip()
                if base_reason:
                    ocr_reasons[field_name] = f"{base_reason}; OCR skipped: {exc}"
                else:
                    ocr_reasons[field_name] = f"OCR skipped: {exc}"
        if ocr_matches:
            raw_matches.extend(ocr_matches)
            grouped = {}
            for match in raw_matches:
                grouped.setdefault(match["field"], []).append(match)
    elif ocr_field_names and not ocr_pages:
        for field_name in ocr_field_names:
            base_reason = (ocr_reasons.get(field_name) or "").strip()
            if base_reason:
                ocr_reasons[field_name] = f"{base_reason}; no keyword pages"
            else:
                ocr_reasons[field_name] = "no keyword pages"
    elif ocr_field_names and not ocr_available():
        for field_name in ocr_field_names:
            base_reason = (ocr_reasons.get(field_name) or "").strip()
            if base_reason:
                ocr_reasons[field_name] = f"{base_reason}; OCR unavailable"
            else:
                ocr_reasons[field_name] = "OCR unavailable"

    missing_fallback = [
        name
        for name in (
            "Non-Performing Loan Ratio (NPL)",
            "Provision Coverage Ratio (PCR)",
            "Credit Rating (CR)",
        )
        if not grouped.get(name)
    ]
    if missing_fallback and fitz is not None and ocr_available():
        low_text_pages = [
            page_num
            for page_num, text in (page_text_cache or {}).items()
            if len(normalize_text(text)) < 30
        ]
        if low_text_pages:
            print(
                f"OCR fallback on {len(low_text_pages)} low-text pages for {', '.join(missing_fallback)}.",
                file=sys.stderr,
            )
            try:
                ocr_fields = [f for f in scan_fields if f.get("name") in missing_fallback]
                ocr_cache = {}
                pages = iter_pages_ocr_selected(
                    final_pdf_path,
                    sorted(low_text_pages),
                    max_pages=args.max_pages,
                    cache=ocr_cache,
                )
                ocr_matches = extract_fields(
                    pages, ocr_fields, scan_keywords=None, source="ocr"
                )
            except Exception as exc:
                print(
                    f"OCR fallback for low-text pages skipped: {exc}",
                    file=sys.stderr,
                )
                ocr_matches = []
            if ocr_matches:
                raw_matches.extend(ocr_matches)
                grouped = {}
                for match in raw_matches:
                    grouped.setdefault(match["field"], []).append(match)

    best_matches = {}
    field_metadata = {}
    total_score = 0
    for field_name in FIELD_ORDER:
        if scan_field_names and field_name not in scan_field_names:
            continue
        matches = grouped.get(field_name, [])
        best, confidence, winning_source, winning_reason, _ = (
            select_best_match_with_confidence(field_name, matches, year)
        )
        if field_name == "Credit Rating (CR)" and (not best or not best.get("value")):
            fallback = fallback_credit_rating_from_pdf(
                final_pdf_path, args.max_pages, year, page_text_cache=page_text_cache
            )
            if fallback:
                best = {
                    "field": field_name,
                    "value": fallback.get("value"),
                    "page": fallback.get("page"),
                    "line": None,
                    "line_text": "credit-rating fallback extractor",
                    "context_text": "",
                    "value_span": None,
                    "value_index": 0,
                    "value_count": 1,
                    "value_year": str(year) if year else None,
                    "value_column": None,
                    "raw_value": fallback.get("value"),
                    "source": "fallback",
                }
                confidence = 0.78
                winning_source = "fallback"
                winning_reason = "fallback table/section parser"
        best_matches[field_name] = best
        field_metadata[field_name] = {
            "confidence": confidence,
            "winning_source": winning_source,
            "winning_reason": winning_reason,
            "ocr_reason": ocr_reasons.get(field_name),
        }
        value = best["value"] if best else None
        score = score_field_value(field_name, value)
        if score is not None:
            total_score += score
    if eligibility_only:
        return {
            "bank": output_bank,
            "year": year,
            "values": {k: (v["value"] if v else None) for k, v in best_matches.items()},
            "matches": best_matches,
            "pdf_path": final_pdf_path,
            "pdf_url": pdf_url,
        }
    summary_row = build_summary_row(
        output_bank,
        {k: v["value"] if v else None for k, v in best_matches.items()},
        total_score,
    )
    developer_rows = build_developer_rows(
        output_bank,
        year,
        source_url,
        source_type,
        best_matches,
        total_score,
        field_metadata=field_metadata,
        ocr_triggered_fields=ocr_triggered_fields,
    )
    print(f"Total score: {total_score} (expected 100)")
    return {
        "bank": output_bank,
        "year": year,
        "summary_row": summary_row,
        "developer_rows": developer_rows,
    }


# --- CLI entrypoint ---
def main():
    parser = argparse.ArgumentParser(description="Annual report PDF scraper")
    parser.add_argument("--pdf-url", help="Direct PDF URL")
    parser.add_argument("--pdf-path", help="Use a local PDF path instead of downloading")
    parser.add_argument("--bank", help="Bank name from config/bank_seeds.json")
    parser.add_argument("--year", type=int, help="Target year for crawler scoring")
    parser.add_argument("--fields", default="config/fields.json", help="Fields config JSON")
    parser.add_argument("--banks", default="config/bank_seeds.json", help="Bank seeds JSON")
    parser.add_argument("--output", help="Excel output path for single run")
    parser.add_argument(
        "--output-dir",
        default="eligible_output",
        help="Directory for output files (batch or default naming)",
    )
    parser.add_argument(
        "--no-output",
        action="store_true",
        help="Skip writing eligibility XLSX output files",
    )
    parser.add_argument(
        "--download-dir", default="eligible_downloads", help="PDF download directory"
    )
    parser.add_argument("--max-pages", type=int, help="Max PDF pages to scan")
    parser.add_argument("--scan-keywords", nargs="*", help="Only scan pages that contain these keywords")
    parser.add_argument("--max-crawl-pages", type=int, default=200, help="Crawler page limit")
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="HTTP timeout seconds for crawl requests",
    )
    parser.add_argument(
        "--download-timeout",
        type=int,
        default=120,
        help="PDF download timeout seconds",
    )
    parser.add_argument(
        "--sources",
        default="config/sources.json",
        help="Sources JSON for batch runs",
    )

    args = parser.parse_args()

    fields_cfg = read_json(args.fields)
    fields = fields_cfg.get("fields", [])
    if not fields:
        print("No fields configured in config/fields.json", file=sys.stderr)
        return 2

    eligibility_fields = [
        field
        for field in fields
        if field.get("name")
        in (
            "Non-Performing Loan Ratio (NPL)",
            "Provision Coverage Ratio (PCR)",
            "Credit Rating (CR)",
        )
    ]
    if not eligibility_fields:
        print("Eligibility fields missing from config/fields.json", file=sys.stderr)
        return 2

    eligibility_columns = [
        "Bank Name",
        "Non Performing Loan Ratio",
        "NPL Page",
        "Provision Coverage Ratio",
        "PCR Page",
        "Credit Rating",
        "Credit Rating Page",
    ]

    def run_single(
        pdf_url,
        pdf_path,
        bank_name,
        year,
        fields_override=None,
        eligibility_only=False,
    ):
        return run_single_with_config(
            args,
            fields,
            pdf_url,
            pdf_path,
            bank_name,
            year,
            fields_override=fields_override,
            eligibility_only=eligibility_only,
        )

    if args.pdf_url or args.pdf_path or args.bank:
        print(f"Eligibility scan: {args.bank} {args.year}")
        eligibility = None
        scan_ok = True
        try:
            eligibility = run_single(
                args.pdf_url,
                args.pdf_path,
                args.bank,
                args.year,
                fields_override=eligibility_fields,
                eligibility_only=True,
            )
            if isinstance(eligibility, int):
                raise RuntimeError("Eligibility scan failed")
            bank_label = args.bank or eligibility.get("bank")
            values = eligibility.get("values", {})
            matches = eligibility.get("matches", {})
            npl_match = matches.get("Non-Performing Loan Ratio (NPL)")
            pcr_match = matches.get("Provision Coverage Ratio (PCR)")
            rating_match = matches.get("Credit Rating (CR)")
            npl_value = values.get("Non-Performing Loan Ratio (NPL)")
            pcr_value = values.get("Provision Coverage Ratio (PCR)")
            rating_value = values.get("Credit Rating (CR)")
            npl_page = npl_match.get("page") if npl_match else None
            pcr_page = pcr_match.get("page") if pcr_match else None
            rating_page = rating_match.get("page") if rating_match else None
        except Exception as exc:
            print(f"Eligibility scan failed for {args.bank}: {exc}", file=sys.stderr)
            scan_ok = False
            bank_label = args.bank
            npl_value = None
            pcr_value = None
            rating_value = None
            npl_page = None
            pcr_page = None
            rating_page = None
        if pcr_value is None:
            pcr_value = ""
        if npl_value is None:
            npl_value = ""
        if rating_value is None:
            rating_value = ""
        if scan_ok:
            push_eligibility_to_apex(bank_label, args.year, npl_value, rating_value, pcr=pcr_value)
        else:
            print(f"APEX push skipped for {bank_label} {args.year} due to scan failure.", file=sys.stderr)
        print(
            f"Eligibility result: {bank_label} | NPL={npl_value} (p{npl_page}) | "
            f"PCR={pcr_value} (p{pcr_page}) | CR={rating_value} (p{rating_page})"
        )
        pdf_path = (eligibility.get("pdf_path") if isinstance(eligibility, dict) else None) or args.pdf_path or args.pdf_url
        npl_score = score_field_value("Non-Performing Loan Ratio (NPL)", npl_value)
        pcr_score = score_field_value("Provision Coverage Ratio (PCR)", pcr_value)
        rating_score = score_field_value("Credit Rating (CR)", rating_value)
        emit_eligibility_data(
            bank_label,
            args.year,
            npl_value,
            npl_page,
            pcr_value,
            pcr_page,
            rating_value,
            rating_page,
            pdf_path,
            npl_score=npl_score,
            pcr_score=pcr_score,
            rating_score=rating_score,
        )
        if not args.no_output:
            eligibility_rows = [
                {
                    "Bank Name": bank_label,
                    "Non Performing Loan Ratio": npl_value,
                    "NPL Page": npl_page,
                    "Provision Coverage Ratio": pcr_value,
                    "PCR Page": pcr_page,
                    "Credit Rating": rating_value,
                    "Credit Rating Page": rating_page,
                }
            ]
            ensure_dir(args.output_dir)
            output_path = (
                args.output
                if args.output
                else os.path.join(args.output_dir, build_eligible_output_name(args.year))
            )
            eligibility_df = pd.DataFrame(eligibility_rows, columns=eligibility_columns)
            save_excel_df(eligibility_df, output_path)
            print(f"Saved eligibility output to {output_path}")
        return 0

    sources = load_sources(args.sources)
    if not sources:
        print("No sources found in sources file", file=sys.stderr)
        return 2
    entries_by_year = {}
    for entry in sources:
        entries_by_year.setdefault(entry.get("year"), []).append(entry)
    for entry_year, entries in entries_by_year.items():
        eligibility_rows = []
        for entry in entries:
            try:
                eligibility = None
                scan_ok = True
                entry_pdf_url = entry.get("pdf_url")
                entry_pdf_path = entry.get("pdf_path")
                entry_bank = entry.get("bank")
                print(f"Eligibility scan: {entry_bank} {entry_year}")
                try:
                    eligibility = run_single(
                        entry_pdf_url,
                        entry_pdf_path,
                        entry_bank,
                        entry_year,
                        fields_override=eligibility_fields,
                        eligibility_only=True,
                    )
                    if isinstance(eligibility, int):
                        raise RuntimeError("Eligibility scan failed")
                    bank_label = entry_bank or eligibility.get("bank")
                    values = eligibility.get("values", {})
                    matches = eligibility.get("matches", {})
                    npl_match = matches.get("Non-Performing Loan Ratio (NPL)")
                    pcr_match = matches.get("Provision Coverage Ratio (PCR)")
                    rating_match = matches.get("Credit Rating (CR)")
                    npl_value = values.get("Non-Performing Loan Ratio (NPL)")
                    pcr_value = values.get("Provision Coverage Ratio (PCR)")
                    rating_value = values.get("Credit Rating (CR)")
                    npl_page = npl_match.get("page") if npl_match else None
                    pcr_page = pcr_match.get("page") if pcr_match else None
                    rating_page = rating_match.get("page") if rating_match else None
                except Exception as exc:
                    print(f"Eligibility scan failed for {entry_bank}: {exc}", file=sys.stderr)
                    scan_ok = False
                    bank_label = entry_bank
                    npl_value = None
                    pcr_value = None
                    rating_value = None
                    npl_page = None
                    pcr_page = None
                    rating_page = None
                if pcr_value is None:
                    pcr_value = ""
                if npl_value is None:
                    npl_value = ""
                if rating_value is None:
                    rating_value = ""
                if scan_ok:
                    push_eligibility_to_apex(bank_label, entry_year, npl_value, rating_value, pcr=pcr_value)
                else:
                    print(f"APEX push skipped for {bank_label} {entry_year} due to scan failure.", file=sys.stderr)
                pdf_path = (eligibility.get("pdf_path") if isinstance(eligibility, dict) else None) or entry_pdf_path or entry_pdf_url
                npl_score = score_field_value("Non-Performing Loan Ratio (NPL)", npl_value)
                pcr_score = score_field_value("Provision Coverage Ratio (PCR)", pcr_value)
                rating_score = score_field_value("Credit Rating (CR)", rating_value)
                emit_eligibility_data(
                    bank_label,
                    entry_year,
                    npl_value,
                    npl_page,
                    pcr_value,
                    pcr_page,
                    rating_value,
                    rating_page,
                    pdf_path,
                    npl_score=npl_score,
                    pcr_score=pcr_score,
                    rating_score=rating_score,
                )
                eligibility_rows.append(
                    {
                        "Bank Name": bank_label,
                        "Non Performing Loan Ratio": npl_value,
                        "NPL Page": npl_page,
                        "Provision Coverage Ratio": pcr_value,
                        "PCR Page": pcr_page,
                        "Credit Rating": rating_value,
                        "Credit Rating Page": rating_page,
                    }
                )
                print(
                    f"Eligibility result: {bank_label} | NPL={npl_value} (p{npl_page}) | "
                    f"PCR={pcr_value} (p{pcr_page}) | CR={rating_value} (p{rating_page})"
                )
                normalized_rating = normalize_credit_rating(rating_value)
                numeric_npl = parse_numeric(npl_value)
                is_eligible = (
                    numeric_npl is not None
                    and numeric_npl < 8
                    and normalized_rating in ("AAA", "AA")
                )
            except Exception as exc:
                print(f"Eligibility pipeline error for {entry.get('bank')} {entry_year}: {exc}", file=sys.stderr)
                continue

        if not args.no_output:
            ensure_dir(args.output_dir)
            eligible_path = os.path.join(
                args.output_dir, build_eligible_output_name(entry_year)
            )
            eligibility_df = pd.DataFrame(eligibility_rows, columns=eligibility_columns)
            save_excel_df(eligibility_df, eligible_path)
            print(f"Saved eligibility output to {eligible_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
