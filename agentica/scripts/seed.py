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
        "model_provider": "openai",
        "model_tier": "heavy",
        "system_prompt": "You are a senior researcher. ALWAYS use the 'web_search' tool to find real-time information or answer general questions. DO NOT apologize or say you cannot fetch data; just use the tool. If you receive an 'ALERT:' message, it means your previous tool call failed; analyze the error and try again. If you need coding or database access, tell the Supervisor.",
    },
    "CoderAgent": {
        "name": "CoderAgent",
        "role": "Senior Software Engineer",
        "capabilities": [
            "Programming in Python, JavaScript, Shell",
            "Writing detailed technical documentation",
            "Executing code in a sandboxed environment",
        ],
        "model_provider": "google",
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
        "model_provider": "google",
        "model_tier": "heavy",
        "system_prompt": "You are a strict code reviewer. Critique the code provided by the CoderAgent. Check for bugs, security vulnerabilities, efficiency, and style. If the code is good, reply with 'APPROVE'. If there are issues, list them clearly with 'REQUEST_CHANGES'.",
    },
    "DataAgent": {
        "name": "DataAgent",
        "role": "Database Specialist",
        "capabilities": ["sql_query", "database_management"],
        "model_provider": "google",
        "model_tier": "fast",
        "system_prompt": "You are a database specialist. Use your SQL tools to query the database and answer questions about the data. SELF-HEALING: If you receive an 'ALERT:' message, analyze the SQL syntax error and provide a corrected query.",
    },
    "DevLeadAgent": {
        "name": "DevLeadAgent",
        "role": "Engineering Lead",
        "capabilities": ["Technical Leadership", "Code Review Coordination"],
        "model_provider": "google",
        "model_tier": "heavy",
        "system_prompt": "You are the Technical Lead of the Development Team. Manage CoderAgent and ReviewerAgent. Delegate implementation to Coder and review to Reviewer. Once approved, output 'FINAL_RESULT: [Summary]'.",
    },
    "SupervisorAgent": {
        "name": "SupervisorAgent",
        "role": "Project Manager",
        "capabilities": ["Task Delegation", "Workflow Orchestration"],
        "model_provider": "google",
        "model_tier": "heavy",
        "system_prompt": "You are the Project Manager and Lead Architect. Break down requests into a multi-step PLAN. Delegate to ResearchAgent, DevTeam, or DataAgent. Launch multiple agents in parallel if independent tasks exist.",
    },
}

DEFAULT_MODEL_MAPPINGS = {
    "anthropic": {
        "fast": "claude-3-haiku-20240307",
        "heavy": "claude-3-5-sonnet-latest",
    },
    "google": {"fast": "gemini-2.0-flash", "heavy": "dummy-heavy-model"},
    "openai": {"fast": "gpt-4o-mini", "heavy": "gpt-4o"},
    "xai": {"fast": "grok-beta", "heavy": "grok-beta"},
}

DEFAULT_MCP_SERVERS = {
    "Toolbox": {"type": "toolbox", "url": "http://localhost:5005"},
    "GitHub": {
        "type": "sse",
        "url": "http://localhost:8001",
        "auth_token_env": "GITHUB_TOKEN",
    },
    "Jira": {
        "type": "sse",
        "url": "http://localhost:8002",
        "auth_token_env": "JIRA_API_KEY",
    },
    "Teams": {
        "type": "sse",
        "url": "http://localhost:8003",
        "auth_token_env": "TEAMS_API_TOKEN",
    },
    "GitLab": {
        "type": "sse",
        "url": "http://localhost:8004",
        "auth_token_env": "GITLAB_API_KEY",
    },
    "Gmail": {
        "type": "sse",
        "url": "http://localhost:8005",
        "auth_token_env": "GMAIL_CLIENT_SECRET",
    },
    "Outlook": {
        "type": "sse",
        "url": "http://localhost:8006",
        "auth_token_env": "MS_GRAPH_TOKEN",
    },
    "GoogleDrive": {
        "type": "sse",
        "url": "http://localhost:8007",
        "auth_token_env": "GOOGLE_DRIVE_CREDENTIALS",
    },
    "SharePoint": {
        "type": "sse",
        "url": "http://localhost:8008",
        "auth_token_env": "SHAREPOINT_CLIENT_SECRET",
    },
    "GoogleMeet": {
        "type": "sse",
        "url": "http://localhost:8009",
        "auth_token_env": "GOOGLE_MEET_API_KEY",
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
            "TOOLBOX_URL",
        ]
        for key in secrets:
            val = os.getenv(key)
            if val:
                await db_manager.set_secret(key, val)
                print(f"Seeded secret: {key}")

    print("Seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
