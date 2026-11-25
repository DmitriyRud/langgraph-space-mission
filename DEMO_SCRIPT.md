# Mentor Demo Script — AI Space Mission (5–7 Minutes)

This script walks through every core LangGraph capability in **5 to 7 minutes** using **Demo Mode** (fast, deterministic, zero network/API risk) and optionally shows **Live Mode (Ollama)**.

---

## Preparation (Before Presentation)

1. Start Backend:
   ```bash
   cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000
   ```
2. Start Frontend:
   ```bash
   cd frontend && npm run dev
   ```
3. Open **http://localhost:5173** in a wide browser window.
4. Confirm **DEMO MODE** is active and **Engine Failure** is selected.

---

## Minute 0:00 – 1:00 | Concept & Real Graph Topology

- Point to the 4-zone Mission Control layout:
  - **Left**: Ship Telemetry for **AURORA-7** (9 metrics + live schematic SVG).
  - **Center**: **LangGraph Live Inspector** (React Flow) — emphasize that the graph structure is fetched dynamically from `compiled_graph.get_graph()` on the backend, not hardcoded on the frontend.
  - **Right**: **AI Crew** cards (Commander, Engineer, Scientist, Medical Officer, Safety Officer).
  - **Bottom**: **Developer Console** (Logs, State, State Diff, Checkpoints, LLM Calls, LangGraph Learning).
- Mention that **Demo Mode** executes the exact same real LangGraph `StateGraph`, reducers, SQLite checkpointer, and `interrupt()` — only the LLM call is replaced by deterministic structured outputs.

---

## Minute 1:00 – 2:30 | Parallel `Send()`, Reducers & Cyclic Safety Rejection

1. Click **Start Mission**.
2. Narrate what happens live on the graph:
   - `incident_init` loads **Engine Failure** (Engine drops to 35%, Energy to 58%).
   - `commander` dynamically selects `engineer` and `medical_officer` and dispatches them in parallel via **LangGraph `Send()`** (`scientist` shows dashed `skipped`).
   - Both specialists complete and converge in `plan_aggregator` via the custom `merge_specialist_reports` **reducer**.
   - **Watch the Safety Loop**: Draft #1 proposes an unsafe shortcut (`overdrive_damaged_core`). `safety_officer` turns **red**, rejects the plan, and routes back to `commander` along the purple cyclic edge!
   - `commander` resets iteration reports via the reducer sentinel, re-runs specialists (`2x` badge appears), and produces a safe EVA thruster repair plan.
   - `safety_officer` approves Draft #2 and the graph pauses at `human_approval` (**amber**).

---

## Minute 2:30 – 4:00 | Human-in-the-Loop (`interrupt()` & `Command`) + Persistence

1. Show the **Captain Authorization** overlay showing the proposed actions, resource summary, and projected telemetry deltas.
2. Demonstrate **Request Revision** (optional, 15s) OR demonstrate **Browser Reload Recovery**:
   - Refresh the browser page (`Cmd+R`).
   - Point out that the paused mission **automatically restores** from SQLite (`AsyncSqliteSaver`) right at the `interrupt()`!
3. Click **Approve & Execute**.
   - Backend resumes the thread with `Command(resume={"decision": "approve"})`.
   - `executor` (non-LLM deterministic node) applies the repair -> watch **Engine Condition** jump from 35% to 75% on the left panel!
   - `mission_evaluator` checks thresholds: Energy is still below 60%, so it loops to **Iteration 2**.
4. Approve Iteration 2 (`rebalance_reactor_bus` + `medical_eva_prep`).
   - Ship telemetry hits all targets -> `mission_evaluator` routes to **END** -> Status becomes **STABILIZED**!

---

## Minute 4:00 – 5:30 | Deep Inspection: Node Drawer, State Diff, Replay & Time Travel

1. **Node Inspector**: Click the `safety_officer` or `commander` node to open the right-hand drawer showing timing, run count, system prompt, Pydantic structured output, and LangGraph mechanism.
2. **State & State Diff**: Open the **State Diff** tab and step through supersteps to show exact before/after changes to `MissionState`.
3. **Replay vs Time Travel**:
   - Toggle **REPLAY** in the top bar and scrub the slider — explain this is read-only playback of recorded SSE events (no LLM calls, no state mutation).
   - Switch back to **LIVE**, open the **Checkpoints** tab, select an earlier SQLite checkpoint, and click **Fork Time Travel**.
   - Show that a brand-new mission thread (`msn_... (fork)`) starts from that historical checkpoint while preserving the original mission intact!

---

## Minute 5:30 – 6:30 | LangGraph Learning Panel & Local Ollama Live Mode

1. Open the **LangGraph Learning** tab in the Developer Console to show real code snippets and clickable node links for every LangGraph concept.
2. Open **Settings** (gear icon) to show local Ollama configuration (`qwen3:4b` / `qwen3:8b`, `LLM_MAX_CONCURRENCY=1` for 16GB M2 Pro) and how Live Mode surfaces clear errors without silently faking results if Ollama is offline.
3. Conclude with Q&A!
