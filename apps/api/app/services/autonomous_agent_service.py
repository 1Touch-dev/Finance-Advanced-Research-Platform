"""
Autonomous Agent Service (J6)
Auto-discover subsidiaries/family entities using real SEC EDGAR filings
and the Entity Graph Store.

Real data sources:
- SEC EDGAR Exhibit 21 (10-K/20-F) for subsidiaries
- SEC EDGAR DEF 14A proxy statements for board members/executives
- SEC Form 4 for insider transactions and executive identification
- Entity Graph Store for relationship traversal
"""
import logging
import re
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from html import unescape

from app.services.entity_graph_service import (
    get_graph_store,
    get_recursion_engine,
    RecursionConfig,
    ConfidenceTier,
    RelationshipType,
    EntityNode,
    Edge,
    EvidenceRef,
)
from app.services import graph_ingestion_service
from app.connectors.sec_edgar_connector import (
    get_filer_cik,
    get_company_submissions,
    get_insider_transactions,
    find_latest_filing,
    find_latest_annual_filing,
    is_foreign_private_issuer,
)
from app.connectors.sec_http import sec_get_text

log = logging.getLogger(__name__)

_JOBS: Dict[str, Dict] = {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEC EDGAR FILING PARSERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _parse_exhibit_21_subsidiaries(html_text: str) -> List[Dict[str, Any]]:
    """
    Parse Exhibit 21 (Subsidiaries of the Registrant) from SEC filing.

    Exhibit 21 lists all significant subsidiaries with:
    - Subsidiary name
    - Jurisdiction of incorporation

    Format varies but typically a table or list.
    """
    subsidiaries = []
    if not html_text:
        return subsidiaries

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")

        # Remove scripts and styles
        for tag in soup(["script", "style"]):
            tag.decompose()

        # Look for table rows (most common format)
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 1:
                    # First cell is typically the subsidiary name
                    name = cells[0].get_text(strip=True)
                    name = unescape(name)

                    # Skip headers and empty rows
                    if not name or len(name) < 3:
                        continue
                    if any(kw in name.lower() for kw in [
                        "name of subsidiary", "subsidiary", "jurisdiction",
                        "exhibit", "incorporated", "state of"
                    ]) and len(name) < 30:
                        continue

                    # Extract jurisdiction if present
                    jurisdiction = ""
                    if len(cells) >= 2:
                        jurisdiction = cells[1].get_text(strip=True)
                        jurisdiction = unescape(jurisdiction)

                    # Clean up common artifacts
                    name = re.sub(r'\s+', ' ', name).strip()
                    name = re.sub(r'^\d+[.\)]\s*', '', name)  # Remove numbering

                    if len(name) > 3 and len(name) < 200:
                        subsidiaries.append({
                            "name": name,
                            "jurisdiction": jurisdiction,
                        })

        # If no tables, try parsing as plain text with patterns
        if not subsidiaries:
            text = soup.get_text("\n", strip=True)
            # Look for lines with jurisdiction indicators
            lines = text.split("\n")
            for line in lines:
                line = line.strip()
                # Pattern: "Company Name (Delaware)" or "Company Name - Delaware"
                match = re.match(
                    r'^(.+?)\s*[\(\-]\s*(Delaware|California|Nevada|Texas|'
                    r'New York|Florida|Massachusetts|Virginia|Illinois|'
                    r'Maryland|Georgia|Washington|Colorado|Oregon|'
                    r'United Kingdom|Ireland|Netherlands|Luxembourg|'
                    r'Cayman Islands|British Virgin Islands|Hong Kong|'
                    r'Singapore|Japan|Germany|France|Switzerland|Canada|'
                    r'Australia)[^\)]*[\)\s]*$',
                    line, re.I
                )
                if match:
                    name = match.group(1).strip()
                    jurisdiction = match.group(2).strip()
                    if len(name) > 3 and len(name) < 200:
                        subsidiaries.append({
                            "name": name,
                            "jurisdiction": jurisdiction,
                        })

    except ImportError:
        log.warning("BeautifulSoup not available for Exhibit 21 parsing")
    except Exception as e:
        log.warning("Error parsing Exhibit 21: %s", e)

    # Deduplicate by name
    seen = set()
    unique = []
    for sub in subsidiaries:
        key = sub["name"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(sub)

    return unique


def _parse_def14a_executives(html_text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parse DEF 14A proxy statement for executives and board members.

    DEF 14A contains:
    - Named Executive Officers (NEOs) in compensation tables
    - Board of Directors nominees and current members
    - Committee memberships

    Returns:
        (executives, board_members)
    """
    executives = []
    board_members = []

    if not html_text:
        return executives, board_members

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")

        # Remove scripts and styles
        for tag in soup(["script", "style"]):
            tag.decompose()

        text = soup.get_text("\n", strip=True)

        # Common executive titles to look for
        exec_titles = [
            "Chief Executive Officer", "CEO",
            "Chief Financial Officer", "CFO",
            "Chief Operating Officer", "COO",
            "Chief Technology Officer", "CTO",
            "President",
            "Executive Vice President", "EVP",
            "Senior Vice President", "SVP",
            "Vice President",
            "General Counsel",
            "Secretary",
            "Treasurer",
        ]

        # Board-related keywords
        board_keywords = [
            "Director", "Chairman", "Chair of the Board",
            "Independent Director", "Lead Independent Director",
            "Audit Committee", "Compensation Committee",
            "Nominating Committee", "Governance Committee",
        ]

        # Look for Summary Compensation Table (contains NEOs)
        # Pattern: "Name and Principal Position" followed by compensation data
        lines = text.split("\n")
        in_compensation_section = False
        in_directors_section = False

        for i, line in enumerate(lines):
            line = line.strip()

            # Detect sections
            if "summary compensation" in line.lower():
                in_compensation_section = True
                in_directors_section = False
            elif any(kw in line.lower() for kw in [
                "board of directors", "director nominees",
                "election of directors", "directors continuing"
            ]):
                in_compensation_section = False
                in_directors_section = True
            elif "proposal" in line.lower() and len(line) < 50:
                in_compensation_section = False
                in_directors_section = False

            # Extract executives from compensation section
            if in_compensation_section:
                for title in exec_titles:
                    if title.lower() in line.lower():
                        # Try to extract name (usually before the title or on previous line)
                        name = None
                        if i > 0:
                            prev_line = lines[i-1].strip()
                            # Check if previous line looks like a name
                            if (2 <= len(prev_line.split()) <= 4 and
                                    not any(c.isdigit() for c in prev_line) and
                                    len(prev_line) < 50):
                                name = prev_line

                        if not name:
                            # Try to extract name from the line itself
                            parts = re.split(r',\s*|\s+(?=' + re.escape(title) + r')', line, 1)
                            if parts and len(parts[0].split()) <= 4:
                                name = parts[0].strip()

                        if name and len(name) > 3:
                            # Clean name
                            name = re.sub(r'\(\d+\)', '', name).strip()
                            name = re.sub(r'\s+', ' ', name)

                            if not any(e["name"].lower() == name.lower() for e in executives):
                                executives.append({
                                    "name": name,
                                    "title": title,
                                    "source": "DEF 14A Compensation Table",
                                })
                        break

            # Extract board members from directors section
            if in_directors_section:
                for kw in board_keywords:
                    if kw.lower() in line.lower():
                        # Look for name patterns
                        # Directors are often listed as "John Smith, age 65, has served..."
                        match = re.match(
                            r'^([A-Z][a-z]+(?:\s+[A-Z]\.?\s+)?[A-Z][a-z]+)'
                            r'(?:,?\s+(?:age\s+)?\d+)?',
                            line
                        )
                        if match:
                            name = match.group(1).strip()
                            if (len(name) > 3 and len(name.split()) >= 2 and
                                    not any(b["name"].lower() == name.lower()
                                            for b in board_members)):
                                board_members.append({
                                    "name": name,
                                    "role": kw if "Director" in kw else "Director",
                                    "source": "DEF 14A Directors Section",
                                })
                        break

        # Also search tables for directors
        tables = soup.find_all("table")
        for table in tables:
            header_row = table.find("tr")
            if header_row:
                header_text = header_row.get_text(" ", strip=True).lower()
                if any(kw in header_text for kw in ["director", "nominee", "board"]):
                    rows = table.find_all("tr")[1:]  # Skip header
                    for row in rows:
                        cells = row.find_all(["td", "th"])
                        if cells:
                            name = cells[0].get_text(strip=True)
                            name = unescape(name)
                            name = re.sub(r'\s+', ' ', name).strip()

                            if (len(name) > 3 and len(name.split()) >= 2 and
                                    len(name) < 50 and
                                    not any(c.isdigit() for c in name)):
                                if not any(b["name"].lower() == name.lower()
                                           for b in board_members):
                                    board_members.append({
                                        "name": name,
                                        "role": "Director",
                                        "source": "DEF 14A Directors Table",
                                    })

    except ImportError:
        log.warning("BeautifulSoup not available for DEF 14A parsing")
    except Exception as e:
        log.warning("Error parsing DEF 14A: %s", e)

    return executives, board_members


def _fetch_exhibit_21_content(cik: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch Exhibit 21 content from SEC EDGAR.

    Returns:
        (exhibit_content, source_url)
    """
    # Find the latest annual report (10-K or 20-F for FPIs)
    filing = find_latest_annual_filing(cik)
    if not filing:
        return None, None

    base_url = filing.get("base_url", "")
    if not base_url:
        return None, None

    # Get the filing summary to find Exhibit 21
    summary_url = f"{base_url}/FilingSummary.xml"
    summary = sec_get_text(summary_url)
    if not summary:
        return None, None

    # Find Exhibit 21 in the filing
    ex21_file = None
    for match in re.finditer(
        r'<Report[^>]*>.*?<LongName>([^<]*21[^<]*)</LongName>.*?'
        r'<HtmlFileName>([^<]+)</HtmlFileName>.*?</Report>',
        summary, re.S | re.I
    ):
        name = match.group(1)
        if "subsidiaries" in name.lower() or "exhibit 21" in name.lower():
            ex21_file = match.group(2)
            break

    # Also try common naming patterns
    if not ex21_file:
        for pattern in [
            r'<HtmlFileName>(ex21[^<]*\.htm[l]?)</HtmlFileName>',
            r'<HtmlFileName>([^<]*ex-?21[^<]*\.htm[l]?)</HtmlFileName>',
            r'<HtmlFileName>([^<]*exhibit21[^<]*\.htm[l]?)</HtmlFileName>',
        ]:
            match = re.search(pattern, summary, re.I)
            if match:
                ex21_file = match.group(1)
                break

    if not ex21_file:
        return None, None

    # Fetch the exhibit content
    exhibit_url = f"{base_url}/{ex21_file}"
    content = sec_get_text(exhibit_url)
    return content, exhibit_url


def _fetch_def14a_content(cik: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch DEF 14A proxy statement content from SEC EDGAR.

    Returns:
        (proxy_content, source_url)
    """
    filing = find_latest_filing(cik, "DEF 14A")
    if not filing:
        return None, None

    base_url = filing.get("base_url", "")
    primary_doc = filing.get("primary_document", "")

    if not base_url or not primary_doc:
        return None, None

    doc_url = f"{base_url}/{primary_doc}"
    content = sec_get_text(doc_url)
    return content, doc_url


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENTITY RESOLUTION AND GRAPH HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _resolve_entity_id_for_ticker(ticker: str) -> Optional[str]:
    """Resolve a ticker to its graph entity ID, checking multiple schemes."""
    store = get_graph_store()
    store._ensure_loaded()

    # Try resolving by ticker identifier
    entity = store.resolve_entity("ticker", ticker.upper())
    if entity:
        return entity.id

    # Try CIK-based ID (how graph_ingestion_service creates org entities)
    cik = get_filer_cik(ticker)
    if cik:
        entity = store.resolve_entity("CIK", cik)
        if entity:
            return entity.id
        # Convention used by graph_ingestion_service
        candidate = f"org:sec-{cik.zfill(10)}"
        if store.get_entity(candidate):
            return candidate

    # Scan entities for matching ticker in identifiers
    for eid, ent in store._entities.items():
        if ent.identifiers.get("ticker", "").upper() == ticker.upper():
            return eid

    return None


def _normalize_name_for_id(name: str) -> str:
    """Normalize a name to create an ID-safe string."""
    clean = re.sub(r'[^\w\s-]', '', name.lower())
    clean = re.sub(r'[\s_]+', '-', clean)
    return clean.strip('-')


def _add_subsidiary_to_graph(
    parent_entity_id: str,
    subsidiary_name: str,
    jurisdiction: str,
    source_url: str,
    as_of_date: Optional[datetime] = None,
) -> Optional[str]:
    """
    Add a subsidiary entity and relationship to the graph.

    Returns the subsidiary entity ID if successful.
    """
    store = get_graph_store()
    subsidiary_id = f"org:sub-{_normalize_name_for_id(subsidiary_name)}"

    try:
        # Create or update subsidiary entity
        entity = EntityNode(
            id=subsidiary_id,
            kind="org",
            name=subsidiary_name,
            identifiers={},
            aliases=[],
            meta={
                "jurisdiction": jurisdiction,
                "source": "SEC Exhibit 21",
            },
        )
        store.add_entity(entity)

        # Create subsidiary_of edge
        edge_id = f"edge:{subsidiary_id}-subsidiary_of-{parent_entity_id}"
        evidence = EvidenceRef(
            document_id=f"ex21-{_normalize_name_for_id(subsidiary_name)}",
            source_name="SEC Exhibit 21",
            source_url=source_url,
        )
        edge = Edge(
            id=edge_id,
            src_entity_id=subsidiary_id,
            dst_entity_id=parent_entity_id,
            relationship_type=RelationshipType.SUBSIDIARY_OF.value,
            confidence_tier=ConfidenceTier.CONFIRMED,
            evidence_refs=[evidence],
            as_of=as_of_date,
            source_name="SEC EDGAR",
        )
        store.add_edge(edge)

        return subsidiary_id

    except Exception as e:
        log.debug("Error adding subsidiary %s: %s", subsidiary_name, e)
        return None


def _add_executive_to_graph(
    company_entity_id: str,
    name: str,
    title: str,
    source_url: str,
    as_of_date: Optional[datetime] = None,
) -> Optional[str]:
    """
    Add an executive entity and relationship to the graph.

    Returns the person entity ID if successful.
    """
    store = get_graph_store()
    person_id = f"person:{_normalize_name_for_id(name)}"

    try:
        # Create or update person entity
        entity = EntityNode(
            id=person_id,
            kind="person",
            name=name,
            identifiers={},
            aliases=[],
            meta={
                "title": title,
                "source": "SEC DEF 14A",
            },
        )
        store.add_entity(entity)

        # Create employed_at edge
        edge_id = f"edge:{person_id}-employed_at-{company_entity_id}"
        evidence = EvidenceRef(
            document_id=f"def14a-{_normalize_name_for_id(name)}",
            source_name="SEC DEF 14A",
            source_url=source_url,
        )
        edge = Edge(
            id=edge_id,
            src_entity_id=person_id,
            dst_entity_id=company_entity_id,
            relationship_type=RelationshipType.EMPLOYED_AT.value,
            confidence_tier=ConfidenceTier.CONFIRMED,
            evidence_refs=[evidence],
            as_of=as_of_date,
            source_name="SEC EDGAR",
            meta={"title": title},
        )
        store.add_edge(edge)

        return person_id

    except Exception as e:
        log.debug("Error adding executive %s: %s", name, e)
        return None


def _add_board_member_to_graph(
    company_entity_id: str,
    name: str,
    role: str,
    source_url: str,
    as_of_date: Optional[datetime] = None,
) -> Optional[str]:
    """
    Add a board member entity and relationship to the graph.

    Returns the person entity ID if successful.
    """
    store = get_graph_store()
    person_id = f"person:{_normalize_name_for_id(name)}"

    try:
        # Create or update person entity
        entity = EntityNode(
            id=person_id,
            kind="person",
            name=name,
            identifiers={},
            aliases=[],
            meta={
                "role": role,
                "source": "SEC DEF 14A",
            },
        )
        store.add_entity(entity)

        # Create board_member edge
        edge_id = f"edge:{person_id}-board_member-{company_entity_id}"
        evidence = EvidenceRef(
            document_id=f"def14a-{_normalize_name_for_id(name)}",
            source_name="SEC DEF 14A",
            source_url=source_url,
        )
        edge = Edge(
            id=edge_id,
            src_entity_id=person_id,
            dst_entity_id=company_entity_id,
            relationship_type=RelationshipType.BOARD_MEMBER.value,
            confidence_tier=ConfidenceTier.CONFIRMED,
            evidence_refs=[evidence],
            as_of=as_of_date,
            source_name="SEC EDGAR",
            meta={"role": role},
        )
        store.add_edge(edge)

        return person_id

    except Exception as e:
        log.debug("Error adding board member %s: %s", name, e)
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DISCOVERY JOB MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _run_discovery(job_id: str, ticker: str, depth: int, entity_types: Optional[List[str]]):
    """
    Background worker that performs entity ingestion from real SEC data.

    Steps:
    1. Resolve ticker to CIK
    2. Ingest company from SEC EDGAR
    3. Parse Exhibit 21 for subsidiaries
    4. Parse DEF 14A for executives and board members
    5. Run recursive graph expansion
    """
    job = _JOBS[job_id]
    try:
        job["status"] = "running"
        job["progress"] = {"step": "resolving_cik", "detail": f"Looking up CIK for {ticker}"}

        cik = get_filer_cik(ticker)
        company_name = None
        if cik:
            subs = get_company_submissions(cik)
            company_name = subs.get("name") or ticker
            job["progress"] = {"step": "ingesting_company", "detail": f"Found {company_name}"}
        else:
            job["status"] = "failed"
            job["error"] = f"Could not resolve ticker {ticker} to SEC CIK"
            job["completed_at"] = datetime.utcnow().isoformat() + "Z"
            return

        # Run standard graph ingestion
        job["progress"] = {"step": "graph_ingestion", "detail": "Running entity graph ingestion"}
        result = graph_ingestion_service.ingest_entity_full(
            entity_name=company_name or ticker,
            cik=cik,
            include_sec=True,
            include_fec=True,
            include_contracts=True,
        )

        # Resolve the entity ID for the company
        entity_id = _resolve_entity_id_for_ticker(ticker)
        if not entity_id:
            # Create a fallback entity ID
            entity_id = f"org:sec-{cik.zfill(10)}"

        # Parse Exhibit 21 for subsidiaries
        job["progress"] = {"step": "parsing_exhibit_21", "detail": "Extracting subsidiaries from Exhibit 21"}
        subsidiaries_added = 0
        ex21_content, ex21_url = _fetch_exhibit_21_content(cik)
        if ex21_content:
            subsidiaries = _parse_exhibit_21_subsidiaries(ex21_content)
            for sub in subsidiaries:
                sub_id = _add_subsidiary_to_graph(
                    parent_entity_id=entity_id,
                    subsidiary_name=sub["name"],
                    jurisdiction=sub.get("jurisdiction", ""),
                    source_url=ex21_url or "",
                )
                if sub_id:
                    subsidiaries_added += 1

        # Parse DEF 14A for executives and board (skip for FPIs without proxy)
        job["progress"] = {"step": "parsing_def14a", "detail": "Extracting executives from proxy statement"}
        executives_added = 0
        board_members_added = 0

        if not is_foreign_private_issuer(cik):
            def14a_content, def14a_url = _fetch_def14a_content(cik)
            if def14a_content:
                executives, board_members = _parse_def14a_executives(def14a_content)

                for exec_info in executives:
                    exec_id = _add_executive_to_graph(
                        company_entity_id=entity_id,
                        name=exec_info["name"],
                        title=exec_info["title"],
                        source_url=def14a_url or "",
                    )
                    if exec_id:
                        executives_added += 1

                for board_info in board_members:
                    board_id = _add_board_member_to_graph(
                        company_entity_id=entity_id,
                        name=board_info["name"],
                        role=board_info["role"],
                        source_url=def14a_url or "",
                    )
                    if board_id:
                        board_members_added += 1

        # If depth > 1, run recursive expansion on discovered entities
        if depth > 1 and entity_id:
            job["progress"] = {"step": "recursive_expansion", "detail": f"Expanding graph to depth {depth}"}
            config = RecursionConfig(
                max_depth=min(depth, 5),
                max_nodes=200,
                min_confidence=ConfidenceTier.INFERRED,
            )
            get_recursion_engine().explore(entity_id, config)

        job["status"] = "completed"
        job["completed_at"] = datetime.utcnow().isoformat() + "Z"
        job["result"] = {
            "total_entities": result.get("total_entities", 0) + subsidiaries_added + executives_added + board_members_added,
            "total_edges": result.get("total_edges", 0) + subsidiaries_added + executives_added + board_members_added,
            "subsidiaries_discovered": subsidiaries_added,
            "executives_discovered": executives_added,
            "board_members_discovered": board_members_added,
            "errors": result.get("errors", []),
            "data_sources": {
                "exhibit_21": ex21_url if ex21_content else None,
                "def_14a": def14a_url if not is_foreign_private_issuer(cik) else "N/A (Foreign Private Issuer)",
            },
        }

    except Exception as exc:
        log.error("Discovery job %s failed: %s", job_id, exc)
        job["status"] = "failed"
        job["error"] = str(exc)
        job["completed_at"] = datetime.utcnow().isoformat() + "Z"


def start_discovery_job(ticker: str, depth: int = 2, entity_types: List[str] = None) -> Dict[str, Any]:
    """Start an autonomous entity discovery job in a background thread."""
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "ticker": ticker.upper(),
        "depth": depth,
        "entity_types": entity_types,
        "status": "queued",
        "started_at": datetime.utcnow().isoformat() + "Z",
        "completed_at": None,
        "result": None,
        "error": None,
        "progress": {"step": "queued", "detail": "Job queued for processing"},
    }
    _JOBS[job_id] = job

    thread = threading.Thread(
        target=_run_discovery,
        args=(job_id, ticker, depth, entity_types),
        daemon=True,
    )
    job["_thread"] = thread
    thread.start()

    return {
        "job_id": job_id,
        "status": "queued",
        "ticker": ticker.upper(),
        "depth": depth,
        "started_at": job["started_at"],
    }


def get_job_status(job_id: str) -> Dict[str, Any]:
    """Return actual status of a running background discovery job."""
    job = _JOBS.get(job_id)
    if not job:
        return {
            "status": "not_found",
            "job_id": job_id,
            "no_data": True,
            "message": f"Job {job_id} not found. It may have expired or never existed.",
        }

    response = {
        "job_id": job_id,
        "ticker": job["ticker"],
        "status": job["status"],
        "started_at": job["started_at"],
        "completed_at": job.get("completed_at"),
        "progress": job.get("progress"),
    }

    if job["status"] == "completed" and job.get("result"):
        response["result_summary"] = {
            "total_entities": job["result"].get("total_entities", 0),
            "total_edges": job["result"].get("total_edges", 0),
            "subsidiaries_discovered": job["result"].get("subsidiaries_discovered", 0),
            "executives_discovered": job["result"].get("executives_discovered", 0),
            "board_members_discovered": job["result"].get("board_members_discovered", 0),
            "errors": job["result"].get("errors", []),
            "data_sources": job["result"].get("data_sources", {}),
        }
    elif job["status"] == "failed":
        response["error"] = job.get("error")

    return response


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENTITY DISCOVERY FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_discovered_entities(ticker: str) -> Dict[str, Any]:
    """Query the EntityGraphStore for all entities connected to this ticker."""
    store = get_graph_store()
    entity_id = _resolve_entity_id_for_ticker(ticker)

    if not entity_id:
        return {
            "ticker": ticker,
            "status": "no_entity",
            "no_data": True,
            "message": f"No entity found for ticker {ticker}. Run a discovery job first.",
            "entities": [],
        }

    # Gather all neighbors (1-hop outgoing + incoming)
    outgoing = store.get_outgoing_edges(entity_id)
    incoming = store.get_incoming_edges(entity_id)

    seen_ids = {entity_id}
    entities = []

    root = store.get_entity(entity_id)
    if root:
        entities.append({
            "id": root.id,
            "kind": root.kind,
            "name": root.name,
            "identifiers": root.identifiers,
            "relationship": "self",
        })

    for edge in outgoing:
        if edge.dst_entity_id not in seen_ids:
            seen_ids.add(edge.dst_entity_id)
            dst = store.get_entity(edge.dst_entity_id)
            if dst:
                entities.append({
                    "id": dst.id,
                    "kind": dst.kind,
                    "name": dst.name,
                    "identifiers": dst.identifiers,
                    "relationship": edge.relationship_type,
                    "direction": "outgoing",
                })

    for edge in incoming:
        if edge.src_entity_id not in seen_ids:
            seen_ids.add(edge.src_entity_id)
            src = store.get_entity(edge.src_entity_id)
            if src:
                entities.append({
                    "id": src.id,
                    "kind": src.kind,
                    "name": src.name,
                    "identifiers": src.identifiers,
                    "relationship": edge.relationship_type,
                    "direction": "incoming",
                })

    return {
        "ticker": ticker,
        "root_entity_id": entity_id,
        "count": len(entities),
        "entities": entities,
    }


def get_entity_graph(ticker: str, depth: int = 2) -> Dict[str, Any]:
    """Use EntityGraphStore BFS (RecursionEngine.explore) for real graph neighborhood."""
    entity_id = _resolve_entity_id_for_ticker(ticker)

    if not entity_id:
        return {
            "ticker": ticker,
            "status": "no_entity",
            "no_data": True,
            "message": f"No entity found for ticker {ticker}. Run a discovery job first.",
            "nodes": [],
            "edges": [],
        }

    config = RecursionConfig(
        max_depth=min(depth, 5),
        max_nodes=500,
        min_confidence=ConfidenceTier.SPECULATIVE,
    )
    result = get_recursion_engine().explore(entity_id, config)

    if "error" in result:
        return {"ticker": ticker, "status": "error", "message": result["error"]}

    return {
        "ticker": ticker,
        "root_entity_id": entity_id,
        **result,
    }


def discover_subsidiaries(ticker: str) -> Dict[str, Any]:
    """
    Discover subsidiaries via SEC EDGAR (Exhibit 21 data) and graph edges.

    1. First queries the graph for existing subsidiary_of edges
    2. If no subsidiaries found, fetches and parses Exhibit 21 directly
    3. Returns real subsidiary data from SEC filings
    """
    store = get_graph_store()
    entity_id = _resolve_entity_id_for_ticker(ticker)
    subsidiaries = []

    # Query existing graph relationships
    if entity_id:
        # Look for subsidiary_of edges where this entity is the parent (incoming)
        incoming = store.get_incoming_edges(entity_id)
        for edge in incoming:
            if edge.relationship_type == RelationshipType.SUBSIDIARY_OF.value:
                sub = store.get_entity(edge.src_entity_id)
                if sub:
                    subsidiaries.append({
                        "id": sub.id,
                        "name": sub.name,
                        "kind": sub.kind,
                        "jurisdiction": sub.meta.get("jurisdiction", ""),
                        "confidence": edge.confidence_tier.value,
                        "source": edge.source_name,
                        "as_of": str(edge.as_of) if edge.as_of else None,
                    })

        # Also check owns edges
        outgoing = store.get_outgoing_edges(entity_id)
        seen = {s["id"] for s in subsidiaries}
        for edge in outgoing:
            if edge.relationship_type == RelationshipType.OWNS.value:
                if edge.dst_entity_id not in seen:
                    owned = store.get_entity(edge.dst_entity_id)
                    if owned and owned.kind == "org":
                        subsidiaries.append({
                            "id": owned.id,
                            "name": owned.name,
                            "kind": owned.kind,
                            "jurisdiction": owned.meta.get("jurisdiction", ""),
                            "confidence": edge.confidence_tier.value,
                            "source": edge.source_name,
                            "relationship": "owned",
                            "as_of": str(edge.as_of) if edge.as_of else None,
                        })

    # If no subsidiaries in graph, try fetching from SEC directly
    sec_context = None
    cik = get_filer_cik(ticker)
    if cik:
        # Get filing context
        subs = get_company_submissions(cik, forms=["10-K", "20-F"], limit=5)
        filings = subs.get("filings", [])
        if filings:
            latest_annual = filings[0] if filings else None
            sec_context = {
                "latest_annual_filing": latest_annual.get("filing_date") if latest_annual else None,
                "form_type": latest_annual.get("form") if latest_annual else None,
            }

        # If no subsidiaries from graph, parse Exhibit 21
        if not subsidiaries:
            ex21_content, ex21_url = _fetch_exhibit_21_content(cik)
            if ex21_content:
                parsed_subs = _parse_exhibit_21_subsidiaries(ex21_content)
                for sub in parsed_subs:
                    subsidiaries.append({
                        "id": None,  # Not yet in graph
                        "name": sub["name"],
                        "kind": "org",
                        "jurisdiction": sub.get("jurisdiction", ""),
                        "confidence": "CONFIRMED",
                        "source": "SEC Exhibit 21 (parsed)",
                        "source_url": ex21_url,
                        "in_graph": False,
                    })
                sec_context = sec_context or {}
                sec_context["exhibit_21_url"] = ex21_url
                sec_context["subsidiaries_parsed"] = len(parsed_subs)

    if not subsidiaries and not sec_context:
        return {
            "ticker": ticker,
            "root_entity_id": entity_id,
            "count": 0,
            "subsidiaries": [],
            "no_data": True,
            "message": f"No subsidiaries found for {ticker}. The company may not have filed Exhibit 21 or the data has not been ingested.",
        }

    return {
        "ticker": ticker,
        "root_entity_id": entity_id,
        "count": len(subsidiaries),
        "subsidiaries": subsidiaries,
        "sec_context": sec_context,
    }


def discover_investments(ticker: str) -> Dict[str, Any]:
    """Query graph for invested_in edges originating from this ticker's entity."""
    store = get_graph_store()
    entity_id = _resolve_entity_id_for_ticker(ticker)
    investments = []

    if entity_id:
        outgoing = store.get_outgoing_edges(entity_id)
        for edge in outgoing:
            if edge.relationship_type == RelationshipType.INVESTED_IN.value:
                target = store.get_entity(edge.dst_entity_id)
                if target:
                    investments.append({
                        "id": target.id,
                        "name": target.name,
                        "kind": target.kind,
                        "confidence": edge.confidence_tier.value,
                        "source": edge.source_name,
                        "as_of": str(edge.as_of) if edge.as_of else None,
                        "meta": edge.meta,
                    })

        # Also check LP relationships
        for edge in outgoing:
            if edge.relationship_type == RelationshipType.LP_OF.value:
                target = store.get_entity(edge.dst_entity_id)
                if target:
                    investments.append({
                        "id": target.id,
                        "name": target.name,
                        "kind": target.kind,
                        "relationship": "lp_of",
                        "confidence": edge.confidence_tier.value,
                        "source": edge.source_name,
                        "as_of": str(edge.as_of) if edge.as_of else None,
                        "meta": edge.meta,
                    })

    if not investments:
        return {
            "ticker": ticker,
            "root_entity_id": entity_id,
            "count": 0,
            "investments": [],
            "no_data": True,
            "message": f"No investment relationships found for {ticker}. Run a discovery job to ingest data.",
        }

    return {
        "ticker": ticker,
        "root_entity_id": entity_id,
        "count": len(investments),
        "investments": investments,
    }


def discover_board_connections(ticker: str) -> Dict[str, Any]:
    """
    Query graph for board_member edges pointing at this ticker's entity.

    Also fetches from DEF 14A proxy statement if no data in graph.
    """
    store = get_graph_store()
    entity_id = _resolve_entity_id_for_ticker(ticker)
    board_members = []

    if entity_id:
        incoming = store.get_incoming_edges(entity_id)
        for edge in incoming:
            if edge.relationship_type == RelationshipType.BOARD_MEMBER.value:
                person = store.get_entity(edge.src_entity_id)
                if person:
                    # Find other board seats for this person
                    other_seats = []
                    person_outgoing = store.get_outgoing_edges(person.id)
                    for pe in person_outgoing:
                        if (pe.relationship_type == RelationshipType.BOARD_MEMBER.value
                                and pe.dst_entity_id != entity_id):
                            other_org = store.get_entity(pe.dst_entity_id)
                            if other_org:
                                other_seats.append({
                                    "id": other_org.id,
                                    "name": other_org.name,
                                })

                    board_members.append({
                        "id": person.id,
                        "name": person.name,
                        "role": edge.meta.get("role", "Director"),
                        "confidence": edge.confidence_tier.value,
                        "source": edge.source_name,
                        "as_of": str(edge.as_of) if edge.as_of else None,
                        "other_board_seats": other_seats,
                    })

    # If no board members in graph, try parsing DEF 14A
    sec_context = None
    cik = get_filer_cik(ticker)
    if cik and not board_members:
        if not is_foreign_private_issuer(cik):
            def14a_content, def14a_url = _fetch_def14a_content(cik)
            if def14a_content:
                _, parsed_board = _parse_def14a_executives(def14a_content)
                for member in parsed_board:
                    board_members.append({
                        "id": None,
                        "name": member["name"],
                        "role": member["role"],
                        "confidence": "CONFIRMED",
                        "source": "SEC DEF 14A (parsed)",
                        "source_url": def14a_url,
                        "in_graph": False,
                        "other_board_seats": [],
                    })
                sec_context = {
                    "def_14a_url": def14a_url,
                    "board_members_parsed": len(parsed_board),
                }
        else:
            sec_context = {
                "note": "Foreign Private Issuer - DEF 14A not required",
            }

    if not board_members:
        return {
            "ticker": ticker,
            "root_entity_id": entity_id,
            "count": 0,
            "board_members": [],
            "no_data": True,
            "message": f"No board member data found for {ticker}. Run a discovery job to ingest data.",
            "sec_context": sec_context,
        }

    return {
        "ticker": ticker,
        "root_entity_id": entity_id,
        "count": len(board_members),
        "board_members": board_members,
        "sec_context": sec_context,
    }


def discover_executives(ticker: str) -> Dict[str, Any]:
    """
    Discover executives via SEC EDGAR DEF 14A and Form 4 filings.

    Returns named executive officers from proxy statements and
    insiders from Form 4 filings.
    """
    store = get_graph_store()
    entity_id = _resolve_entity_id_for_ticker(ticker)
    executives = []

    # Query graph for employed_at relationships
    if entity_id:
        incoming = store.get_incoming_edges(entity_id)
        for edge in incoming:
            if edge.relationship_type == RelationshipType.EMPLOYED_AT.value:
                person = store.get_entity(edge.src_entity_id)
                if person:
                    executives.append({
                        "id": person.id,
                        "name": person.name,
                        "title": edge.meta.get("title", "Executive"),
                        "confidence": edge.confidence_tier.value,
                        "source": edge.source_name,
                        "as_of": str(edge.as_of) if edge.as_of else None,
                    })

    # Try to get executives from SEC if none in graph
    sec_context = None
    cik = get_filer_cik(ticker)
    if cik:
        # Get insider transactions for executive identification
        insiders = get_insider_transactions(cik, max_filings=50)
        insider_names = set()
        for txn in insiders.get("transactions", []):
            if txn.get("roles") and any(r in ["Officer", "Director"] for r in txn.get("roles", [])):
                name = txn.get("insider", "")
                title = txn.get("title", "")
                if name and name not in insider_names:
                    insider_names.add(name)
                    # Check if already in executives list
                    if not any(e["name"].lower() == name.lower() for e in executives):
                        executives.append({
                            "id": None,
                            "name": name,
                            "title": title or "Executive (from Form 4)",
                            "confidence": "CONFIRMED",
                            "source": "SEC Form 4",
                            "in_graph": False,
                        })

        # Parse DEF 14A for additional executives (skip for FPIs)
        if not is_foreign_private_issuer(cik):
            def14a_content, def14a_url = _fetch_def14a_content(cik)
            if def14a_content:
                parsed_execs, _ = _parse_def14a_executives(def14a_content)
                for exec_info in parsed_execs:
                    if not any(e["name"].lower() == exec_info["name"].lower() for e in executives):
                        executives.append({
                            "id": None,
                            "name": exec_info["name"],
                            "title": exec_info["title"],
                            "confidence": "CONFIRMED",
                            "source": "SEC DEF 14A (parsed)",
                            "source_url": def14a_url,
                            "in_graph": False,
                        })
                sec_context = {
                    "def_14a_url": def14a_url,
                    "executives_parsed": len(parsed_execs),
                }
        else:
            sec_context = {
                "note": "Foreign Private Issuer - executive data from Form 4 and 20-F",
            }

        sec_context = sec_context or {}
        sec_context["form_4_filings_checked"] = insiders.get("filings_count", 0)

    if not executives:
        return {
            "ticker": ticker,
            "root_entity_id": entity_id,
            "count": 0,
            "executives": [],
            "no_data": True,
            "message": f"No executive data found for {ticker}. Run a discovery job to ingest data.",
            "sec_context": sec_context,
        }

    return {
        "ticker": ticker,
        "root_entity_id": entity_id,
        "count": len(executives),
        "executives": executives,
        "sec_context": sec_context,
    }


def get_family_tree(ticker: str) -> Dict[str, Any]:
    """
    Build corporate family tree from graph edges.

    Traverses subsidiary_of, owns, and controls edges to construct
    the parent-child hierarchy.
    """
    store = get_graph_store()
    entity_id = _resolve_entity_id_for_ticker(ticker)

    if not entity_id:
        return {
            "ticker": ticker,
            "status": "no_entity",
            "no_data": True,
            "message": f"No entity found for ticker {ticker}. Run a discovery job first.",
            "tree": None,
        }

    root = store.get_entity(entity_id)

    # Find parent (if this entity is subsidiary_of something)
    parent_info = None
    outgoing = store.get_outgoing_edges(entity_id)
    for edge in outgoing:
        if edge.relationship_type == RelationshipType.SUBSIDIARY_OF.value:
            parent = store.get_entity(edge.dst_entity_id)
            if parent:
                parent_info = {"id": parent.id, "name": parent.name, "kind": parent.kind}
                break

    # Find children (entities that are subsidiary_of this entity, or that it owns)
    children = []
    incoming = store.get_incoming_edges(entity_id)
    seen_children = set()

    for edge in incoming:
        if edge.relationship_type in (
            RelationshipType.SUBSIDIARY_OF.value,
        ):
            if edge.src_entity_id not in seen_children:
                seen_children.add(edge.src_entity_id)
                child = store.get_entity(edge.src_entity_id)
                if child:
                    children.append({
                        "id": child.id,
                        "name": child.name,
                        "kind": child.kind,
                        "jurisdiction": child.meta.get("jurisdiction", ""),
                        "relationship": edge.relationship_type,
                    })

    for edge in outgoing:
        if edge.relationship_type in (
            RelationshipType.OWNS.value,
            RelationshipType.CONTROLS.value,
        ):
            if edge.dst_entity_id not in seen_children:
                seen_children.add(edge.dst_entity_id)
                child = store.get_entity(edge.dst_entity_id)
                if child and child.kind == "org":
                    children.append({
                        "id": child.id,
                        "name": child.name,
                        "kind": child.kind,
                        "jurisdiction": child.meta.get("jurisdiction", ""),
                        "relationship": edge.relationship_type,
                    })

    return {
        "ticker": ticker,
        "root_entity_id": entity_id,
        "tree": {
            "parent": parent_info,
            "entity": {
                "id": root.id,
                "name": root.name,
                "kind": root.kind,
                "identifiers": root.identifiers,
            } if root else None,
            "children": children,
            "children_count": len(children),
        },
    }
