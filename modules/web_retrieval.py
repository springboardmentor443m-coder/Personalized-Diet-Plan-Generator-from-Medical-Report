"""Web Retrieval Module — Fetch evidence from trusted medical sources.

Retrieves relevant medical nutrition information from PubMed and other
trusted online sources (WHO, NIH) to supplement the local knowledge base.

Uses PubMed E-utilities API (free, no API key required for moderate use)
and caches results to `data/web_cache/` to avoid redundant network calls.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "web_cache"
CACHE_EXPIRY_HOURS = 72  # Re-fetch after 72 hours

# PubMed E-utilities base URLs (10 req/sec with API key, 3/sec without)
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# Load API key from settings
def _get_api_key_param() -> str:
    """Return the &api_key= param string if configured, else empty."""
    from config.settings import PUBMED_API_KEY
    if PUBMED_API_KEY:
        return f"&api_key={PUBMED_API_KEY}"
    return ""

# Max articles to fetch per query
MAX_ARTICLES = 5
# Max total web context chars
MAX_WEB_CONTEXT_CHARS = 3000

# Condition → targeted PubMed search queries
CONDITION_QUERY_MAP: dict[str, str] = {
    "diabetes": "diabetes mellitus medical nutrition therapy diet guidelines",
    "glucose_metabolism": "diabetes blood glucose dietary management guidelines",
    "hypertension": "hypertension DASH diet sodium restriction nutrition",
    "cardiovascular": "cardiovascular disease diet Mediterranean heart healthy nutrition",
    "lipid": "dyslipidemia diet cholesterol lowering nutrition therapy",
    "kidney": "chronic kidney disease CKD diet protein restriction renal nutrition",
    "liver": "liver disease NAFLD diet nutrition hepatic encephalopathy",
    "thyroid": "thyroid disorder diet iodine selenium nutrition",
    "anemia": "anemia iron deficiency diet nutrition therapy B12 folate",
    "obesity": "obesity weight management diet caloric restriction nutrition",
    "pcos": "polycystic ovary syndrome PCOS diet insulin resistance nutrition",
    "osteoporosis": "osteoporosis calcium vitamin D diet bone health nutrition",
    "gout": "gout hyperuricemia diet purine restriction nutrition",
    "cancer": "cancer nutrition support oncology diet malnutrition cachexia",
    "copd": "COPD nutrition pulmonary diet respiratory",
    "celiac": "celiac disease gluten free diet nutrition",
    "ibd": "inflammatory bowel disease IBD diet Crohn ulcerative colitis nutrition",
    "pregnancy": "pregnancy nutrition gestational diabetes diet prenatal",
    "geriatric": "elderly geriatric nutrition sarcopenia malnutrition diet",
    "mental_health": "depression anxiety diet nutrition omega-3 gut brain",
}

# Article type filters for higher quality results
PUBMED_ARTICLE_FILTERS = (
    " AND (Review[pt] OR Guideline[pt] OR Practice Guideline[pt] "
    "OR Meta-Analysis[pt] OR Systematic Review[pt]) "
    "AND (\"last 10 years\"[dp]) "
    "AND English[la]"
)


def _get_cache_path(query: str) -> Path:
    """Generate a unique cache file path for a query."""
    query_hash = hashlib.md5(query.encode()).hexdigest()[:12]
    return CACHE_DIR / f"pubmed_{query_hash}.json"


def _is_cache_valid(cache_path: Path) -> bool:
    """Check if cached result is still fresh."""
    if not cache_path.exists():
        return False
    age_seconds = time.time() - cache_path.stat().st_mtime
    return age_seconds < (CACHE_EXPIRY_HOURS * 3600)


def _load_cache(cache_path: Path) -> list[dict[str, str]] | None:
    """Load cached results if valid."""
    if not _is_cache_valid(cache_path):
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_cache(cache_path: Path, data: list[dict[str, str]]) -> None:
    """Save results to cache."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("Failed to save web cache: %s", exc)


# ---------------------------------------------------------------------------
# PubMed API
# ---------------------------------------------------------------------------
def _search_pubmed(query: str, max_results: int = MAX_ARTICLES) -> list[str]:
    """Search PubMed and return list of PMIDs.

    Uses E-utilities esearch.fcgi (free, rate limit: 3 requests/second
    without API key, 10/second with key).
    """
    import urllib.request
    import xml.etree.ElementTree as ET

    full_query = query + PUBMED_ARTICLE_FILTERS
    params = (
        f"?db=pubmed&retmode=xml&retmax={max_results}"
        f"&sort=relevance&term={quote_plus(full_query)}"
        f"{_get_api_key_param()}"
    )
    url = PUBMED_SEARCH_URL + params

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DietPlanApp/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            xml_data = resp.read().decode("utf-8")

        root = ET.fromstring(xml_data)
        id_list = root.find("IdList")
        if id_list is None:
            return []

        pmids = [id_elem.text for id_elem in id_list.findall("Id") if id_elem.text]
        logger.info("PubMed search returned %d results for: %s", len(pmids), query[:80])
        return pmids

    except Exception as exc:
        logger.warning("PubMed search failed (timeout/network): %s", exc)
        return []


