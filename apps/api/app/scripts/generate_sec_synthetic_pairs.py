#!/usr/bin/env python3
"""
Generate Synthetic Embedding Pairs from SEC EDGAR Filings
==========================================================
Uses SEC EDGAR filings to generate 5-10K+ embedding triplets synthetically.

This script:
1. Fetches SEC filings (10-K, 10-Q, 8-K) for major companies
2. Extracts key sections (Risk Factors, MD&A, Financial Statements)
3. Uses Claude/GPT to generate semantically related pairs
4. Creates hard negatives from different companies/filings

Usage:
    python -m app.scripts.generate_sec_synthetic_pairs --count 5000
    python -m app.scripts.generate_sec_synthetic_pairs --tickers "AAPL,MSFT,NVDA" --count 1000
"""

import argparse
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Output directory
EXPORTS_DIR = Path(__file__).parent.parent.parent / "exports"
OUTPUT_FILE = EXPORTS_DIR / "sec_synthetic_triplets.jsonl"

# SEC EDGAR API configuration
SEC_BASE_URL = "https://data.sec.gov"
SEC_HEADERS = {
    "User-Agent": "Finance Intelligence Platform research@example.com",
    "Accept-Encoding": "gzip, deflate",
}

# Major company CIKs for training data
COMPANY_CIKS = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "META": "0001326801",
    "NVDA": "0001045810",
    "TSLA": "0001318605",
    "JPM": "0000019617",
    "JNJ": "0000200406",
    "V": "0001403161",
    "PG": "0000080424",
    "UNH": "0000731766",
    "HD": "0000354950",
    "MA": "0001141391",
    "DIS": "0001001039",
    "BAC": "0000070858",
    "PFE": "0000078003",
    "ABBV": "0001551152",
    "KO": "0000021344",
    "PEP": "0000077476",
    "MRK": "0000310158",
    "COST": "0000909832",
    "TMO": "0000097745",
    "CSCO": "0000858877",
    "AVGO": "0001730168",
    "ACN": "0001467373",
    "ABT": "0000001800",
    "WMT": "0000104169",
    "LLY": "0000059478",
    "AMD": "0000002488",
    "INTC": "0000050863",
    "ORCL": "0001341439",
    "IBM": "0000051143",
    "QCOM": "0000804328",
    "TXN": "0000097476",
    "GS": "0000886982",
    "MS": "0000895421",
    "C": "0000831001",
    "WFC": "0000072971",
    "BLK": "0001364742",
    "LMT": "0000936468",
    "RTX": "0000101829",
    "BA": "0000012927",
    "NOC": "0001133421",
    "GD": "0000040533",
    "XOM": "0000034088",
    "CVX": "0000093410",
    "COP": "0001163165",
    "NEE": "0000753308",
    "DUK": "0001326160",
}


@dataclass
class EmbeddingTriplet:
    """A training triplet for contrastive embedding learning."""
    anchor: str
    positive: str
    hard_negative: str
    source: str
    entity: str
    triplet_type: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        h = hashlib.md5((self.anchor + self.positive).encode()).hexdigest()[:12]
        return h


def fetch_company_filings(cik: str, form_types: List[str] = None, limit: int = 10) -> List[Dict]:
    """Fetch recent filings for a company from SEC EDGAR."""
    if form_types is None:
        form_types = ["10-K", "10-Q", "8-K"]

    # Pad CIK to 10 digits
    cik_padded = cik.zfill(10)

    url = f"{SEC_BASE_URL}/cgi-bin/browse-edgar?action=getcompany&CIK={cik_padded}&type=&dateb=&owner=include&count={limit}&output=atom"

    try:
        resp = requests.get(url, headers=SEC_HEADERS, timeout=30)
        resp.raise_for_status()

        # Parse XML response (simplified)
        filings = []
        # This is a simplified parser - in production use proper XML parsing
        for form_type in form_types:
            # Get submissions JSON
            submissions_url = f"{SEC_BASE_URL}/cgi-bin/browse-edgar?action=getcompany&CIK={cik_padded}&type={form_type}&dateb=&owner=include&count={limit}&output=atom"
            resp = requests.get(submissions_url, headers=SEC_HEADERS, timeout=30)
            if resp.status_code == 200:
                # Parse entries from atom feed
                entries = re.findall(r'<entry>(.*?)</entry>', resp.text, re.DOTALL)
                for entry in entries[:limit]:
                    title_match = re.search(r'<title[^>]*>(.*?)</title>', entry)
                    link_match = re.search(r'<link[^>]*href="([^"]*)"', entry)
                    date_match = re.search(r'<updated>(.*?)</updated>', entry)

                    if title_match and link_match:
                        filings.append({
                            "form_type": form_type,
                            "title": title_match.group(1),
                            "url": link_match.group(1),
                            "date": date_match.group(1) if date_match else "",
                        })

        return filings[:limit]

    except Exception as e:
        logger.warning(f"Failed to fetch filings for CIK {cik}: {e}")
        return []


