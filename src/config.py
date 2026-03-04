"""Configuration constants for CAD Repair Assistant."""

# FreeCAD connection defaults
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9875

# View angle mappings
VIEW_ANGLES = [
    "Isometric",
    "Front",
    "Rear",
    "Left",
    "Right",
    "Top",
    "FrontLeft",
    "FrontRight",
    "RearLeft",
    "RearRight",
]

# Map detected views to FreeCAD render views
FREECAD_VIEW_MAPPING = {
    "FrontLeft": "Left",
    "FrontRight": "Right",
    "RearLeft": "Left",
    "RearRight": "Right",
    "Front": "Front",
    "Rear": "Rear",
    "Left": "Left",
    "Right": "Right",
    "Top": "Top",
    "Isometric": "Isometric",
}

# View visibility descriptions for AI context
VIEW_VISIBILITY_INFO = {
    "Front": "FRONT view - can see: front face, both front wheels. CANNOT see: rear parts.",
    "Rear": "REAR view - can see: back face, both rear wheels. CANNOT see: front parts.",
    "Left": "LEFT SIDE view - can see: left side, left wheels. CANNOT see: right side details.",
    "Right": "RIGHT SIDE view - can see: right side, right wheels. CANNOT see: left side details.",
    "Top": "TOP view - can see: top surface. CANNOT see: bottom parts, wheel details.",
    "FrontLeft": "FRONT-LEFT diagonal (3/4 view) - can see: ALL 4 wheel positions, front and left side details.",
    "FrontRight": "FRONT-RIGHT diagonal (3/4 view) - can see: ALL 4 wheel positions, front and right side details.",
    "RearLeft": "REAR-LEFT diagonal (3/4 view) - can see: ALL 4 wheel positions, rear and left side details.",
    "RearRight": "REAR-RIGHT diagonal (3/4 view) - can see: ALL 4 wheel positions, rear and right side details.",
    "Isometric": "ISOMETRIC view - can see: ALL 4 wheel positions, multiple sides.",
}

# AI Model configuration
GEMINI_MODEL = "gemini-2.5-flash"
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Available AI providers
AI_PROVIDERS = ["Gemini", "Claude"]

# Image display settings
MAX_THUMBNAIL_WIDTH = 400
COLS_PER_ROW = 3
MAX_RENDERED_PARTS = 3

# Highlight colors (RGBA, 0-1 range)
HIGHLIGHT_COLOR_ORANGE = [1.0, 0.3, 0.0, 1.0]
HIGHLIGHT_COLOR_RED = [1.0, 0.0, 0.0, 1.0]
HIGHLIGHT_COLOR_GREEN = [0.0, 1.0, 0.0, 1.0]

# Default repair part options
DEFAULT_REPAIR_PARTS = [
    "Front Left Wheel",
    "Front Right Wheel",
    "Rear Left Wheel",
    "Rear Right Wheel",
    "Windshield",
    "Left Headlight",
    "Right Headlight",
    "Left Side Mirror",
    "Right Side Mirror",
    "Front Bumper",
    "Rear Bumper",
    "Hood",
    "Trunk",
    "Doors",
]
