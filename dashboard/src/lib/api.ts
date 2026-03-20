const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = {
  async getAgents() {
    const res = await fetch(`${BASE_URL}/agents`);
    if (!res.ok) throw new Error("Failed to fetch agents");
    return res.json();
  },
  async getMCPServers() {
    const res = await fetch(`${BASE_URL}/mcp/servers`);
    if (!res.ok) throw new Error("Failed to fetch MCP servers");
    return res.json();
  },
  async getMetrics(startDate?: string, endDate?: string) {
    const url = new URL(`${BASE_URL}/metrics`);
    if (startDate) url.searchParams.append("start_date", startDate);
    if (endDate) url.searchParams.append("end_date", endDate);
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error("Failed to fetch metrics");
    return res.json();
  },
  async getMetricsHistory(interval: string, agent?: string, model?: string, startDate?: string, endDate?: string) {
    const url = new URL(`${BASE_URL}/metrics/history`);
    url.searchParams.append("interval", interval);
    if (agent) url.searchParams.append("agent_name", agent);
    if (model) url.searchParams.append("model_name", model);
    if (startDate) url.searchParams.append("start_date", startDate);
    if (endDate) url.searchParams.append("end_date", endDate);
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error("Failed to fetch metrics history");
    return res.json();
  },
  async getMetricsByModel(startDate?: string, endDate?: string) {
    const url = new URL(`${BASE_URL}/metrics/by-model`);
    if (startDate) url.searchParams.append("start_date", startDate);
    if (endDate) url.searchParams.append("end_date", endDate);
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error("Failed to fetch metrics by model");
    return res.json();
  },
  async getRecentTrajectories(limit: number = 10) {
    const res = await fetch(`${BASE_URL}/trajectories/recent?limit=${limit}`);
    if (!res.ok) throw new Error("Failed to fetch recent trajectories");
    return res.json();
  },
  async getThreadHistory(threadId: string, limit: number = 20, offset: number = 0) {
    const res = await fetch(`${BASE_URL}/threads/${threadId}/history?limit=${limit}&offset=${offset}`);
    if (!res.ok) throw new Error("Failed to fetch thread history");
    return res.json();
  },
  async runWorkflow(threadId: string, message: string, thinkingMode: boolean = false, useWeb: boolean = true) {
    return fetch(`${BASE_URL}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: threadId, message, thinking_mode: thinkingMode, use_web: useWeb }),
    });
  },
  async deleteState(threadId: string) {
    const res = await fetch(`${BASE_URL}/state/${threadId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete state");
    return res.json();
  },
  async renameThread(threadId: string, name: string) {
    const res = await fetch(`${BASE_URL}/trajectories/${threadId}/name`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) throw new Error("Failed to rename thread");
    return res.json();
  },
  async deleteAgent(name: string) {
    const res = await fetch(`${BASE_URL}/agents/${name}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete agent");
    return res.json();
  },
  async updateAgent(name: string, data: any) {
    const res = await fetch(`${BASE_URL}/agents/${name}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to update agent");
    return res.json();
  },
  async createAgent(data: any) {
    const res = await fetch(`${BASE_URL}/agents`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to create agent");
    return res.json();
  },
  async addMCPServer(data: any) {
    const res = await fetch(`${BASE_URL}/config/mcp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to add MCP server");
    return res.json();
  },
  async deleteMCPServer(name: string) {
    const res = await fetch(`${BASE_URL}/config/mcp/${name}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete MCP server");
    return res.json();
  },
  async getSecrets() {
    const res = await fetch(`${BASE_URL}/config/secrets`);
    if (!res.ok) throw new Error("Failed to fetch secrets");
    return res.json();
  },
  async updateSecrets(secrets: any) {
    const res = await fetch(`${BASE_URL}/config/secrets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(secrets),
    });
    if (!res.ok) throw new Error("Failed to update secrets");
    return res.json();
  },
  async getModelConfig() {
    const res = await fetch(`${BASE_URL}/models/config`);
    if (!res.ok) throw new Error("Failed to fetch model config");
    return res.json();
  },
  async updateModelConfig(config: any) {
    const res = await fetch(`${BASE_URL}/models/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error("Failed to update model config");
    return res.json();
  },
};
