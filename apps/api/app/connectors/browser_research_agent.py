"""
Browser Research Agent — fallback intelligence for uncovered jurisdictions.

Replaces the Perplexity approach James described: when we have no dedicated
connector for a country or state (e.g. Argentina, Brazil, UAE), this agent
browses public sources directly using Apify's web-scraping infrastructure
and GPT-4o synthesis.

Architecture:
  1. Detect jurisdiction from entity name / context
  2. Build a set of target URLs per jurisdiction (public registries, courts,
     government procurement portals, news sites)
  3. Use Apify's cheerio-scraper or browser-based actor to fetch page content
  4. Send raw content to GPT-4o for extraction + structuring
  5. Return structured findings with source URLs and confidence tags

Jurisdictions with dedicated connectors (skip browser fallback):
  - United States: SEC, FEC, FARA, USASpending, LDA, OFAC, CourtListener

Jurisdictions using browser fallback:
  - Argentina, Brazil, Mexico, UK, EU, UAE, Australia, Canada, Singapore, + any other
"""

import os
import re
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_BASE = "https://api.apify.com/v2"
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

# ── Jurisdiction router ───────────────────────────────────────────────────────

US_JURISDICTIONS = {"us", "usa", "united states", "federal", "sec", "fec"}

# Per-jurisdiction public source templates
JURISDICTION_SOURCES: Dict[str, List[Dict[str, str]]] = {
    "argentina": [
        {"name": "AFIP (Tax Registry)", "url": "https://www.afip.gob.ar/genericos/consulta/consulta.aspx?q={query}"},
        {"name": "IGJ (Business Registry)", "url": "https://www.argentina.gob.ar/justicia/igj"},
        {"name": "Contrataciones (Procurement)", "url": "https://contrataciones.gov.ar/busqueda.html?q={query}"},
        {"name": "Infojus (Courts)", "url": "https://www.saij.gob.ar/busqueda?q={query}"},
        {"name": "La Nacion News", "url": "https://www.lanacion.com.ar/buscar/?q={query}"},
        {"name": "Clarin News", "url": "https://www.clarin.com/busqueda.html?q={query}"},
    ],
    "brazil": [
        {"name": "CNPJ (Business Registry)", "url": "https://www.receita.fazenda.gov.br/pessoajuridica/cnpj/cnpjreva/cnpjreva_solicitacao.asp"},
        {"name": "COMPRASNET (Procurement)", "url": "https://www.comprasnet.gov.br/acesso.asp?url=/ConsultaLicitacoes/ConsLicitacao_Filtro.asp"},
        {"name": "Portal da Transparencia", "url": "https://www.portaltransparencia.gov.br/busca?termo={query}"},
        {"name": "Folha de S.Paulo News", "url": "https://search.folha.uol.com.br/search?q={query}"},
    ],
    "uk": [
        {"name": "Companies House", "url": "https://find-and-update.company-information.service.gov.uk/search?q={query}"},
        {"name": "UK Contracts Finder", "url": "https://www.contractsfinder.service.gov.uk/Search/Results?q={query}"},
        {"name": "UK Courts (Find Case Law)", "url": "https://caselaw.nationalarchives.gov.uk/search?query={query}"},
        {"name": "Companies House Officers", "url": "https://api.company-information.service.gov.uk/search/companies?q={query}"},
        {"name": "The Guardian News", "url": "https://www.theguardian.com/search?q={query}"},
    ],
    "uae": [
        {"name": "Dubai Chamber", "url": "https://www.dubaichamber.com/en/business-directory?search={query}"},
        {"name": "Abu Dhabi DED", "url": "https://www.added.gov.ae/en/search#q={query}"},
        {"name": "UAE MOJ Courts", "url": "https://www.moj.gov.ae/en/search/#q={query}"},
        {"name": "Khaleej Times News", "url": "https://www.khaleejtimes.com/search/{query}"},
    ],
    "australia": [
        {"name": "ASIC (Business Registry)", "url": "https://connectonline.asic.gov.au/RegistrySearch/faces/landing/byNameSearch.jspx?_adf.ctrl-state=1d8x3bua6_4&name={query}"},
        {"name": "AusTender (Procurement)", "url": "https://www.tenders.gov.au/Search/ListATM?statusDateFilter=current&agencyStatus=publishedStatus&keyword={query}"},
        {"name": "Federal Court", "url": "https://www.fedcourt.gov.au/online-services/search/case-search?q={query}"},
        {"name": "The Australian News", "url": "https://www.theaustralian.com.au/search-results?q={query}"},
    ],
    "canada": [
        {"name": "SEDAR+ (Securities)", "url": "https://www.sedarplus.ca/csa-party/party/search.xhtml?searchQuery={query}"},
        {"name": "Buyandsell (Procurement)", "url": "https://buyandsell.gc.ca/procurement-data/search/site?q={query}"},
        {"name": "Corporations Canada", "url": "https://ised-isde.canada.ca/cc/lgcy/fdrl/srch/index?lang=eng&SearchTerm={query}"},
        {"name": "Globe and Mail News", "url": "https://www.theglobeandmail.com/search/?q={query}"},
    ],
    "mexico": [
        {"name": "SAT (Tax Registry)", "url": "https://www.sat.gob.mx/consulta/99963/consulta-el-registro-federal-de-contribuyentes-(rfc)"},
        {"name": "CompraNet (Procurement)", "url": "https://compranet.hacienda.gob.mx/esop/guest/go/public/opportunity/current"},
        {"name": "El Universal News", "url": "https://www.eluniversal.com.mx/buscador/?q={query}"},
    ],
    "singapore": [
        {"name": "ACRA (Business Registry)", "url": "https://www.acra.gov.sg/home/"},
        {"name": "GeBIZ (Procurement)", "url": "https://www.gebiz.gov.sg/ptn/opportunity/BOAListing.xhtml?search=open&q={query}"},
        {"name": "Straits Times News", "url": "https://www.straitstimes.com/search?searchkey={query}"},
    ],
    "default": [
        {"name": "OpenCorporates", "url": "https://opencorporates.com/companies?q={query}&utf8=%E2%9C%93"},
        {"name": "GLEIF LEI Registry", "url": "https://search.gleif.org/#/search?query={query}"},
        {"name": "Google News", "url": "https://news.google.com/search?q={query}"},
        {"name": "Wikipedia", "url": "https://en.wikipedia.org/w/index.php?search={query}"},
    ],
}


