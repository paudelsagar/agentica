import os
from typing import Any, Dict

from src.core.agent import EnterpriseAgent
from src.core.config import load_agent_config
from src.core.tool_manager import ToolManager

WORKSPACE_DIR = os.path.join(os.getcwd(), "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)


class CoderAgent(EnterpriseAgent):
    """
    Agent specialized in coding tasks.
    """

    def __init__(self):
        config = load_agent_config("CoderAgent")
        super().__init__(config)
        self.tool_manager = ToolManager()
        self._register_tools()
        self._load_dynamic_tools()

    def _load_dynamic_tools(self):
        """Loads and registers dynamic tools."""
        dynamic_tools = self.tool_manager.load_tools()
        for tool in dynamic_tools:
            # Assuming tool is a callable with a 'name' attribute (like StructuredTool or @tool decorated function)
            if hasattr(tool, "name"):
                self.register_tool(tool.name, tool)

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

        def create_tool(filename: str, content: str) -> str:
            """
            Creates a new tool for the agent system.
            The content MUST be valid Python code defining a function decorated with @tool.
            filename should end with .py
            """
            if not filename.endswith(".py"):
                return "Error: Filename must end with .py"

            # Security check: basic validation, though we are in a sandbox-ish environment.
            # In a real enterprise system, stricter checks would be needed.

            try:
                # Write to dynamic tools directory
                import src.core.tool_manager as tm

                file_path = os.path.join(
                    tm.DYNAMIC_TOOLS_DIR, os.path.basename(filename)
                )

                with open(file_path, "w") as f:
                    f.write(content)

                # Hot-reload: Refresh tools and re-register
                self._load_dynamic_tools()

                return f"Successfully created tool at {file_path}. Tool has been reloaded and is ready to use."
            except Exception as e:
                return f"Error creating tool: {str(e)}"

        # Manually register tools for LangChain binding and Global Registry
        self.register_tool("write_code", write_code)
        self.register_tool("execute_code", execute_code)
        self.register_tool("create_tool", create_tool)
