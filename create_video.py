#!/usr/bin/env python3
"""
NotebookLM to YouTube Video Creator with Customization Options

A comprehensive script to create videos from audio with various options for cover art,
transcription, and output customization.
"""

import argparse
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from transcribe import transcribe_audio
from cover_art import generate_cover_art
from video import create_video as create_video_ffmpeg

def create_video_with_options(
    audio_path: str,
    output_path: str = None,
    cover_art_path: str = None,
    custom_prompt: str = None,
    skip_transcription: bool = False,
    auto_approve: bool = False,
    output_dir: str = "data"
):
    """
    Create a video with various customization options.
    
    Args:
        audio_path: Path to input audio file
        output_path: Custom output video path (optional)
        cover_art_path: Use existing cover art instead of generating (optional)
        custom_prompt: Custom prompt for AI cover art generation (optional)
        skip_transcription: Skip transcription if transcript already exists
        auto_approve: Skip user approval and proceed automatically
        output_dir: Directory for output files
    """
    
    audio_file = Path(audio_path)
    if not audio_file.exists():
        print(f"❌ Error: Audio file not found: {audio_path}")
        return False
    
    print(f"🎵 Processing: {audio_file.name}")
    
    # Set default output path
    if not output_path:
        output_path = Path(output_dir) / f"{audio_file.stem}_video.mp4"
    else:
        output_path = Path(output_path)
    
    transcript_path = audio_file.with_suffix('.txt')
    transcript_content = ""
    
    # Step 1: Transcription (only if needed for cover art generation)
    if cover_art_path:
        print("⏭️ Step 1: Skipping transcription (using provided cover art)")
    elif skip_transcription and transcript_path.exists():
        print(f"⏭️ Step 1: Using existing transcript: {transcript_path}")
        try:
            with open(transcript_path, 'r') as f:
                transcript_content = f.read()
        except Exception as e:
            print(f"❌ Could not read transcript: {e}")
            return False
    else:
        print("\n📝 Step 1: Transcribing Audio")
        try:
            transcript_path = transcribe_audio(str(audio_file))
            print(f"✅ Transcription saved: {transcript_path}")
            with open(transcript_path, 'r') as f:
                transcript_content = f.read()
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            return False
    
    # Step 2: Cover Art
    print("\n🎨 Step 2: Cover Art")
    
    if cover_art_path:
        # Use provided cover art
        cover_art_file = Path(cover_art_path)
        if not cover_art_file.exists():
            print(f"❌ Error: Cover art file not found: {cover_art_path}")
            return False
        print(f"🖼️ Using provided cover art: {cover_art_file}")
        final_cover_art = str(cover_art_file)
    else:
        # Generate new cover art
        try:
            if custom_prompt:
                print(f"🎯 Using custom prompt: {custom_prompt[:100]}...")
                # Temporarily replace the transcript with custom prompt
                final_cover_art = generate_cover_art(custom_prompt)
            else:
                print("🤖 Generating AI cover art from transcript...")
                final_cover_art = generate_cover_art(transcript_content)
            
            print(f"✅ Cover art generated: {final_cover_art}")
        except Exception as e:
            print(f"❌ Cover art generation failed: {e}")
            print("🔄 Falling back to placeholder...")
            placeholder_path = Path("data/placeholder.png")
            if placeholder_path.exists():
                final_cover_art = str(placeholder_path)
            else:
                print("❌ No fallback cover art available")
                return False
    
    # Step 3: User Approval
    if not auto_approve:
        print(f"\n👀 Step 3: Review")
        print(f"🎨 Cover art: {final_cover_art}")
        print(f"🎬 Output will be: {output_path}")
        
        try:
            approval = input("\n🤔 Proceed with video creation? (y/n): ").strip().lower()
            if approval != 'y':
                print("❌ Video creation cancelled by user")
                return False
        except KeyboardInterrupt:
            print("\n❌ Video creation cancelled by user")
            return False
    else:
        print(f"\n⚡ Step 3: Auto-approved, proceeding...")
    
    # Step 4: Video Creation
    print(f"\n🎬 Step 4: Creating Video")
    try:
        create_video_ffmpeg(final_cover_art, str(audio_file), str(output_path))
        
        # Show results
        size = output_path.stat().st_size
        size_mb = size / (1024 * 1024)
        print(f"\n🎉 Success! Video created:")
        print(f"📁 Location: {output_path}")
        print(f"📊 Size: {size:,} bytes ({size_mb:.1f} MB)")
        return True
        
    except Exception as e:
        print(f"❌ Video creation failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="🎙️ Create YouTube-ready videos from audio with customization options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🎯 Examples:

Basic usage:
  python3 create_video.py data/my-audio.mp4

With custom output:
  python3 create_video.py data/podcast.m4a -o videos/episode-001.mp4

Use existing cover art:
  python3 create_video.py data/audio.wav --cover-art data/my-art.png

Auto-approve (no manual intervention):
  python3 create_video.py data/audio.mp3 --auto-approve

Custom AI prompt for cover art:
  python3 create_video.py data/audio.wav --prompt "Abstract geometric art with purple gradients"

Skip transcription (use existing):
  python3 create_video.py data/audio.mp4 --skip-transcription

🎨 Combine options:
  python3 create_video.py data/audio.m4a -o final.mp4 --auto-approve --prompt "Minimalist podcast art"
        """
    )
    
    # Required argument
    parser.add_argument("audio_file", help="Path to input audio file")
    
    # Optional arguments
    parser.add_argument("-o", "--output", help="Output video path (default: auto-generated)")
    parser.add_argument("--cover-art", help="Use existing cover art image instead of generating")
    parser.add_argument("--prompt", help="Custom prompt for AI cover art generation")
    parser.add_argument("--skip-transcription", action="store_true", 
                       help="Skip transcription if transcript file already exists")
    parser.add_argument("--auto-approve", action="store_true",
                       help="Skip user approval and proceed automatically")
    parser.add_argument("--output-dir", default="data",
                       help="Directory for output files (default: data)")
    parser.add_argument("--version", action="version", version="Video Creator v1.0.0")
    
    args = parser.parse_args()
    
    # Create video with options
    success = create_video_with_options(
        audio_path=args.audio_file,
        output_path=args.output,
        cover_art_path=args.cover_art,
        custom_prompt=args.prompt,
        skip_transcription=args.skip_transcription,
        auto_approve=args.auto_approve,
        output_dir=args.output_dir
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
