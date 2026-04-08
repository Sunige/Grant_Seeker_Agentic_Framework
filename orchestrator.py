"""
What: Main execution entry point that coordinates the grant discovery pipeline.
Why: Centralises the workflow so that scraping, alignment, and data writing occur in a guaranteed, repeatable sequence.
How: Instantiates the ScoutAgent to fetch raw opportunities, passes them systematically to the StrategyAlignmentAgent for filtering and enrichment, and finally merges surviving records into the Excel dashboard via Pandas.
"""
import pandas as pd
import os
import re
from dotenv import load_dotenv
load_dotenv()

from scout_agent import ScoutAgent
from alignment_agent import StrategyAlignmentAgent
from discovery_agent import DiscoveryAgent

from config import TARGET_URLS, SEARCH_QUERIES, STRATEGIC_KEYWORDS, TARGETED_COMPANIES

# New column schema (matches user-facing dashboard)
DASHBOARD_COLUMNS = [
    "Calls (+ ID Number)",
    "Open Date",
    "Close Date",
    "Kick off date",
    "Total Eligible Cost",
    "Status",
    "Link",
    "SCOPE (Official)",
    "Specific Outcome",
]

class ExcellenceOrchestrator:
    """
    What: Class governing the lifecycle of a single pipeline run.
    Why: Encapsulates state (such as the target Excel path) and provides a clean interface (.run()) to execute the pipeline.
    How: Uses sequential method calls to trigger downstream agents and manages the `_write_output` merging logic.
    """
    def __init__(self, excel_path="Grant_Opportunities_Template_v2.xlsx"):
        self.excel_path = os.path.join(os.getcwd(), excel_path)
        
    def run(self):
        """
        What: The main orchestrator function.
        Why: It serves as the primary controller, orchestrating the step-by-step grant tracking process.
        How: Prints the config banner, triggers the scout agent, maps results to the alignment agent, and submits to local output.
        """
        print("=" * 60)
        print("  GRANT STRATEGY MULTI-AGENT FRAMEWORK")
        print("=" * 60)
        print(f"  Config: {len(TARGET_URLS)} URLs | {len(SEARCH_QUERIES)} queries")
        print(f"  Keywords: {len(STRATEGIC_KEYWORDS)} | Companies: {len(TARGETED_COMPANIES)}")
        print("=" * 60)

        # Step 0: Discovery Agent (disabled — StructuredScoutAgent scrapes sources directly)
        updated_urls = TARGET_URLS
        print(f"[Orchestrator] Structured scout will query IUK IFS, UKRI, and Horizon EU directly.")
        
        # Step 1: Scout Agent
        scout = ScoutAgent(updated_urls, SEARCH_QUERIES)
        raw_opportunities = scout.fetch_opportunities()
        
        if not raw_opportunities:
            print("\n[Orchestrator] No new opportunities found from live search.")
            print("[Orchestrator] Preserving existing seeded data in the Excel file.")
            return
        
        # Step 2: Alignment Agent
        aligner = StrategyAlignmentAgent(STRATEGIC_KEYWORDS, TARGETED_COMPANIES)
        enriched = []
        
        total = len(raw_opportunities)
        print(f"\n[Orchestrator] Evaluating {total} opportunities against Target Technology Strategy...")
        for i, opp in enumerate(raw_opportunities):
            opp_name = opp.get('Calls (+ ID Number)', opp.get('Name of the call', ''))[:60]
            print(f"  [{i+1}/{total}] {opp_name}...")
            enriched_opp = aligner.evaluate_opportunity(opp)
            if enriched_opp is None:
                print(f"    -> [Dropped] Rejected by Strategy Alignment constraints.")
                continue
            enriched.append(enriched_opp)
            
        print(f"\n[Orchestrator] {len(enriched)} / {total} opportunities passed alignment.")
            
        # Step 3: Write to Excel (merge with existing seed data)
        self._write_output(enriched)
        
    def _write_output(self, new_data):
        """
        What: Writes newly enriched grant opportunities to the Excel dashboard.
        Why: Ensures we persist new discoveries while safely preserving historical "seed" data (hand-picked grants) and discarding scraped noise.
        How: Loads the existing Excel logic into a Pandas DataFrame, concats the new records, runs de-duplication rules, applies a quality gate on scraped entries, and saves the file.
        """
        print(f"\n[Orchestrator] Merging {len(new_data)} live opportunities with existing data...")
        
        # Load existing seed/historical data if the file exists
        existing_df = pd.DataFrame(columns=DASHBOARD_COLUMNS)
        seed_names = set()
        if os.path.exists(self.excel_path):
            try:
                existing_df = pd.read_excel(self.excel_path, sheet_name="Opportunities Dashboard")
                # Normalise columns – drop any extras from old schema
                existing_df = existing_df[[c for c in DASHBOARD_COLUMNS if c in existing_df.columns]]
                # Track seed row names so the quality gate won't remove them
                seed_names = set(existing_df["Calls (+ ID Number)"].dropna().astype(str))
                print(f"  Loaded {len(existing_df)} existing rows from Excel ({len(seed_names)} seeds protected from quality gate).")
            except Exception as e:
                print(f"  [Warning] Could not read existing file: {e}")
        
        new_df = pd.DataFrame(new_data)
        
        # Ensure all new columns exist
        for col in DASHBOARD_COLUMNS:
            if col not in new_df.columns:
                new_df[col] = "Not specified"
        new_df = new_df[DASHBOARD_COLUMNS]
        
        # Combine and deduplicate – new data wins on conflicts
        combined = pd.concat([existing_df, new_df], ignore_index=True)
        
        # CLEANING
        combined = combined[combined["Calls (+ ID Number)"].notna()]
        combined = combined[combined["Calls (+ ID Number)"].str.strip() != ""]
        combined = combined[~combined["Calls (+ ID Number)"].str.contains("Example:", case=False, na=False)]
        
        # Deduplicate – keep the latest version
        combined.drop_duplicates(subset=["Calls (+ ID Number)"], keep="last", inplace=True)
        combined.drop_duplicates(subset=["Link"], keep="last", inplace=True)
        
        # Fill blanks
        combined.fillna("Not specified", inplace=True)
        combined.replace(
            {"": "Not specified", "Unknown": "Not specified",
             "Seeking...": "Not specified", "Extraction Pending": "Not specified"},
            inplace=True
        )
        
        # Sort by Status: Open → Upcoming → Forthcoming → remove Closed
        # Why: Ensures the most actionable (Open/Upcoming) grants appear at the top of the Excel sheet.
        # How: Maps string statuses to an integer (_sort) purely for robust dataframe sorting mechanics.
        # Apply quality gate: discard live rows where cost AND close date are both unknown
        status_order = {"Open": 0, "Upcoming": 1, "Forthcoming": 2, "Closed": 3, "Not specified": 4}
        combined["_sort"] = combined["Status"].map(status_order).fillna(4)

        # --- Quality filter on LIVE (non-seed) rows only ---
        is_seed = combined["Calls (+ ID Number)"].isin(seed_names)
        is_closed = combined["Status"] == "Closed"
        no_cost = combined["Total Eligible Cost"].str.strip().str.lower().isin(
            ["not specified", "", "n/a"]
        )
        no_date = combined["Close Date"].str.strip().str.lower().isin(
            ["not specified", "", "n/a"]
        )
        # Remove closed rows that aren't seeds
        combined = combined[is_seed | ~is_closed]
        # Remove rows with neither cost nor close date (generic portal pages)
        combined = combined[is_seed | ~(no_cost & no_date)]
        # Remove rows where name contains "Funding competition" prefix artifact (IUK scrape noise)
        combined["Calls (+ ID Number)"] = combined["Calls (+ ID Number)"].str.replace(
            r"^Funding competition\s*", "", regex=True
        )

        combined.sort_values(by=["_sort", "Close Date"], inplace=True)
        combined.drop(columns=["_sort"], inplace=True)
        combined.reset_index(drop=True, inplace=True)
        
        # Sanitise: remove illegal XML characters that crash openpyxl
        illegal_xml_re = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')
        for col in combined.columns:
            combined[col] = combined[col].astype(str).apply(lambda x: illegal_xml_re.sub('', x))
        
        with pd.ExcelWriter(self.excel_path, engine="openpyxl", mode="w") as writer:
            combined.to_excel(writer, sheet_name="Opportunities Dashboard", index=False)
            
            # Instructions tab
            instructions = pd.DataFrame({
                "How This Framework Works": [
                    "1. Edit config.py to add/remove URLs, search queries, keywords, or target companies.",
                    "2. Set SERPER_API_KEY and OPENROUTER_API_KEY in the .env file.",
                    "3. Run: python orchestrator.py",
                    "4. The Discovery Agent searches for new grant portals and adds them to config.py.",
                    "5. The Scout Agent searches Google (via Serper) and scrapes each page for dates and funding info.",
                    "6. The Alignment Agent evaluates each call against Target strategy (via OpenRouter LLM or keyword fallback).",
                    "7. Results are merged with existing rows and written to the 'Opportunities Dashboard' tab.",
                    "8. Re-run weekly to pick up new calls. Existing calls are deduplicated automatically.",
                ]
            })
            instructions.to_excel(writer, sheet_name="Framework Instructions", index=False)
            
        print("=" * 60)
        print(f"  COMPLETE: {len(combined)} opportunities in {os.path.basename(self.excel_path)}")
        print("=" * 60)

if __name__ == "__main__":
    orchestrator = ExcellenceOrchestrator()
    orchestrator.run()
