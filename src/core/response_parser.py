"""Response parser for structured AI analysis output."""

import json
import re
from typing import Dict, Any, Optional, Tuple, List

from utils.logger import log
from core.prompts import COMPONENT_TO_ASSEMBLY
from core.parts_database import BUGGY_ASSEMBLIES, get_repair_steps


def extract_json_from_response(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON object from AI response text.

    Handles cases where JSON might be wrapped in markdown code blocks
    or have extra text around it.

    Args:
        raw_text: Raw response text from AI model

    Returns:
        Parsed JSON dict or None if parsing fails
    """
    if not raw_text:
        return None

    # Try direct JSON parse first
    try:
        return json.loads(raw_text.strip())
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code block
    json_block_pattern = r'```(?:json)?\s*\n?([\s\S]*?)\n?```'
    matches = re.findall(json_block_pattern, raw_text)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # Try to find JSON object by looking for { ... }
    brace_pattern = r'\{[\s\S]*\}'
    matches = re.findall(brace_pattern, raw_text)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    log("Failed to extract JSON from response", "WARNING")
    return None


def map_component_to_assemblies(component_name: str) -> List[str]:
    """
    Map a component name from AI output to CAD assembly keys.

    Args:
        component_name: Component name like "front-left wheel"

    Returns:
        List of assembly keys from BUGGY_ASSEMBLIES
    """
    name_lower = component_name.lower().strip()

    # Direct match
    if name_lower in COMPONENT_TO_ASSEMBLY:
        return COMPONENT_TO_ASSEMBLY[name_lower]

    # Partial match
    for key, assemblies in COMPONENT_TO_ASSEMBLY.items():
        if key in name_lower or name_lower in key:
            return assemblies

    # Fuzzy match for wheels
    if "wheel" in name_lower:
        if "front" in name_lower and "left" in name_lower:
            return ["wheel_front_left"]
        if "front" in name_lower and "right" in name_lower:
            return ["wheel_front_right"]
        if "rear" in name_lower and "left" in name_lower:
            return ["wheel_rear_left"]
        if "rear" in name_lower and "right" in name_lower:
            return ["wheel_rear_right"]
        if "front" in name_lower:
            return ["wheel_front_left", "wheel_front_right"]
        if "rear" in name_lower or "back" in name_lower:
            return ["wheel_rear_left", "wheel_rear_right"]
        # All wheels
        return ["wheel_front_left", "wheel_front_right",
                "wheel_rear_left", "wheel_rear_right"]

    # Other components
    if "bumper" in name_lower:
        return ["front_bumper"]
    if "spoiler" in name_lower or "wing" in name_lower or "visor" in name_lower:
        return ["rear_spoiler"]
    if "body" in name_lower or "roof" in name_lower:
        return ["upper_body"]
    if "steering" in name_lower:
        return ["steering"]
    if "axle" in name_lower:
        if "front" in name_lower:
            return ["front_axle"]
        if "rear" in name_lower:
            return ["rear_axle"]
        return ["front_axle", "rear_axle"]

    log(f"Could not map component '{component_name}' to assembly", "WARNING")
    return []


def enrich_with_cad_data(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich the parsed AI response with CAD part data.

    Takes the simplified AI output and adds:
    - Assembly details from BUGGY_ASSEMBLIES
    - Part numbers and IDs
    - Repair steps

    Args:
        parsed: Parsed JSON from AI

    Returns:
        Enriched response with CAD data
    """
    enriched = {
        "status": parsed.get("status", "UNKNOWN"),
        "confidence_score": parsed.get("confidence", 0),
        "view_analyzed": "detected",
        "missing_assemblies": [],
        "verified_assemblies": [],
        "summary": parsed.get("notes", "")
    }

    # Convert status
    if enriched["status"] == "COMPLETE":
        enriched["status"] = "DEFECT_FREE"

    # Process missing components
    missing_components = parsed.get("missing_components", [])
    processed_assemblies = set()

    for component in missing_components:
        component_name = component.get("component", "")
        location = component.get("location", "")

        # Map to CAD assemblies
        assembly_keys = map_component_to_assemblies(component_name)

        for key in assembly_keys:
            if key in processed_assemblies:
                continue
            processed_assemblies.add(key)

            assembly_info = BUGGY_ASSEMBLIES.get(key, {})
            if not assembly_info:
                continue

            # Build parts_needed list
            parts_needed = []
            if "assembly_part" in assembly_info:
                ap = assembly_info["assembly_part"]
                parts_needed.append({
                    "part_number": ap["number"],
                    "part_name": f"{assembly_info['name']} Sub-Assembly",
                    "part_id": ap["id"]
                })

            for comp in assembly_info.get("components", []):
                parts_needed.append({
                    "part_number": comp["number"],
                    "part_name": comp["name"],
                    "part_id": comp["id"]
                })

            # Get repair steps
            repair_steps = get_repair_steps(key)

            enriched["missing_assemblies"].append({
                "assembly_key": key,
                "assembly_name": assembly_info.get("name", component_name),
                "importance": assembly_info.get("importance", "structural"),
                "location": location or assembly_info.get("location", ""),
                "confidence": parsed.get("confidence", 0.9),
                "parts_needed": parts_needed,
                "repair_steps": repair_steps
            })

    # Process present components
    present = parsed.get("present_components", [])
    for comp_name in present:
        assembly_keys = map_component_to_assemblies(comp_name)
        for key in assembly_keys:
            if key not in processed_assemblies:
                enriched["verified_assemblies"].append(key)

    # Generate summary if not provided
    if not enriched["summary"]:
        if enriched["missing_assemblies"]:
            names = [a["assembly_name"] for a in enriched["missing_assemblies"]]
            enriched["summary"] = f"Missing: {', '.join(names)}"
        else:
            enriched["summary"] = "All components appear to be present."

    return enriched


def format_for_display(parsed: Dict[str, Any], model_name: str = "") -> str:
    """
    Convert parsed/enriched response to user-friendly markdown display.

    Args:
        parsed: Enriched parsed response
        model_name: Name of the CAD model

    Returns:
        Formatted markdown string
    """
    output = []
    status = parsed.get("status", "UNKNOWN")
    confidence = parsed.get("confidence_score", 0)
    summary = parsed.get("summary", "")

    # Header
    output.append(f"## Quality Inspection Report: {model_name}")
    output.append("")

    if status == "DEFECT_FREE":
        output.append("**Status:** ALL PARTS PRESENT")
    else:
        output.append("**Status:** MISSING PARTS DETECTED")

    output.append(f"**Confidence:** {confidence:.0%}")
    output.append("")
    output.append("### Summary")
    output.append("")
    output.append(summary)
    output.append("")

    # Missing assemblies
    missing = parsed.get("missing_assemblies", [])
    if missing:
        # Sort by importance
        importance_order = {"critical": 0, "structural": 1, "cosmetic": 2}
        missing = sorted(
            missing,
            key=lambda x: importance_order.get(x.get("importance", ""), 3)
        )

        output.append("---")
        output.append("")

        for assembly in missing:
            importance = assembly.get("importance", "").upper()
            badge = f"[{importance}]" if importance else ""

            output.append(
                f"## Missing: {assembly.get('assembly_name', 'Unknown')} {badge}"
            )
            output.append("")

            if assembly.get("location"):
                output.append(f"**Location:** {assembly['location']}")
                output.append("")

            # Parts needed
            parts = assembly.get("parts_needed", [])
            if parts:
                output.append("### Parts Required")
                output.append("")
                output.append("| Part # | Part Name |")
                output.append("|--------|-----------|")
                for part in parts:
                    num = part.get("part_number", "?")
                    name = part.get("part_name", "Unknown")
                    output.append(f"| #{num} | {name} |")
                output.append("")

            # Repair steps
            steps = assembly.get("repair_steps", [])
            if steps:
                output.append("### How to Fix")
                output.append("")
                for step in steps:
                    output.append(step)
                output.append("")

            output.append("---")
            output.append("")

    # Verified assemblies
    verified = parsed.get("verified_assemblies", [])
    if verified:
        output.append("### Verified Components")
        output.append("")
        for key in verified:
            assembly = BUGGY_ASSEMBLIES.get(key, {})
            name = assembly.get("name", key)
            output.append(f"- {name}")
        output.append("")

    return "\n".join(output)


def parse_and_format_response(
    raw_text: str,
    model_name: str = ""
) -> Tuple[str, Dict[str, Any], List[str]]:
    """
    Parse raw AI response, enrich with CAD data, and format for display.

    Args:
        raw_text: Raw AI response text
        model_name: Name of the CAD model

    Returns:
        Tuple of (formatted_text, enriched_data, mentioned_part_ids)
    """
    # Try to extract JSON
    parsed = extract_json_from_response(raw_text)

    if parsed is None:
        log("Could not parse structured response, using raw text", "WARNING")
        return raw_text, {}, []

    # Enrich with CAD data
    enriched = enrich_with_cad_data(parsed)

    # Extract part IDs for rendering
    mentioned_parts = []
    for assembly in enriched.get("missing_assemblies", []):
        for part in assembly.get("parts_needed", []):
            if part.get("part_id"):
                mentioned_parts.append(part["part_id"])

    # Format for display
    formatted = format_for_display(enriched, model_name)

    return formatted, enriched, mentioned_parts
