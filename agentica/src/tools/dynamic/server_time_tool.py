from langchain_core.tools import tool
import datetime

@tool
def get_server_time() -> str:
    """Returns the current time as a string."""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")