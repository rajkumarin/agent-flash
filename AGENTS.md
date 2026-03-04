# AGENTS.md

## Mission For Next Agent
Build a **POC camera-overlay system** that labels the **top 5 most probable LEGO dozer parts** visible from a live camera stream.

This repository is transitioning away from Streamlit + FreeCAD RPC runtime.

## Confirmed Product Constraints (Approved)
- Camera source: **live camera on Samsung Galaxy Tab A9+** (browser client preferred).
- UX: **only live camera overlay UI** (labels/symbols/text on video).
- Deployment: **local backend on laptop + thin client on tablet**.
- CAD path: **OpenCascade-native route preferred**.
- Runtime CAD GUI: **not needed**.
- MCP/RPC runtime: **drop now**.
- Keep extension point for future:
  - LLM-based repair instructions
  - VLM support (local via Ollama if feasible, or API)

## POC Scope (Strict)
### In scope
- Single-object scene: LEGO dozer.
- Per frame (or sampled frames), detect/identify visible parts.
- Return and render **Top-5 part labels by probability**.
- Overlay each label near detected part with confidence score.
- Smooth labels over time with tracking to reduce flicker.

### Out of scope (for POC)
- Full defect diagnostics.
- Repair instruction generation.
- Multi-model support.
- Complex assembly-graph reasoning in real time.
- FreeCAD runtime control.

## Target Runtime Architecture
1. **Tablet Web Client (Thin Client)**
- Opens camera in browser (WebRTC/getUserMedia).
- Sends compressed frames or feature payload to backend.
- Renders overlay boxes/keypoints/text from backend results.

2. **Laptop Backend (Local Inference Service)**
- Receives frame stream.
- Runs CV/VLM inference + tracking.
- Produces top-5 labeled part hypotheses with scores and 2D positions.
- Sends overlay payload back via WebSocket.

3. **Model Asset Service (Preprocess once, use many times)**
- Convert CAD model into inference-friendly assets offline.
- Store part metadata, IDs, canonical names, optional synthetic views/embeddings.

## Recommended Technical Stack (POC)
### Client
- Web app (PWA-capable) for Android tablet compatibility.
- Rendering: Canvas/WebGL overlay layer above video element.
- Transport: WebSocket for low-latency bidirectional messaging.

### Backend
- Python service (FastAPI + WebSocket).
- CV pipeline with OpenCV + model inference runtime.
- Tracking: ByteTrack/DeepSORT-like temporal smoothing (lightweight config).

### Model options for top-5 labeling
Use a hybrid design, in this order:
1. **Primary (deterministic CV)**
- Part detector/classifier fine-tuned for dozer parts.
- Best for stable latency and confidence calibration.
2. **Optional VLM fallback**
- Use VLM only when detector confidence is low/ambiguous.
- Candidate backends:
  - Local: Ollama-hosted vision model (if acceptable FPS)
  - Remote API: Gemini/Claude vision endpoint (fallback path)

## OpenCascade-Native CAD Plan
Goal: remove FreeCAD GUI dependency at runtime.

1. Offline CAD ingest (one-time per model revision)
- Parse STEP/BREP/mesh using OpenCascade bindings.
- Extract part hierarchy, part names, transforms, rough geometry descriptors.

2. Asset generation
- Build part catalog (`part_id`, `name`, aliases, color hints if available).
- Generate synthetic renders from multiple viewpoints (optional but recommended).
- Precompute part embeddings/features for retrieval/classification assist.

3. Runtime usage
- No CAD GUI calls.
- Runtime loads prepared assets only.

## API Contracts (POC-first)
### `ws://backend/session`
Client -> Backend:
- `frame`: `{ ts, jpeg_bytes/base64, camera_intrinsics? }`

Backend -> Client:
- `overlay`: `{ ts, parts: [ { part_id, label, conf, bbox, anchor } ], top_k: 5 }`
- `status`: `{ fps, latency_ms, model_name }`

### Future-ready extension ports
Keep these interfaces now (can be no-op initially):
- `ReasoningProvider` (LLM for repair text)
- `VisionReasoner` (VLM for ambiguous frame interpretation)
- `KnowledgeStore` (part metadata + repair docs)

