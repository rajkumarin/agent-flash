"""Simple test script to check Gemini's image recognition capabilities."""

import os
import sys
import time
import google.generativeai as genai
from PIL import Image

# Configure Gemini API - accept from command line or environment
API_KEY = None
if len(sys.argv) > 1:
    API_KEY = sys.argv[1]
else:
    API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    print("Usage: python test_image_recognition.py <YOUR_GEMINI_API_KEY>")
    print("Or set GEMINI_API_KEY environment variable")
    exit(1)

genai.configure(api_key=API_KEY)

# Try different models in order of preference
MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]

model = None
for model_name in MODELS_TO_TRY:
    try:
        print(f"Trying model: {model_name}...")
        model = genai.GenerativeModel(model_name)
        # Quick test to see if model works
        break
    except Exception as e:
        print(f"  Failed: {e}")
        continue

if model is None:
    print("ERROR: No available model found!")
    exit(1)

print(f"Using model: {model_name}")

# Load the test image
image_path = r"C:\Users\linux\Downloads\dataset_MCP\1.jpeg"
print(f"\nLoading image: {image_path}")

try:
    image = Image.open(image_path)
    print(f"Image size: {image.width} x {image.height} pixels")
    print(f"Image mode: {image.mode}")
except Exception as e:
    print(f"ERROR loading image: {e}")
    exit(1)

def call_with_retry(prompt, image, max_retries=3):
    """Call the model with retry logic for rate limits."""
    for attempt in range(max_retries):
        try:
            response = model.generate_content([prompt, image])
            return response.text
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e):
                wait_time = (attempt + 1) * 30
                print(f"  Rate limited. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                return f"ERROR: {e}"
    return "ERROR: Max retries exceeded due to rate limiting."

# Test 1: Basic recognition
print("\n" + "="*60)
print("TEST 1: What can Gemini see in this image?")
print("="*60)

prompt1 = """Describe this image in detail.
What object is shown?
What parts can you identify?
Is it a complete model or are parts missing?"""

result1 = call_with_retry(prompt1, image)
print(result1)

# Test 2: Wheel counting
print("\n" + "="*60)
print("TEST 2: Wheel counting test")
print("="*60)

prompt2 = """Look at this LEGO vehicle image carefully.

Count the wheels:
1. How many wheels can you see in total?
2. Is there a wheel at the FRONT-LEFT position? (YES/NO)
3. Is there a wheel at the FRONT-RIGHT position? (YES/NO)
4. Is there a wheel at the REAR-LEFT position? (YES/NO)
5. Is there a wheel at the REAR-RIGHT position? (YES/NO)

Answer each question specifically."""

result2 = call_with_retry(prompt2, image)
print(result2)

# Test 3: Steering wheel check
print("\n" + "="*60)
print("TEST 3: Steering wheel presence")
print("="*60)

prompt3 = """Look at the cockpit area of this LEGO vehicle.

Is there a steering wheel visible in the cockpit?
Look carefully at the driver's position.
Answer: YES or NO, and describe what you see in that area."""

result3 = call_with_retry(prompt3, image)
print(result3)

# Test 4: Missing parts identification
print("\n" + "="*60)
print("TEST 4: What parts appear to be missing?")
print("="*60)

prompt4 = """This appears to be a partially assembled LEGO vehicle.

List ALL the parts that appear to be MISSING from this model:
- Look at where wheels should be attached
- Look at the front bumper area
- Look at any exposed connection points

Be specific about what's missing and where."""

result4 = call_with_retry(prompt4, image)
print(result4)

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
