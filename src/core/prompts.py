"""AI prompt templates for CAD Repair Assistant."""

import json

# JSON Schema for structured output - simplified for visual comparison
ANALYSIS_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["COMPLETE", "MISSING_PARTS"]
        },
        "missing_components": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "component": {"type": "string"},
                    "location": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["component", "location"]
            }
        },
        "present_components": {
            "type": "array",
            "items": {"type": "string"}
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "notes": {"type": "string"}
    },
    "required": ["status", "missing_components", "confidence"]
}

# Component name mapping to assembly keys (for CAD lookup)
COMPONENT_TO_ASSEMBLY = {
    # Wheels
    "wheel": ["wheel_front_left", "wheel_front_right",
              "wheel_rear_left", "wheel_rear_right"],
    "wheels": ["wheel_front_left", "wheel_front_right",
               "wheel_rear_left", "wheel_rear_right"],
    "front wheel": ["wheel_front_left", "wheel_front_right"],
    "rear wheel": ["wheel_rear_left", "wheel_rear_right"],
    "front-left wheel": ["wheel_front_left"],
    "front-right wheel": ["wheel_front_right"],
    "rear-left wheel": ["wheel_rear_left"],
    "rear-right wheel": ["wheel_rear_right"],
    "front left wheel": ["wheel_front_left"],
    "front right wheel": ["wheel_front_right"],
    "rear left wheel": ["wheel_rear_left"],
    "rear right wheel": ["wheel_rear_right"],
    "all wheels": ["wheel_front_left", "wheel_front_right",
                   "wheel_rear_left", "wheel_rear_right"],
    # Bumper
    "bumper": ["front_bumper"],
    "front bumper": ["front_bumper"],
    # Spoiler
    "spoiler": ["rear_spoiler"],
    "rear spoiler": ["rear_spoiler"],
    "visor": ["rear_spoiler"],
    "wing": ["rear_spoiler"],
    # Body
    "upper body": ["upper_body"],
    "body": ["upper_body"],
    # Roof
    "roof": ["roof_cover"],
    "top": ["roof_cover"],
    "roof cover": ["roof_cover"],
    "top cover": ["roof_cover"],
    "top roof": ["roof_cover"],
    # Steering
    "steering": ["steering"],
    "steering wheel": ["steering"],
    # Axles
    "front axle": ["front_axle"],
    "rear axle": ["rear_axle"],
    "axle": ["front_axle", "rear_axle"],
    # Headlamps
    "headlamp": ["headlamps"],
    "headlamps": ["headlamps"],
    "headlight": ["headlamps"],
    "headlights": ["headlamps"],
    "front light": ["headlamps"],
    "front lights": ["headlamps"],
    # Exhaust/Silencer
    "exhaust": ["exhaust"],
    "silencer": ["exhaust"],
    "exhaust pipe": ["exhaust"],
    "exhaust pipes": ["exhaust"],
    "muffler": ["exhaust"],
    # Taillights
    "taillight": ["taillights"],
    "taillights": ["taillights"],
    "rear light": ["taillights"],
    "rear lights": ["taillights"],
    "tail light": ["taillights"],
    "tail lights": ["taillights"],
    # Roll bar
    "roll bar": ["rollbar"],
    "rollbar": ["rollbar"],
    "roll cage": ["rollbar"],
    "cage": ["rollbar"],
}


