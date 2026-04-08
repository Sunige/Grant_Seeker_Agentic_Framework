"""
What: High-fidelity web scraper that retrieves grant data directly from official funding portals.
Why: Generic web scraping using Google often misses new grants, so direct integration with Innovate UK, UKRI, and the European APIs is necessary.
How: Uses regex, BeautifulSoup, and REST APIs to fetch robust semi-structured HTML/JSON data and standardises it into our schema.
"""
import os
import re
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

TODAY = datetime.today()

# ─────────────────────────────────────────────────────────────────────────────
# Quality gate thresholds
# ─────────────────────────────────────────────────────────────────────────────

# Generic/portal page names that are NOT real competition entries
GENERIC_TITLES = {
    "funding finder", "innovation competitions", "opportunities", "funding opportunities",
    "eu funding & tenders portal", "eu funding and tenders portal", "apply for funding",
    "ukri", "innovate uk", "grants", "support links", "home", "search results",
    "r&d opportunities", "case study library", "business support", "current projects",
    "usa banner", "composites united e.v.", "area of investment and support",
}


def _infer_status(open_date_str: str, close_date_str: str) -> str:
    date_formats = [
        "%d %B %Y", "%d-%b-%y", "%d/%m/%Y", "%B %Y", "%b-%y",
        "%d %b %Y", "%d %b %y",
    ]

    def parse(s):
        if not s or s.strip().lower() in ("", "not specified", "tbc"):
            return None
        s = s.strip()
        for fmt in date_formats:
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None

    open_dt = parse(open_date_str)
    close_dt = parse(close_date_str)

    if close_dt and close_dt < TODAY:
        return "Closed"
    if open_dt and open_dt > TODAY:
        return "Forthcoming" if (open_dt - TODAY).days > 180 else "Upcoming"
    return "Open"


def _fmt_date(raw: str) -> str:
    """Normalise scraped date text to DD-Mon-YY format."""
    if not raw:
        return ""
    raw = raw.strip()
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %Y", "%b %Y"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%-d-%b-%y") if os.name != "nt" else dt.strftime("%#d-%b-%y")
        except ValueError:
            continue
    return raw  # Return as-is if we can't parse


def _extract_competition_id(url: str) -> str:
    """Pull numeric competition ID from an IUK IFS URL."""
    m = re.search(r'/competition/(\d+)/', url)
    return m.group(1) if m else ""


def _is_quality_row(row: dict) -> bool:
    """
    What: Pre-evaluation quality gate for scraped rows.
    Why: Keeps generic pages (like 'EU Funding & Tenders Portal homepage') from clogging the alignment agent.
    How: Evaluates the name against a generic title blacklist, checks string length, and asserts that at least one meaningful piece of context (close date or cost) is present.
    """
    name = row.get("Calls (+ ID Number)", "").strip().lower()
    cost = row.get("Total Eligible Cost", "").strip().lower()
    close_date = row.get("Close Date", "").strip().lower()
    status = row.get("Status", "").strip()

    # Reject generic titles
    if not name or name in GENERIC_TITLES:
        return False
    if any(g in name for g in ["portal", "gateway", "homepage", "sign in", "login"]):
        return False
    # Name must be at least 10 chars
    if len(name) < 10:
        return False

    # Don't include calls that are already closed
    if status == "Closed":
        return False

    # Must have either a cost OR a valid date.
    # If it is missing both, it is likely a generic portal page.
    has_cost = cost and cost not in ("not specified", "", "n/a")
    has_date = close_date and close_date not in ("not specified", "", "n/a")
    if not has_cost and not has_date:
        return False

    return True


