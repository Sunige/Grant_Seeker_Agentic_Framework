"""
What: Evaluates and filters scraped grant opportunities against the the Target Organisation's strategic goals.
Why: Ensures that the final Excel dashboard only displays highly relevant, curated grants instead of a noisy mix of generic funding streams.
How: Interfaces with an OpenRouter LLM (GPT-4o) using zero-shot classification to confirm alignment and extract clean metadata. If the API fails, it falls back to basic keyword matching.
"""
import os
import json
import re
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

TODAY = datetime.today()


def _infer_status(open_date_str: str, close_date_str: str) -> str:
    date_formats = [
        "%d %B %Y", "%d-%b-%y", "%d/%m/%Y", "%B %Y", "%b-%y",
        "%d %b %Y", "%d %b %y",
    ]

    def parse(s):
        if not s or s.strip().lower() in ("", "not specified", "tbc"):
            return None
        for fmt in date_formats:
            try:
                return datetime.strptime(s.strip(), fmt)
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


class StrategyAlignmentAgent:
    """
    What: Class orchestrating the strategic validation logic.
    Why: By isolating strategy checks from web scraping logic (scout), the system remains modular.
    How: Evaluates each grant opportunity against Target strategy. Uses GPT-4o via OpenRouter when available; falls back to keyword matching. Enforces quality: concise, factual SCOPE and Specific Outcome <= 20 words each.
    """

    def __init__(self, strategic_keywords, target_companies):
        self.strategic_keywords = strategic_keywords
        self.target_companies = target_companies

    def evaluate_opportunity(self, opportunity_data):
        """
        What: The primary evaluation method called per grant.
        Why: Decides whether to invoke the high-quality LLM pipeline or fall back to keyword logic.
        How: Extracts the scope and URL, checks for an API key, and routes to either `_call_openrouter` or `_fallback_match`.
        """
        scope = opportunity_data.get("SCOPE (Official)", "")
        call_name = opportunity_data.get("Calls (+ ID Number)", "")
        scope_for_llm = scope[:3000]

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if OpenAI and api_key:
            return self._call_openrouter(opportunity_data, scope_for_llm, call_name, api_key)
        else:
            return self._fallback_match(opportunity_data, scope, call_name)

    # ── LLM PATH ──────────────────────────────────────────────────────────────

    def _call_openrouter(self, data, scope, call_name, api_key):
        """
        What: Queries an LLM via OpenRouter.
        Why: LLMs natively understand semantic nuance, meaning they can detect a grant's relevance to 'Composites' even if exact keywords are poorly phrased.
        How: Sends a rigid JSON structured prompt containing the `scope` and asks for a Yes/No boolean on `Aligned`, plus tightly formatted summaries.
        """
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

        prompt = f"""You are a grant analyst for the Target Organisation, a UK Research & Technology Organisation specialising in composite materials and advanced manufacturing.

Target Organisation TECHNOLOGY STRATEGY:
The Target Organisation exclusively pursues grants within:
Sectors: Aerospace, Defence, Energy.
Themes: Advanced Materials, Hypersonics, Ceramics, Recycling, Composite/Metallic Processes, Production Systems, Systems Engineering, Design & Test, Circularity (Hydrogen storage, Wind blades), Autonomous Systems, and Digital Engineering/Twins.

Grants focused on unrelated domains (e.g. healthcare, agriculture, biological/eco-modelling, pure software not related to manufacturing/engineering, unconnected civic infrastructure) are strictly OUT OF SCOPE.

TASK: Review this funding call scraped from the official competition page. Determine if it aligns with the strategy above. Fill in the 10 fields below with high-quality, tightly formatted values explicitly matching the EXAMPLES.

EXAMPLES OF PERFECT OUTPUT:
- Calls: "CMDC 7: Feasibility (IUK-59100)"
- Open Date: "11-Mar-26"
- Close Date: "15-Jul-26"
- Kick off date: "Apr-27"
- Total Eligible Cost: "£100k – £1m"
- Status: "Open"
- SCOPE (Official): "Technical and economic feasibility studies for clean maritime or maritime skills."
- Specific Outcome: "A detailed business case and technical roadmap for future commercialisation."
- Aligned: "Yes"

FUNDING CALL:
Title: {call_name}
Page content: {scope}

Return ONLY a JSON object with these EXACT keys:
{{
  "Calls (+ ID Number)": "Short descriptive label + (competition ID from URL or page). Format: 'Name: Subtype (ID)'. Max 60 chars. Extract the real official competition name from the page content. Use the numeric IUK ID or Horizon topic ID.",
  "Open Date": "DD-Mon-YY (e.g. 07-Apr-26). Extract from page. 'Not specified' if absent.",
  "Close Date": "DD-Mon-YY (e.g. 03-Jun-26). Extract from page. 'Not specified' if absent.",
  "Kick off date": "Mon-YY format (e.g. Oct-26) for expected project start. 'Not specified' if absent.",
  "Total Eligible Cost": "Per-project range like '£150k – £1.5m' or total pot like '~€13m (Per Proj)'. Extract exact figures from page. 'Not specified' if absent.",
  "Status": "EXACTLY one of: Open | Upcoming | Forthcoming | Closed. Infer from dates. Open = currently accepting applications.",
  "Link": "Keep the URL already provided.",
  "SCOPE (Official)": "EXACTLY one factual sentence of max 20 words extracted from the official brief. Must describe what funded projects must DO, not what exists.",
  "Specific Outcome": "EXACTLY one measurable sentence of max 20 words describing the target deliverable. Must be specific and quantifiable.",
  "Aligned": "EXACTLY 'Yes' or 'No'. Is this grant opportunity aligned with the Target Technology Strategy themes?"
}}"""

        try:
            response = client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)

            # --- alignment Check ---
            # What: Evaluates boolean output from LLM.
            # Why: So we drop entirely irrelevant grants from our resulting dashboard before saving them.
            # How: If Aligned is explicitly 'No', we return None.
            if result.get("Aligned", "No").strip() == "No":
                # Drop this entirely
                return None

            new_data = {}
            for key in [
                "Calls (+ ID Number)", "Open Date", "Close Date",
                "Kick off date", "Total Eligible Cost", "Status",
                "Link", "SCOPE (Official)", "Specific Outcome",
            ]:
                llm_val = result.get(key, "").strip()
                # Prefer LLM value when it's substantive
                if llm_val and llm_val.lower() not in ("not specified", ""):
                    new_data[key] = llm_val
                else:
                    # Fall back to what Scout scraped
                    new_data[key] = str(data.get(key, "Not specified")).strip() or "Not specified"

            # Always keep original link
            new_data["Link"] = data.get("Link", new_data.get("Link", ""))

            # Re-infer status from dates if LLM gave something invalid
            if new_data.get("Status") not in ("Open", "Upcoming", "Forthcoming", "Closed"):
                new_data["Status"] = _infer_status(
                    new_data.get("Open Date", ""), new_data.get("Close Date", "")
                )

            return new_data

        except Exception as e:
            print(f"  [Alignment] OpenRouter error: {e}")
            return self._fallback_match(data, scope, call_name)

    # ── FALLBACK PATH ────────────────────────────────────────────────────────

    def _fallback_match(self, data, scope, call_name):
        """
        What: Failsafe evaluation using literal text parsing.
        Why: Ensures the pipeline does not stop running if OpenRouter API credits dry up or the network fails.
        How: Concatenates scope/title, lowercases them, and checks for substrings from `strategic_keywords`.
        """
        combined = (scope + " " + call_name).lower()
        matched_kws = [kw for kw in self.strategic_keywords if kw.lower() in combined]

        if len(matched_kws) >= 3:
            outcome = f"HIGH Target alignment – matched: {', '.join(matched_kws[:5])}."
        elif len(matched_kws) >= 1:
            outcome = f"MEDIUM Target alignment – matched: {', '.join(matched_kws)}."
        else:
            outcome = "LOW alignment – no direct Target keyword match; manual review needed."

        # Trim outcome to ~100 chars
        if len(outcome) > 100:
            outcome = outcome[:97] + "..."

        result = {k: str(data.get(k, "Not specified")).strip() or "Not specified"
                  for k in ["Calls (+ ID Number)", "Open Date", "Close Date",
                             "Kick off date", "Total Eligible Cost", "Link",
                             "SCOPE (Official)"]}
        result["Status"] = _infer_status(result.get("Open Date", ""), result.get("Close Date", ""))
        result["Specific Outcome"] = outcome

        # Trim scope
        scope_clean = re.sub(r"\s+", " ", str(data.get("SCOPE (Official)", "")).strip())
        if len(scope_clean) > 250:
            scope_clean = scope_clean[:247] + "..."
        result["SCOPE (Official)"] = scope_clean or "Not specified"

        return result
