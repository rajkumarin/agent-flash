# CAD Repair Assistant

> Status update (2026-03-04): a new tablet camera-overlay POC path is in progress in this repo.
> Start here for current work:
> - `AGENTS.md`
> - `IMPLEMENTATION_CHECKLIST.md`
> - `backend/README.md`
> - `client/README.md`
> - `POC_RESOURCES.md`

An AI-powered assistant that helps identify missing or damaged parts in CAD models by comparing uploaded images against FreeCAD reference models. Built with MCP (Model Context Protocol), Google Gemini AI, and Streamlit.

## Overview

The CAD Repair Assistant connects to FreeCAD via XML-RPC and provides an intelligent interface for:
- Comparing physical images against CAD reference models
- Identifying missing, damaged, or misassembled parts
- Generating detailed analysis reports with part numbers
- Rendering CAD views from multiple angles

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Streamlit Web UI                             │
│              (CAD Repair Assistant Interface)                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Tools Layer                               │
│         (FreeCADMCPTools - Python Interface)                     │
│                                                                  │
│  Tools: get_visible_parts, get_view_screenshot, list_documents,  │
│         get_all_parts, get_part_details, highlight_part,         │
│         compare_views                                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │ XML-RPC (Port 9875)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FreeCAD Application                           │
│              (CADRepairMCP Addon + RPC Server)                   │
│                                                                  │
│  RPC Methods: ping, get_objects, get_active_screenshot,          │
│               highlight_part, get_part_screenshot,               │
│               get_model_overview_screenshot, etc.                │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- FreeCAD 0.21+ ([Download](https://www.freecad.org/downloads.php))
- Google Gemini API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/freecad-mcp.git
   cd freecad-mcp
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install the FreeCAD addon**

   **Windows (CMD):**
   ```cmd
   xcopy /E /I addon\CADRepairMCP "%APPDATA%\FreeCAD\Mod\CADRepairMCP"
   ```

   **Windows (PowerShell/Git Bash):**
   ```bash
   cp -r addon/CADRepairMCP "$env:APPDATA/FreeCAD/Mod/"
   ```

   **macOS:**
   ```bash
   cp -r addon/CADRepairMCP ~/Library/Application\ Support/FreeCAD/Mod/
   ```

   **Linux:**
   ```bash
   cp -r addon/CADRepairMCP ~/.FreeCAD/Mod/
   ```

### Running the Application

1. **Start FreeCAD**
   - Open FreeCAD
   - Load your CAD model (.FCStd file)
   - Go to Menu: **CAD Repair MCP > Start RPC Server**

2. **Start the Streamlit UI**
   ```bash
   streamlit run src/server.py
   ```

3. **Configure in the UI**
   - Enter your Google Gemini API key
   - Test the FreeCAD connection
   - Select your document and click "Load Model Parts"

4. **Analyze Images**
   - Upload an image of your physical model
   - Click "Analyze Image" to compare against the CAD reference

---

## MCP Tools Reference

The system provides 7 MCP tools for interacting with FreeCAD. These can be enabled/disabled based on your needs.

### Tool 1: `get_visible_parts`

Get parts visible from a specific view angle with automatic filtering of hidden/internal parts.

**Function:** `FreeCADMCPTools.get_visible_parts(doc_name, view_name, side_threshold=5.0)`

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `doc_name` | string | Yes | FreeCAD document name |
| `view_name` | string | Yes | View angle: Left, Right, Front, Rear, Top, FrontLeft, FrontRight, RearLeft, RearRight |
| `side_threshold` | number | No | Distance threshold for visibility (mm), default: 5.0 |

**Returns:** List of visible parts with names, labels, and colors.

**Example:**
```python
result = mcp_tools.get_visible_parts("MyModel", "FrontLeft")
# Returns: {"visible_parts": [...], "hidden_parts": [...], "total_parts": 74}
```

---

### Tool 2: `get_view_screenshot`

Capture a screenshot of the CAD model from a specific view angle.

**Function:** `FreeCADMCPTools.get_view_screenshot(doc_name=None, view_name="Isometric")`

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `doc_name` | string | No | Document name (uses active if not specified) |
| `view_name` | string | No | View angle, default: "Isometric" |

**Returns:** Base64-encoded PNG image.

**Example:**
```python
result = mcp_tools.get_view_screenshot("MyModel", "Left")
# Returns: {"image": "base64...", "view": "Left", "format": "base64_png"}
```

---

### Tool 3: `list_documents`

List all open FreeCAD documents.

**Function:** `FreeCADMCPTools.list_documents()`

**Parameters:** None

**Returns:** List of document names.

**Example:**
```python
result = mcp_tools.list_documents()
# Returns: {"documents": ["MyModel", "TestDoc"], "count": 2}
```

---

### Tool 4: `get_all_parts`

Get all parts in a document with full metadata.

**Function:** `FreeCADMCPTools.get_all_parts(doc_name)`

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `doc_name` | string | Yes | FreeCAD document name |

**Returns:** List of all parts with name, label, type, and color.

**Example:**
```python
result = mcp_tools.get_all_parts("MyModel")
# Returns: {"parts": [{"name": "Part001", "label": "Wheel", "type": "Part::Feature", "color": {...}}], "count": 74}
```

---

### Tool 5: `get_part_details`

Get detailed information about a specific part including bounding box.

**Function:** `FreeCADMCPTools.get_part_details(doc_name, part_name)`

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `doc_name` | string | Yes | FreeCAD document name |
| `part_name` | string | Yes | Name of the part |

**Returns:** Part details with bounding box coordinates.

**Example:**
```python
result = mcp_tools.get_part_details("MyModel", "Wheel001")
# Returns: {"name": "Wheel001", "label": "Front Wheel", "bounding_box": {...}}
```

---

### Tool 6: `highlight_part`

Highlight a specific part with a color in the FreeCAD view.

**Function:** `FreeCADMCPTools.highlight_part(doc_name, part_name, color=None)`

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `doc_name` | string | Yes | FreeCAD document name |
| `part_name` | string | Yes | Name of the part to highlight |
| `color` | array | No | RGBA color [r,g,b,a] 0-1 range, default: orange |

**Returns:** Highlight status and original color for restoration.

**Example:**
```python
result = mcp_tools.highlight_part("MyModel", "Bucket001", [1.0, 0.0, 0.0, 1.0])
# Returns: {"part": "Bucket001", "color": [1,0,0,1], "original_color": [...]}
```

---

### Tool 7: `compare_views`

Compare which parts are visible between two different view angles.

**Function:** `FreeCADMCPTools.compare_views(doc_name, view1, view2)`

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `doc_name` | string | Yes | FreeCAD document name |
| `view1` | string | Yes | First view angle |
| `view2` | string | Yes | Second view angle |

**Returns:** Parts visible in both views, only in view1, only in view2.

**Example:**
```python
result = mcp_tools.compare_views("MyModel", "Left", "Right")
# Returns: {"parts_in_both": [...], "parts_only_in_view1": [...], "parts_only_in_view2": [...]}
```

---

## RPC Server Methods (Low-Level)

These are the underlying XML-RPC methods exposed by the FreeCAD addon. The MCP Tools layer wraps these for easier use.

| Method | Description | File Location |
|--------|-------------|---------------|
| `ping()` | Check server connectivity | `rpc_server.py:137` |
| `list_documents()` | List all open documents | `rpc_server.py:237` |
| `get_objects(doc_name)` | Get all objects in a document | `rpc_server.py:211` |
| `get_object(doc_name, obj_name)` | Get specific object details | `rpc_server.py:219` |
| `get_active_screenshot(view_name)` | Capture active view screenshot | `rpc_server.py:873` |
| `get_part_screenshot(...)` | Screenshot focused on a part | `rpc_server.py:431` |
| `get_model_overview_screenshot(...)` | Full model screenshot with highlights | `rpc_server.py:672` |
| `highlight_part(doc_name, part_name, color)` | Change part color | `rpc_server.py:245` |
| `reset_part_color(doc_name, part_name, color)` | Reset part to original color | `rpc_server.py:292` |
| `get_part_bounding_box(doc_name, part_name)` | Get part bounds | `rpc_server.py:328` |
| `get_all_parts_mapping(doc_name)` | Get all parts with metadata | `rpc_server.py:373` |
| `create_document(name)` | Create new document | `rpc_server.py:141` |
| `create_object(doc_name, obj_data)` | Create new object | `rpc_server.py:150` |
| `edit_object(doc_name, obj_name, properties)` | Modify object properties | `rpc_server.py:165` |
| `delete_object(doc_name, obj_name)` | Remove an object | `rpc_server.py:178` |
| `execute_code(code)` | Run Python code in FreeCAD | `rpc_server.py:187` |

---

## Project Structure

```
freecad-mcp/
├── src/
│   ├── __init__.py                # Package exports
│   ├── server.py                  # Main Streamlit application
│   ├── config.py                  # Configuration constants
│   │
│   ├── mcp_tools/                 # MCP Tools package
│   │   ├── __init__.py            # Exports FreeCADMCPTools, ToolResult
│   │   ├── client.py              # Main FreeCADMCPTools client class
│   │   ├── base.py                # ToolResult dataclass, BaseMCPTool
│   │   ├── registry.py            # Tool registry for AI discovery
│   │   ├── visibility.py          # View-based visibility filtering
│   │   ├── gemini.py              # Gemini AI integration (agentic loop)
│   │   └── tools/                 # Individual tool implementations
│   │       ├── __init__.py
│   │       ├── visible_parts.py   # GetVisiblePartsTool
│   │       ├── screenshot.py      # GetViewScreenshotTool
│   │       ├── documents.py       # ListDocumentsTool
│   │       ├── parts.py           # GetAllParts, GetPartDetails, HighlightPart
│   │       └── compare.py         # CompareViewsTool
│   │
│   ├── core/                      # Core analysis functionality
│   │   ├── __init__.py
│   │   ├── analysis.py            # Image analysis with Gemini
│   │   ├── rendering.py           # FreeCAD screenshot rendering
│   │   ├── model_context.py       # CAD model context for AI
│   │   └── prompts.py             # AI prompt templates
│   │
│   ├── ui/                        # Streamlit UI components
│   │   ├── __init__.py
│   │   ├── sidebar.py             # Sidebar configuration
│   │   ├── tabs.py                # Main tab views
│   │   └── components.py          # Reusable UI components
│   │
│   └── utils/                     # Utility functions
│       ├── __init__.py
│       ├── logger.py              # Logging utility
│       ├── color.py               # Color name extraction
│       └── image.py               # Image display utilities
│
├── addon/
│   └── CADRepairMCP/              # FreeCAD addon
│       ├── __init__.py
│       ├── Init.py
│       ├── InitGui.py
│       └── rpc_server/
│           ├── rpc_server.py      # XML-RPC server implementation
│           ├── serialize.py       # Object serialization
│           └── parts_library.py   # Parts library utilities
│
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Configuration

### Environment Variables

```bash
# Google Gemini API Key (required for AI features)
GEMINI_API_KEY=your_gemini_api_key_here

# FreeCAD Connection (defaults)
FREECAD_HOST=localhost
FREECAD_PORT=9875
```

### Supported View Angles

The system supports the following view angles for rendering and visibility filtering:

| View Name | Description |
|-----------|-------------|
| `Isometric` | Standard 3D isometric view |
| `Front` | Looking at the front face |
| `Rear` | Looking at the back face |
| `Left` | Looking at the left side |
| `Right` | Looking at the right side |
| `Top` | Looking from above |
| `FrontLeft` | 3/4 view showing front and left |
| `FrontRight` | 3/4 view showing front and right |
| `RearLeft` | 3/4 view showing rear and left |
| `RearRight` | 3/4 view showing rear and right |

---

## Disabling/Enabling Tools

The client can selectively enable or disable MCP tools by commenting out entries in the `TOOL_REGISTRY` dictionary in `src/mcp_tools/registry.py`:

```python
# src/mcp_tools/registry.py

TOOL_REGISTRY = {
    "get_visible_parts": {...},      # Comment to disable
    "get_view_screenshot": {...},    # Comment to disable
    "list_documents": {...},
    "get_all_parts": {...},
    "get_part_details": {...},
    # "highlight_part": {...},       # Example: disabled
    # "compare_views": {...},        # Example: disabled
}
```

---

## Troubleshooting

### FreeCAD Connection Issues

1. Ensure FreeCAD is running
2. Verify the CADRepairMCP addon is installed correctly
3. Start the RPC server from FreeCAD menu: **CAD Repair MCP > Start RPC Server**
4. Check that port 9875 is not blocked by firewall

### Image Analysis Issues

1. Load the CAD model first (click "Load Model Parts")
2. Ensure the uploaded image shows the same type of object as the CAD model
3. Verify Gemini API key is valid and has quota

### Logging

The application includes logging for debugging. Check the terminal output for log messages with timestamps:

```
[2024-01-15 10:30:45] [INFO] Starting image analysis
[2024-01-15 10:30:46] [DEBUG] Detected view angle: FrontLeft
[2024-01-15 10:30:47] [INFO] Building prompt for model: volvo_wheel_loader
```
---