class StructuredScoutAgent:
    """
    What: Agent class responsible for scraping raw opportunities.
    Why: Centralises all raw network extraction logic into a single class before alignment logic applies.
    How: Initialises an HTTP Session, hits predefined URLs or APIs, and returns an array of dicts adhering to the expected schema.
    Scrapes Innovate UK IFS, UKRI, and Horizon Europe.
    """

    def __init__(self, target_urls, search_queries):
        # target_urls / search_queries kept for signature compatibility
        self.search_queries = search_queries
        self.seen_links = set()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        })

    # ── PUBLIC ────────────────────────────────────────────────────────────────

    def fetch_opportunities(self):
        """
        What: Main public method coordinating the three scraping phases.
        Why: Allows the orchestrator to fire one command and wait for a single combined array.
        How: Iterates through discrete functions (IUK, UKRI, Horizon), merges the arrays, and runs the result through `_is_quality_row`.
        """
        all_opps = []

        print("[Scout] Phase 1: Scraping Innovate UK IFS competition listings...")
        all_opps += self._scrape_iuk_ifs()

        print("[Scout] Phase 2: Scraping UKRI Opportunities listing...")
        all_opps += self._scrape_ukri_opportunities()

        print("[Scout] Phase 3: Horizon Europe targeted search...")
        all_opps += self._scrape_horizon_europe()

        # Quality gate
        before = len(all_opps)
        all_opps = [r for r in all_opps if _is_quality_row(r)]
        print(f"[Scout] Quality gate: kept {len(all_opps)} / {before} opportunities.")

        return all_opps

    # ── PHASE 1: INNOVATE UK IFS ──────────────────────────────────────────────

    def _scrape_iuk_ifs(self):
        """
        What: Scrapes the Innovate UK IFS "competition search" pages.
        Why: Direct extraction prevents missing grants that haven't been indexed by Google yet.
        How: Iterates through pagination (page 0-4), extracts target URLs from href tags, and passes them to the single-page scraper `_scrape_iuk_competition_page`.
        """
        base = "https://apply-for-innovation-funding.service.gov.uk"
        results = []

        for page in range(0, 5):  # Pages 0–4 covers ~50 competitions (10 per page)
            url = f"{base}/competition/search?keywords=&page={page}"
            try:
                resp = self.session.get(url, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                # Each competition is linked from an <a> whose href matches /competition/NNNN/overview
                comp_links = soup.find_all(
                    "a", href=re.compile(r"/competition/\d+/overview")
                )

                if not comp_links:
                    break  # No more pages

                for a in comp_links:
                    href = a["href"]
                    full_url = urljoin(base, href)
                    if full_url in self.seen_links:
                        continue
                    self.seen_links.add(full_url)

                    comp_id = _extract_competition_id(full_url)
                    google_title = a.get_text(strip=True)

                    print(f"  -> IUK {comp_id}: {google_title[:60]}")
                    detail = self._scrape_iuk_competition_page(full_url, comp_id, google_title)
                    if detail:
                        results.append(detail)

            except Exception as e:
                print(f"  [Scout] IUK IFS page {page} error: {e}")
                break

        print(f"  IUK IFS: collected {len(results)} competitions.")
        return results

    def _scrape_iuk_competition_page(self, url: str, comp_id: str, fallback_title: str) -> dict:
        """Scrape a single IUK competition overview page for all structured fields."""
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator="\n")
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            full_text = "\n".join(lines)
            tl = full_text.lower()

            # ── Title ──────────────────────────────────────────────────────────
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else fallback_title
            # Strip "Funding competition " prefix IUK often prepends (sometimes missing trailing space in H1)
            title = re.sub(r"^(Funding competition\s*|Funding competition)", "", title, flags=re.IGNORECASE).strip()

            # Format: "Short Name (ID)"
            call_name = f"{title} ({comp_id})" if comp_id else title

            # ── Dates ──────────────────────────────────────────────────────────
            open_date = self._extract_iuk_date(tl, full_text, ["opened:", "opens:", "opening date:"])
            close_date = self._extract_iuk_date(tl, full_text, ["closes:", "closing date:", "deadline:"])
            kick_date = self._extract_iuk_date(tl, full_text, ["project start:", "projects start:", "kick-off:", "contract date:"])

            # ── Cost ───────────────────────────────────────────────────────────
            cost = self._extract_iuk_cost(tl)

            # ── Status ─────────────────────────────────────────────────────────
            status = _infer_status(open_date, close_date)
            if "coming soon" in tl or "not yet open" in tl:
                status = "Upcoming"

            # ── Scope: first meaningful paragraph after "Description" heading ──
            scope = self._extract_iuk_scope(soup, tl)

            return {
                "Calls (+ ID Number)": call_name,
                "Open Date": open_date or "Not specified",
                "Close Date": close_date or "Not specified",
                "Kick off date": kick_date or "Not specified",
                "Total Eligible Cost": cost or "Not specified",
                "Status": status,
                "Link": url,
                "SCOPE (Official)": scope,
                "Specific Outcome": "Not specified",  # Alignment agent fills this
            }

        except Exception as e:
            print(f"    [Scout] Error scraping {url}: {e}")
            return None

    def _extract_iuk_date(self, tl: str, full_text: str, labels: list) -> str:
        date_pat = r"(\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+2\d{3})"
        for label in labels:
            idx = tl.find(label)
            if idx != -1:
                snippet = tl[idx: idx + 60]
                m = re.search(date_pat, snippet)
                if m:
                    return _fmt_date(m.group(1).title())
        # Fallback: find all dates and pick contextually
        all_dates = re.findall(date_pat, tl)
        return _fmt_date(all_dates[0].title()) if all_dates else ""

    def _extract_iuk_cost(self, tl: str) -> str:
        # "total eligible costs must be between £X and £Y"
        m = re.search(
            r"total eligible costs?\s+must\s+be\s+between\s+(£[\d,\.]+\s*(?:million|m|k)?)"
            r"\s+and\s+(£[\d,\.]+\s*(?:million|m|k)?)",
            tl,
        )
        if m:
            return f"{m.group(1).strip()} – {m.group(2).strip()}"

        # "up to £Xm per project"
        m2 = re.search(r"up\s+to\s+(£[\d,\.]+\s*(?:million|m|k)?)\s+per\s+project", tl)
        if m2:
            return f"Up to {m2.group(1).strip()}"

        # Generic £ match
        m3 = re.search(r"(£[\d,\.]+\s*(?:million|m|billion|b|k)?)", tl)
        if m3:
            return m3.group(1).strip()

        return ""

    def _extract_iuk_scope(self, soup, tl: str) -> str:
        """Extract a clean 1–2 sentence scope from the competition description."""
        # Find the description section
        for heading in soup.find_all(["h2", "h3"]):
            if "description" in heading.get_text(strip=True).lower():
                content_parents = []
                
                # GovUK grid system: the heading is usually in one column, text in the next
                col_container = heading.find_parent("div", class_=lambda x: x and "govuk-grid-column" in x)
                if col_container:
                    content_div = col_container.find_next_sibling("div", class_=lambda x: x and "govuk-grid-column" in x)
                    if content_div:
                        content_parents.append(content_div)
                
                # Fallback if not inside a gov shell
                content_parents.append(heading.parent)
                
                for parent_container in content_parents:
                    # Look at next siblings of the heading (if they share the same container) or just everything in the content div
                    if parent_container == heading.parent:
                        elements = heading.find_next_siblings(["p", "ul", "li"])
                    else:
                        elements = parent_container.find_all(["p", "ul", "li"])
                        
                    paras = []
                    for el in elements:
                        text = el.get_text(separator=" ", strip=True)
                        # Skip generic banners / support text
                        if "our phone lines" in text.lower() or "innovate uk will be closed" in text.lower() or "support@iuk.ukri.org" in text.lower():
                            continue
                        if "cookies on innovation" in text.lower():
                            continue
                        if text:
                            paras.append(text)
                        if len(" ".join(paras)) >= 400:
                            break
                    
                    if paras:
                        raw = " ".join(paras)
                        raw = re.sub(r"\s+", " ", raw).strip()
                        if len(raw) > 250:
                            raw = raw[:250]
                            idx = max(raw.rfind("."), raw.rfind("!"), raw.rfind("?"))
                            if idx > 80:
                                raw = raw[: idx + 1]
                        return raw + "..."

        # Fallback: find first long paragraph in body text
        for p in soup.find_all("p"):
            t = p.get_text(strip=True)
            if "innovate uk will be closed" in t.lower() or "support" in t.lower():
                continue
            if len(t) > 80 and "cookie" not in t.lower():
                return t[:250] + "..."

        return "Not specified"

    # ── PHASE 2: UKRI OPPORTUNITIES ───────────────────────────────────────────

    def _scrape_ukri_opportunities(self):
        """
        What: Scrapes the UKRI primary opportunities list.
        Why: UKRI acts as a secondary channel for significant UK innovation grants outside of IUK.
        How: Looks for link nodes targeting `ukri.org/opportunity`, crawls them, and executes `_scrape_ukri_page`.
        """
        results = []
        base_url = "https://www.ukri.org/opportunity/"
        try:
            resp = self.session.get(base_url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            links = soup.find_all("a", href=re.compile(r"ukri\.org/opportunity/[^/]+/$"))
            for a in links:
                href = a["href"]
                if not href.startswith("http"):
                    href = "https://www.ukri.org" + href
                if href in self.seen_links:
                    continue
                self.seen_links.add(href)

                title = a.get_text(strip=True)
                print(f"  -> UKRI: {title[:60]}")
                detail = self._scrape_ukri_page(href, title)
                if detail:
                    results.append(detail)

        except Exception as e:
            print(f"  [Scout] UKRI listing error: {e}")

        print(f"  UKRI: collected {len(results)} opportunities.")
        return results

    def _scrape_ukri_page(self, url: str, fallback_title: str) -> dict:
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator="\n")
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            full_text = "\n".join(lines)
            tl = full_text.lower()

            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else fallback_title

            # UKRI pages use "Opening date" / "Closing date" labels
            open_date = self._extract_iuk_date(tl, full_text, ["opening date:", "opens:", "open from:"])
            close_date = self._extract_iuk_date(tl, full_text, ["closing date:", "closes:", "deadline:"])
            kick_date = self._extract_iuk_date(tl, full_text, ["start date:", "project start:"])

            cost = self._extract_iuk_cost(tl)
            # UKRI uses "total value" phrasing
            if not cost:
                m = re.search(r"total\s+value[:\s]+?(£[\d,\.]+\s*(?:million|m|k)?)", tl)
                if m:
                    cost = m.group(1).strip()

            status = _infer_status(open_date, close_date)
            scope = self._extract_iuk_scope(soup, tl)

            # Try to extract UKRI reference ID from page
            ref_match = re.search(r'\bMR/[A-Z0-9]+\b|\bEP/[A-Z0-9]+\b|\bIUK-\d+\b', full_text)
            ref_id = ref_match.group(0) if ref_match else urlparse(url).path.split("/")[-2].replace("-", " ").title()[:20]
            call_name = f"{title} ({ref_id})"

            return {
                "Calls (+ ID Number)": call_name,
                "Open Date": open_date or "Not specified",
                "Close Date": close_date or "Not specified",
                "Kick off date": kick_date or "Not specified",
                "Total Eligible Cost": cost or "Not specified",
                "Status": status,
                "Link": url,
                "SCOPE (Official)": scope,
                "Specific Outcome": "Not specified",
            }

        except Exception as e:
            print(f"    [Scout] Error scraping UKRI {url}: {e}")
            return None

    # ── PHASE 3: HORIZON EUROPE (EU API & CORDIS CONNECTION) ────────────────
    #
    # This phase queries the authoritative EU Funding & Tenders Portal REST API.
    # The F&T Portal lists all open funding opportunities. Funded projects are 
    # subsequently published to the CORDIS database once they commence. 
    # By querying this API, the system proactively discovers Horizon Europe grants
    # before they transition into active CORDIS projects.
    # ─────────────────────────────────────────────────────────────────────────────

    def _scrape_horizon_europe(self):
        """
        What: Queries the official EU Funding & Tenders REST API.
        Why: Standard HTML scraping against EU portals is notoriously unstable. API access directly retrieves structured, authoritative JSON.
        How: Converts strategic keywords to API params. Submits to the REST endpoint targeting grants (status Open/Forthcoming in Horizon Europe framework). Maps JSON output fields such as `startDate` and `deadlineDate` into standard dictionary keys.
        """
        results = []
        import config
        # Use the NCC strategic keywords to intelligently search the EU portal natively
        api_queries = config.NCC_STRATEGIC_KEYWORDS
        if not api_queries:
            # Fallback if config is empty
            api_queries = ["advanced manufacturing", "composites", "clean energy"]

        # EU F&T Portal REST API endpoint (upstream data source for CORDIS)
        base_api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/search?apiKey=SEDIA&pageSize=50&pageNumber=1&text="
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Payload filters: Open/Forthcoming Horizon Europe grants
        payload = {
            "query": {
                "bool": {
                    "must": [
                        # Type 0,1,2,8 roughly cover grants/tenders, but framework ensures it's Horizon
                        {"terms": {"type": ["0", "1", "2", "8"]}},
                        # Statuses: 31094501 = Open, 31094502 = Forthcoming
                        {"terms": {"status": ["31094501", "31094502"]}},
                        # Framework: 43108390 = Horizon Europe (2021-2027)
                        {"terms": {"frameworkProgramme": ["43108390"]}}
                    ]
                }
            }
        }

        for query in api_queries:
            # The EU API takes URL-encoded text
            url = base_api_url + requests.utils.quote(query)
            print(f"  -> Horizon API search for keyword: '{query[:40]}'")
            
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=20)
                resp.raise_for_status()
                data = resp.json()
                items = data.get("results", [])
                
                for item in items:
                    meta = item.get("metadata", {})
                    
                    identifier = meta.get("identifier", [""])[0]
                    title = meta.get("title", [""])[0]
                    if not identifier or identifier in self.seen_links:
                        # Use identifier as a unique key for EU calls
                        continue
                    self.seen_links.add(identifier)
                    
                    full_url = item.get("url", f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{identifier}")
                    
                    open_date_raw = meta.get("startDate", [""])[0]
                    close_date_raw = meta.get("deadlineDate", [""])[0]
                    
                    # Convert ISO dates to standard DD-Mon-YY
                    def format_iso(iso_str):
                        if not iso_str: return "Not specified"
                        try:
                            idx = iso_str.find("T")
                            if idx != -1: iso_str = iso_str[:idx]
                            dt = datetime.strptime(iso_str, "%Y-%m-%d")
                            return dt.strftime("%-d-%b-%y") if os.name != "nt" else dt.strftime("%#d-%b-%y")
                        except ValueError:
                            return iso_str
                            
                    open_date = format_iso(open_date_raw)
                    close_date = format_iso(close_date_raw)
                    
                    # In EU API, budgets are often buried in 'budgetOverview' JSON strings, standard scraper defaults here to fallback
                    cost = "Not specified"
                    
                    raw_desc = meta.get("description", [""])[0]
                    if not raw_desc:
                        raw_desc = meta.get("descriptionByte", [""])[0]
                        
                    scope = "Not specified"
                    if raw_desc:
                        soup = BeautifulSoup(raw_desc, "html.parser")
                        text_only = soup.get_text(separator=" ", strip=True)
                        scope = text_only[:250] + ("..." if len(text_only) > 250 else "")
                    
                    status = _infer_status(open_date, close_date)
                    
                    call_name = f"{title} ({identifier})" if identifier else title
                    print(f"    -> EU topic ID {identifier}: {title[:50]}")
                    
                    results.append({
                        "Calls (+ ID Number)": call_name,
                        "Open Date": open_date,
                        "Close Date": close_date,
                        "Kick off date": "Not specified",
                        "Total Eligible Cost": cost,
                        "Status": status,
                        "Link": full_url,
                        "SCOPE (Official)": scope,
                        "Specific Outcome": "Not specified",
                    })

            except Exception as e:
                print(f"  [Scout] Horizon API error on query '{query[:40]}': {e}")
                
        print(f"  Horizon EU: collected {len(results)} topics via API.")
        return results


# Backwards-compatible alias
ScoutAgent = StructuredScoutAgent