def _fetch_pubmed_summaries(pmids: list[str]) -> list[dict[str, str]]:
    """Fetch article summaries (title + abstract) from PubMed.

    Uses efetch.fcgi to get abstracts in XML format.
    """
    import urllib.request
    import xml.etree.ElementTree as ET

    if not pmids:
        return []

    ids_str = ",".join(pmids)
    params = f"?db=pubmed&retmode=xml&rettype=abstract&id={ids_str}{_get_api_key_param()}"
    url = PUBMED_FETCH_URL + params

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DietPlanApp/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            xml_data = resp.read().decode("utf-8")

        root = ET.fromstring(xml_data)
        articles: list[dict[str, str]] = []

        for article in root.findall(".//PubmedArticle"):
            try:
                # Extract title
                title_elem = article.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None and title_elem.text else ""

                # Extract abstract text
                abstract_parts: list[str] = []
                abstract = article.find(".//Abstract")
                if abstract is not None:
                    for abs_text in abstract.findall("AbstractText"):
                        label = abs_text.get("Label", "")
                        text = "".join(abs_text.itertext()).strip()
                        if label and text:
                            abstract_parts.append(f"{label}: {text}")
                        elif text:
                            abstract_parts.append(text)

                abstract_str = " ".join(abstract_parts)

                # Extract journal and year
                journal_elem = article.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None else ""

                year_elem = article.find(".//PubDate/Year")
                year = year_elem.text if year_elem is not None else ""

                # Extract PMID
                pmid_elem = article.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else ""

                if title and abstract_str:
                    articles.append({
                        "title": title,
                        "abstract": abstract_str,
                        "journal": journal,
                        "year": year,
                        "pmid": pmid,
                        "source": f"PubMed PMID:{pmid}",
                    })
            except Exception:
                continue

        logger.info("Fetched %d article summaries from PubMed", len(articles))
        return articles

    except Exception as exc:
        logger.warning("PubMed fetch failed: %s", exc)
        return []


def _format_article_for_context(article: dict[str, str]) -> str:
    """Format a PubMed article summary for inclusion in the RAG context."""
    parts = [f"[PubMed {article.get('year', '')} — {article.get('journal', '')}]"]
    parts.append(f"Title: {article['title']}")

    # Truncate abstract to keep context manageable
    abstract = article.get("abstract", "")
    if len(abstract) > 600:
        abstract = abstract[:597] + "..."
    parts.append(f"Findings: {abstract}")
    parts.append(f"(PMID: {article.get('pmid', 'N/A')})")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Query Building
# ---------------------------------------------------------------------------
def _identify_conditions(
    aggregated_state: dict,
    per_doc_results: list[dict] | None = None,
) -> list[str]:
    """Identify medical conditions from the patient's health state.

    Returns a list of condition keys that map to CONDITION_QUERY_MAP.
    """
    conditions: list[str] = []

    # Check abnormal findings
    abnormals = aggregated_state.get("aggregated_abnormal_findings", [])
    for finding in abnormals:
        key = finding.get("canonical_test_key", "").lower()
        category = finding.get("category", "").lower()

        if any(w in key for w in ["glucose", "hba1c", "sugar", "insulin"]):
            conditions.append("diabetes")
        if any(w in key for w in ["cholesterol", "ldl", "hdl", "triglyceride"]):
            conditions.append("lipid")
        if any(w in key for w in ["creatinine", "bun", "egfr", "urea"]):
            conditions.append("kidney")
        if any(w in key for w in ["alt", "ast", "bilirubin", "ggt", "albumin"]):
            conditions.append("liver")
        if any(w in key for w in ["tsh", "t3", "t4", "thyroid"]):
            conditions.append("thyroid")
        if any(w in key for w in ["hemoglobin", "hb", "iron", "ferritin", "b12"]):
            conditions.append("anemia")
        if any(w in key for w in ["uric_acid", "urate"]):
            conditions.append("gout")

        # Category-based detection
        if "glucose" in category:
            conditions.append("diabetes")
        if "lipid" in category:
            conditions.append("lipid")
        if "renal" in category:
            conditions.append("kidney")
        if "liver" in category or "hepatic" in category:
            conditions.append("liver")
        if "thyroid" in category:
            conditions.append("thyroid")

    # Check chronic flags
    chronic = aggregated_state.get("chronic_flags", [])
    for flag in chronic:
        name = flag.get("test_name", "").lower()
        if "diabet" in name or "glucose" in name:
            conditions.append("diabetes")
        if "hypertens" in name or "blood pressure" in name:
            conditions.append("hypertension")
        if "kidney" in name or "renal" in name:
            conditions.append("kidney")
        if "liver" in name or "hepat" in name:
            conditions.append("liver")

    # Check BMI
    bmi = aggregated_state.get("bmi", {})
    bmi_cat = bmi.get("category", "").lower()
    if "obese" in bmi_cat or "overweight" in bmi_cat:
        conditions.append("obesity")

    # Check patient demographics
    patient = aggregated_state.get("patient_information", {})
    age = patient.get("age_years")
    if age is not None:
        if age >= 65:
            conditions.append("geriatric")
        elif age < 18:
            pass  # pediatric not yet in PubMed queries

    sex = patient.get("sex", "").lower()
    # PCOS only in females
    if sex in ("female", "f"):
        # Check for PCOS-related signs
        for finding in abnormals:
            key = finding.get("canonical_test_key", "").lower()
            if any(w in key for w in ["testosterone", "dhea", "lh", "fsh", "androgen"]):
                conditions.append("pcos")

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for c in conditions:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    return unique[:5]  # Limit to top 5 conditions to control API calls


