"""
Seed script for initializing the Agentica database with default agents, tools, and configurations.

Usage:
    cd agentica/agentica
    source ../.venv/bin/activate
    PYTHONPATH=. python scripts/seed.py
"""

import asyncio
import os

from dotenv import load_dotenv
from src.core.db_manager import db_manager

# --- DEFAULT CONFIGURATION DATA ---

DEFAULT_AGENTS = {
    "ResearchAgent": {
        "name": "ResearchAgent",
        "role": "Researcher",
        "capabilities": ["web_search", "summarization"],
        "model_provider": "ollama",
        "model_tier": "heavy",
        "system_prompt": """You are a senior researcher. ALWAYS use the 'web_search' tool to find real-time information or answer general questions.

CRITICAL: To communicate with the user, you MUST use the 'respond_to_user' tool.
- ONLY content sent via respond_to_user() will be shown to the user
- All other output (your reasoning, planning, tool results) is hidden from the user
- Synthesize information into clear, helpful responses before calling respond_to_user()

EXAMPLE WORKFLOW:
1. Use web_search to find information
2. Analyze and synthesize the results
3. Call respond_to_user("Here's what I found: [your summary]")

Do NOT include raw JSON, tool output, or internal notes in respond_to_user - only the final user-friendly message.""",
    },
    "CoderAgent": {
        "name": "CoderAgent",
        "role": "Senior Software Engineer",
        "capabilities": [
            "Programming in Python, JavaScript, Shell",
            "Writing detailed technical documentation",
            "Executing code in a sandboxed environment",
        ],
        "model_provider": "ollama",
        "model_tier": "heavy",
        "system_prompt": "You are an expert software engineer. Your goal is to write high-quality, efficient, and secure code. You can use the 'write_code' tool to create files and 'execute_code' to run them. DYNAMIC TOOL CREATION: If you need a reusable utility that is NOT available, you can create it using the 'create_tool' tool. ALWAYS verify your code works by creating a small test script if possible. SELF-HEALING: If you receive an 'ALERT:' message, analyze the error carefully and fix it.",
    },
    "ReviewerAgent": {
        "name": "ReviewerAgent",
        "role": "Senior Code Reviewer",
        "capabilities": [
            "Code Analysis",
            "Security Auditing",
            "Best Practices Enforcement",
        ],
        "model_provider": "ollama",
        "model_tier": "heavy",
        "system_prompt": "You are a strict code reviewer. Critique the code provided by the CoderAgent. Check for bugs, security vulnerabilities, efficiency, and style. If the code is good, reply with 'APPROVE'. If there are issues, list them clearly with 'REQUEST_CHANGES'.",
    },
    "DataAgent": {
        "name": "DataAgent",
        "role": "Database Specialist",
        "capabilities": ["sql_query", "database_management"],
        "model_provider": "ollama",
        "model_tier": "fast",
        "system_prompt": """You are a database specialist with access to SQL query tools via MCP Toolbox.

AVAILABLE DATA: users, accounts, merchants, transactions, KYC records, payment methods, currencies.

WORKFLOW:
1. Analyze the user's question to determine which tables/tools to query
2. Use your SQL tools to fetch the data
3. Format the results clearly (use tables, lists, or summaries as appropriate)
4. Call respond_to_user() with the final formatted answer

CRITICAL: To communicate with the user, you MUST use the 'respond_to_user' tool.
- ONLY content sent via respond_to_user() will be shown to the user
- All other output (reasoning, raw SQL results) is hidden from the user
- Do NOT include raw JSON or SQL output in respond_to_user — format it into a human-readable response

EXAMPLE WORKFLOW:
1. User asks: "list travel merchants"
2. Use list_merchants tool to fetch all merchants
3. Filter results for travel category
4. Call respond_to_user("Here are the travel merchants: ...")

SELF-HEALING: If you receive an error, analyze the SQL syntax and try a corrected query.""",
    },
    "DevLeadAgent": {
        "name": "DevLeadAgent",
        "role": "Engineering Lead",
        "capabilities": ["Technical Leadership", "Code Review Coordination"],
        "model_provider": "ollama",
        "model_tier": "heavy",
        "system_prompt": "You are the Technical Lead of the Development Team. Manage CoderAgent and ReviewerAgent. Delegate implementation to Coder and review to Reviewer. Once approved, output 'FINAL_RESULT: [Summary]'.",
    },
    "SupervisorAgent": {
        "name": "SupervisorAgent",
        "role": "Project Manager",
        "capabilities": ["Task Delegation", "Workflow Orchestration"],
        "model_provider": "ollama",
        "model_tier": "heavy",
        "system_prompt": """You are the Project Manager and Lead Architect. Your role is to route user requests to the correct specialist agent.

ROUTING RULES (follow these strictly):
1. DataAgent — ANY question about database data: users, accounts, merchants, transactions, KYC, reports, balances, payment status, currencies, or any internal structured data.
2. ResearchAgent — ANY question requiring web search: news, weather, prices, general knowledge, "what is", "how to", current events.
3. DevTeam — ANY request to write, fix, review, or debug code.
4. FINISH — Simple greetings, clarifications, or when the task is already complete.

CRITICAL RULES:
- Do NOT answer data/database questions yourself. ALWAYS delegate to DataAgent.
- Do NOT use ResearchAgent for database/internal data questions.
- Do NOT attempt to use tools directly (e.g., do not call web_search yourself). Delegate instead.

To communicate with the user, use the 'respond_to_user' tool for brief status updates.
Your internal planning (hidden from user):
PLAN: [numbered list of steps]
NEXT AGENT: [AgentName]""",
    },
}