def fetch_filing_text(filing_url: str, max_chars: int = 50000) -> str:
    """Fetch and extract text from a filing."""
    try:
        # Get the filing index page
        resp = requests.get(filing_url, headers=SEC_HEADERS, timeout=30)
        resp.raise_for_status()

        # Find the main document link (usually .htm or .txt)
        doc_links = re.findall(r'href="([^"]*(?:\.htm|\.txt)[^"]*)"', resp.text)

        for doc_link in doc_links[:3]:
            if not doc_link.startswith("http"):
                # Construct full URL
                base_url = filing_url.rsplit("/", 1)[0]
                doc_url = f"{base_url}/{doc_link}"
            else:
                doc_url = doc_link

            # Fetch document
            doc_resp = requests.get(doc_url, headers=SEC_HEADERS, timeout=60)
            if doc_resp.status_code == 200:
                text = doc_resp.text

                # Strip HTML tags
                text = re.sub(r'<[^>]+>', ' ', text)
                # Normalize whitespace
                text = re.sub(r'\s+', ' ', text).strip()

                if len(text) > 1000:
                    return text[:max_chars]

        return ""

    except Exception as e:
        logger.warning(f"Failed to fetch filing text: {e}")
        return ""


def extract_sections(text: str) -> Dict[str, str]:
    """Extract key sections from filing text."""
    sections = {}

    # Common section patterns
    section_patterns = [
        (r"(?i)ITEM\s*1A[\.\s]*RISK\s*FACTORS(.*?)(?=ITEM\s*1B|ITEM\s*2|$)", "risk_factors"),
        (r"(?i)ITEM\s*7[\.\s]*MANAGEMENT.S DISCUSSION(.*?)(?=ITEM\s*7A|ITEM\s*8|$)", "mda"),
        (r"(?i)ITEM\s*1[\.\s]*BUSINESS(.*?)(?=ITEM\s*1A|ITEM\s*2|$)", "business"),
        (r"(?i)ITEM\s*8[\.\s]*FINANCIAL\s*STATEMENTS(.*?)(?=ITEM\s*9|$)", "financials"),
        (r"(?i)EXECUTIVE\s*SUMMARY(.*?)(?=\n\n|\Z)", "executive_summary"),
    ]

    for pattern, name in section_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            section_text = match.group(1).strip()
            if len(section_text) > 200:
                sections[name] = section_text[:10000]

    return sections


def generate_triplets_from_section(
    section_text: str,
    section_type: str,
    entity: str,
    other_sections: List[Tuple[str, str, str]],  # (text, type, entity)
) -> List[EmbeddingTriplet]:
    """Generate triplets from a section using sentence splitting."""
    triplets = []

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', section_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 50 and len(s.strip()) < 500]

    if len(sentences) < 3:
        return triplets

    # Generate triplets by pairing adjacent sentences (anchor, positive)
    # with sentences from different entities (hard negative)
    for i in range(len(sentences) - 1):
        anchor = sentences[i]
        positive = sentences[i + 1]

        # Find hard negative from other companies
        for other_text, other_type, other_entity in other_sections:
            if other_entity != entity and other_type == section_type:
                other_sentences = re.split(r'(?<=[.!?])\s+', other_text)
                other_sentences = [s.strip() for s in other_sentences if len(s.strip()) > 50]
                if other_sentences:
                    hard_negative = random.choice(other_sentences[:20])

                    triplets.append(EmbeddingTriplet(
                        anchor=anchor[:400],
                        positive=positive[:400],
                        hard_negative=hard_negative[:400],
                        source=f"sec:{entity}:{section_type}",
                        entity=entity,
                        triplet_type=f"sec_{section_type}",
                    ))
                    break

    return triplets[:50]  # Limit per section


