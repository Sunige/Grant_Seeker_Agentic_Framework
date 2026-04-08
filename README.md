# 🎯 Grant Seeker Agentic Framework

An autonomous, multi-agent AI system specifically designed to discover, extract, and strategically evaluate grant funding opportunities from highly complex UK and European government portals.

By combining structured data extraction with intelligent LLM classification, the framework produces a professional, actionable Excel dashboard populated *only* with funding opportunities strictly aligned to the Target Organisation technology strategy.

## 🧠 System Architecture

![System Flow Diagram](system_flow_new.svg)

The pipeline revolves around a central orchestrator driving a sequence of specialized autonomous agents:

- **🕵️‍♂️ Scout Agent (`scout_agent.py`)**: Executes high-fidelity extractions natively within Innovate UK IFS, UKRI tables, and Horizon Europe APIs to pull granular grant details (e.g., Dates, Funding Budgets, Scope).
- **⚖️ Strategy Alignment Agent (`alignment_agent.py`)**: Leverages GPT-4o (via OpenRouter) to evaluate technical grant scopes against explicit Target strategy domains (such as *Advanced Materials, Circularity, Digital Twin*). Discards irrelevant calls and condenses valid outcomes into crisp, 20-word specific outcomes.
- **🌐 Discovery Agent (`discovery_agent.py`)**: An exploratory module querying Google (via Serper) to proactively locate new grant portals and maintain the configuration lists dynamically.
- **🎼 Excellence Orchestrator (`orchestrator.py`)**: Commands the linear process. It handles dataframe ingestion, duplicate resolution, ensures historical "seed" grants are protected, and writes out the final `Grant_Opportunities_Template_v2.xlsx`.

### 🚰 Key Data Pipelines

To ensure absolute reliability, the system avoids generic web searching for core UK and EU grants, utilizing directly integrated pipelines:

#### Innovate UK (IFS) Pipeline
The system iteratively crawls the official Innovate UK Innovation Funding Service (IFS) competition directory. It parses the pagination sequence (pages 0 through 4) to detect every listed grant, then visits each dedicated `/competition/{id}/overview` page. A specialized `BeautifulSoup` and regex parser strips out governmental boilerplate text and precise financial constraints (e.g., "total eligible costs", "up to £Xm per project"), normalizing dates and costs into a standardized structure before strategy validation.

#### Horizon Europe & CORDIS Pipeline
For European grants, the framework integrates directly with the authoritative **EU Funding & Tenders Portal REST API**. Rather than attempting to scrape CORDIS—which primarily indexes *already funded and active* projects—the pipeline intercepts opportunities upstream at the Funding & Tenders platform when they are in their *Open* or *Forthcoming* statuses. It translates strategic Target Organisation search phrases into API payloads to pull JSON descriptors, allowing the system to flag early-stage Horizon Europe topics before they ever hit the CORDIS registry.

## ⚙️ Configuration & Execution

The framework is highly configurable and modular. Target keywords, companies, and static URLs are explicitly separated out to `config.py` so they can be modified by non-technical staff without touching logical flow.

### 1. Requirements

Ensure you have your environment built and API keys staged locally in a `.env` file:
```env
OPENROUTER_API_KEY="sk-or-v1-..."
SERPER_API_KEY="..."
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Bootstrapping

If you need to generate a brand new Excel tracking template with seeded template data:
```bash
python create_excel.py
```

### 3. Execution

To trigger the autonomous discovery and extraction pipeline:
```bash
python orchestrator.py
```

### 4. Headless Inspect

You can quickly view the health and results of the pipeline directly in your terminal using:
```bash
python inspect_output.py
```

---
*Every module contains explicit inline documentation detailing exactly What it does, Why it exists, and How it operates to ensure long-term legibility.*
