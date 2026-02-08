# System Architecture

Agentica is a multi-agent system built on **LangGraph**, designed to orchestrate specialized LLM-powered agents to solve complex tasks.

## Anatomy of an AI Agent

Each agent in the system is an autonomous loop that combines reasoning with tool execution.

```mermaid
graph TD
    Input([Input: State/Messages]) --> Reason{LLM Reasoning}
    Reason -->|Chain of Thought| Plan[Action Plan]
    Plan -->|Tool Call| MCP[FastMCP Executor]
    MCP -->|Execute| Tools[Internal/External Tools]
    Tools -->|Observation| Feedback[Tool Results]
    Feedback --> Reason
    Reason -->|Final Answer| Output([Output: AIMessage])
    
    subgraph Core_Loop ["Sense-Think-Act Loop"]
        Reason
        Plan
        MCP
    end
```

## Orchestration Flow

The system uses a **Supervisor-Worker** pattern. The `SupervisorAgent` acts as the brain, analyzing user intent and delegating to specialized workers.

```mermaid
graph TD
    User([User / CLI Chat]) --> API[FastAPI Server]
    API --> Graph[[LangGraph Orchestrator]]
    
    subgraph Agents
        Graph --> Supervisor{SupervisorAgent}
        Supervisor -->|Delegate| Researcher[ResearchAgent]
        Supervisor -->|Delegate| Coder[CoderAgent]
        Supervisor -->|Delegate| Data[DataAgent]
        
        Researcher -->|Result| Supervisor
        Coder -->|Validate| Reviewer[ReviewerAgent]
        Reviewer -->|Critique| Coder
        Reviewer -->|Pass| Supervisor
        Data -->|Result| Supervisor
    end
    
    subgraph Persistence
        Graph -.-> Checkpointer[(State DB: state.db)]
        Agents -.-> Usage[UsageTracker]
        Usage -.-> Checkpointer
    end
    
    Supervisor -->|Final Answer| User
```

## Agent Capabilities

| Agent | Core Responsibility | Primary Tools |
| :--- | :--- | :--- |
| **Supervisor** | Orchestration & Routing | Internal Routing Logic |
| **Researcher** | Information Gathering | `web_search`, `recall_memory` |
| **Coder** | Logic & Scripting | `python_repl`, `create_tool` |
| **Reviewer** | Quality Assurance | Self-Reflection / critique |
| **Data Specialist**| Database Interaction | `db_query`, `db_schema` (via Toolbox) |

## Component Interactions

```mermaid
sequenceDiagram
    participant U as User
    participant S as Supervisor
    participant R as Researcher
    participant D as DataAgent
    participant T as Toolbox Server
    participant DB as SQLite (state.db)

    U->>S: "How many users are active?"
    S->>S: Analyze Intent
    S->>D: Delegate to DataAgent
    D->>T: Load Tools (Lazy)
    T-->>D: Available SQL Tools
    D->>D: Generate SQL
    D->>T: Execute Query
    T->>DB: SQL Execution
    DB-->>T: Raw Result
    T-->>D: Tool Result
    D-->>S: Structured Response
    S->>U: Final Answer
```

## Model Context Protocol (MCP) Integration

The system leverages the **Model Context Protocol (MCP)** to standardize how agents interact with tools and external resources.

```mermaid
graph LR
    subgraph Agent_Internal ["Agent (e.g., DataAgent)"]
        LLM[Gemini LLM]
        MCP_Srv[FastMCP Server]
        LLM <--> MCP_Srv
    end
    
    subgraph External_Tools ["MCP Toolsets"]
        Toolbox[GenAI Toolbox Server]
        Local_Tools[Local Python Tools]
    end

    MCP_Srv <-->|Protocol| Toolbox
    MCP_Srv <-->|Protocol| Local_Tools
```

### Key MCP Concepts in Agentica:
- **FastMCP**: Each `EnterpriseAgent` hosts a `FastMCP` instance (via `mcp.server.fastmcp`) to manage and expose tools to the LLM in a structured format.
- **Protocol-Based Tools**: Agents register tools using the MCP pattern, which provides a unified interface for both local Python functions and external toolbox servers.
- **JSON-RPC Communication**: Tool discovery and invocation follow the MCP specification, ensuring consistency across different tool providers.

## Component Interactions (MCP-Aware)

```mermaid
sequenceDiagram
    participant U as User
    participant S as Supervisor
    participant D as DataAgent
    participant LLM as Gemini LLM
    participant MCP as FastMCP (Internal)
    participant T as Toolbox Server (MCP)

    U->>S: "Query the db"
    S->>D: Delegate
    D->>MCP: Load Tools (Lazy)
    alt First Run
        MCP->>T: List Tools
        T-->>MCP: Tool JSON-RPC Defs
    end
    D->>LLM: Bind Tools
    LLM->>LLM: Reason + Action
    LLM->>MCP: Call Tool (SQL)
    MCP->>T: JSON-RPC: tool/call
    T-->>MCP: SQL Results
    MCP-->>LLM: Observations
    LLM-->>D: Final Answer
    D-->>S: Response
    S->>U: Final Answer
```


## Infrastructure Layer

- **Language Model**: Google Gemini (via `gemini-2.0-flash`).
- **State Management**: LangGraph checkpointing for persistent threads.
- **External Dependencies**: 
  - `googleapis/genai-toolbox` for database sandboxing.
  - `duckduckgo-search` for real-time web access.
  - `structlog` for structured, JSON-based diagnostics.
