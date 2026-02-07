from pprint import pprint

import mcp

print("\nDir(mcp):")
pprint(dir(mcp))

try:
    import mcp.server

    print("\nDir(mcp.server):")
    pprint(dir(mcp.server))
except ImportError:
    print("\nmcp.server not found")

try:
    import mcp.types

    print("\nDir(mcp.types):")
    pprint(dir(mcp.types))
except ImportError:
    print("\nmcp.types not found")

try:
    from mcp.server.fastmcp import FastMCP

    print("\nFastMCP found!")
except ImportError:
    print("\nFastMCP not found")
