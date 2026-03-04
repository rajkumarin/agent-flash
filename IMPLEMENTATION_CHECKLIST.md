# Implementation Checklist

## Current Goal
POC: live camera overlay showing top-5 probable LEGO dozer parts.

## Phase 1: Vertical Slice (Now)
- [x] Create handoff plan in `AGENTS.md`
- [x] Define POC checklist in `IMPLEMENTATION_CHECKLIST.md`
- [x] Create local backend service with WebSocket endpoint
- [x] Define overlay message schema (`top_k=5`, part label, confidence, anchor/bbox)
- [x] Create browser camera thin client for Android tablet
- [x] Send frames from browser to backend and receive overlay results
- [x] Render live text/symbol overlays on top of camera view
- [x] Add future extension interfaces (`PartDetector`, `Tracker`, `VisionReasoner`, `ReasoningProvider`)

## Phase 2: Replace Mock Inference
- [ ] Add real part detector/classifier model
- [x] Add tracking for temporal consistency and reduced flicker
- [ ] Calibrate confidence scores
- [ ] Add performance mode switch (frame size, sampling rate)

## Phase 3: OCC Model Ingest (No CAD GUI Runtime)
- [x] Build OpenCascade-based ingest pipeline
- [x] Generate part catalog (`part_id`, canonical name, aliases)
- [ ] Generate synthetic views/features for detector support
- [ ] Version model packages for repeatable runtime behavior

## Phase 4: Stability and Operations
- [ ] Add structured logs and metrics (`fps`, `latency_ms`, dropped frames)
- [x] Add reconnect behavior for camera/backend socket
- [ ] Add model warmup and health endpoint
- [x] Add local network setup guide for tablet -> laptop access

## Phase 5: Future Intelligence Ports
- [ ] Plug in VLM ambiguity resolver (Ollama/API)
- [ ] Plug in LLM repair-instructions engine (event-triggered)
- [ ] Add retrieval grounding from part catalog and assembly metadata

## De-scope / Legacy
- [ ] Move Streamlit app to `legacy/streamlit/`
- [ ] Move FreeCAD RPC addon path to `legacy/freecad_rpc/`
- [ ] Move MCP runtime layer to `legacy/mcp_runtime/`
- [ ] Keep only shared utilities needed by new architecture

## Runbook (POC)
1. Start backend: `uvicorn backend.app:app --host 0.0.0.0 --port 8080 --reload`
2. Open `client/index.html` via simple static server (or file mode for quick test).
3. On tablet browser, open client URL, grant camera permission.
4. Verify top-5 labels and confidence update on overlay.

## Session Learnings (2026-03-04)
- Android Chrome camera access requires secure context; HTTP LAN URL failed even after insecure-origin flag.
- WebSocket path was reachable on tablet; camera permission/security was the blocker.
- Reliable mode for tablet testing is HTTPS + WSS from single backend origin (`https://<ip>:8443`).
- Local process lifecycle confusion came from detached shell behavior and stale PID files; dedicated start/stop/status scripts reduced drift.
- The `30433 - Volvo Wheel Loader.STEP` assembly uses external references; assembly rendering required resolving component references and transforms against part STEP files.
