import argparse
from pathlib import Path
from transcribe import transcribe_audio
from video import create_video
from cover_art import generate_cover_art

def main():
    parser = argparse.ArgumentParser(
        description="🎙️ Convert NotebookLM audio into YouTube-ready videos with AI-generated podcast album art.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 src/main.py data/my-podcast.m4a
  python3 src/main.py ~/Downloads/episode-001.wav

The tool will:
1. Transcribe your audio using whisper.cpp
2. Generate artistic cover art based on content themes  
3. Create a YouTube-ready MP4 video

For more information: https://github.com/yourusername/notebooklm-to-youtube
        """
    )
    parser.add_argument("audio_file", type=str, help="Path to the input audio file (supports .mp3, .wav, .m4a, .mp4)")
    parser.add_argument("--version", action="version", version="NotebookLM to YouTube Converter v1.0.0")
    args = parser.parse_args()

    audio_path = Path(args.audio_file)
    if not audio_path.exists():
        print(f"Error: The file '{audio_path}' does not exist.")
        return

    # --- 1. Transcription ---
    print("--- Step 1: Transcribing Audio ---")
    try:
        transcript_path = transcribe_audio(str(audio_path))
        with open(transcript_path, 'r') as f:
            transcript = f.read()
        print("Transcription successful.")
        # print("Transcript:", transcript) # Optionally print the full transcript
    except Exception as e:
        print(f"An error occurred during transcription: {e}")
        return

    # --- 2. Cover Art Generation ---
    print("\n--- Step 2: Cover Art Generation ---")
    try:
        cover_art_path = generate_cover_art(transcript)
    except Exception as e:
        print(f"Failed to generate cover art: {e}")
        print("Falling back to placeholder...")
        cover_art_path = "data/placeholder.png"
        if not Path(cover_art_path).exists():
            print(f"Error: Placeholder image not found at '{cover_art_path}'.")
            print("Please run 'python3 src/video.py' once to generate it.")
            return

    # --- 3. User Approval ---
    print("\n--- Step 3: User Approval ---")
    print(f"Generated cover art: {cover_art_path}")
    try:
        approval = input("Do you want to proceed with video creation? (y/n): ")
        if approval.lower() != 'y':
            print("Operation cancelled by user.")
            return
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return

    # --- 4. Video Creation ---
    print("\n--- Step 4: Creating Video ---")
    output_video_path = audio_path.with_suffix(".mp4")
    try:
        create_video(cover_art_path, str(audio_path), str(output_video_path))
        print(f"\nProcess complete! Video saved to: {output_video_path}")
    except Exception as e:
        print(f"An error occurred during video creation: {e}")

if __name__ == '__main__':
    main()
