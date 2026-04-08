# config.py
# Authoritative sources are scraped directly by StructuredScoutAgent.
# TARGET_URLS is kept for legacy compatibility but the new scout ignores it.

TARGET_URLS = [
    # IUK IFS — scraped directly (all pages of /competition/search)
    "https://apply-for-innovation-funding.service.gov.uk/competition/search",
    # UKRI Opportunities — scraped directly
    "https://www.ukri.org/opportunity/",
    # DASA — kept as supplementary
    "https://www.gov.uk/government/publications/defence-and-security-accelerator-dasa-open-call-for-innovation",
]

# SEARCH_QUERIES: used ONLY for Horizon Europe targeted topic-ID searches.
# The EU Funding & Tenders Portal API is directly integrated to discover topics.
# This serves as the upstream opportunity source for projects that will eventually
# be published on CORDIS (Community Research and Development Information Service).
# IUK IFS and UKRI are scraped directly — no generic queries needed for those.
SEARCH_QUERIES = [
    "HORIZON-CL5-2026 site:ec.europa.eu/info/funding-tenders",
    "HORIZON-CL4-2026 site:ec.europa.eu/info/funding-tenders",
    "HORIZON-CL2-2026 site:ec.europa.eu/info/funding-tenders",
    "HORIZON JU CLEANH2 2026 open call site:clean-hydrogen.europa.eu OR site:ec.europa.eu",
    "HORIZON-MSCA-2026 site:ec.europa.eu/info/funding-tenders",
    "DASA open call innovation 2026 site:gov.uk",
]

# Comprehensive list of keywords representing NCC's Strategic Pathways
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

# Expanded list of target companies and key partners associated with NCC domains
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
