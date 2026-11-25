# Contributing to AI Space Mission (LangGraph Learning Lab)

This repository is designed as a **hands-on educational sandbox for learning LangGraph**. Contributions that make LangGraph concepts even clearer, more observable, or easier to experiment with are very welcome!

## Great Ways to Contribute

- **New Emergency Scenarios**: Add a scenario to `backend/app/scenarios/catalog.py` (plus `en.json` / `ru.json` translations) that exercises a specific LangGraph routing pattern.
- **LangGraph Patterns**: Add or refine visual explanations in the built-in Learning Panel (`backend/app/graph/learning_catalog.py`) and [LANGGRAPH_GUIDE.md](./LANGGRAPH_GUIDE.md).
- **Inspector Improvements**: Enhance React Flow visualizations, State Diff readability, or Checkpoint Explorer ergonomics.
- **Additional Localizations**: Add a new locale JSON under `backend/app/i18n/locales/` and `frontend/src/i18n/locales/`.

## Development Guidelines

1. **Backend is the single source of truth**: Never fake graph execution with `setTimeout` on the frontend. All UI state must derive from real LangGraph streaming events or persisted checkpoints.
2. **Keep Demo Mode deterministic**: Demo Mode must run the exact same compiled `StateGraph` without requiring Ollama or API keys.
3. **Run checks before opening a PR**:
   ```bash
   cd backend && .venv/bin/pytest -v
   cd ../frontend && npm run build
   ```