# ---------------------------------------------------------------------------
# Main retrieval function
# ---------------------------------------------------------------------------
def retrieve_web_context(
    aggregated_state: dict,
    per_doc_results: list[dict] | None = None,
    max_articles_per_condition: int = 3,
) -> str:
    """Retrieve relevant medical nutrition evidence from PubMed.

    This function:
    1. Identifies patient conditions from health state
    2. Maps conditions to targeted PubMed queries
    3. Fetches and caches article abstracts
    4. Formats relevant findings as context for the LLM

    Parameters
    ----------
    aggregated_state : dict
        The patient's aggregated health state.
    per_doc_results : list[dict] | None
        Per-document extraction results.
    max_articles_per_condition : int
        Max PubMed articles to fetch per condition.

    Returns
    -------
    str
        Formatted web-retrieved evidence context, or empty string if
        no relevant results or network unavailable.
    """
    conditions = _identify_conditions(aggregated_state, per_doc_results)

    if not conditions:
        logger.info("Web retrieval: no specific conditions identified")
        return ""

    logger.info("Web retrieval: identified conditions: %s", conditions)

    all_articles: list[dict[str, str]] = []
    total_chars = 0

    for condition in conditions:
        query = CONDITION_QUERY_MAP.get(condition)
        if not query:
            continue

        # Check cache first
        cache_path = _get_cache_path(query)
        cached = _load_cache(cache_path)

        if cached is not None:
            logger.info("Web cache hit for: %s (%d articles)", condition, len(cached))
            articles = cached
        else:
            # Fetch from PubMed
            logger.info("Fetching from PubMed for: %s", condition)
            pmids = _search_pubmed(query, max_results=max_articles_per_condition)

            if not pmids:
                continue

            articles = _fetch_pubmed_summaries(pmids)

            # Cache results (even empty — to avoid hammering API)
            _save_cache(cache_path, articles)

            # Rate limiting: 0.5s between PubMed API calls
            time.sleep(0.5)

        # Add articles within character budget
        for article in articles:
            formatted = _format_article_for_context(article)
            if total_chars + len(formatted) > MAX_WEB_CONTEXT_CHARS:
                break
            all_articles.append(article)
            total_chars += len(formatted)

            # Persist to ChromaDB for cross-reference and future retrieval
            try:
                from modules.knowledge_store import index_pubmed_article
                index_pubmed_article(
                    pmid=article.get("pmid", ""),
                    title=article.get("title", ""),
                    abstract=article.get("abstract", ""),
                    journal=article.get("journal", ""),
                    year=article.get("year", ""),
                )
            except Exception:
                pass  # non-fatal

        if total_chars >= MAX_WEB_CONTEXT_CHARS:
            break

    if not all_articles:
        logger.info("Web retrieval: no articles found")
        return ""

    # Format all articles
    formatted_parts = [_format_article_for_context(a) for a in all_articles]
    context = "\n\n---\n\n".join(formatted_parts)

    logger.info(
        "Web retrieval: %d articles (%d chars) for conditions: %s",
        len(all_articles),
        len(context),
        conditions,
    )

    return context


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------
def clear_web_cache() -> int:
    """Clear all cached web retrieval results. Returns count of files removed."""
    if not CACHE_DIR.exists():
        return 0

    count = 0
    for f in CACHE_DIR.glob("pubmed_*.json"):
        try:
            f.unlink()
            count += 1
        except Exception:
            pass

    logger.info("Cleared %d web cache files", count)
    return count


def get_web_cache_stats() -> dict[str, Any]:
    """Return statistics about the web cache."""
    if not CACHE_DIR.exists():
        return {"cached_queries": 0, "total_size_kb": 0}

    files = list(CACHE_DIR.glob("pubmed_*.json"))
    total_size = sum(f.stat().st_size for f in files)

    return {
        "cached_queries": len(files),
        "total_size_kb": round(total_size / 1024, 1),
        "cache_dir": str(CACHE_DIR),
        "cache_expiry_hours": CACHE_EXPIRY_HOURS,
    }