def build_system_prompt(model_name: str, view_info: str, model_context: str) -> str:
    """
    Build the system prompt for CAD quality inspection.

    Args:
        model_name: Name of the loaded CAD model
        view_info: Description of the current viewing angle
        model_context: Formatted list of parts (not used in new approach)

    Returns:
        Complete system prompt string
    """
    schema_str = json.dumps(ANALYSIS_OUTPUT_SCHEMA, indent=2)

    return f"""You are a visual comparison expert. Compare two images and identify differences.

## TASK

You have TWO images:
1. **IMAGE 1 (REFERENCE):** Complete LEGO Off-Road Buggy with all parts
2. **IMAGE 2 (USER'S PHOTO):** User's buggy - may have missing parts

**Find what is MISSING in Image 2 compared to Image 1.**

## COMPONENTS TO CHECK

Compare BOTH images and identify which of these components are MISSING in the user's photo:

| Component | Description | Location |
|-----------|-------------|----------|
| Front-left wheel | Large BLACK rubber tire on WHITE rim | Front-left corner |
| Front-right wheel | Large BLACK rubber tire on WHITE rim | Front-right corner |
| Rear-left wheel | Large BLACK rubber tire on WHITE rim | Rear-left corner |
| Rear-right wheel | Large BLACK rubber tire on WHITE rim | Rear-right corner |
| Front bumper | Lime GREEN slope pieces | Front of buggy |
| Rear spoiler | GREEN wedge plates forming a wing | Rear of buggy |
| Roof/Top cover | WHITE curved plates | Top center of buggy |
| Headlamps | GREEN headlight bricks | Front corners |
| Exhaust/Silencer | GREY exhaust pipes | Sides of buggy |
| Taillights | YELLOW transparent round pieces | Rear of buggy |
| Roll bar | BLACK bar pieces | Around cockpit |
| Steering wheel | Small BLACK steering wheel | Cockpit area |

Check EACH component in BOTH images and report what's MISSING from the user's photo.

## OUTPUT FORMAT

Return a JSON object:

```json
{schema_str}
```

## EXAMPLES

**Example 1 - All wheels missing:**
```json
{{
  "status": "MISSING_PARTS",
  "missing_components": [
    {{"component": "front-left wheel", "location": "front-left corner"}},
    {{"component": "front-right wheel", "location": "front-right corner"}},
    {{"component": "rear-left wheel", "location": "rear-left corner"}},
    {{"component": "rear-right wheel", "location": "rear-right corner"}}
  ],
  "present_components": ["front bumper", "rear spoiler", "upper body"],
  "confidence": 0.95,
  "notes": "No wheels are attached. All 4 wheel positions are empty."
}}
```

**Example 2 - Everything present:**
```json
{{
  "status": "COMPLETE",
  "missing_components": [],
  "present_components": ["all wheels", "front bumper", "rear spoiler", "upper body"],
  "confidence": 0.95,
  "notes": "All major components are present."
}}
```

**Example 3 - Multiple components missing:**
```json
{{
  "status": "MISSING_PARTS",
  "missing_components": [
    {{"component": "rear spoiler", "location": "back of buggy"}},
    {{"component": "headlamps", "location": "front corners"}},
    {{"component": "exhaust", "location": "sides of buggy"}}
  ],
  "present_components": ["all wheels", "front bumper", "roof cover", "taillights"],
  "confidence": 0.85,
  "notes": "Missing the green rear spoiler, headlight bricks, and exhaust pipes."
}}
```

**Example 4 - Roof and headlamps missing:**
```json
{{
  "status": "MISSING_PARTS",
  "missing_components": [
    {{"component": "roof cover", "location": "top of buggy"}},
    {{"component": "headlamps", "location": "front of buggy"}}
  ],
  "present_components": ["all wheels", "front bumper", "rear spoiler", "exhaust"],
  "confidence": 0.90,
  "notes": "The white curved roof cover and green headlight bricks are missing."
}}
```

## IMPORTANT - READ CAREFULLY

**IDENTIFICATION GUIDE:**
- **Wheels:** Large BLACK rubber tires on WHITE rims at each corner
- **Roof/Top cover:** WHITE and GREEN plates covering the TOP of the buggy
- **Headlamps:** GREEN bricks with chrome/silver centers at FRONT corners
- **Exhaust/Silencer:** GREY cylindrical pipes on the SIDES
- **Taillights:** YELLOW/ORANGE transparent round studs at REAR
- **Roll bar:** BLACK bar pieces around cockpit/driver area
- **Rear spoiler:** GREEN wing/wedge plates at the REAR
- **Front bumper:** LIME GREEN slopes at the FRONT

**CRITICAL RULES:**
1. Check the TOP of the buggy - if no white/green plates visible on top = roof cover is MISSING
2. If you can see bare axles/chassis on top = roof cover is MISSING
3. Be specific: "front-left wheel" not just "wheel"
4. List ALL missing components - check EVERY item in the table above
5. Do NOT say a component is "present" unless you can clearly see it in the user's photo
6. If in doubt, mark it as MISSING
7. Output ONLY valid JSON, no other text"""


VIEW_DETECTION_PROMPT = """Analyze this image and determine the camera viewing angle.

Consider these viewing directions:
- Front: Directly facing the front of the buggy
- Rear: Directly facing the back
- Left: Directly facing the left side
- Right: Directly facing the right side
- Top: Looking down from above
- FrontLeft: Diagonal view showing front AND left side
- FrontRight: Diagonal view showing front AND right side
- RearLeft: Diagonal view showing rear AND left side
- RearRight: Diagonal view showing rear AND right side

Respond with ONLY ONE word: Front, Rear, Left, Right, Top, FrontLeft, FrontRight, RearLeft, RearRight"""


REPAIR_GUIDE_PROMPT = """You are an expert LEGO technician. Provide step-by-step
instructions for assembling parts of the Off-Road Buggy (31123).

**Available CAD Model Parts:**
{model_context}

When mentioning parts, always include the part number for reference."""


FULL_ANALYSIS_PROMPT = """You are an expert LEGO model inspector.
Analyze the Off-Road Buggy model and identify any missing or incorrectly assembled parts.
Provide clear instructions suitable for beginners."""
