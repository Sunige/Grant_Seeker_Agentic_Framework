import pandas as pd
import os

# ─────────────────────────────────────────────────────────────────────────────
# SEED DATA – 11 known grant calls in the new schema
# This file creates the master template. Run orchestrator.py to append live calls.
# ─────────────────────────────────────────────────────────────────────────────

COLUMNS = [
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

SEED_DATA = [
    {
        "Calls (+ ID Number)": "Offshore Wind: Feasibility (2432)",
        "Open Date": "07-Apr-26",
        "Close Date": "03-Jun-26",
        "Kick off date": "01-Oct-26",
        "Total Eligible Cost": "£50k – £250k",
        "Status": "Upcoming",
        "Link": "https://apply-for-innovation-funding.service.gov.uk/competition/2432/overview",
        "SCOPE (Official)": "Early-stage innovation in advanced turbines, foundations, cables, and O&M.",
        "Specific Outcome": "Build a pipeline of high-growth UK businesses for future scale-up.",
    },
    {
        "Calls (+ ID Number)": "Offshore Wind: Industrial Research (2433)",
        "Open Date": "07-Apr-26",
        "Close Date": "03-Jun-26",
        "Kick off date": "01-Oct-26",
        "Total Eligible Cost": "£150k – £1.5m",
        "Status": "Upcoming",
        "Link": "https://apply-for-innovation-funding.service.gov.uk/competition/2433/overview",
        "SCOPE (Official)": "Mid-stage research on deepwater solutions (>50m), foundations, and electrical systems.",
        "Specific Outcome": "Technology advancements aligned with the UK Offshore Wind Industrial Growth Plan.",
    },
    {
        "Calls (+ ID Number)": "ZEVI 2: Electric Power (IUK-58214)",
        "Open Date": "26-Mar-26",
        "Close Date": "16-Sep-26",
        "Kick off date": "Jan-27",
        "Total Eligible Cost": "£6m – £60m",
        "Status": "Open",
        "Link": "https://apply-for-innovation-funding.service.gov.uk/competition/58214/overview",
        "SCOPE (Official)": "Real-world demo of 100% battery electric vessels and shore-side charging infra.",
        "Specific Outcome": "Validated operational and commercial performance data over a 3-year demo phase.",
    },
    {
        "Calls (+ ID Number)": "ZEVI 2: Alt Fuels / Efficiency (IUK-58215)",
        "Open Date": "26-Mar-26",
        "Close Date": "16-Sep-26",
        "Kick off date": "Jan-27",
        "Total Eligible Cost": "£6m – £60m",
        "Status": "Open",
        "Link": "https://apply-for-innovation-funding.service.gov.uk/competition/58215/overview",
        "SCOPE (Official)": "Deployment and operation of vessels using zero-emission fuels or energy efficiency tech.",
        "Specific Outcome": "Quantified GHG reduction and infrastructure integration for long-term use.",
    },
    {
        "Calls (+ ID Number)": "CMDC 7: Deployment Trials (IUK-59102)",
        "Open Date": "11-Mar-26",
        "Close Date": "15-Jul-26",
        "Kick off date": "Apr-27",
        "Total Eligible Cost": "£3m – £15m",
        "Status": "Open",
        "Link": "https://apply-for-innovation-funding.service.gov.uk/competition/59102/overview",
        "SCOPE (Official)": "Large-scale trials of clean maritime tech (TRL 7-8) in operational environments.",
        "Specific Outcome": "Evidence of technical and commercial viability in \"live\" maritime settings.",
    },
    {
        "Calls (+ ID Number)": "CMDC 7: Pre-deployment (IUK-59101)",
        "Open Date": "11-Mar-26",
        "Close Date": "15-Jul-26",
        "Kick off date": "Apr-27",
        "Total Eligible Cost": "£750k – £6m",
        "Status": "Open",
        "Link": "https://apply-for-innovation-funding.service.gov.uk/competition/59101/overview",
        "SCOPE (Official)": "Testing and validation of maritime systems in controlled or simulated environments.",
        "Specific Outcome": "A verified, functional prototype ready for final stage operational deployment.",
    },
    {
        "Calls (+ ID Number)": "CMDC 7: Feasibility (IUK-59100)",
        "Open Date": "11-Mar-26",
        "Close Date": "15-Jul-26",
        "Kick off date": "Apr-27",
        "Total Eligible Cost": "£100k – £1m",
        "Status": "Open",
        "Link": "https://apply-for-innovation-funding.service.gov.uk/competition/59100/overview",
        "SCOPE (Official)": "Technical and economic feasibility studies for clean maritime or maritime skills.",
        "Specific Outcome": "A detailed business case and technical roadmap for future commercialisation.",
    },
    {
        "Calls (+ ID Number)": "AI Champions: Frontier AI (IUK-62145)",
        "Open Date": "17-Mar-26",
        "Close Date": "29-Apr-26",
        "Kick off date": "Oct-26",
        "Total Eligible Cost": "£150k – £250k",
        "Status": "Open",
        "Link": "https://apply-for-innovation-funding.service.gov.uk/competition/62145/overview",
        "SCOPE (Official)": "Development of state-of-the-art AI/ML to de-risk technical feasibility in the UK.",
        "Specific Outcome": "A proof-of-concept prototype and technical white paper on AI novelty.",
    },
    {
        "Calls (+ ID Number)": "HE: AI Materials Discovery (CL4-2026-01-23)",
        "Open Date": "06-Jan-26",
        "Close Date": "21-Apr-26",
        "Kick off date": "Jan-27",
        "Total Eligible Cost": "~€13m (Per Proj)",
        "Status": "Open",
        "Link": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/horizon-cl4-2026-01-23",
        "SCOPE (Official)": "Accelerating the discovery of materials/chemicals via AI and digital twin models.",
        "Specific Outcome": "A digital discovery pipeline that accelerates the material development cycle by 50%.",
    },
    {
        "Calls (+ ID Number)": "HE: Integrated Battery Prod (CL5-2026-10-D2-03)",
        "Open Date": "04-Jun-26",
        "Close Date": "08-Oct-26",
        "Kick off date": "May-27",
        "Total Eligible Cost": "~€33m (Pot)",
        "Status": "Forthcoming",
        "Link": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/horizon-cl5-2026-10-d2-03",
        "SCOPE (Official)": "Integrated product and process development for next-gen Li-based batteries.",
        "Specific Outcome": "Demonstrated increase in production yield and measurable reduction in scrap.",
    },
    {
        "Calls (+ ID Number)": "HE: Wind Energy Systems (CL5-2026-09-D3-03)",
        "Open Date": "05-May-26",
        "Close Date": "15-Sep-26",
        "Kick off date": "May-27",
        "Total Eligible Cost": "~€93m (Pot)",
        "Status": "Forthcoming",
        "Link": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/horizon-cl5-2026-09-d3-03",
        "SCOPE (Official)": "Floating wind demo, AI/Robotics for remote O&M, and circularity/recycling.",
        "Specific Outcome": "Optimized floating turbine designs and autonomous maintenance models.",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Build & write
# ─────────────────────────────────────────────────────────────────────────────

df_seed = pd.DataFrame(SEED_DATA, columns=COLUMNS)

instructions = pd.DataFrame({
    "How This Framework Works": [
        "1. Edit config.py to add/remove URLs, search queries, keywords, or target companies.",
        "2. Set SERPER_API_KEY and OPENROUTER_API_KEY in the .env file.",
        "3. Run: python orchestrator.py",
        "4. The Discovery Agent searches for new grant portals and adds them to config.py.",
        "5. The Scout Agent searches Google (via Serper) and scrapes each page for dates and funding info.",
        "6. The Alignment Agent evaluates each call against NCC strategy (via OpenRouter LLM or keyword fallback).",
        "7. Results are written to the 'Opportunities Dashboard' tab.",
        "8. Re-run weekly to pick up new calls. Existing calls are deduplicated automatically.",
        "",
        "Column Guide:",
        "  Calls (+ ID Number)  – Official call name and competition/topic ID.",
        "  Open Date            – Date the competition opened for applications.",
        "  Close Date           – Application deadline.",
        "  Kick off date        – Expected project start / contract commencement date.",
        "  Total Eligible Cost  – Per-project eligible cost range or total pot.",
        "  Status               – Open | Upcoming | Forthcoming | Closed.",
        "  Link                 – Direct URL to the competition page.",
        "  SCOPE (Official)     – Official scope description from the competition brief.",
        "  Specific Outcome     – Target deliverable / measurable outcome for funded projects.",
    ]
})

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Grant_Opportunities_Template_v2.xlsx")

with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
    df_seed.to_excel(writer, sheet_name="Opportunities Dashboard", index=False)
    instructions.to_excel(writer, sheet_name="Framework Instructions", index=False)

print(f"✓ Template created: {output_path}")
print(f"  Rows: {len(df_seed)}  Columns: {len(COLUMNS)}")
print(f"  Columns: {', '.join(COLUMNS)}")
