"""
What: Central configuration file for the Grant Discovery framework.
Why: Separating these lists makes it safe and easy for non-technical users to update URLs, search domains, and strategic keywords without risking changes to the core application logic.
How: Agents import these constants and iterate over them (e.g. alignment_agent uses NCC_STRATEGIC_KEYWORDS, scout_agent uses URLs and queries).
"""

# TARGET_URLS list
# What: A list of legacy or non-API web sources for scraping.
# Why: Authoritative sources are scraped directly by StructuredScoutAgent, but this array is kept for legacy compatibility and fallback use.
# How: The scout ignores the URLs for IUK and UKRI, as they are hardcoded directly in the python logic, but reads these for supplementary sources.
TARGET_URLS = [
    # IUK IFS — scraped directly (all pages of /competition/search)
    "https://apply-for-innovation-funding.service.gov.uk/competition/search",
    # UKRI Opportunities — scraped directly
    "https://www.ukri.org/opportunity/",
    # DASA — kept as supplementary
    "https://www.gov.uk/government/publications/defence-and-security-accelerator-dasa-open-call-for-innovation",
]

# SEARCH_QUERIES list
# What: Targeted domain searches used for the Horizon Europe topics.
# Why: Standard web scraping is often blocked or generic, so we use precise site-specific strings for external APIs.
# How: The EU Funding & Tenders Portal API natively integrates these keywords to discover specific topics instead of random links.
# (Note: IUK IFS and UKRI are scraped directly — no generic queries needed for those).
SEARCH_QUERIES = [
    "HORIZON-CL5-2026 site:ec.europa.eu/info/funding-tenders",
    "HORIZON-CL4-2026 site:ec.europa.eu/info/funding-tenders",
    "HORIZON-CL2-2026 site:ec.europa.eu/info/funding-tenders",
    "HORIZON JU CLEANH2 2026 open call site:clean-hydrogen.europa.eu OR site:ec.europa.eu",
    "HORIZON-MSCA-2026 site:ec.europa.eu/info/funding-tenders",
    "DASA open call innovation 2026 site:gov.uk",
]

# NCC_STRATEGIC_KEYWORDS list
# What: A comprehensive list of technical domains and themes representing NCC's Strategic Pathways.
# Why: Evaluates whether a scraped grant is actually relevant to the NCC, filtering out noise.
# How: Used by the StrategyAlignmentAgent. The code checks scraped grant titles and scope for matches against these exact phrases.
NCC_STRATEGIC_KEYWORDS = [
    "Advanced Materials",
    "Composites",
    "Ceramic Matrix Composites",
    "CMC",
    "Hydrogen Storage",
    "Digital Twin",
    "MBSE",
    "Model-Based Systems Engineering",
    "Digital Engineering",
    "Circularity",
    "End of Life Processing",
    "Blade Recycling",
    "Thermoplastic",
    "Aerospace Structures",
    "Sustainable Manufacturing",
    "Net Zero Industry",
    "Hypersonics",
    "Thermal Management",
    "Autonomous Systems",
    "UAS",
    "Oil & Gas",
    "New Nuclear",
    "Wind Energy",
    "High-Rate Deposition",
    "Automated Manufacture",
    "Non-Destructive Testing",
    "NDT",
    "Assurance",
    "Cryotanks",
    "Pressure Vessels",
    "Dry Wing Architectures",
    "Resilient Supply Chain",
    "Maritime Decarbonisation",
    "Clean Maritime",
    "Zero Emission Shipping",
]

# TARGETED_COMPANIES list
# What: A list of major industry players and key partners associated with NCC domains.
# Why: Allows the platform to later flag grants if they mention these high-value partners.
# How: Passed to the StrategyAlignmentAgent to detect corporate presence in the grant calls.
TARGETED_COMPANIES = [
    "Airbus",
    "BAE Systems",
    "Rolls Royce",
    "Vestas",
    "Leonardo",
    "SGRE",               # Siemens Gamesa Renewable Energy
    "Siemens Gamesa",
    "GE Vernova",
    "Baker Hughes",
    "GKN Aerospace",
    "Spirit AeroSystems",
    "Boeing",
    "EDF",
    "Babcock",
    "Thales",
    "MBDA",
    "QinetiQ",
    "Shell",
    "BP",
    "Equinor",
    "Orsted",
]
