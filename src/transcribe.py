import os
import subprocess
from pathlib import Path
import tempfile

def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcribes the given audio file using the local whisper.cpp executable.
    It first converts the audio to a WAV file format.

    Args:
        audio_file_path (str): The path to the audio file.

    Returns:
        str: The path to the generated transcript file.
    """
    audio_path = Path(audio_file_path).resolve()
    whisper_dir = Path.home() / "LLM-apps" / "whisper.cpp"
    whisper_executable = whisper_dir / "build" / "bin" / "whisper-cli"
    model_path = whisper_dir / "models" / "ggml-tiny.en.bin"

    if not whisper_executable.exists():
        raise FileNotFoundError(f"Whisper executable not found at {whisper_executable}")
    if not model_path.exists():
        raise FileNotFoundError(f"Whisper model not found at {model_path}")

    output_file_path = audio_path.with_suffix(".txt")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav_file:
        wav_path = Path(tmp_wav_file.name)

    # Convert audio to WAV format using ffmpeg
    print(f"Converting {audio_path} to WAV format...")
    try:
        subprocess.run(
            ["ffmpeg", "-i", str(audio_path), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav_path), "-y"],
            check=True
        )
        print("Audio conversion completed.")
    except subprocess.CalledProcessError as e:
        print(f"Error during audio conversion: {e}")
        os.remove(wav_path)
        raise

    command = [
        str(whisper_executable),
        "--model", str(model_path),
        "--file", str(wav_path),
        "--output-txt",
        "--output-file", str(output_file_path.with_suffix(''))
    ]

    print("Starting transcription...")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Transcription complete. Output saved to {output_file_path}")
        print("Whisper.cpp output:\n", result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error during transcription: {e.stderr}")
        raise
    finally:
        # Clean up the temporary WAV file
        os.remove(wav_path)

    return str(output_file_path)

if __name__ == '__main__':
    # This is an example of how to use the function.
    audio_file_to_process = "data/Beyond_the_Hype__Debunking_the_AI_Bubble_and_Unpacking_Its_True_Impact (1).m4a"

    if not os.path.exists(audio_file_to_process):
        print(f"Error: The file '{audio_file_to_process}' does not exist.")
    else:
        try:
            transcript_path = transcribe_audio(audio_file_to_process)
            with open(transcript_path, 'r') as f:
                print("\n--- Transcript ---")
                print(f.read())
                print("------------------")
        except FileNotFoundError as e:
            print(e)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
