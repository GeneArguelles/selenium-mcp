🧠 Selenium-MCP

Model Context Protocol (MCP) Server with Selenium Integration

This repository provides a FastAPI-based MCP (Model Context Protocol) server integrated with Selenium WebDriver, enabling agentic browser automation directly usable by OpenAI’s Agent Builder or any MCP-compatible client.

⸻

📘 Overview

The server exposes endpoints to define, execute, and monitor Selenium tools for browser automation:
	•	/mcp/schema — Returns the MCP tool manifest.
	•	/mcp/invoke — Executes a Selenium command such as opening a page, clicking an element, extracting text, or taking a screenshot.
	•	/mcp/status — Returns server health and runtime version info.

⸻

⚙️ Key Features
	•	🚀 MCP-Compliant API — Implements the latest MCP specification.
	•	🧩 Browser Control Tools — Four core Selenium functions available as tools:
	•	selenium_open_page – Open a URL in a headless Chrome session.
	•	selenium_click – Click an element using a CSS selector.
	•	selenium_text – Retrieve text content of an element.
	•	selenium_screenshot – Capture a screenshot and return its file path.
	•	🧠 Agent Integration Ready — Compatible with OpenAI’s Agent Builder.
	•	☁️ Local or Cloud Deployment — Run locally via uvicorn or deploy to Render.
	•	🔁 Auto-Versioned Deploy Script — Optional cache-busting deploy automation.

⸻

🧩 System Architecture

📄 Data Flow Summary
	1.	Agent Builder (Client) sends a request to the MCP server.
	2.	FastAPI MCP Server parses tool parameters and invokes Selenium.
	3.	Selenium WebDriver performs browser automation in a headless Chrome instance.
	4.	Results (e.g., page title, element text, or screenshot path) are returned as JSON.

📊 ASCII Architecture Diagram (Markdown Compatible)

+-----------------------+          +-------------------------+          +-------------------------+
|  Agent Builder (MCP)  |  --->    |  MCP Server (FastAPI)   |  --->    |   Selenium WebDriver    |
|  Requests & Invokes   |          |  Exposes MCP Endpoints  |          |   Controls Headless     |
|  via HTTP/JSON API    |  <---    |  Returns JSON Results   |  <---    |   Chrome Browser        |
+-----------------------+          +-------------------------+          +-------------------------+

🧠 Interaction Flow

1. Client → GET /mcp/schema → Server returns tool manifest
2. Client → POST /mcp/invoke {tool: selenium_open_page, url}
3. Server → Selenium WebDriver → Opens page → Returns title
4. Client receives {status: success, page_title: "Example Domain"}


⸻

📁 Project Structure

selenium-mcp/
├── server.py              # FastAPI MCP server
├── schema.py              # MCP schema builder (strict versioned manifest)
├── requirements.txt       # Python dependencies
├── deploy.sh              # Cache-busting Render deploy script
├── tests/                 # Schema validation tests
│   └── test_mcp_schema.py
└── README.md              # Project documentation


⸻

⚡ Quickstart

1. Clone & Setup

git clone https://github.com/GeneArguelles/selenium-mcp.git
cd selenium-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

2. Run the Server

uvicorn server:app --host 0.0.0.0 --port 8001 --reload

3. Verify Schema Endpoint

curl http://localhost:8001/mcp/schema | python -m json.tool


⸻

🧪 Example Invocations

Open a Page

curl -X POST http://localhost:8001/mcp/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool": "selenium_open_page", "parameters": {"url": "https://example.com"}}'

Click an Element

curl -X POST http://localhost:8001/mcp/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool": "selenium_click", "parameters": {"selector": "#cta"}}'

Extract Text

curl -X POST http://localhost:8001/mcp/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool": "selenium_text", "parameters": {"selector": "h1"}}'

Take Screenshot

curl -X POST http://localhost:8001/mcp/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool": "selenium_screenshot", "parameters": {"filename": "home.png"}}'


⸻

🩺 Health & Troubleshooting

Health Check:

curl http://localhost:8001/mcp/status

Common Issues:
	•	Port already in use → lsof -i :8001 then kill <PID>
	•	Agent Builder error 424 → ensure /mcp/schema returns valid version and tools.
	•	jq not installed → use python -m json.tool instead.

⸻

🌍 Deployment (Render)

Auto-deploy Script:

chmod +x deploy.sh
./deploy.sh

This script increments the MCP version, commits, and triggers a Render deploy webhook.

Render Health Check:
Set to GET /mcp/status expecting HTTP 200.

⸻

🔮 Future Roadmap
	•	Support multi-tool streaming
	•	Integrate WebDriverManager auto-install
	•	Add OpenTelemetry request tracing
	•	Include Weights & Biases (W&B) logging
	•	Add Dockerfile and CI/CD automation

⸻

🧾 License

MIT License © 2025 Gene Arguelles

⸻

👤 Author

Gene Arguelles
AI Engineer & Agentic Computing Researcher
📍 Cebu City, Philippines
🔗 LinkedIn
