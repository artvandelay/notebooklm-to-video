from pathlib import Path

def load_prompt(prompt_name: str) -> str:
    """
    Load a prompt from the prompts directory.
    
    Args:
        prompt_name (str): Name of the prompt file (without .txt extension)
        
    Returns:
        str: The prompt content
    """
    prompt_path = Path("prompts") / f"{prompt_name}.txt"
    if prompt_path.exists():
        with open(prompt_path, 'r') as f:
            return f.read().strip()
    else:
        print(f"Warning: Prompt file {prompt_path} not found. Using default.")
        return ""

def get_image_prompt(transcript: str) -> str:
    """
    Generate an image prompt based on the transcript using the configured prompts.
    
    Args:
        transcript (str): The audio transcript
        
    Returns:
        str: A complete prompt for image generation
    """
    # Load the prompt components
    image_aesthetic = load_prompt("image_aesthetic")
    
    # Analyze the transcript to extract key themes for artistic representation
    key_themes = transcript[:400] if len(transcript) > 400 else transcript
    
    # Create a direct image generation prompt that combines the aesthetic with content themes
    full_prompt = f"""Create sophisticated podcast album art based on these themes from the audio content: "{key_themes}"

{image_aesthetic}

Generate an artistic, abstract visual representation that captures the essence of this content while maintaining the signature podcast series aesthetic described above."""
    
    return full_prompt.strip()