def detect_jurisdiction(entity_name: str, context: str = "") -> str:
    """
    Heuristic jurisdiction detection from entity name and optional context string.
    Returns lowercase jurisdiction key.
    """
    combined = f"{entity_name} {context}".lower()

    if any(k in combined for k in ["argentina", "arg ", "buenos aires", "mendoza", "córdoba"]):
        return "argentina"
    if any(k in combined for k in ["brazil", "brasil", "são paulo", "rio de janeiro", "cnpj"]):
        return "brazil"
    if any(k in combined for k in ["united kingdom", "uk ", " uk,", "london", "companies house", "plc"]):
        return "uk"
    if any(k in combined for k in ["uae", "dubai", "abu dhabi", "emirates"]):
        return "uae"
    if any(k in combined for k in ["australia", "asic", "sydney", "melbourne"]):
        return "australia"
    if any(k in combined for k in ["canada", "ontario", "sedar", "vancouver", "toronto"]):
        return "canada"
    if any(k in combined for k in ["mexico", "méxico", "cdmx", "monterrey"]):
        return "mexico"
    if any(k in combined for k in ["singapore", "acra", " sg "]):
        return "singapore"

    return "default"


def _scrape_url(url: str, query: str) -> str:
    """
    Fetch a URL via Apify Cheerio scraper and return extracted text.
    Falls back to simple requests GET if Apify is unavailable.
    """
    target_url = url.replace("{query}", requests.utils.quote(query))

    # Try Apify cheerio scraper first (handles JS-rendered pages better)
    if APIFY_TOKEN:
        try:
            run_resp = requests.post(
                f"{APIFY_BASE}/acts/apify~cheerio-scraper/runs",
                params={"token": APIFY_TOKEN, "waitForFinish": 60},
                json={
                    "startUrls": [{"url": target_url}],
                    "pageFunction": """async function pageFunction({ $, request }) {
                        const text = $('body').text().replace(/\\s+/g, ' ').trim().slice(0, 3000);
                        const links = $('a[href]').map((i, el) => $(el).attr('href')).get().slice(0, 20);
                        return { url: request.url, text, links };
                    }""",
                    "maxRequestsPerCrawl": 1,
                },
                timeout=90,
            )
            if run_resp.ok:
                run_data = run_resp.json().get("data", run_resp.json())
                dataset_id = run_data.get("defaultDatasetId")
                if dataset_id:
                    items_r = requests.get(
                        f"{APIFY_BASE}/datasets/{dataset_id}/items",
                        params={"token": APIFY_TOKEN, "clean": "true", "format": "json"},
                        timeout=20,
                    )
                    if items_r.ok:
                        items = items_r.json()
                        if items and isinstance(items, list):
                            return items[0].get("text", "")[:3000]
        except Exception as e:
            logger.debug("Apify scrape failed for %s: %s", target_url, e)

    # Fallback: direct HTTP GET
    try:
        headers = {"User-Agent": "Mozilla/5.0 IntelPlatform/1.0 research@example.com"}
        r = requests.get(target_url, headers=headers, timeout=15, allow_redirects=True)
        if r.ok:
            # Strip HTML tags for plain text
            text = re.sub(r"<[^>]+>", " ", r.text)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:3000]
    except Exception as e:
        logger.debug("Direct fetch failed for %s: %s", target_url, e)

    return ""


