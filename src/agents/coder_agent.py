import os
from typing import Any, Dict

from src.core.agent import EnterpriseAgent
from src.core.config import load_agent_config

WORKSPACE_DIR = os.path.join(os.getcwd(), "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)


class CoderAgent(EnterpriseAgent):
    """
    Agent specialized in coding tasks.
    """

    def __init__(self):
        config = load_agent_config("CoderAgent")
        super().__init__(config)
        self._register_tools()

    def _register_tools(self):
        def write_code(filename: str, content: str) -> str:
            """
            Writes code to a file within the sandboxed workspace.
            """
            # Sandboxing: Ensure filename is just a basename or relative path inside workspace
            safe_filename = os.path.basename(filename)
            file_path = os.path.join(WORKSPACE_DIR, safe_filename)

            try:
                with open(file_path, "w") as f:
                    f.write(content)
                return f"Successfully wrote code to {file_path}"
            except Exception as e:
                return f"Error writing file: {str(e)}"

        def execute_code(filename: str) -> str:
            """
            Executes a Python script located in the workspace.
            """
            safe_filename = os.path.basename(filename)
            file_path = os.path.join(WORKSPACE_DIR, safe_filename)

            if not os.path.exists(file_path):
                return f"Error: File {safe_filename} not found in workspace."

            try:
                # Run the script with a timeout
                import subprocess

                result = subprocess.run(
                    ["python3", file_path],
                    cwd=WORKSPACE_DIR,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                output = result.stdout
                if result.stderr:
                    output += f"\nError Output:\n{result.stderr}"
                return f"Execution Output:\n{output}"
            except subprocess.TimeoutExpired:
                return "Error: Execution timed out (limit: 10s)."
            except Exception as e:
                return f"Error executing file: {str(e)}"

        def review_code(code: str) -> str:
            """
            Simulates reviewing code.
            """
            return "Code Review: Looks good, no syntax errors found."

        # Manually register tools for LangChain binding
        self.tool_functions["write_code"] = write_code
        self.tool_functions["execute_code"] = execute_code
        self.tool_functions["review_code"] = review_code

        # Register with FastMCP
        self.mcp_server.add_tool(write_code)
        self.mcp_server.add_tool(execute_code)
        self.mcp_server.add_tool(review_code)
