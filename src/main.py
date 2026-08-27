import argparse
from pathlib import Path
from transcribe import transcribe_audio
from video import create_video
from cover_art import generate_cover_art
from job import resolve_job

def main():
    parser = argparse.ArgumentParser(
        description="🎙️ Convert NotebookLM audio into YouTube-ready videos with AI-generated podcast album art.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 src/main.py uploads/my-episode
  python3 src/main.py uploads/my-episode/episode.m4a

Put each upload in its own folder under uploads/. All outputs stay there.

The tool will:
1. Transcribe your audio using whisper.cpp
2. Generate artistic cover art based on content themes  
3. Create a YouTube-ready MP4 video
        """
    )
    parser.add_argument("audio_file", type=str, help="Job folder (uploads/<name>/) or path to an audio file")
    parser.add_argument("--version", action="version", version="NotebookLM to YouTube Converter v1.0.0")
    args = parser.parse_args()

    try:
        job_dir, audio_path = resolve_job(args.audio_file)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return

    # --- 1. Transcription ---
    print("--- Step 1: Transcribing Audio ---")
    print(f"Job folder: {job_dir}")
    try:
        transcript_path = transcribe_audio(str(audio_path))
        with open(transcript_path, 'r') as f:
            transcript = f.read()
        print("Transcription successful.")
    except Exception as e:
        print(f"An error occurred during transcription: {e}")
        return

    # --- 2. Cover Art Generation ---
    print("\n--- Step 2: Cover Art Generation ---")
    try:
        cover_art_path = generate_cover_art(transcript, output_dir=str(job_dir))
    except Exception as e:
        print(f"Failed to generate cover art: {e}")
        print("Falling back to placeholder...")
        cover_art_path = str(job_dir / "placeholder.png")
        if not Path(cover_art_path).exists():
            print(f"Error: Placeholder image not found at '{cover_art_path}'.")
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
    output_video_path = job_dir / f"{audio_path.stem}_video.mp4"
    try:
        create_video(cover_art_path, str(audio_path), str(output_video_path))
        print(f"\nProcess complete! Video saved to: {output_video_path}")
    except Exception as e:
        print(f"An error occurred during video creation: {e}")

if __name__ == '__main__':
    main()
