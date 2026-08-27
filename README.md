# 🎙️ NotebookLM Audio to YouTube Video Converter

Convert your NotebookLM audio content into YouTube-ready videos with AI-generated podcast album art.

This tool automatically transcribes audio, generates sophisticated podcast album art based on content themes, and creates professional MP4 videos ready for upload.

## ✨ Features

- 🎯 **Local Transcription** - Uses whisper.cpp for fast, accurate transcription
- 🎨 **AI-Generated Album Art** - Creates sophisticated podcast-style cover art via OpenRouter
- 🎬 **Video Creation** - Combines audio + cover art into YouTube-ready MP4s  
- 🎭 **Artistic Branding** - Consistent, gallery-quality visual style for your podcast series
- ⚙️ **Customizable Prompts** - Easily customize the AI's artistic style and approach
- 📱 **CLI Interface** - Simple command-line workflow

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **FFmpeg** - [Download here](https://ffmpeg.org/download.html)
3. **whisper.cpp** - [Setup instructions](#whisper-setup)
4. **OpenRouter API Key** - [Get one here](https://openrouter.ai/)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/notebooklm-to-video.git
   cd notebooklm-to-video
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenRouter API key
   ```

4. **Set up whisper.cpp** (see [detailed instructions](#whisper-setup))

### Usage

#### Basic Usage
```bash
# New upload: one folder per episode, all files stay there
mkdir -p uploads/my-episode
cp ~/Downloads/episode.m4a uploads/my-episode/

python3 create_video.py uploads/my-episode --auto-approve
```

#### Advanced Options
```bash
# Use existing cover art (skips transcription)
python3 create_video.py uploads/my-episode --cover-art uploads/my-episode/cover.png --auto-approve

# Custom AI prompt for cover art
python3 create_video.py uploads/my-episode --prompt "Minimalist podcast art" --auto-approve

# Custom output path
python3 create_video.py uploads/my-episode -o uploads/my-episode/final.mp4

# Use existing transcript
python3 create_video.py uploads/my-episode --skip-transcription
```

The tool will:
1. 📝 Transcribe your audio using whisper.cpp (only when needed)
2. 🎨 Generate artistic cover art based on content themes (or use provided art)
3. 🖼️ Show you the generated art for approval (unless auto-approved)
4. 🎬 Create a YouTube-ready MP4 video

## 📁 Project Structure

Scripts stay at the repo root. **Every episode gets its own folder under `uploads/`** — audio, cover, transcripts, translations, and the final video all go there. Do not leave generated files in the repo root.

```
├── create_video.py          # audio + cover → YouTube MP4
├── translate_to_marathi.py  # Gujarati audio → Marathi text + speech
├── src/
│   ├── main.py              # Interactive orchestration
│   ├── job.py               # Resolves a job folder or audio file
│   ├── transcribe.py        # whisper.cpp transcription
│   ├── cover_art.py         # OpenRouter cover art
│   ├── video.py             # ffmpeg still-image video
│   └── prompt_loader.py
├── prompts/                 # Cover-art style prompts
├── uploads/
│   └── <episode-name>/      # One folder per upload
│       ├── <episode>.m4a
│       ├── <episode>.png            # cover / thumbnail
│       ├── <episode>.txt            # transcript
│       ├── <episode>.gujarati.txt
│       ├── <episode>.marathi.txt
│       ├── <episode>.marathi.mp3
│       └── <episode>_video.mp4
├── AGENTS.md                # Conventions for coding agents
├── requirements.txt
└── README.md
```

See [`AGENTS.md`](AGENTS.md) for the same layout written for automated agents.

## 🎨 Customizing Your Podcast Style

Edit files in the `prompts/` directory to customize the AI's artistic approach:

- **`image_aesthetic.txt`** - Define your visual brand (colors, style, mood)
- **`transcript_to_image_prompt.txt`** - How content becomes visual concepts
- **`system_instructions.txt`** - AI personality and behavior

See [`prompts/README.md`](prompts/README.md) for detailed customization instructions.

## ⚙️ Setup Instructions

### Whisper Setup

1. **Clone whisper.cpp**
   ```bash
   cd ~/
   mkdir -p LLM-apps
   cd LLM-apps
   git clone https://github.com/ggerganov/whisper.cpp.git
   cd whisper.cpp
   ```

2. **Compile whisper.cpp**
   ```bash
   make
   ```

3. **Download the tiny.en model** (fast, good quality for podcast content)
   ```bash
   bash models/download-ggml-model.sh tiny.en
   ```

### OpenRouter Setup

1. **Get API Key**
   - Sign up at [OpenRouter](https://openrouter.ai/)
   - Generate an API key
   - Add it to your `.env` file

2. **Verify Setup**
   ```bash
   python3 -c "from src.cover_art import generate_cover_art; print('Setup successful!')"
   ```

## 🛠️ Advanced Configuration

### Using Different Whisper Models

Edit `src/transcribe.py` line 20 to change models:
```python
# Faster, smaller model (default)
model_path = whisper_dir / "models" / "ggml-tiny.en.bin"

# More accurate, larger model  
model_path = whisper_dir / "models" / "ggml-base.en.bin"
```

### Customizing Image Models

Edit `src/cover_art.py` line 37 to use different image generation models:
```python
model_name = "google/gemini-2.5-flash-image-preview"  # Default
# or try: "openai/dall-e-3", "anthropic/claude-3-5-sonnet", etc.
```

## 📋 Examples

### Basic Usage
```bash
mkdir -p uploads/my-podcast-episode
cp ~/Downloads/my-podcast-episode.m4a uploads/my-podcast-episode/
python3 create_video.py uploads/my-podcast-episode
```

### Expected Output
```
🎵 Processing: my-podcast-episode.m4a
📁 Job folder: uploads/my-podcast-episode

📝 Step 1: Transcribing Audio
Audio conversion completed.
Starting transcription...
✅ Transcription saved: uploads/my-podcast-episode/my-podcast-episode.txt

🎨 Step 2: Cover Art
Generated image prompt: Create sophisticated podcast album art...
Cover art successfully saved to: uploads/my-podcast-episode/cover_art_1234567890.png

👀 Step 3: Review
🎨 Cover art: uploads/my-podcast-episode/cover_art_1234567890.png
🎬 Output will be: uploads/my-podcast-episode/my-podcast-episode_video.mp4
🤔 Proceed with video creation? (y/n): y

🎬 Step 4: Creating Video
Creating video... Output will be saved to uploads/my-podcast-episode/my-podcast-episode_video.mp4
Video created successfully.

🎉 Success! Video created:
📁 Location: uploads/my-podcast-episode/my-podcast-episode_video.mp4
📊 Size: 45,123,456 bytes (43.0 MB)
```

## 🐛 Troubleshooting

### Common Issues

**"Whisper executable not found"**
- Ensure whisper.cpp is compiled and located at `~/LLM-apps/whisper.cpp/build/bin/whisper-cli`
- Run the whisper setup instructions above

**"Model not found"** 
- Download the required model: `bash ~/LLM-apps/whisper.cpp/models/download-ggml-model.sh tiny.en`

**"OPENROUTER_API_KEY not found"**
- Copy `.env.example` to `.env` and add your API key
- Get a key from [OpenRouter](https://openrouter.ai/)

**"FFmpeg not found"**
- Install FFmpeg: [Download instructions](https://ffmpeg.org/download.html)
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`

### Debug Mode

Run with verbose output:
```bash
python3 src/main.py your-audio.m4a 2>&1 | tee debug.log
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)  
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) for fast local transcription
- [OpenRouter](https://openrouter.ai/) for AI model access
- [FFmpeg](https://ffmpeg.org/) for video processing

## 📞 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/notebooklm-to-video/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/notebooklm-to-video/discussions)
- 📖 **Documentation**: [Wiki](https://github.com/yourusername/notebooklm-to-video/wiki)

---

**Made with ❤️ for podcast creators and content producers**

## Script to podcast

Create `uploads/<episode>/podcast.json` with this exact structure:

```json
{
  "version": 1,
  "episode": {
    "slug": "example-episode",
    "title": "Example Episode",
    "language": "en",
    "summary": "A concise, content-accurate summary.",
    "art_prompt": "Editorial illustration featuring the named people and concepts.",
    "scene": "Two hosts recording in a quiet professional studio.",
    "director_notes": "Natural conversation; vary pace; avoid announcer delivery."
  },
  "tts": {
    "model": "google/gemini-3.1-flash-tts-preview",
    "sample_rate": 24000,
    "default_pause_ms": 180,
    "fade_ms": 8
  },
  "speakers": {
    "HOST": {
      "name": "Maya",
      "voice": "Kore",
      "style": "Warm, confident, curious host."
    },
    "GUEST": {
      "name": "Arun",
      "voice": "Puck",
      "style": "Thoughtful expert with conversational energy."
    }
  },
  "turns": [
    {
      "speaker": "HOST",
      "text": "[excited] Welcome to the show.",
      "pause_after_ms": 140
    },
    {
      "speaker": "GUEST",
      "text": "Thanks, Maya. [laughs] This will be fun."
    }
  ],
  "chapters": [
    {
      "title": "Introduction",
      "turn": 0
    }
  ],
  "youtube": {
    "title": "Optional override",
    "description": "Optional description prefix",
    "tags": ["podcast", "education"],
    "category": "Education"
  }
}
```

The contract accepts no unknown fields. `version` must be `1`; `episode.slug` must contain lowercase letters, digits, and single hyphens only. Episode text fields must be non-empty. Configure one or two speakers and at least one turn; every turn must reference a configured speaker. `sample_rate` must be `24000`, pauses must be from `0` to `5000` milliseconds, and `fade_ms` must be from `0` to `50`. Chapter turn indices must be unique, ascending, and valid. If chapters are omitted or empty, an `Introduction` chapter is added at turn `0`. YouTube fields are optional and default to the episode title, an empty description and tag list, and the `Education` category.

OpenRouter's speech endpoint accepts one voice per request. The pipeline therefore renders each turn separately with its configured speaker voice, then joins and masters the turns. English inline audio tags such as `[laughs]`, `[whispers]`, and `[excited]` can guide delivery.

Activate the repository's uv-managed environment, then run one of these commands:

```bash
source ~/pyenv/notebooklm-to-video/bin/activate
python3 create_podcast.py uploads/<episode> --auto-approve
python3 create_podcast.py uploads/<episode> --cover-art uploads/<episode>/cover.png --auto-approve
python3 create_podcast.py uploads/<episode> --force-audio --force-art --auto-approve
```

Long paid TTS/image generation and ffmpeg runs must be launched in tmux. Completed turn audio is cached under `uploads/<episode>/.podcast/segments/`; rerunning resumes from that cache unless `--force-audio` is used.

The pipeline writes all assets to the episode folder:

```text
uploads/<episode>/
├── podcast.json
├── .podcast/
│   ├── manifest.json
│   └── segments/
├── <slug>.podcast.wav
├── <slug>.podcast.mp3
├── <slug>.png
├── <slug>_video.mp4
└── <slug>.youtube.md
```

The MP4, thumbnail, and Markdown metadata file are a package for manual YouTube upload. The pipeline does not upload to YouTube or use the YouTube API.
