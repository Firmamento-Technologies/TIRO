# TIRO — Analisi Completa di 13 Repository

> Generato il 2026-04-06 tramite GitNexus + estrazione documentazione automatica

---

## Indice

1. [Panoramica e Metriche GitNexus](#panoramica-e-metriche-gitnexus)
2. [CrewAI](#1-crewai) — Multi-agent orchestration framework
3. [nanobot](#2-nanobot) — Ultra-lightweight personal AI agent
4. [PM4Py](#3-pm4py) — Process mining library
5. [Open Notebook](#4-open-notebook) — AI research assistant
6. [AFFiNE](#5-affine) — All-in-one workspace platform
7. [Agency Swarm](#6-agency-swarm) — Multi-agent swarm framework
8. [Activepieces](#7-activepieces) — AI automation platform
9. [AutoGen](#8-autogen) — Microsoft multi-agent framework
10. [Torq](#9-torq) — High-performance vector search
11. [Digital Twin Framework](#10-digital-twin-framework) — Autonomous business AI
12. [Vexa](#11-vexa) — Meeting intelligence platform
13. [Atomic CRM](#12-atomic-crm) — Open-source React CRM
14. [Krayin Laravel CRM](#13-krayin-laravel-crm) — Laravel CRM for SMEs
15. [Tabella Comparativa Finale](#tabella-comparativa-finale)

---

## Panoramica e Metriche GitNexus

| # | Repository | Files | Nodes | Edges | Communities | Linguaggio | Licenza | Dimensione |
|---|-----------|-------|-------|-------|-------------|-----------|---------|------------|
| 1 | **crewai** | 2,744 | 36,322 | 65,750 | 627 | Python | MIT | 578M |
| 2 | **nanobot** | 217 | 4,689 | 13,550 | 299 | Python | MIT | 135M |
| 3 | **pm4py** | 1,995 | 9,060 | 28,303 | 1,028 | Python | AGPL-3.0 | 283M |
| 4 | **open-notebook** | 430 | 5,652 | 11,237 | 226 | Python+TS | MIT | 89M |
| 5 | **AFFiNE** | 8,063 | 48,396 | 135,087 | 1,992 | TS+Rust | MIT | 778M |
| 6 | **agency-swarm** | 392 | 5,021 | 12,242 | 309 | Python | MIT | 148M |
| 7 | **activepieces** | 19,061 | 46,240 | 120,998 | 982 | TypeScript | MIT+Comm. | 1.0G |
| 8 | **autogen** | 1,679 | 14,710 | 36,631 | 1,241 | Python+C# | MIT | 316M |
| 9 | **Torq** | 49 | 755 | 1,780 | 29 | Rust+Python | Apache-2.0 | 3.8G |
| 10 | **digital-twin** | 399 | 4,642 | 11,992 | 227 | Python | BUSL-1.1 | 90M |
| 11 | **vexa** | 354 | 5,791 | 11,566 | 244 | Python | Apache-2.0 | 111M |
| 12 | **atomic-crm** | 485 | 1,917 | 4,306 | 103 | TypeScript | MIT | 115M |
| 13 | **laravel-crm** | 991 | 5,826 | 14,828 | 400 | PHP | MIT | 188M |

**Legenda GitNexus:**
- **Nodes** = simboli nel knowledge graph (funzioni, classi, moduli, variabili esportate)
- **Edges** = relazioni tra simboli (chiamate, import, ereditarietà, dipendenze)
- **Communities** = cluster di simboli fortemente connessi (moduli logici rilevati automaticamente)

---

## 1. CrewAI

**Repository:** `crewaiinc/crewai`
**Path:** `/root/TIRO/crewai`

### Project Name and Description

**CrewAI** — Fast and Flexible Multi-Agent Automation Framework. A lean, lightning-fast Python framework for orchestrating role-playing, autonomous AI agents. Built entirely from scratch, completely independent of LangChain or any other agent framework. It empowers agents to work together seamlessly through collaborative intelligence.

### Version and License

- **License:** MIT
- **Python:** `>=3.10, <3.14`
- **Package manager:** UV (astral.sh/uv)
- **Author:** Joao Moura (joao@crewai.com)
- **PyPI package:** `crewai`

### Tech Stack and Main Dependencies

The workspace is a UV monorepo with four sub-packages under `lib/`:

| Package | Purpose |
|---------|---------|
| `crewai` | Core framework |
| `crewai-tools` | Tool library (file, web, DB, AI) |
| `crewai-files` | Multimodal file handling |
| `crewai-devtools` | Internal CLI for versioning/releasing |

Core dependencies (from `lib/crewai`): `pydantic`, `opentelemetry`, `rich`, `pydantic-core`. Dev tooling: `ruff 0.15.1`, `mypy 1.19.1`, `pytest`, `bandit`, `pre-commit`.

Notable dependency overrides (security/compat):
- `langchain-core>=1.2.11,<2` (CVE-2026-26013 SSRF fix)
- `urllib3>=2.6.3`
- `pillow>=12.1.1`

### Architecture Overview

CrewAI offers two complementary paradigms:

**Crews** — autonomous agent collaboration
- Teams of role-based agents working together
- Natural, autonomous decision-making
- Dynamic task delegation between agents
- Flexible problem-solving

**Flows** — event-driven, production-grade orchestration
- Fine-grained control over execution paths
- Secure, consistent state management via Pydantic models
- Conditional branching with `@start`, `@listen`, `@router` decorators
- Supports `or_` / `and_` logical operators for complex trigger conditions

The real power comes from **combining Crews inside Flows**: a Flow step can instantiate and `kickoff()` a Crew, then route based on the result.

**Internal source layout** (`lib/crewai/src/crewai/`):

| Directory | Purpose |
|-----------|---------|
| `agent/`, `agents/` | Agent definitions and builder patterns |
| `crew.py`, `crews/` | Crew orchestration, `@CrewBase` decorator |
| `flow/` | Flow engine, decorators, persistence, visualization |
| `memory/` | Unified memory system, encoding, recall, storage |
| `llm.py`, `llms/` | LLM abstraction layer |
| `mcp/` | Model Context Protocol integration |
| `tools/` (via crewai-tools) | Tool ecosystem |
| `a2a/` | Agent-to-agent communication |
| `knowledge/` | Knowledge base |
| `hooks/` | Lifecycle hooks |
| `cli/` | `crewai` CLI commands |

### Key Features

- **Standalone & Lean:** No LangChain dependency; 5.76x faster than LangGraph in benchmarks
- **Crews + Flows:** Two modes that compose seamlessly
- **Deep Customization:** Down to internal prompts and agent behaviors
- **MCP Support:** Connect to any Model Context Protocol server
- **Human-in-the-Loop:** Native support for human input during execution
- **Memory System:** Unified memory with encoding, storage, recall flows
- **Multimodal Files:** `crewai-files` handles images, PDFs, audio, video as task inputs
- **Telemetry:** Anonymous OTEL-based usage telemetry (disable with `OTEL_SDK_DISABLED=true`)
- **Enterprise (AMP Suite):** Control Plane, tracing/observability, on-premise/cloud deployment

**Processes available:**
- `Process.sequential` — tasks run in order
- `Process.hierarchical` — auto-assigns a manager agent for delegation

### API / Usage Patterns

**Project scaffold:**

```bash
crewai create crew <project_name>
crewai run
```

**Crew definition via YAML + decorators:**

```python
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

@CrewBase
class MyCrew:
    @agent
    def researcher(self) -> Agent:
        return Agent(config=self.agents_config['researcher'], verbose=True)

    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config['research_task'])

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, process=Process.sequential)
```

**Flow with routing:**

```python
from crewai.flow.flow import Flow, listen, start, router, or_
from pydantic import BaseModel

class MarketState(BaseModel):
    confidence: float = 0.0

class AnalysisFlow(Flow[MarketState]):
    @start()
    def fetch_data(self): ...

    @listen(fetch_data)
    def analyze(self, data):
        return analysis_crew.kickoff(inputs=data)

    @router(analyze)
    def route(self):
        if self.state.confidence > 0.8: return "high_confidence"
        return "low_confidence"

    @listen(or_("medium_confidence", "low_confidence"))
    def gather_more(self): ...
```

**Custom tools:**

```python
from crewai.tools import BaseTool

class MyTool(BaseTool):
    name: str = "Tool Name"
    description: str = "What it does."

    def _run(self, *args, **kwargs):
        return result

# Or decorator form:
from crewai import tool

@tool("Tool Name")
def my_tool(input): return output
```

### File Structure

```
crewai/
├── README.md
├── pyproject.toml             # UV workspace root, dev tooling config
├── uv.lock
├── docs/                      # Full documentation (MDX, multilingual: en/ko/pt-BR)
└── lib/
    ├── crewai/                # Core package
    │   └── src/crewai/        # Main source
    ├── crewai-tools/          # Tool collection
    ├── crewai-files/          # Multimodal file handling
    └── devtools/              # Internal release CLI
```

### Notable Design Patterns

- **`@CrewBase` decorator pattern:** Class-level decorator that auto-wires `@agent` and `@task` decorated methods into `self.agents` / `self.tasks` lists, auto-loading YAML configs from `config/agents.yaml` and `config/tasks.yaml`
- **YAML-first configuration:** Agent role/goal/backstory and task descriptions/outputs defined in YAML with `{topic}`-style template variables
- **Pydantic-typed Flow state:** `Flow[StateModel]` generic — state is a Pydantic BaseModel ensuring type safety across step transitions
- **Event-driven decorators:** `@start`, `@listen(fn)`, `@router(fn)` compose into a DAG evaluated at runtime
- **OpenTelemetry integration:** Native OTEL spans for tracing agent/task execution

---

## 2. nanobot

**Repository:** `HKUDS/nanobot`
**Path:** `/root/TIRO/nanobot`

### Project Name and Description

**nanobot** (`nanobot-ai` on PyPI) — Ultra-Lightweight Personal AI Agent. Inspired by OpenClaw, nanobot delivers core agent functionality with ~99% fewer lines of code than full frameworks. It is a long-running personal AI assistant that connects to chat platforms, executes tools, manages persistent memory, and runs scheduled tasks.

- Built by HKUDS (Hong Kong University of Data Science team)
- Version **0.1.5** (April 2026)

### Version and License

- **Version:** 0.1.5
- **License:** MIT
- **Python:** `>=3.11`

### Tech Stack and Main Dependencies

| Category | Libraries |
|----------|-----------|
| LLM clients | `anthropic`, `openai` (native SDKs, no litellm) |
| CLI | `typer`, `prompt-toolkit`, `questionary`, `rich` |
| Config/validation | `pydantic`, `pydantic-settings` |
| HTTP | `httpx` |
| MCP | `mcp>=1.26.0` |
| Scheduling | `croniter` |
| Web search | `ddgs` (DuckDuckGo, zero config default) |
| Git (memory versioning) | `dulwich` |
| Channels | `python-telegram-bot`, `lark-oapi`, `dingtalk-stream`, `slack-sdk`, `qq-botpy`, `discord.py`, `matrix-nio` |

### Architecture Overview

```
nanobot/
├── agent/         # Core agent loop, AgentHook system
├── api/           # OpenAI-compatible REST API server
├── bus/           # Internal event bus (OutboundMessage events)
├── channels/      # Channel implementations (BaseChannel + plugins)
├── cli/           # CLI commands (typer app)
├── command/       # In-chat command routing (/new, /dream, etc.)
├── config/        # Config schema (Pydantic models), config.json loading
├── cron/          # Cron scheduler
├── heartbeat/     # 30-min periodic task runner
├── providers/     # Provider registry + LLM routing
├── security/      # SSRF blocking, workspace restriction, bwrap sandbox
├── session/       # Session management, conversation history
├── skills/        # Built-in skill markdown files
└── templates/     # SOUL.md, USER.md, MEMORY.md, HEARTBEAT.md defaults
```

**Key architectural concepts:**

1. **Provider Registry** — single `ProviderSpec` registry; adding a new LLM provider is 2 steps
2. **Channel Plugin System** — channels discovered via Python entry points (`nanobot.channels` group)
3. **Event Bus** — channels publish/subscribe `OutboundMessage` events
4. **AgentHook system** — composable lifecycle hooks for the agent loop
5. **Layered Dream Memory:**
   - Short-term: `session.messages`
   - Compressed history: `memory/history.jsonl`
   - Long-term durable: `SOUL.md`, `USER.md`, `memory/MEMORY.md`
   - Version control: `GitStore` (dulwich) tracks changes

### Key Features

- **Ultra-lightweight:** Minimal codebase, fast startup
- **11 chat channels:** Telegram, Discord, WhatsApp, WeChat, Feishu, DingTalk, Slack, Matrix, Email, QQ, Wecom
- **22+ LLM providers:** OpenRouter, Anthropic, OpenAI, Azure, Groq, DeepSeek, Gemini, Ollama, vLLM, GitHub Copilot
- **MCP support:** Stdio and HTTP transports
- **Layered Dream memory** with git versioning
- **Cron/Heartbeat scheduling**
- **OpenAI-compatible API:** `nanobot serve`
- **Multi-instance:** Multiple bots with separate configs/workspaces
- **Security:** SSRF blocking, workspace restriction, bubblewrap sandbox
- **Voice transcription:** Via Whisper (Groq free tier or OpenAI)

### API / Usage Patterns

```bash
pip install nanobot-ai
nanobot onboard
nanobot agent          # interactive CLI chat
nanobot gateway        # start chat channel gateway
```

**Python SDK:**

```python
import asyncio
from nanobot import Nanobot

async def main():
    bot = Nanobot.from_config()
    result = await bot.run("What time is it in Tokyo?")
    print(result.content)

asyncio.run(main())
```

### Notable Design Patterns

- **Provider Registry as single source of truth** — no if-elif chains for provider detection
- **Entry-point plugin architecture** — zero code change needed to add external channel packages
- **Two-stage memory (Consolidator + Dream)** — Consolidator is reactive, Dream is proactive
- **Native SDK clients (no litellm)** — direct `openai` + `anthropic` SDK calls
- **GitStore for memory versioning** — uses `dulwich` for auditable, restorable memory changes

---

## 3. PM4Py

**Repository:** `process-intelligence-solutions/pm4py`
**Path:** `/root/TIRO/pm4py`

### Project Name and Description

**PM4Py** — Process Mining for Python. The reference implementation of process mining in the Python ecosystem, originally developed at the Fraunhofer Institute for Applied Information Technology FIT.

### Version and License

- **Version:** 2.7.22.1
- **License:** GNU AGPL-3.0 (open source); separate commercial license available
- **Python:** 3.9.x through 3.14.x

### Tech Stack and Main Dependencies

**Essential:** `numpy`, `pandas`, `deprecation`, `networkx`
**Normal:** `graphviz`, `intervaltree`, `lxml`, `matplotlib`, `pydotplus`, `pytz`, `scipy`, `tqdm`
**Optional:** `requests`, `pyvis`, `scikit-learn`, `polars`, `openai`, `pyarrow`

### Architecture Overview

PM4Py follows a **simplified interface + algorithm library** dual-structure:

**Top-level modules:**

| Module | Purpose |
|--------|---------|
| `read.py` | Import event logs (XES, CSV, OCEL) |
| `discovery.py` | Process model discovery |
| `conformance.py` | Conformance checking (alignments, token replay) |
| `filtering.py` | Log filtering |
| `visualization/` | Model visualization |
| `ocel.py` | Object-centric event logs |
| `ml.py` | ML feature extraction |
| `llm.py` | LLM integration |
| `streaming/` | Stream processing |

**Algorithm library** (`pm4py/algo/`): Discovery (Alpha Miner, Inductive Miner, Heuristics Miner), Conformance, Filtering, Simulation, Evaluation, Clustering, Concept Drift, Decision Mining, Organizational Mining.

**Process model objects** (`pm4py/objects/`): Petri nets, Process trees, BPMN, DFG, Heuristics nets, OCEL 2.0, POWL, Stochastic Petri nets.

### Key Features

- **Process Discovery:** Alpha Miner, Inductive Miner, Heuristics Miner, BPMN, DECLARE, DFG
- **Conformance Checking:** Token-based replay, alignments, DECLARE, LTL
- **Object-Centric Process Mining (OCEL 2.0):** Full support
- **Simulation:** Log generation from models
- **ML Integration:** Feature extraction for scikit-learn
- **LLM Integration:** `pm4py.llm` module
- **Privacy:** Anonymization, differential privacy
- **Streaming:** Online/streaming process mining
- **Polars Support:** Alternative to pandas

### API / Usage Patterns

```python
import pm4py

log = pm4py.read_xes('eventlog.xes')
net, im, fm = pm4py.discover_petri_net_inductive(log)
pm4py.view_petri_net(net, im, fm, format="svg")
fitness = pm4py.conformance_diagnostics_token_based_replay(log, net, im, fm)
```

### Notable Design Patterns

- **Simplified interface over algorithm library** — `pm4py.*` top-level functions with sensible defaults
- **Immutable model objects with explicit markings** — `(net, initial_marking, final_marking)` tuples
- **Algorithm variants as sub-packages** — switchable via `variant` parameter
- **OCEL 2.0 first-class citizen** — dedicated modules in `algo/`, `objects/`, and top-level API
- **Polars alternative path** — transparent Polars-compatible versions alongside pandas

---

## 4. Open Notebook

**Repository:** `lfnovo/open-notebook`
**Path:** `/root/TIRO/open-notebook`

### Project Name and Description

**Open Notebook** — An open-source, privacy-focused alternative to Google's Notebook LM. A self-hosted AI research assistant that lets users upload multi-modal content (PDFs, videos, audio, web pages, Office docs), generate intelligent notes, search semantically, chat with AI models, and produce professional multi-speaker podcasts.

### Version and License

- **Version:** 1.8.2
- **License:** MIT
- **Python:** `>=3.11, <3.13`

### Tech Stack and Main Dependencies

**Frontend:** Next.js 16 / React 19, Zustand, TanStack Query, Tailwind CSS + Shadcn/ui, i18n (7 languages)

**Backend:** FastAPI, LangChain + LangGraph, Pydantic v2, Uvicorn

**Database:** SurrealDB (graph database with native vector embeddings)

**AI Providers (via Esperanto):** OpenAI, Anthropic, Google, Groq, Ollama, Mistral, DeepSeek, xAI, Perplexity, ElevenLabs, Azure OpenAI, OpenRouter, DashScope, MiniMax, LM Studio (18+ providers)

**Content/Media:** `content-core` (50+ formats), `podcast-creator` (multi-speaker podcasts), `ai-prompter` (Jinja2 prompt templating)

### Architecture Overview

Three-tier async-first architecture:

```
Browser → Port 8502 (Next.js Frontend)
            ↓ proxies /api/* requests
         Port 5055 (FastAPI Backend)
            ↓ SurrealQL
         Port 8000 (SurrealDB)
```

**LangGraph Workflows:**

| Workflow | Purpose |
|----------|---------|
| Source Processing | Extract → embed → save |
| Chat | Multi-turn conversational AI |
| Ask (RAG) | Search + synthesize answers |
| Transformation | Extract insights from sources |
| Prompt | Generic LLM task execution |

### Key Features

- **Privacy-First**: All data self-hosted
- **Multi-Provider AI**: 18+ providers
- **Universal Content Support**: PDFs, videos, audio, web pages, Office docs
- **Intelligent Search**: Full-text + vector semantic search
- **Context-Aware Chat**: Chat (full context) and Ask (RAG retrieval)
- **Content Transformations**: Custom Jinja2-prompted extraction pipelines
- **Professional Podcast Generation**: 1–4 speakers with custom personas and TTS voices
- **MCP Integration**
- **Fine-Grained Context Control**: Three levels

### Notable Design Patterns

- **Domain-Driven Design (DDD)** with repository pattern
- **Async-First** — all I/O operations are async
- **Service Pattern** — services orchestrate domain models + repositories + LangGraph
- **Streaming Pattern** — SSE via FastAPI `StreamingResponse`
- **Job Queue Pattern** — fire-and-forget via `surreal-commands`
- **Factory Pattern (ModelManager)** — centralized AI model selection with fallback logic
- **Automatic Database Migrations** — numbered `.surql` files on API startup

---

## 5. AFFiNE

**Repository:** `toeverything/AFFiNE`
**Path:** `/root/TIRO/AFFiNE`

### Project Name and Description

**AFFiNE** — An open-source, all-in-one workspace platform. "Write, Draw and Plan All at Once." A privacy-focused, local-first alternative to Notion and Miro, featuring a unique "hyper-merged" canvas where documents, whiteboards, and databases coexist.

### Version and License

- **Version:** 0.26.3
- **License:** MIT (Community Edition)
- **Node.js:** `<23.0.0`

### Tech Stack and Main Dependencies

**Frontend:** TypeScript (strict), React, Jotai, Vite, Electron, Yarn 4.x

**Backend:** Node.js (NestJS pattern), PostgreSQL with pgvector, Redis, Prisma ORM

**Collaboration Engine:** BlockSuite (collaborative editor), Yjs / y-octo (CRDT — Rust implementation), OctoBase (local-first database, Rust)

**Native Layer:** Rust + NAPI.rs

**Testing:** Playwright (E2E), Vitest (unit)

### Architecture Overview

```
packages/
  backend/
    server/         # NestJS-style Node.js API server
    native/         # Rust native bindings for server
  frontend/
    apps/           # Deployable app targets
    core/           # Main web application (React)
    component/      # @affine/component UI library
    electron-api/   # Electron integration layer
    native/         # Rust native bindings for frontend
  common/
    theme/          # @toeverything/theme design tokens
    y-octo/         # Rust CRDT implementation
blocksuite/         # Collaborative editor engine
```

**Key architectural principles:**
- **Local-first**: Data lives on-disk; sync is additive
- **Block-based**: Everything is a "block"
- **CRDT-powered**: y-octo (Rust) for conflict-free real-time collaboration
- **Edgeless Canvas**: Any block type on a 2D whiteboard
- **Plugin-ready**: Extensible through third-party blocks

**Backend plugins:** `copilot`, `payment`, `oauth`, `indexer`, `calendar`, `license`, `gcloud`, `worker`

**Frontend modules (~40+):** `doc`, `collection`, `cloud`, `db`, `comment`, `backup`, `blob-management`, `desktop-api`, `dialogs`, `dnd`, `doc-info`, `doc-link`, `doc-summary`, and more

### Key Features

- **Merged Docs + Whiteboard**: Rich text, sticky notes, embedded web pages, databases, shapes, slides
- **Multimodal AI (AFFiNE AI)**: Write reports, turn outlines into slides, summarize to mind maps
- **Local-First + Real-Time Collaboration**: Own your data; cloud sync optional
- **Self-Host**: Full self-hosted via Docker
- **Cross-Platform**: Web app + Electron desktop (macOS, Windows, Linux)
- **Templates**: Vision boards, lesson plans, planners, Cornell notes, etc.

### Notable Design Patterns

- **Block Architecture** — everything is a composable "block" extended to 2D canvas
- **CRDT-first Collaboration** — y-octo ensures conflict-free merging; local is truth
- **Yarn Monorepo with Custom CLI** — `affine.ts` drives all workspace tasks
- **Hybrid Native/JS** — hot paths in Rust via NAPI.rs
- **Plugin Architecture (Backend)** — isolated NestJS-style feature plugins
- **Feature Module Pattern (Frontend)** — ~40 independent modules

---

## 6. Agency Swarm

**Repository:** `VRSEN/agency-swarm`
**Path:** `/root/TIRO/agency-swarm`

### Project Name and Description

**Agency Swarm** — A framework for building multi-agent applications built on top of the OpenAI Agents SDK. Simplifies creating, orchestrating, and managing collaborative swarms of AI agents organized around real-world organizational structures.

### Version and License

- **Version:** 1.8.0
- **License:** MIT
- **Python:** `>=3.12`
- **Coverage:** 92%

### Tech Stack and Main Dependencies

**Core:** `openai`, `openai-agents ==0.9.3`, `pydantic >=2.11`, `python-dotenv`

**Tool system:** `datamodel-code-generator`, `fastmcp >=2.13.1`, `mcp >=1.13.1`

**UI/CLI:** `rich`, `prompt-toolkit`, `termcolor`, `watchfiles`

**API server (optional):** `fastapi`, `uvicorn`, `ag-ui-protocol` (CopilotKit)

**Optional:** `litellm` (multi-provider), `graphviz` (visualization)

### Architecture Overview

```
User / External System
        ↓
    Agency (entry points)
        ↓ communication_flows
    Agent (CEO / role)
        ↓ SendMessage tool
    Agent (Developer / role)  ←→  Agent (VA / role)
        ↓ tools
    Custom Tools / MCP Servers / OpenAPI Tools
```

**Communication patterns:**
- **Orchestrator-Worker**: One agent delegates, control returns after each delegation
- **Handoff**: Control transfers completely to another agent

### Key Features

- **Customizable Agent Roles**: CEO, Developer, VA, etc.
- **Full Prompt Control**: No preset constraints
- **Type-Safe Tools**: Pydantic validation; `@function_tool` decorator or `BaseTool` class
- **Directional Communication Flows**: Explicit `(sender, receiver)` tuples
- **State Persistence**: `load_threads_callback` / `save_threads_callback` hooks
- **MCP Integration**
- **Guardrails**: Input and output with configurable retry
- **Multiple Run Modes**: CopilotKit/AG-UI, TUI, programmatic API
- **Observability**: OpenAI tracing, Langfuse, AgentOps
- **LiteLLM Router**: Anthropic, Gemini, Azure, Grok, OpenRouter

### API / Usage Patterns

```python
from agency_swarm import Agency, Agent, function_tool

@function_tool
def my_tool(example_field: str) -> str:
    """Brief description."""
    return f"Result: {example_field}"

ceo = Agent(name="CEO", description="Client communication.", tools=[my_tool], model="gpt-5.4-mini")
dev = Agent(name="Developer", description="Writes code.", model="gpt-5.4-mini")

agency = Agency(
    ceo, dev,
    communication_flows=[(ceo, dev)],
    shared_instructions="agency_manifesto.md",
)

result = await agency.get_response("Build me a project skeleton.")
```

### Notable Design Patterns

- **Organizational Metaphor** — agents as company employees
- **Directional Communication Graph** — explicit directed edges prevent unintended interactions
- **Tool-as-Class Pattern (BaseTool)** — Pydantic models with docstrings as tool descriptions
- **Folder-Based Agent Discovery** — `tools_folder` and `files_folder` for self-contained agents
- **Persistence via Callbacks** — framework is storage-agnostic
- **AG-UI Protocol** — auto-launches CopilotKit interface

---

## 7. Activepieces

**Repository:** `activepieces/activepieces`
**Path:** `/root/TIRO/activepieces`

### Project Name and Description

**Activepieces** — An open-source, all-in-one AI automation platform. "An open source replacement for Zapier." Extensible through a type-safe pieces framework in TypeScript, with MCP support so all integrations can be used directly with LLMs.

### Version and License

- **Version:** 0.81.3
- **License:** MIT (Community); Commercial (Enterprise)
- **Package Manager:** Bun 1.3.3, Turborepo

### Tech Stack and Main Dependencies

**Backend:** Fastify, BullMQ, TypeORM, PostgreSQL / PGLite, Redis, AWS S3

**Frontend:** Angular

**AI:** `@ai-sdk/anthropic`, `@ai-sdk/openai`, `@ai-sdk/google`, `@ai-sdk/azure`, `@ai-sdk/replicate`, `@ai-sdk/mcp` — Vercel AI SDK

**Infrastructure:** Docker / Docker Compose / Kubernetes (Helm)

### Architecture Overview

| Service | Purpose |
|---------|---------|
| `api` (server) | REST API, flow management |
| `engine` | Flow execution engine |
| `worker` | Background job processor (BullMQ) |
| `web` | Angular frontend |

```
packages/
  server/api/       Backend API (Fastify + TypeORM)
  server/worker/    BullMQ worker
  engine/           Step execution runtime
  web/              Angular SPA
  shared/           Shared types and utilities
  pieces/community/ 200+ community integration pieces
  pieces/ee/        Enterprise pieces
  cli/              CLI for piece scaffolding
  tests-e2e/        Playwright E2E tests
docs/               Mintlify documentation
```

### Key Features

- **280+ Pieces (Integrations):** All open-source, versioned on npm
- **MCP Server Built-In:** All 280+ pieces exposed as MCP tools; 30 categorized MCP tools
- **Flow Builder:** Visual no-code with loops, branches, auto-retries, human-in-the-loop
- **AI-First:** Native AI pieces, AI SDK integration
- **Enterprise:** Custom branding, SSO (SAML), network-gapped self-hosting, RBAC

### API / Usage Patterns

**Creating a Piece (Action):**

```typescript
import { createAction, Property, PieceAuth } from '@activepieces/pieces-framework';
import { httpClient, HttpMethod } from '@activepieces/pieces-common';

export const getIcecreamFlavor = createAction({
  name: 'get_icecream_flavor',
  auth: gelatoAuth,
  displayName: 'Get Icecream Flavor',
  props: {},
  async run(context) {
    const res = await httpClient.sendRequest<string[]>({
      method: HttpMethod.GET,
      url: 'https://api.example.com/flavors',
      headers: { Authorization: context.auth },
    });
    return res.body;
  },
});
```

### Notable Design Patterns

- **Pieces as versioned npm packages** — independently versioned and published
- **Type-safe framework** — `createPiece`, `createAction`, `createTrigger` with full TypeScript inference
- **Go-style error handling** — `tryCatch` / `tryCatchSync` from `@activepieces/shared`
- **MCP as first-class citizen** — same TypeScript definition powers both automation and MCP
- **Hot Reloading** — piece changes reflect in ~7 seconds during development

---

## 8. AutoGen

**Repository:** `microsoft/autogen`
**Path:** `/root/TIRO/autogen`

### Project Name and Description

**AutoGen** (Microsoft) — A framework for creating multi-agent AI applications. v0.4 is a ground-up rewrite with asynchronous messaging, distributed runtimes, cross-language support (.NET and Python), and layered architecture.

> Note: Microsoft announced the [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) as the forward path.

### Version and License

- **Version:** 0.7.5
- **License:** MIT (code); CC BY 4.0 (docs)
- **Python:** 3.10+

### Tech Stack and Main Dependencies

| Package | Purpose |
|---------|---------|
| `autogen-core` | Event-driven agent runtime, Actor model |
| `autogen-agentchat` | High-level multi-agent chat API |
| `autogen-ext` | LLM clients, tools, memory, code execution, MCP |
| `autogenstudio` | No-code GUI (FastAPI + React/Gatsby) |

Extensions: OpenAI, Anthropic, Azure, Docker, Ollama, LangChain, GraphRAG, ChromaDB, Mem0, llama.cpp, MCP

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  AutoGen Studio  — no-code GUI                           │
│  Magentic-One — task-capable team                        │
├─────────────────────────────────────────────────────────┤
│  AgentChat API (autogen-agentchat)                       │
│  Agents, Teams, Patterns (RoundRobin, Swarm, etc.)      │
├─────────────────────────────────────────────────────────┤
│  Extensions API (autogen-ext)                            │
│  LLM clients, tools, memory, code execution, MCP        │
├─────────────────────────────────────────────────────────┤
│  Core API (autogen-core)                                 │
│  Actor model, pub-sub messaging, distributed runtime     │
└─────────────────────────────────────────────────────────┘
```

**Core programming model:** Publish-Subscribe using CloudEvents specification. Agents subscribe to topics and publish events. Agent instances are `AgentType:key`.

### Key Features

- **Multi-agent orchestration:** `AgentTool` wraps any agent as a callable tool
- **Streaming:** Token streaming through Console UI
- **MCP integration:** `McpWorkbench` connects to any MCP server
- **Distributed runtime:** Local or gRPC; same agent code works in both
- **Cross-language:** Python and .NET (protobuf/gRPC)
- **Magentic-One:** Pre-built SOTA multi-agent team
- **AutoGen Studio:** No-code GUI for prototyping
- **Observability:** OpenTelemetry integration

### API / Usage Patterns

```python
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main():
    model_client = OpenAIChatCompletionClient(model="gpt-4.1")
    agent = AssistantAgent("assistant", model_client=model_client)
    print(await agent.run(task="Say 'Hello World!'"))
    await model_client.close()

asyncio.run(main())
```

**MCP + Agent-as-Tool:**

```python
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams

server_params = StdioServerParams(command="npx", args=["@playwright/mcp@latest", "--headless"])
async with McpWorkbench(server_params) as mcp:
    agent = AssistantAgent("browser", model_client=model_client, workbench=mcp)
    await Console(agent.run_stream(task="Find contributors for microsoft/autogen"))
```

### Notable Design Patterns

- **Actor Model** — agents process messages asynchronously, no shared state
- **CloudEvents-based messaging** — interoperable event specification
- **Layered abstraction** — high-level AgentChat, low-level Core, cross-language .NET
- **Subscriptions as pure functions** — cacheable by runtime
- **Agent-as-Tool pattern** — hierarchical orchestration via `AgentTool`
- **Cross-runtime portability** — local code runs unchanged on distributed gRPC

---

## 9. Torq

**Repository:** `Firmamento-Technologies/Torq`
**Path:** `/root/TIRO/Torq`

### Project Name and Description

**Torq** (`torq-vec` on PyPI) — High-performance vector search with near-optimal scalar quantization. Combines **TurboQuant** scalar quantization (2.72x Shannon limit) with Rust-native HNSW graph, AVX2 SIMD acceleration, and Python bindings via PyO3.

Created by Luca Di Domenico at Firmamento Technologies.

### Version and License

- **Version:** 0.1.0
- **License:** Apache-2.0
- **Python:** 3.10+
- **Rust edition:** 2021

### Tech Stack and Main Dependencies

**Rust:** `faer` (linear algebra), `rayon` (parallelism), `serde` (serialization), `rand` (RNG), `criterion` (benchmarks)

**Python:** `pyo3` (Rust-Python FFI), `numpy >= 1.24`, `maturin >= 1.5`

### Architecture Overview

```
torq-core/          Rust library
  src/
    quantizer/      LloydMax codebook, TurboQuantMSE, TurboQuantProd
    index/          FlatIndex + HnswIndex (normal + compact + delete + filter)
    hnsw/           Graph, Builder, Search
    simd/           AVX2 PSHUFB ADC + FMA dot product + scalar fallback
    storage/        .torq binary format

torq-py/            PyO3 bindings
  src/lib.rs        TorqIndex + HnswTorqIndex (GIL release, rayon parallel)
```

**Two operating modes:**
- **Normal:** HNSW + AVX2 FMA on raw float32
- **Compact** (after `.compact()`): ADC on quantized codes — **75% memory reduction**

### Key Features

- **TurboQuant:** 3.2x better recall than FAISS PQ at same 4-bit budget
- **Compact mode:** 75% memory reduction, ~0.5pp recall loss
- **Filtered search:** `allowed_ids` parameter for ID-filtered ANN
- **Soft delete:** `index.delete(id)` without rebuild
- **Persistence:** `.save()` / `.load()` to `.torq` binary format
- **GIL release:** True parallelism in Python
- **AVX2 SIMD:** 32 floats/cycle with 4-accumulator FMA

### API / Usage Patterns

```python
from torq import HnswTorqIndex
import numpy as np

vectors = np.random.randn(10_000, 128).astype(np.float32)
queries = np.random.randn(10, 128).astype(np.float32)

index = HnswTorqIndex(dimension=128, num_bits=8, m=16, ef_construction=200, ef_search=50, seed=42)
index.add(vectors)
similarities, indices = index.search(queries, k=10)

# Compact mode: 75% less memory
index.compact()
similarities, indices = index.search(queries, k=10)

# Filtered search
sims, ids = index.search(queries, k=3, allowed_ids=[0, 2, 4, 6, 8])

# Persistence
index.save("index.torq")
loaded = HnswTorqIndex.load("index.torq")
```

### Notable Design Patterns

- **Workspace Rust crate** — pure Rust library + thin PyO3 wrapper
- **Dual-mode index** — same struct supports normal and compact, toggled by `.compact()`
- **Zero-copy NumPy interop** — `PyReadonlyArray2<f32>` reads directly
- **Scalar over product quantization** — theoretically superior to FAISS PQ
- **Soft delete via bitset** — online deletion without graph rebuild
- **ADC reranking** — balance speed and recall via dequantization

---

## 10. Digital Twin Framework

**Repository:** `Firmamento-Technologies/digital-twin`
**Path:** `/root/TIRO/digital-twin`

### Project Name and Description

**Digital Twin Framework** — Autonomous multi-agent digital twin for businesses. Deploy a team of 9 AI executives (CEO, CTO, CMO, CFO, CLO, HR, Intelligence, BizDev, Efficiency Analyst) that autonomously manage business operations. Every action queued for human approval.

Created by Luca Di Domenico at Firmamento Technologies.

### Version and License

- **Version:** 1.4.0
- **License:** Business Source License 1.1 (→ Apache 2.0 on 2030-03-16)
- **Python:** 3.11+

### Tech Stack and Main Dependencies

- **Language:** Pure Python 3.11+ (stdlib only for core — zero external deps)
- **Optional:** `jinja2` (admin panel), `sentence-transformers` (neural embeddings)
- **Admin UI:** Jinja2 + htmx + Tailwind CSS
- **LLM calls:** Pure `urllib` — zero SDK dependencies

### Architecture Overview

Three nested cycles via cron every 30 minutes:

1. **Proactive Cycle (every 30 min):** Scans `.twin/` directories, processes event triggers
2. **Creative Cycle (~every 6 hours):** Morning analysis + afternoon web research. Ideas self-scored; only >6 reach queue
3. **HR + Maintenance Cycle (~daily):** Capability gap detection, data validation, security checks

**Full 19-phase tick sequence:**
```
READ STATE → LOAD ETHICS → SECURITY CHECK → UPDATE PHASE
→ PROACTIVE CYCLE → MESSAGING CHECK → ACTIVE SUPPORT
→ CREATIVE CYCLE → COMMS-TEAM CYCLE → HR CHECK
→ FEEDBACK LOOP → PROCESS APPROVED → ADMIN COMMANDS
→ MAINTENANCE → COMMS MAINTENANCE → BRIEFING/DIGEST
→ ETHICS SAFETY NET → COMMIT & PUSH → UPDATE FINAL STATE
```

**Git as Message Bus:** Human approvals via git file moves, picked up on next tick.

### Key Features

- **9 C-suite agents** + **26+ specialist roles** across 7 categories
- **Deliberation Room:** Multi-agent consensus sessions
- **Budget Governance:** Per-agent and global monthly limits
- **Admin Panel:** Jinja2 + htmx, 48 REST endpoints
- **Workflow Engine:** JSON-defined multi-agent pipelines
- **Semantic Memory:** TF-IDF vector store (SQLite + cosine similarity)
- **Autonomous Hands:** Pre-built capability packages with lifecycle management
- **10 LLM providers:** Anthropic, OpenAI, Google, Groq, DeepSeek, Mistral, OpenRouter, Claude Code, Ollama, Demo
- **17 integrations:** Google Workspace, LinkedIn, Twitter, Instagram, Slack, Discord, Telegram, WhatsApp, etc.
- **23 security layers** including AES-256 vault, RBAC, CSRF, prompt injection detection
- **Knowledge Base:** Fact extraction from documents/email
- **724 passing tests** (51 modules)

### File Structure

```
digital-twin/
├── .twin/                  # Business state (JSON, git-versioned)
│   ├── agents/             # Registry, teams, memory, deliberations
│   ├── company/            # Profile, brand, services, legal
│   ├── goals/              # Mission, KPIs, quarterly targets
│   ├── queue/              # pending/ → approved/ → executed/
│   ├── budget/             # Policies, incident log
│   ├── knowledge/          # AI-extracted facts
│   ├── vault/              # AES-256 encrypted data
│   ├── workflows/          # JSON workflow definitions
│   └── events.jsonl        # Immutable audit trail
├── .claude/skills/         # 13 Claude Code skill definitions
├── scripts/
│   ├── engine/             # LLM engine, providers, cost tracker
│   ├── integrations/       # 17 external service connectors
│   ├── panel/              # Admin web panel
│   └── marketplace/        # Hand manager
├── shared/schemas/         # 16 JSON Schema validation files
├── tests/                  # 724 passing tests
└── pyproject.toml
```

### Notable Design Patterns

- **Event Sourcing** — all state changes emit events to `events.jsonl` (append-only)
- **Human-in-the-Loop** — nothing executes without queue approval; 4 risk levels
- **Feedback Adaptation** — approvals increase focus weight; rejections decrease and raise thresholds
- **Zero External Dependencies** — all LLM calls via pure `urllib`
- **Schema-Validated State** — 16 JSON schemas validate all `.twin/` writes
- **Git as Message Bus** — human approvals communicated via git file moves

---

## 11. Vexa

**Repository:** `Vexa-ai/vexa`
**Path:** `/root/TIRO/vexa`

### Project Name and Description

**Vexa** — Self-hosted, open-source meeting intelligence platform. Automatically joins Google Meet, Microsoft Teams, and Zoom meetings, captures audio, and provides real-time transcriptions via REST API and WebSocket.

### Version and License

- **Version:** v0.9 (pre-release)
- **License:** Apache-2.0

### Tech Stack and Main Dependencies

**Backend services (Python/FastAPI microservices):**
- `api-gateway`: FastAPI, Redis
- `admin-api`: FastAPI, PostgreSQL, Alembic
- `bot-manager`: Docker-in-Docker orchestration
- `vexa-bot`: Selenium/browser automation
- `WhisperLive`: Real-time Whisper transcription
- `transcription-collector`: Segment storage
- `tts-service`: OpenAI TTS
- `mcp`: MCP server

**Infrastructure:** Docker Compose, PostgreSQL, Redis, MinIO/S3

### Architecture Overview

```
Client (REST/WebSocket)
  → api-gateway (:8056)
      → admin-api (:8057)
      → bot-manager → vexa-bot (Docker-in-Docker per meeting)
      → transcription-collector → WhisperLive → transcription-service
      → mcp (:18888)
```

### Key Features

- **Meeting bots** for Google Meet, Microsoft Teams, Zoom
- **Real-time transcription** via Whisper — 100+ languages
- **Real-time translation** across all languages
- **WebSocket streaming** for live transcript updates
- **Interactive Bots API:** speak, chat, screen share, avatar
- **Recording persistence:** local, MinIO, S3-compatible
- **MCP server** — AI agents can control meetings
- **Webhook events:** `meeting.status_change`, `recording.completed`
- **Self-hostable:** Lite (single container) or full stack

### API / Usage Patterns

```bash
# Send bot to meeting
curl -X POST "$API_BASE/bots" \
  -H "X-API-Key: $API_KEY" \
  -d '{"platform": "google_meet", "native_meeting_id": "abc-defg-hij", "recording_enabled": true}'

# Get transcript
curl -H "X-API-Key: $API_KEY" "$API_BASE/transcripts/google_meet/abc-defg-hij"

# Interactive bot — speak in meeting
curl -X POST "$API_BASE/bots/google_meet/abc-defg-hij/speak" \
  -H "X-API-Key: $API_KEY" \
  -d '{"text": "Hello everyone.", "voice": "nova"}'
```

### Notable Design Patterns

- **Microservices with clear separation** — api-gateway never accesses DB directly
- **Session-based transcript alignment** — `session_uid` links segments to recording timeline
- **Docker-in-Docker for bots** — individual containers per meeting join
- **Decoupled recording/transcription** — independent flags
- **MCP prompts pattern** — pre-built agent workflows as MCP prompts
- **Anonymization on delete** — purge artifacts then anonymize

---

## 12. Atomic CRM

**Repository:** `marmelab/atomic-crm`
**Path:** `/root/TIRO/atomic-crm`

### Project Name and Description

**Atomic CRM** — A full-featured, free and open-source CRM built with React, shadcn-admin-kit, and Supabase. Intentionally small (~15,000 LOC). Distributed as a Shadcn Registry file.

### Version and License

- **Version:** 0.1.0
- **License:** MIT (Marmelab)

### Tech Stack and Main Dependencies

**Frontend:** React 19, TypeScript, Vite 7, React Router v7, TanStack React Query v5, React Hook Form, shadcn-admin-kit + ra-core, Shadcn UI + Radix UI, Tailwind CSS v4, Zod v4

**Backend:** Supabase (PostgreSQL + PostgREST + Auth + Edge Functions)

**Testing:** Vitest + Playwright, Storybook 9

### Architecture Overview

```
Browser SPA (React)
  → Shadcn Admin Kit (ra-core framework)
      → Supabase Data Provider (ra-supabase-core)
          → PostgREST API
          → Supabase Auth
          → Edge Functions
      ↓ (dev/demo mode)
      → FakeRest Data Provider (in-browser)

Supabase PostgreSQL:
  Tables: contacts, companies, deals, tasks, contact_notes, deal_notes, sales, tags, products
  Views: contacts_summary, companies_summary
  Edge Functions: users, inbound-email
```

### Key Features

- Contact management with CSV import/export and merging
- Company management
- Task management with reminders
- Note taking (manual + inbound email auto-capture)
- Deal pipeline as Kanban board
- Activity history
- SSO: Google, Azure, Keycloak, Auth0
- Custom fields, theme customization
- MCP server
- PWA support

### Notable Design Patterns

- **Mutable Vendor Pattern** — shadcn components copied and modified directly
- **Database-as-Source-of-Truth** — declarative schema in `supabase/schemas/`
- **Two Data Provider Strategy** — Supabase (production) + FakeRest (demo)
- **Shadcn Registry Distribution** — entire CRM distributed as a registry JSON
- **No user deletion** — Supabase ban for account disabling

---

## 13. Krayin Laravel CRM

**Repository:** `krayin/laravel-crm`
**Path:** `/root/TIRO/laravel-crm`

### Project Name and Description

**Krayin CRM** — Free and open-source Laravel CRM for SMEs and Enterprises. Complete customer lifecycle management built on Laravel 12 and Vue.js with a modular package architecture.

### Version and License

- **Version:** 2.2.0
- **License:** MIT
- **PHP:** 8.3+
- **Laravel:** 12.x

### Tech Stack and Main Dependencies

**Backend:** `laravel/framework ^12.0`, `laravel/sanctum ^4.0`, `konekt/concord ^1.17` (module system), `prettus/l5-repository ^3.0`, `league/fractal ^0.21.0`, `maatwebsite/excel ^3.1`, `webklex/laravel-imap ^6.0`, `barryvdh/laravel-dompdf ^3.1`

**Frontend:** Vue.js, Vite 5

**Testing:** `pestphp/pest ^3.0`

### Architecture Overview

Modular monolith using `konekt/concord`:

```
packages/Webkul/
├── Core/          # Foundation: config, helpers, traits
├── Admin/         # Admin panel: controllers, views, bouncer, datagrid
├── Lead/          # Leads: models, repos, services
├── Contact/       # Contacts & Organizations
├── Activity/      # Activity timeline
├── Email/         # IMAP parsing, SendGrid
├── Marketing/     # Campaigns, automation
├── Quote/         # Quotes and proposals
├── Product/       # Product catalog
├── Attribute/     # Custom attributes system
├── DataGrid/      # DataGrid component
├── DataTransfer/  # Import/export
├── User/          # Users & roles
├── Tag/           # Tagging
├── Warehouse/     # Warehouse/inventory
└── WebForm/       # Web-to-lead forms
```

### Key Features

- Leads management with pipeline
- Quotes with PDF generation
- Contact & Organization management
- Activity timeline
- Email parsing (SendGrid + IMAP)
- Marketing campaigns and automation
- Custom attributes system
- DataGrid component with filters, sorting, mass actions
- Data import/export (Excel/CSV)
- Web-to-lead forms
- Role-based ACL (Bouncer)
- Multi-language (including Arabic)
- Commercial extensions: Multi-tenant SaaS, WhatsApp, VoIP

### API / Usage Patterns

```bash
composer create-project krayin/laravel-crm
php artisan krayin-crm:install
php artisan serve
# http://localhost:8000/admin/login → admin@example.com / admin123
```

### Notable Design Patterns

- **Modular Package Architecture (Concord)** — each domain is an independent service provider
- **Repository Pattern (l5-repository)** — controllers never query Eloquent directly
- **Config-driven ACL (Bouncer)** — permissions in each package's `Config/acl.php`
- **DataGrid Component** — reusable server-side grid with declarative API
- **Transformer Layer (Fractal)** — separated serialization from model logic
- **Event-Driven Activity Tracking** — unified timeline without tight coupling

---

## Tabella Comparativa Finale

| Repository | Dominio | Linguaggio | Licenza | Versione | GitNexus Nodes | GitNexus Edges | Pattern Chiave |
|-----------|---------|-----------|---------|----------|---------------|---------------|----------------|
| **crewai** | Multi-agent orchestration | Python | MIT | latest | 36,322 | 65,750 | Crew/Flow duality, YAML-first config |
| **nanobot** | Personal AI agent | Python | MIT | 0.1.5 | 4,689 | 13,550 | Dream memory, provider registry |
| **pm4py** | Process mining | Python | AGPL-3.0 | 2.7.22 | 9,060 | 28,303 | Simplified interface, OCEL 2.0 |
| **open-notebook** | AI research assistant | Python+TS | MIT | 1.8.2 | 5,652 | 11,237 | DDD, LangGraph workflows |
| **AFFiNE** | Knowledge workspace | TS+Rust | MIT | 0.26.3 | 48,396 | 135,087 | CRDT-first, block architecture |
| **agency-swarm** | Agent swarm framework | Python | MIT | 1.8.0 | 5,021 | 12,242 | Org metaphor, directional comms |
| **activepieces** | Automation (iPaaS) | TypeScript | MIT+Comm. | 0.81.3 | 46,240 | 120,998 | Pieces as npm packages, MCP |
| **autogen** | Multi-agent framework | Python+C# | MIT | 0.7.5 | 14,710 | 36,631 | Actor model, CloudEvents |
| **Torq** | Vector search (ANN) | Rust+Python | Apache-2.0 | 0.1.0 | 755 | 1,780 | TurboQuant, compact mode |
| **digital-twin** | Autonomous business AI | Python | BUSL-1.1 | 1.4.0 | 4,642 | 11,992 | Event sourcing, git-as-bus |
| **vexa** | Meeting intelligence | Python | Apache-2.0 | v0.9 | 5,791 | 11,566 | Microservices, DinD bots |
| **atomic-crm** | Sales CRM | TypeScript | MIT | 0.1.0 | 1,917 | 4,306 | Shadcn registry, Supabase BaaS |
| **laravel-crm** | Customer CRM | PHP | MIT | 2.2.0 | 5,826 | 14,828 | Modular monolith, Concord |

### Raggruppamento per Categoria

**Framework Agentici (4):**
- CrewAI → Crews + Flows, YAML config, 5.76x faster than LangGraph
- AutoGen → Actor model, distributed gRPC, cross-language (Python + .NET)
- Agency Swarm → Organizational metaphor, OpenAI Agents SDK, directional comms
- nanobot → Ultra-lightweight, Dream memory, 11 chat channels

**Automazione & Workflow (1):**
- Activepieces → 280+ integrations, MCP built-in, visual flow builder

**Knowledge & Research (2):**
- AFFiNE → Docs + whiteboard + database on one canvas, CRDT, Electron
- Open Notebook → NotebookLM alternative, 18+ AI providers, podcast generation

**Process Mining (1):**
- PM4Py → Academic reference, OCEL 2.0, 20+ algorithms

**CRM (2):**
- Atomic CRM → React + Supabase, 15K LOC, Shadcn registry distribution
- Krayin CRM → Laravel 12, modular monolith, enterprise-ready

**Meeting Intelligence (1):**
- Vexa → Real-time transcription, interactive bots, MCP server

**Infrastructure & Search (1):**
- Torq → Rust HNSW + TurboQuant, 75% memory savings, AVX2 SIMD

**Business Autonomy (1):**
- Digital Twin → 9 AI executives, human-in-the-loop, zero dependencies
