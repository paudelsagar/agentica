import json
import os
from typing import Any, Dict, List, Optional

import aiosqlite
from src.core.logger import get_logger

logger = get_logger(__name__)

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/agentica_config.db")
)


class DatabaseManager:
    """
    Manages centralized SQLite database for all Agentica configurations.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    async def initialize(self):
        """Initializes the database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    name TEXT PRIMARY KEY,
                    role TEXT,
                    system_prompt TEXT,
                    model_provider TEXT,
                    model_tier TEXT,
                    capabilities TEXT -- JSON string
                )
            """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS model_tiers (
                    provider TEXT,
                    tier TEXT,
                    model_name TEXT,
                    PRIMARY KEY (provider, tier)
                )
            """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS mcp_servers (
                    name TEXT PRIMARY KEY,
                    type TEXT,
                    url TEXT,
                    auth_token_env TEXT
                )
            """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS secrets (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """
            )
            await db.commit()
        logger.info("database_initialized", path=self.db_path)

    # --- Agents ---
    async def get_all_agents(self) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM agents") as cursor:
                rows = await cursor.fetchall()
                agents = {}
                for row in rows:
                    agent = dict(row)
                    agent["capabilities"] = json.loads(agent["capabilities"])
                    agents[agent["name"]] = agent
                return agents

    async def set_agent(self, name: str, data: Dict[str, Any]):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO agents (name, role, system_prompt, model_provider, model_tier, capabilities)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    name,
                    data.get("role"),
                    data.get("system_prompt"),
                    data.get("model_provider"),
                    data.get("model_tier"),
                    json.dumps(data.get("capabilities", [])),
                ),
            )
            await db.commit()

    async def delete_agent(self, name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM agents WHERE name = ?", (name,))
            await db.commit()

    # --- Model Tiers ---
    async def get_model_mappings(self) -> Dict[str, Dict[str, str]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM model_tiers") as cursor:
                rows = await cursor.fetchall()
                mappings = {}
                for row in rows:
                    provider, tier, model_name = row
                    if provider not in mappings:
                        mappings[provider] = {}
                    mappings[provider][tier] = model_name
                return mappings

    async def set_model_mapping(self, provider: str, tier: str, model_name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO model_tiers (provider, tier, model_name)
                VALUES (?, ?, ?)
            """,
                (provider, tier, model_name),
            )
            await db.commit()

    # --- MCP Servers ---
    async def get_mcp_servers(self) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM mcp_servers") as cursor:
                rows = await cursor.fetchall()
                return {row["name"]: dict(row) for row in rows}

    async def set_mcp_server(self, name: str, data: Dict[str, Any]):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO mcp_servers (name, type, url, auth_token_env)
                VALUES (?, ?, ?, ?)
            """,
                (name, data.get("type"), data.get("url"), data.get("auth_token_env")),
            )
            await db.commit()

    async def delete_mcp_server(self, name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM mcp_servers WHERE name = ?", (name,))
            await db.commit()

    # --- Secrets ---
    async def get_secret(self, key: str) -> Optional[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT value FROM secrets WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set_secret(self, key: str, value: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO secrets (key, value)
                VALUES (?, ?)
            """,
                (key, value),
            )
            await db.commit()

    async def get_all_secrets(self) -> Dict[str, str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM secrets") as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}


# Global singleton
db_manager = DatabaseManager()
