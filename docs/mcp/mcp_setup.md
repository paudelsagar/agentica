# MCP Server Setup Guide

MCP (Model Context Protocol) servers are independent processes that expose toolsets to AI agents. In Agentica, we use the **SSE (Server-Sent Events)** transport, which allows agents to connect to tools over HTTP.

## 1. How it Works
1. **Server**: An MCP server (e.g., GitHub MCP) runs on a specific port (e.g., 8001).
2. **Registry**: You add the server's URL to `src/config/mcp_servers.yaml`.
3. **Agent**: When an agent needs a tool, it calls `attach_mcp_server("GitHub")`, which fetches the tools via the URL.

## 2. Setting up the Spreadsheet/Database (Toolbox)
Our system already includes the Google GenAI Toolbox. It is automatically started by `./run.sh`:
```bash
npx -y @toolbox-sdk/server --prebuilt sqlite --port 5005
```

## 3. Setting up GitHub/GitLab/Jira
Most community MCP servers are designed for "Stdio" (running locally within a CLI). To use them with Agentica's remote agents, you should run them as SSE servers.

### Alternative A: Using Docker (Recommended)
Many servers come with a Dockerfile. You can run them as microservices:
```bash
# Example for a GitHub MCP server
docker run -e GITHUB_TOKEN=your_token -p 8001:8001 mcp/github-server
```

### Alternative B: Using Node/Npx
If a server supports SSE natively:
```bash
npx -y @modelcontextprotocol/server-github --port 8001
```

## 4. Setting up Mail (Gmail/Outlook)
Email servers require OAuth credentials.
1. **Gmail**: You'll need a `credentials.json` from the Google Cloud Console.
2. **Run the server**:
   ```bash
   npx -y @modelcontextprotocol/server-gmail --port 8005
   ```

## 5. Adding to Agentica
Once the server is running, update your `src/config/mcp_servers.yaml`:
```yaml
mcp_servers:
  GitHub:
    type: "sse"
    url: "http://localhost:8001"
    auth_token_env: "GITHUB_TOKEN"
```

## 6. Pro-Tip: Running Multiple Servers
You can use a process manager like **PM2** or a `docker-compose.yml` to keep all your MCP servers running in the background.