DEFAULT_MODEL_MAPPINGS = {
    "anthropic": {
        "fast": "claude-3-haiku-20240307",
        "heavy": "claude-3-5-sonnet-latest",
    },
    "google": {"fast": "gemini-2.0-flash", "heavy": "gemini-2.0-flash"},
    "openai": {"fast": "gpt-4o-mini", "heavy": "gpt-4o"},
    "xai": {"fast": "grok-beta", "heavy": "grok-beta"},
    "ollama": {"fast": "glm-4.7:cloud", "heavy": "glm-4.7:cloud"},
}

DEFAULT_MCP_SERVERS = {
    "Toolbox": {"type": "toolbox", "url": "http://localhost:5005"},
    "GitHub": {
        "type": "sse",
        "url": "http://localhost:8001",
        "auth_token": "",
    },
    "Jira": {
        "type": "sse",
        "url": "http://localhost:8002",
        "auth_token": "",
    },
    "Teams": {
        "type": "sse",
        "url": "http://localhost:8003",
        "auth_token": "",
    },
    "GitLab": {
        "type": "sse",
        "url": "http://localhost:8004",
        "auth_token": "",
    },
    "Gmail": {
        "type": "sse",
        "url": "http://localhost:8005",
        "auth_token": "",
    },
    "Outlook": {
        "type": "sse",
        "url": "http://localhost:8006",
        "auth_token": "",
    },
    "GoogleDrive": {
        "type": "sse",
        "url": "http://localhost:8007",
        "auth_token": "",
    },
    "SharePoint": {
        "type": "sse",
        "url": "http://localhost:8008",
        "auth_token": "",
    },
    "GoogleMeet": {
        "type": "sse",
        "url": "http://localhost:8009",
        "auth_token": "",
    },
}


async def seed():
    print("Starting database seeding (Embedded Config)...")
    await db_manager.initialize()

    # 1. Seed Agents
    for name, config in DEFAULT_AGENTS.items():
        await db_manager.set_agent(name, config)
        print(f"Seeded agent: {name}")

    # 2. Seed Model Tiers
    for provider, tiers in DEFAULT_MODEL_MAPPINGS.items():
        for tier, model in tiers.items():
            await db_manager.set_model_mapping(provider, tier, model)
            print(f"Seeded model tier: {provider}/{tier} -> {model}")

    # 3. Seed MCP Servers
    for name, config in DEFAULT_MCP_SERVERS.items():
        await db_manager.set_mcp_server(name, config)
        print(f"Seeded MCP server: {name}")

    # 4. Seed Secrets (from .env)
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ENV_FILE = os.path.join(BASE_DIR, ".env")
    if os.path.exists(ENV_FILE):
        load_dotenv(ENV_FILE)
        secrets = [
            "GOOGLE_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "XAI_API_KEY",
            "COHERE_API_KEY",
            "TAVILY_API_KEY",
            "OLLAMA_BASE_URL",
        ]
        for key in secrets:
            val = os.getenv(key)
            if val:
                await db_manager.set_secret(key, val)
                print(f"Seeded secret: {key}")

    print("Seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
