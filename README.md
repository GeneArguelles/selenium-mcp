🧠 Selenium-MCP
Model Context Protocol (MCP) Server with Selenium Integration
This project implements a Model Context Protocol (MCP) server built with FastAPI and powered by
Selenium. It exposes browser automation capabilities (open page, click element, extract text, capture
screenshot) as MCP-compliant tools that can be invoked by OpenAI Agent Builder or any other MCP-aware
agentic framework.
Table of Contents
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
Features
Architecture
1) Sequence Diagram (Mermaid)
2) Component Diagram (Mermaid)
3) Inline SVG Diagrams
Project Structure
Quickstart
Configuration
API Endpoints
Example Invocations
Health & Observability
Deployment (Render)
Troubleshooting
Roadmap
License
Author
Features
•
•
•
•
•
•
•
•
•
•
✅ MCP-compliant manifest served at /mcp/schema
⚙️ FastAPI backend with health and invocation endpoints
🌐 Selenium WebDriver for real browser interactions (headless by default)
🧩 Toolset includes:
selenium_open_page — open a URL in headless Chrome
selenium_click — click an element by CSS selector
selenium_text — get text content by CSS selector
selenium_screenshot — capture a PNG screenshot and return its path
🔁 Cache-busting deploy script auto-increments version and pushes to Render
💡 Local or cloud-ready: run on localhost:8001 or deploy to Render
1
Architecture
This section provides multiple inline diagrams you can embed directly in GitHub. Mermaid renders natively
in GitHub. The SVGs below are pure inline <svg> —also rendered by GitHub Markdown.
1) Sequence Diagram (Mermaid)
sequenceDiagram
autonumber
participant AB as Agent Builder / Client
participant MCP as MCP Server (FastAPI)
participant SEL as Selenium API
participant CH as Headless Chrome
AB->>MCP: GET /mcp/schema
MCP-->>AB: JSON schema (tools, version)
AB->>MCP: POST /mcp/invoke { tool:"selenium_open_page", url }
MCP->>SEL: webdriver.get(url)
SEL->>CH: Navigate to URL
CH-->>SEL: Page loaded (title)
SEL-->>MCP: { title }
MCP-->>AB: { status:"success", page_title }
AB->>MCP: POST /mcp/invoke { tool:"selenium_click", selector }
MCP->>SEL: driver.find_element(...).click()
SEL-->>MCP: { clicked:true }
MCP-->>AB: { status:"success" }
2) Component Diagram (Mermaid)
flowchart LR
subgraph Client
A[Agent Builder / MCP Client]
end
subgraph Server[FastAPI MCP Server]
S1[/ /mcp/schema /]
S2[/ /mcp/invoke /]
S3[/ /mcp/status /]
Cfg[(config .env)]
end
subgraph Runtime
WDM[WebDriverManager]
2
WD[Selenium WebDriver]
HC[Headless Chrome]
FS[(Filesystem /tmp)]
end
A -->|HTTP| S1
A -->|HTTP| S2
A -->|HTTP| S3
S2 --> WD
WD --> WDM
WD --> HC
S2 --> FS
Cfg -.-> Server
3) Inline SVG Diagrams
MCP ↔ Selenium ↔ Browser (Inline SVG)
You can keep this inline, or save as docs/diagrams/mcp-selenium.svg in the README with ![MCP↔Selenium](docs/diagrams/mcp-selenium.svg).
and reference it
<svg width="760" height="300" xmlns="http://www.w3.org/2000/svg" role="img"
aria-label="MCP–Selenium–Browser Diagram">
<defs>
<style>
.box{fill:#f8fafc;stroke:#0f172a;stroke-width:1.5;rx:8;}
.title{font:700 14px ui-sans-serif,system-ui;fill:#0f172a}
.text{font:500 12px ui-sans-serif,system-ui;fill:#334155}
.arrow{marker-end:url(#arrowhead);stroke:#0f172a;stroke-width:1.5}
</style>
<marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10"
refY="3.5" orient="auto">
<polygon points="0 0, 10 3.5, 0 7" fill="#0f172a" />
</marker>
</defs>
<!-- Boxes -->
<rect class="box" x="20" y="30" width="200" height="80"/>
<text class="title" x="120" y="55" text-anchor="middle">Agent Builder /
Client</text>
<text class="text" x="120" y="75" text-anchor="middle">Requests schema +
invokes tools</text>
<rect class="box" x="280" y="30" width="200" height="120"/>
<text class="title" x="380" y="55" text-anchor="middle">MCP Server (FastAPI)</
3
text>
<text class="text" x="380" y="75" text-anchor="middle">/mcp/schema • /mcp/
invoke • /mcp/status</text>
<rect class="box" x="540" y="30" width="200" height="160"/>
<text class="title" x="640" y="55" text-anchor="middle">Selenium + Headless
Chrome</text>
<text class="text" x="640" y="75" text-anchor="middle">WebDriverManager •
Screenshots (/tmp)</text>
<!-- Arrows -->
<line class="arrow" x1="220" y1="70" x2="280" y2="70" />
<text class="text" x="250" y="62" text-anchor="middle">HTTP</text>
<line class="arrow" x1="480" y1="90" x2="540" y2="90" />
<text class="text" x="510" y="82" text-anchor="middle">WebDriver API</text>
<line class="arrow" x1="540" y1="140" x2="480" y2="140" />
<text class="text" x="510" y="132" text-anchor="middle">Results (title, text,
path)</text>
<line class="arrow" x1="280" y1="110" x2="220" y2="110" />
<text class="text" x="250" y="102" text-anchor="middle">JSON (status, data)</
text>
</svg>
PNG note: GitHub Markdown does not reliably render base64 PNG data URIs inline. To use
PNGs, save the generated images under docs/diagrams/*.png and reference them: !
[MCP Diagram](docs/diagrams/mcp-selenium.png).
Project Structure
selenium-mcp/
├── server.py # FastAPI MCP server
├── schema.py # Strict MCP schema builder
├── requirements.txt # Dependencies
├── deploy.sh # Auto-versioning + Render deploy script
├── README.md # This file
└── tests/
└── test_mcp_schema.py # Schema validation tests
4
Quickstart
1) Clone & Setup
git clone https://github.com/GeneArguelles/selenium-mcp.git
cd selenium-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
2) Run Locally
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
3) Test Schema Endpoint
curl http://localhost:8001/mcp/schema | python -m json.tool
Configuration
Environment variables (e.g., via .env ):
MCP_SERVER_NAME=selenium_mcp
MCP_VERSION=2025-10-01
HEADLESS=true
SELENIUM_DRIVER=chrome
SCREENSHOT_DIR=/tmp
API Endpoints
Endpoint Method Description
/mcp/schema GET Returns MCP manifest JSON including tool definitions
/mcp/invoke POST Executes a selected Selenium action
/mcp/status GET Health and runtime info
Schema shape (example):
5
{
"version": "2025-10-01",
"tools": [
{
"name": "selenium_open_page",
"description": "Open a URL in a headless browser",
"parameters": {
"type": "object",
"properties": {"url": {"type": "string"}},
"required": ["url"]
}
},
{
"name": "selenium_click",
"description": "Click an element by CSS selector",
"parameters": {
"type": "object",
"properties": {"selector": {"type": "string"}},
"required": ["selector"]
}
},
{
"name": "selenium_text",
"description": "Get text content by CSS selector",
"parameters": {
"type": "object",
"properties": {"selector": {"type": "string"}},
"required": ["selector"]
}
},
{
"name": "selenium_screenshot",
"description": "Save a PNG screenshot to /tmp and return its path",
"parameters": {
"type": "object",
"properties": {"filename": {"type": "string"}},
"required": ["filename"]
}
}
]
}
6
Example Invocations
Open a page:
curl -X POST http://localhost:8001/mcp/invoke
-H "Content-Type: application/json"
-d '{
"tool": "selenium_open_page",
"parameters": { "url": "https://example.com" }
}'
Click an element:
curl -X POST http://localhost:8001/mcp/invoke
-H "Content-Type: application/json"
-d '{
"tool": "selenium_click",
"parameters": { "selector": "#cta" }
}'
Get text content:
curl -X POST http://localhost:8001/mcp/invoke
-H "Content-Type: application/json"
-d '{
"tool": "selenium_text",
"parameters": { "selector": "h1" }
}'
Screenshot:
curl -X POST http://localhost:8001/mcp/invoke
-H "Content-Type: application/json"
-d '{
"tool": "selenium_screenshot",
"parameters": { "filename": "home.png" }
}'
7
Health & Observability
•
•
•
Status check: GET /mcp/status returns JSON with uptime, version, and a lightweight WebDriver
probe (optional).
Pretty-print JSON without jq: ... | python -m json.tool
Logs: Configure uvicorn log level with --log-level info (or debug ).
Deployment (Render)
deploy.sh (suggested behavior):
•
•
•
•
Usage:
Parse MCP_VERSION in schema.py (or server.py )
Increment patch version (e.g., 1.0.0 → 1.0.1 )
Commit + push
Optionally hit Render deploy hook (if configured)
chmod +x deploy.sh
./deploy.sh
Health check: configure Render health check to GET /mcp/status expecting 200 .
Troubleshooting
``
•
Another process holds the port. Find and kill:
lsof -i :8001
kill -9 <PID>
•
`** in Agent Builder**
Ensure /mcp/schema returns a valid version string and a non-empty tools` array with
proper JSON Schema.
`
•
Use Python: curl ... | python -m json.tool`
8
Roadmap
•
•
•
•
•
Multi-tool invocation batching & streaming
WebDriverManager auto-provisioning
Request/response tracing (OpenTelemetry)
Weights & Biases (W&B) run logging
Dockerfile + GitHub Actions CI
License
MIT License © 2025 Gene Arguelles
Author
Gene Arguelles
AI Engineer & Agentic Computing Researcher
📍 Cebu City, Philippines
LinkedIn: https://linkedin.com/in/genearguelles
9