## Repository De-scope / Drop Plan
These are unnecessary for the POC runtime and should be retired or isolated:
- Streamlit app layer:
  - `src/server.py`
  - `src/ui/*`
- MCP tools abstraction for runtime:
  - `src/mcp_tools/*`
- FreeCAD addon RPC runtime path:
  - `addon/CADRepairMCP/*`
- Prompt-heavy inspection flow for static image analysis (runtime path):
  - large parts of `src/core/analysis.py`, `src/core/prompts.py`

Keep only if useful for migration references, then archive under `legacy/`.

## Migration Strategy (Phased)
1. **Phase 1: Skeleton (1 week)**
- Stand up web camera client + backend WebSocket + mocked overlay.
- Define stable message schema.

2. **Phase 2: CAD ingest + part catalog (1-2 weeks)**
- OCC ingestion pipeline for selected dozer CAD source.
- Produce canonical part label map for detector classes.

3. **Phase 3: Detection + Top-5 overlay (2 weeks)**
- Implement inference pipeline and tracking.
- Achieve stable top-5 labels and confidence overlays.

4. **Phase 4: Hardening (1 week)**
- Latency optimization, reconnection logic, model warmup, logging.
- Measure on Galaxy Tab A9+ network conditions.

5. **Phase 5: LLM/VLM hooks (parallel/after POC)**
- Add provider interfaces and one pluggable implementation path.

## Acceptance Criteria (POC)
- Live camera feed from tablet in browser works end-to-end with local laptop backend.
- Overlay updates in near-real-time (target: >=10 FPS effective overlay updates).
- Exactly top-5 candidate part labels shown per update.
- Confidence values and label anchors are stable across adjacent frames.
- No FreeCAD GUI or MCP dependency required during runtime.

## Risks and Mitigations
- Domain data scarcity for LEGO part detection.
  - Mitigation: synthetic data from CAD renders + small real capture set.
- VLM latency too high for live loop.
  - Mitigation: keep VLM off critical path; async fallback only.
- CAD naming inconsistency.
  - Mitigation: build alias dictionary during ingest; normalize labels early.

## Next Agent Immediate Tasks
1. Propose concrete folder structure for new runtime (`client/`, `backend/`, `model_ingest/`, `legacy/`).
2. Define JSON schema for overlay payload and telemetry.
3. Implement a no-ML vertical slice:
- tablet camera -> backend -> fake top-5 -> overlay render.
4. Add adapter interfaces:
- `PartDetector`
- `Tracker`
- `VisionReasoner`
- `ReasoningProvider`

## Notes For Future Repair-Instruction Feature
- Use the same part IDs from overlay pipeline as grounding keys for LLM.
- Retrieval should pull part metadata + assembly context before prompting.
- Keep instruction generation event-driven (on user action), not frame-driven.

## POC Resource Links
- See [POC_RESOURCES.md](/Users/rajdhanapal/Documents/repos/FreeCAD-MCP/POC_RESOURCES.md) for:
  - spreadsheet/drive source links
  - extracted tag set
  - extracted Google Drive model link candidates
  - direct-download URL pattern for file IDs

## Build Status (2026-03-04)
- Vertical slice is working end-to-end:
  - Tablet browser loads UI from laptop.
  - Backend socket connects and streams mock top-5 labels with overlay.
- OCC ingest/render baseline is working:
  - Downloaded CAD bundle from Drive.
  - Rendered top view from assembled STEP using OCC transform composition.
  - Output: `outputs/volvo_wheel_loader_top_occ.png`.
- Important runtime mode split:
  - HTTP mode: `scripts/start_poc_detached.sh` (`8080 + 9000`).
  - HTTPS mode for Android camera: `scripts/start_poc_https.sh` (`8443`, same-origin static + API + WSS).

## Known Issues
- Top-5 labels are currently mock predictions and not yet real CV model output.
- HTTPS cert is self-signed; tablet must accept warning page before camera starts.
- `status_poc.sh` can show stale PID files if previous runs crashed; trust listener checks first.

## Next Session Priority
1. Replace mock detector with real part detector.
2. Add confidence threshold + no-detection state.
3. Add minimal model package schema (`part_id`, aliases, color hints, bbox priors).
