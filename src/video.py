import subprocess
from pathlib import Path

def create_video(image_path: str, audio_path: str, output_path: str):
    """
    Creates a video from a single image and an audio file using ffmpeg.

    Args:
        image_path (str): Path to the input image.
        audio_path (str): Path to the input audio.
        output_path (str): Path to the output video file.
    """
    image_p = Path(image_path)
    audio_p = Path(audio_path)
    output_p = Path(output_path)

    if not image_p.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    if not audio_p.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    command = [
        'ffmpeg',
        '-loop', '1',          # Loop the image
        '-i', str(image_p),    # Input image
        '-i', str(audio_p),    # Input audio
        '-c:v', 'libx264',     # Video codec
        '-c:a', 'aac',         # Audio codec
        '-b:a', '192k',        # Audio bitrate
        '-shortest',           # Finish encoding when the shortest input stream ends (the audio)
        str(output_p)
    ]
    
    print(f"Creating video... Output will be saved to {output_p}")
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print("Video created successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error creating video: {e.stderr}")
        raise

if __name__ == '__main__':
    # Example usage:
    # Assumes you have a 'placeholder.png' and a 'dummy_audio.wav' in the 'data' directory.
    
    # Create dummy files if they don't exist
    import os
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    placeholder_image = data_dir / "placeholder.png"
    dummy_audio = data_dir / "dummy_audio.wav"
    output_video = data_dir / "output.mp4"

    if not placeholder_image.exists():
        print("Creating placeholder image...")
        os.system(f"convert -size 1280x720 canvas:black {placeholder_image}") # Requires ImageMagick
        
    if not dummy_audio.exists():
        print("Creating dummy audio...")
        os.system(f"ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 10 -q:a 9 -acodec pcm_s16le {dummy_audio}")

    print("\n--- Testing Video Creation ---")
    try:
        create_video(str(placeholder_image), str(dummy_audio), str(output_video))
    except Exception as e:
        print(f"An error occurred during video creation test: {e}")
