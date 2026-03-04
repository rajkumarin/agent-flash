"""Demo mode data for CAD Repair Assistant.

Contains the guided demo prompt that includes context about the expected analysis
for showcasing the application with real AI responses.
"""

import os
from typing import Dict, Any

# Demo image path (relative to project root)
DEMO_IMAGE_FILENAME = "demo-img.jpeg"


def get_demo_image_path() -> str:
    """Get the absolute path to the demo image."""
    # Navigate from src/core/ to project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    return os.path.join(project_root, DEMO_IMAGE_FILENAME)


# Demo prompt - guides AI to generate output in the correct format
DEMO_PROMPT = """You are analyzing a LEGO Technic buggy model. The image shows the buggy is MISSING its Rear Spoiler Assembly.

Generate an analysis report with EXACTLY this format and structure:

1. Start with a title: "Rear Spoiler Missing Alert + Fixing Guide"
2. Then: "Missing: Rear Spoiler Assembly [ Critical ]"
3. Then: "Total Parts Required: 10"
4. Then a markdown table with these EXACT parts:
   | Part Name / CAD ID | Description | Qty |
   |-------------------|-------------|-----|
   | 6167465 | Tile 1 x 6 (Lime Green) | 2 |
   | 379528 | Plate 2 x 6 (Green) | 1 |
   | 6117940 | Bracket 1 x 2 - 2 x 2 with Rounded Corners (White) | 2 |
   | 4515364 | Plate 1 x 2 with Bar Handle (White) | 2 |
   | 302201 | Plate 2 x 2 (White) | 1 |
   | 6264057 | Plate 3 x 3 with Cut Corner (Lime Green) | 2 |

5. Then "## How to Fix" section with "To repair/build the Rear Spoiler Assembly"
6. Then 5 steps in this format:
   **Step 1: Create the Top Surface** - about placing the two lime green tiles side-by-side
   **Step 2: Install Structural Connectors (Left → Right Order)** - about attaching the 5 white components underneath
   **Step 3: Secure the Assembly** - about attaching the green base plate
   **Step 4: Add Side Extensions** - about adding the cut-corner plates to the sides
   **Step 5: Final Mounting** - about mounting onto the black mechanical arms (6276867)

Create bullet points for each steps like sub steps.Use your own wording for the step descriptions but keep the same structure and information. Do not add any extra sections, headers, or emojis."""


# Demo output - fallback text if AI generation fails
DEMO_OUTPUT = """Rear Spoiler Missing Alert + Fixing Guide

Missing: Rear Spoiler Assembly [ Critical ]

Total Parts Required: 10

| Part Name / CAD ID | Description | Qty |
|-------------------|-------------|-----|
| 6167465 | Tile 1 x 6 (Lime Green) | 2 |
| 379528 | Plate 2 x 6 (Green) | 1 |
| 6117940 | Bracket 1 x 2 - 2 x 2 with Rounded Corners (White) | 2 |
| 4515364 | Plate 1 x 2 with Bar Handle (White) | 2 |
| 302201 | Plate 2 x 2 (White) | 1 |
| 6264057 | Plate 3 x 3 with Cut Corner (Lime Green) | 2 |

## How to Fix

To repair/build the Rear Spoiler Assembly

**Step 1: Create the Top Surface**
- Place two identical surface plates (6167465) side-by-side
- Align edges evenly
- Finished surface faces upward

**Step 2: Install Structural Connectors (Left → Right Order)**
You will now attach five white components to the underside of the green tiles in a specific row from left to right:
- Left Edge: Place the first White Bracket (6117940).
- Inner Left: Attach the first Plate with Bar Handle (4515364).
- Center: Place the White 2 x 2 Plate (302201).
- Inner Right: Attach the second Plate with Bar Handle (4515364).
- Right Edge: Place the second White Bracket (6117940).

**Step 3: Secure the Assembly**
- Attach the base locking plate (379528) underneath all connectors
- Ensure all connection points are fully engaged
- Result: Component becomes a single rigid unit

**Step 4: Add Side Extensions**
- Take one 3 × 3 cut-corner plate.
- Hold the plate so that:
  - The flat right-angle edges sit flush against the bracket
  - The cut/angled corner points toward the front of the vehicle
- Position the plate on the outer side of the bracket (facing away from the vehicle center).
- Press the plate into place.
- Repeat the same process with the second cut-corner plate on the opposite side.

**Step 5: Final Mounting**
- Identify the two Black Mechanical Arms (6276867) at the rear of the buggy chassis.
- Hold the assembled component above the mounting arms.
- Align each bar handle connector on the component with the open end of a mounting arm.
- Lower the component evenly so both connectors enter the arms at the same time.
- Press gently until the component is fully seated."""


# Expected JSON structure for the demo analysis
DEMO_EXPECTED_JSON = {
    "status": "MISSING_PARTS",
    "missing_components": [
        {
            "component": "rear spoiler",
            "location": "rear of buggy, mounted on mechanical arms",
            "description": "Green/lime green wing assembly with white structural connectors"
        }
    ],
    "present_components": [
        "all wheels",
        "front bumper",
        "upper body",
        "roof cover",
        "headlamps",
        "exhaust",
        "taillights",
        "roll bar",
        "steering"
    ],
    "confidence": 0.95,
    "notes": "The rear spoiler assembly is missing from the mechanical mounting arms at the back of the buggy."
}