def _synthesize_with_gpt(entity_name: str, jurisdiction: str,
                          scraped_results: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Use GPT-4o-mini to extract structured intelligence from scraped web pages.
    """
    if not OPENAI_KEY:
        return {
            "summary": "[Browser research synthesis unavailable — OPENAI_API_KEY not configured]",
            "findings": [],
            "sources": [],
        }

    context_parts = []
    sources = []
    for r in scraped_results:
        if r.get("text") and len(r["text"]) > 100:
            context_parts.append(f"\n## Source: {r['source_name']}\nURL: {r['url']}\n{r['text'][:800]}")
            sources.append({"name": r["source_name"], "url": r["url"]})

    if not context_parts:
        return {
            "summary": f"No usable content found from public sources for {entity_name} in {jurisdiction}.",
            "findings": [],
            "sources": sources,
        }

    prompt = f"""You are an intelligence analyst extracting structured information about an entity from public web sources.

ENTITY: {entity_name}
JURISDICTION: {jurisdiction}

PUBLIC SOURCE CONTENT:
{"".join(context_parts)}

Extract everything relevant about {entity_name} from the above sources. Structure your output as:

**Registration & Identity**
- Company registration number, founding date, registered address, legal status

**Key People**
- Directors, officers, founders, and their roles

**Financial & Funding**
- Revenue estimates, funding rounds, investors (if disclosed)

**Government & Regulatory**
- Procurement contracts, regulatory filings, tax registrations

**Legal & Compliance**
- Court cases, enforcement actions, sanctions

**News & Recent Developments**
- Recent news from local sources

**Risk Assessment**
- [DOCUMENTED] for primary source data
- [REPORTED] for news/secondary sources
- [ANALYTICAL] for inferences

If information is not found in the sources, say "Not found in available sources" — do NOT invent data."""

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a senior OSINT analyst. Extract and structure intelligence from public web sources. Be precise, cite sources, and tag claims with confidence levels."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 1500,
            },
            timeout=60,
        )
        if resp.ok:
            content = resp.json()["choices"][0]["message"]["content"]
            # Parse findings into list
            findings = [line.strip("- ").strip() for line in content.split("\n")
                        if line.strip().startswith("-") and len(line.strip()) > 10]
            return {
                "summary": content,
                "findings": findings[:20],
                "sources": sources,
            }
        return {"summary": f"[GPT synthesis error {resp.status_code}]", "findings": [], "sources": sources}
    except Exception as e:
        return {"summary": f"[GPT synthesis error: {e}]", "findings": [], "sources": sources}


def research_entity_browser(
    entity_name: str,
    jurisdiction: Optional[str] = None,
    context: str = "",
    max_sources: int = 4,
    deep_dive: bool = False,
) -> Dict[str, Any]:
    """
    Main entry point. Research an entity using browser-based public source scraping.

    Args:
        entity_name: Entity or person name to research
        jurisdiction: Override jurisdiction detection (e.g. 'argentina')
        context: Optional context string to help with jurisdiction detection
        max_sources: Max number of sources to scrape (default 4, deep_dive uses more)
        deep_dive: If True, scrape more sources including holding company / vehicle searches

    Returns:
        Dict with summary, findings list, sources, jurisdiction, confidence
    """
    result: Dict[str, Any] = {
        "entity_name": entity_name,
        "jurisdiction": None,
        "sources_checked": [],
        "findings": [],
        "summary": "",
        "raw_text": "",
        "confidence": "LOW",
        "source": "Browser Research Agent",
    }

    if not entity_name or len(entity_name.strip()) < 2:
        result["summary"] = "Entity name too short to research."
        return result

    # 1. Detect or use provided jurisdiction
    jur = jurisdiction or detect_jurisdiction(entity_name, context)
    result["jurisdiction"] = jur

    # 2. Get sources for jurisdiction
    sources = JURISDICTION_SOURCES.get(jur, JURISDICTION_SOURCES["default"])
    if deep_dive:
        # Add global fallback sources for deep dives
        for s in JURISDICTION_SOURCES["default"]:
            if s not in sources:
                sources = sources + [s]

    # 3. Scrape top sources
    scraped: List[Dict[str, str]] = []
    for source in sources[:max_sources + (2 if deep_dive else 0)]:
        text = _scrape_url(source["url"], entity_name)
        scraped.append({
            "source_name": source["name"],
            "url": source["url"].replace("{query}", requests.utils.quote(entity_name)),
            "text": text,
            "has_data": len(text) > 200,
        })
        result["sources_checked"].append(source["name"])
        logger.info("Browser agent scraped %s for '%s': %d chars", source["name"], entity_name, len(text))

    # 4. Synthesize with GPT
    synthesis = _synthesize_with_gpt(entity_name, jur, scraped)
    result["summary"] = synthesis.get("summary", "")
    result["findings"] = synthesis.get("findings", [])
    result["raw_sources"] = synthesis.get("sources", [])

    # 5. Confidence based on data found
    sources_with_data = sum(1 for s in scraped if s["has_data"])
    result["confidence"] = "HIGH" if sources_with_data >= 3 else "MEDIUM" if sources_with_data >= 1 else "LOW"
    result["sources_with_data"] = sources_with_data

    return result


def is_us_entity(entity_name: str, entity_type: str = "org") -> bool:
    """
    Heuristic: is this entity likely US-based?
    Used to decide whether to skip browser fallback.
    """
    # US-only type indicators
    if entity_type in ("agency",):
        return True
    # Common US company suffixes
    us_signals = ["inc.", "llc", "corp.", "corporation", "ltd.", "l.p.", "l.l.c"]
    name_lower = entity_name.lower()
    return any(s in name_lower for s in us_signals)
