
import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

# Initialize Gemini client
client = genai.Client(api_key=api_key)

# Select Gemini model
MODEL_NAME = "gemini-3.5-flash-lite"

# Send a test message
response = client.models.generate_content(
    model=MODEL_NAME,
    contents="Hello Gemini! Please introduce yourself briefly."
)

# Display response
print("\nGemini Response:")
print(response.text)
