# HarBr — Rental Trust Infrastructure

Bengaluru's rental market has no verification layer. Tenants get scammed on title fraud, illegal deposits, and lifestyle mismatches. HarBr fixes this with a multi-agent chatbot that audits, matches, and lists — before you ever visit a property.
---
## Architecture

Frontend: Streamlit chatbot UI with agent thinking trace visible to the user.
Backend: FastAPI server on port 8080, exposing `/orchestrator/chat`.
Agent Layer: Google Gemini orchestrates three MCP tools via `mcp_server.py`.
Databases: SQLite (`harbr_seed.db`) for mock land records; Neon PostgreSQL for live listings, owners, tenants, and agreements.
---
## Agents

Shield Agent — `check_ulpin(ulpin)`
Audits a property's ULPIN against mock state land records. Returns owner name, area, city, legal status (Clear / Disputed), and blacklist flag. Blocks the flow if a dispute is detected.

Search Agent —` search_properties(budget, neighborhood, bhk, ...)`
Queries Neon listings with hard filters: max rent, BHK, neighborhood, pet-friendliness, dietary preference, and amenity. Returns ranked results.

List Agent — `list_property(ulpin, owner, rent, bhk, city, floor_info)`**
Ingests a new verified listing into Neon PostgreSQL. Only fires after all required fields are collected conversationally.

PDF Agent — `generate_health_card(data)`
Generates a downloadable Property Health Card (ULPIN, market rent, effective rent, deposit) via fpdf.
---
## Data Layer

- 100 seeded land records, 15% marked Disputed to stress-test the Shield Agent
- PMAY subsidy table for income-bracket matching
- Blacklist table for flagged owners

---

## Stack
Python · FastAPI · Streamlit · Gemini · MCP · SQLite · Neon PostgreSQL · fpdf
