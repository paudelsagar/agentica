# Agentica: System Features & Architecture

Agentica is a production-grade multi-agent autonomous system built on LangChain and LangGraph, designed for high reliability, dynamic tool acquisition, and intelligent orchestration.

## Core Architecture

### 1. Multi-Agent Orchestration (Supervisor Pattern)
- Uses **LangGraph** to manage complex, stateful workflows with recursive path capability.
- Implements a **Planner/Supervisor** pattern where a lead agent dynamically updates a step-by-step dependency plan based on real-time tool outputs.
- **Hierarchical Sub-Graphs**: Supports nested specialist teams (e.g., `DevTeam`) with isolated state and automated state merging/filtering back to the parent graph.
- Supports **Parallel Execution** of independent tasks to minimize latency, consolidated via a `JoinParallel` node.

### 2. Specialized Specialist Agents
- **ResearchAgent**: Autonomous web search and information gathering using DuckDuckGo.
- **CoderAgent**: Writes and executes Python/JS/Shell code in a sandboxed environment.
- **DataAgent**: SQL-specialized agent for database exploration and querying.
- **ReviewerAgent**: Strict code auditor that enforces quality and security before task completion.

### 3. Universal MCP Router & Tool Registry
- **Universal Discovery**: Dynamically attaches and binds tools from multiple MCP (Model Context Protocol) servers via unified connection interfaces.
- **Global Tool Registry**: Centralized registry that allows agents to discover and utilize tools owned by other specialist teams, increasing cross-team collaboration.
- **Dynamic Skill Acquisition**: The CoderAgent can create new, reusable LangChain tools on-the-fly, which are hot-reloaded into the system and globally registered for immediate use.

## Advanced Capabilities

### 4. Self-Healing & Autonomous Recovery
- **ErrorAnalyzer Node**: Automatically intercepts tool failures and exceptions.
- **Recursive Reflection**: Analyzes stack traces and provides feedback to agents for automatic retries and pivots.

### 5. Dynamic Human/Agent Consensus (HITL)
- **Security Gateway**: An `HITLGate` node dynamically assesses the risk of a plan based on keyword analysis and specific agent roles (e.g., auto-pausing for file deletions).
- **Multi-Agent Consensus**: Triggered by the "CRITICAL" flag, this system invokes multiple specialists to "vote" on high-risk operations.
    - **Plurality Voting**: Aggregates `APPROVE`/`REJECT` decisions with reasoning extraction.
    - **Threshold Enforcement**: Configurable approval ratios to ensure high-stakes decisions are validated.
- **Stateful Resumption**: Preserves execution context (`intended_agent`) and state snapshots using SQLite, ensuring flawless workflow continuation after approval.

### 6. Long-Term Memory (RAG & Reflection)
- **Persistent RAG**: Uses ChromaDB to store and retrieve relevant context across different conversation threads.
- **Automated Reflection**: Agents automatically extract facts and lessons-learned after each task to build a growing knowledge base.

### 7. Multi-Model Ensemble & Predictive Scaling
- **Tier-Based Routing**: A `ModelRouter` maps tasks to optimized tiers (`heavy` vs `fast`) based on the complexity requirement of each agent action.
- **Predictive Scaling**: Leverages historical performance metrics to dynamically choose the optimal model tier.
    - **Performance Heuristics**: Automatically promotes an agent to the `heavy` tier if its sliding window of 5 runs shows >15s average latency or <80% success rate.
    - **Cost Efficiency**: Defaults to `fast` models (e.g., Gemini Flash) for the majority of utility tasks to maximize throughput while minimizing cost.

## Infrastructure & Observability

### 8. Token Usage, Profiling & Budgets
- **Real-time Profiling**: Embedded into the `EnterpriseAgent` call loop, capturing high-resolution execution latency (`execution_time_ms`) for every single LLM interaction.
- **Cognitive Budget Enforcement**: A `LoadMonitor` proactively tracks token usage per thread, raising a `RuntimeError` if an agent exceeds its safety budget (e.g., 1M tokens), preventing infinite loops or excessive costs.
- **Granular Persistence**: Records token usage (prompt/completion), model name, and timing per agent in a centralized SQLite database for deep analytics.

### 9. Production-Grade Infrastructure
- **FastAPI Layer**: Robust REST endpoints for running workflows, manual approvals, and real-time state inspection.
- **Post-Invocation Reflection**: Agents automatically run a reflection step after completion, extracting key facts and storing them in ChromaDB for persistent cross-thread retrieval.
- **Sandboxed Workspace**: Strict file operation restriction to a designated workspace directory with comprehensive logging of all file/tool interactions.
