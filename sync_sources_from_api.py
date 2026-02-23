import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests

DEFAULT_API_URL = "http://103.163.96.251:8282/ords/cpa_invst/banks/sources"
DEFAULT_SOURCES_PATH = Path("config/sources.json")


def normalize_space(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def normalize_key(bank: str, year: int, pdf_url: str) -> Tuple[str, int, str]:
    return (
        normalize_space(bank).casefold(),
        int(year),
        normalize_space(pdf_url).casefold(),
    )


def extract_list_payload(payload: object) -> List[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "data", "rows", "result", "sources", "banks"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def pick_first(record: dict, keys: Iterable[str]) -> Optional[object]:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_item(item: dict) -> Optional[Dict[str, object]]:
    bank = pick_first(item, ("bank", "bank_name", "bankName", "name"))
    year = pick_first(item, ("year", "fiscal_year", "fiscalYear"))
    pdf_url = pick_first(item, ("pdf_url", "pdfUrl", "url", "link"))

    bank_text = normalize_space(bank)
    url_text = normalize_space(pdf_url)
    if not bank_text or not url_text:
        return None
    try:
        year_int = int(str(year).strip())
    except Exception:
        return None

    return {"bank": bank_text, "year": year_int, "pdf_url": url_text}


def fetch_json(session: requests.Session, url: str, timeout: int) -> dict:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("API response is not a JSON object")
    return payload


def resolve_next_url(base_url: str, payload: dict) -> Optional[str]:
    links = payload.get("links")
    if isinstance(links, list):
        for entry in links:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("rel", "")).lower() == "next" and entry.get("href"):
                return str(entry["href"])
    has_more = bool(payload.get("hasMore"))
    if not has_more:
        return None
    try:
        limit = int(payload.get("limit", 0))
        offset = int(payload.get("offset", 0))
    except Exception:
        return None
    if limit <= 0:
        return None
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}offset={offset + limit}"


def fetch_all_sources(api_url: str, timeout: int) -> List[Dict[str, object]]:
    session = requests.Session()
    session.trust_env = False

    raw_items: List[dict] = []
    next_url: Optional[str] = api_url
    visited = set()

    while next_url and next_url not in visited:
        visited.add(next_url)
        payload = fetch_json(session, next_url, timeout=timeout)
        raw_items.extend(extract_list_payload(payload))
        next_url = resolve_next_url(api_url, payload)

    normalized: List[Dict[str, object]] = []
    for item in raw_items:
        record = normalize_item(item)
        if record:
            normalized.append(record)
    return normalized


def load_sources(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return []
    sources = payload.get("sources")
    if not isinstance(sources, list):
        return []
    normalized: List[Dict[str, object]] = []
    for row in sources:
        if not isinstance(row, dict):
            continue
        record = normalize_item(row)
        if record:
            normalized.append(record)
    return normalized


def save_sources(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"sources": rows}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def merge_sources(existing: List[Dict[str, object]], incoming: List[Dict[str, object]]) -> Tuple[List[Dict[str, object]], int]:
    merged = list(existing)
    existing_keys = set()
    for row in existing:
        existing_keys.add(normalize_key(row["bank"], int(row["year"]), row["pdf_url"]))

    inserted = 0
    for row in incoming:
        key = normalize_key(row["bank"], int(row["year"]), row["pdf_url"])
        if key in existing_keys:
            continue
        merged.append(row)
        existing_keys.add(key)
        inserted += 1
    return merged, inserted


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch bank PDF sources from API and append non-duplicate records to config/sources.json."
    )
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Source API URL")
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES_PATH), help="Path to sources.json")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Show results without writing file")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    sources_path = Path(args.sources)

    existing = load_sources(sources_path)
    incoming = fetch_all_sources(args.api_url, timeout=args.timeout)
    merged, inserted = merge_sources(existing, incoming)

    if args.dry_run:
        print(
            f"[DRY-RUN] fetched={len(incoming)} existing={len(existing)} inserted={inserted} final={len(merged)}"
        )
        return 0

    save_sources(sources_path, merged)
    print(f"Fetched: {len(incoming)}")
    print(f"Existing: {len(existing)}")
    print(f"Inserted: {inserted}")
    print(f"Final total: {len(merged)}")
    print(f"Updated file: {sources_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
