import os
import sys
import requests
import base64
import binascii
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

def generate_cover_art(
    transcript: str,
    output_dir: str = "data",
    *,
    output_path: str | Path | None = None,
    prompt_override: str | None = None,
) -> str:
    """
    Generates cover art using the OpenRouter API and saves it to a file.

    Args:
        transcript (str): The audio transcript to base the cover art on.
        output_dir (str): The directory to save the image in. Defaults to "data".
        output_path (str | Path | None): An exact filename inside output_dir.
        prompt_override (str | None): An exact prompt to send to the model.

    Returns:
        str: The path to the saved image file.
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not found in .env file")

    output_directory = Path(output_dir)
    image_filepath = Path(output_path) if output_path is not None else None
    if (
        image_filepath is not None
        and image_filepath.resolve().parent != output_directory.resolve()
    ):
        raise ValueError("output_path must be directly inside output_dir")

    # Generate the image prompt using the prompt system unless one was supplied.
    prompt = prompt_override if prompt_override is not None else get_image_prompt(transcript)
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
        json=payload,
        timeout=180,
    )

    if response.status_code != 200:
        raise Exception(f"Error from OpenRouter API: {response.status_code} - {response.text}")

    result = response.json()
    
    try:
        image_data_url = result["choices"][0]["message"]["images"][0]["image_url"]["url"]
        
        # The data URL is in the format "data:image/png;base64,iVBORw0K..."
        header, encoded = image_data_url.split(",", 1)
        if not header.startswith("data:image/") or ";base64" not in header:
            raise ValueError("Malformed image data URL")
        try:
            image_data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as e:
            raise ValueError("Malformed image data URL") from e
        
        if image_filepath is None:
            timestamp = int(time.time())
            image_filepath = output_directory / f"cover_art_{timestamp}.png"

        image_filepath.parent.mkdir(parents=True, exist_ok=True)
        if output_path is not None:
            temporary_path = Path(f"{image_filepath}.tmp")
            temporary_path.write_bytes(image_data)
            os.replace(temporary_path, image_filepath)
        else:
            image_filepath.write_bytes(image_data)
        
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
