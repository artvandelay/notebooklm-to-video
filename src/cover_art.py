import os
import sys
import requests
import base64
from dotenv import load_dotenv
from pathlib import Path
import time

# Add the parent directory to path to find prompt_loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from prompt_loader import get_image_prompt
except ImportError:
    from src.prompt_loader import get_image_prompt

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def generate_cover_art(transcript: str, output_dir: str = "data") -> str:
    """
    Generates cover art using the OpenRouter API and saves it to a file.

    Args:
        transcript (str): The audio transcript to base the cover art on.
        output_dir (str): The directory to save the image in. Defaults to "data".

    Returns:
        str: The path to the saved image file.
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not found in .env file")

    # Generate the image prompt using the prompt system
    prompt = get_image_prompt(transcript)
    print(f"Generated image prompt: {prompt[:100]}...")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Using the google/gemini-3-pro-image-preview model for image generation.
    model_name = "google/gemini-3-pro-image-preview"

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image", "text"]
    }

    print(f"Sending request to OpenRouter for model: {model_name}...")
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload
    )

    if response.status_code != 200:
        raise Exception(f"Error from OpenRouter API: {response.status_code} - {response.text}")

    result = response.json()
    
    try:
        image_data_url = result["choices"][0]["message"]["images"][0]["image_url"]["url"]
        
        # The data URL is in the format "data:image/png;base64,iVBORw0K..."
        header, encoded = image_data_url.split(",", 1)
        image_data = base64.b64decode(encoded)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create a unique filename
        timestamp = int(time.time())
        image_filename = f"cover_art_{timestamp}.png"
        image_filepath = output_path / image_filename

        with open(image_filepath, "wb") as f:
            f.write(image_data)
        
        print(f"Cover art successfully saved to: {image_filepath}")
        return str(image_filepath)

    except (KeyError, IndexError) as e:
        print(f"Could not find image data in the API response: {e}")
        print("Full API Response:", result)
        raise

if __name__ == '__main__':
    # Example usage
    test_transcript = "In this episode, we discuss the future of artificial intelligence, machine learning, and how technology is reshaping our world."
    try:
        image_path = generate_cover_art(test_transcript)
        print(f"Test image generated at: {image_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