def generate_synthetic_pairs_with_llm(
    texts: List[Tuple[str, str, str]],  # (text, section_type, entity)
    count: int = 1000,
) -> List[EmbeddingTriplet]:
    """Generate synthetic pairs using LLM (Claude/GPT)."""
    triplets = []

    try:
        import anthropic
        client = anthropic.Anthropic()
        use_anthropic = True
    except:
        try:
            import openai
            client = openai.OpenAI()
            use_anthropic = False
        except:
            logger.warning("No LLM client available, skipping LLM-based generation")
            return triplets

    # Group texts by section type
    by_type: Dict[str, List[Tuple[str, str]]] = {}
    for text, section_type, entity in texts:
        by_type.setdefault(section_type, []).append((text, entity))

    pairs_per_type = count // max(len(by_type), 1)

    for section_type, type_texts in by_type.items():
        logger.info(f"Generating {pairs_per_type} pairs for section type: {section_type}")

        for text, entity in type_texts[:10]:  # Limit texts per type
            # Prepare prompt for LLM
            prompt = f"""Given this excerpt from a {section_type} section of an SEC filing for {entity}:

"{text[:2000]}"

Generate 5 training examples for an embedding model. Each example should have:
1. anchor: A sentence or claim from the text
2. positive: A semantically related sentence (paraphrase or related fact)
3. hard_negative: A similar-looking but semantically different statement

Output as JSON array:
[{{"anchor": "...", "positive": "...", "hard_negative": "..."}}]

Focus on financial metrics, risks, business strategy, and regulatory matters."""

            try:
                if use_anthropic:
                    response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=2000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    content = response.content[0].text
                else:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        max_tokens=2000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    content = response.choices[0].message.content

                # Parse JSON response
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    pairs = json.loads(json_match.group())
                    for pair in pairs:
                        triplets.append(EmbeddingTriplet(
                            anchor=pair.get("anchor", "")[:400],
                            positive=pair.get("positive", "")[:400],
                            hard_negative=pair.get("hard_negative", "")[:400],
                            source=f"sec_synthetic:{entity}:{section_type}",
                            entity=entity,
                            triplet_type=f"sec_{section_type}_synthetic",
                        ))

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                logger.warning(f"LLM generation failed: {e}")
                continue

            if len(triplets) >= count:
                break

    return triplets[:count]


def main():
    parser = argparse.ArgumentParser(description="Generate SEC EDGAR synthetic pairs")
    parser.add_argument("--count", type=int, default=5000,
                        help="Target number of triplets to generate")
    parser.add_argument("--tickers", type=str, default=None,
                        help="Comma-separated tickers (default: all)")
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE,
                        help="Output JSONL file")
    parser.add_argument("--use-llm", action="store_true",
                        help="Use LLM for synthetic generation (costs $)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)

    # Determine which companies to process
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
        ciks = {t: COMPANY_CIKS[t] for t in tickers if t in COMPANY_CIKS}
    else:
        ciks = COMPANY_CIKS

    logger.info(f"Processing {len(ciks)} companies for SEC filings")

    # Collect sections from all companies
    all_sections: List[Tuple[str, str, str]] = []  # (text, type, entity)

    for ticker, cik in ciks.items():
        logger.info(f"Fetching filings for {ticker} (CIK: {cik})")

        filings = fetch_company_filings(cik, form_types=["10-K", "10-Q"], limit=3)

        for filing in filings[:2]:  # Limit filings per company
            logger.info(f"  Processing {filing['form_type']}: {filing['title']}")

            # Fetch and extract sections
            text = fetch_filing_text(filing["url"])
            if text:
                sections = extract_sections(text)
                for section_type, section_text in sections.items():
                    all_sections.append((section_text, section_type, ticker))

            # Rate limiting for SEC API
            time.sleep(0.2)

    logger.info(f"Collected {len(all_sections)} sections from SEC filings")

    # Generate triplets
    all_triplets: List[EmbeddingTriplet] = []

    # Method 1: Generate from sentence pairs
    logger.info("Generating triplets from sentence pairs...")
    for text, section_type, entity in all_sections:
        other_sections = [(t, st, e) for t, st, e in all_sections if e != entity]
        triplets = generate_triplets_from_section(text, section_type, entity, other_sections)
        all_triplets.extend(triplets)

    logger.info(f"Generated {len(all_triplets)} triplets from sentence pairs")

    # Method 2: Use LLM for synthetic generation (optional)
    if args.use_llm and len(all_triplets) < args.count:
        remaining = args.count - len(all_triplets)
        logger.info(f"Generating {remaining} additional triplets with LLM...")
        llm_triplets = generate_synthetic_pairs_with_llm(all_sections, count=remaining)
        all_triplets.extend(llm_triplets)
        logger.info(f"Total triplets after LLM: {len(all_triplets)}")

    # Deduplicate
    seen = set()
    unique_triplets = []
    for t in all_triplets:
        fp = t.fingerprint()
        if fp not in seen:
            seen.add(fp)
            unique_triplets.append(t)

    logger.info(f"After deduplication: {len(unique_triplets)} unique triplets")

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        for t in unique_triplets:
            f.write(json.dumps(t.to_dict()) + "\n")

    logger.info(f"Wrote {len(unique_triplets)} triplets to {args.output}")

    # Summary by type
    by_type: Dict[str, int] = {}
    for t in unique_triplets:
        by_type[t.triplet_type] = by_type.get(t.triplet_type, 0) + 1

    logger.info("Triplets by type:")
    for ttype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        logger.info(f"  {ttype}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
