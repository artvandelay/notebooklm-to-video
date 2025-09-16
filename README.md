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
# Main workflow script (interactive)
python3 src/main.py path/to/your/audio.file

# Comprehensive script with options
python3 create_video.py path/to/your/audio.file
```

#### Advanced Options
```bash
# Use existing cover art (skips transcription!)
python3 create_video.py audio.mp4 --cover-art my-art.png --auto-approve

# Custom AI prompt for cover art
python3 create_video.py audio.mp4 --prompt "Minimalist podcast art" --auto-approve

# Custom output path
python3 create_video.py audio.mp4 -o videos/episode-001.mp4

# Use existing transcript
python3 create_video.py audio.mp4 --skip-transcription
```

The tool will:
1. 📝 Transcribe your audio using whisper.cpp (only when needed)
2. 🎨 Generate artistic cover art based on content themes (or use provided art)
3. 🖼️ Show you the generated art for approval (unless auto-approved)
4. 🎬 Create a YouTube-ready MP4 video

## 📁 Project Structure

```
├── src/
│   ├── main.py              # Main orchestration script (interactive)
│   ├── transcribe.py        # Audio transcription with whisper.cpp
│   ├── cover_art.py         # AI cover art generation
│   ├── video.py            # Video creation with ffmpeg
│   └── prompt_loader.py    # Prompt management system
├── create_video.py          # Comprehensive video creator with options
├── prompts/
│   ├── image_aesthetic.txt          # Visual style guidelines
│   ├── transcript_to_image_prompt.txt   # Content analysis prompts
│   ├── system_instructions.txt      # AI behavior settings
│   └── README.md                   # Prompt customization guide
├── data/                   # Output directory for generated files
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

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
python3 src/main.py data/my-podcast-episode.m4a
```

### Expected Output
```
🎵 Processing: my-podcast-episode.m4a

📝 Step 1: Transcribing Audio
Audio conversion completed.
Starting transcription...
✅ Transcription saved: data/my-podcast-episode.txt

🎨 Step 2: Cover Art
Generated image prompt: Create sophisticated podcast album art...
Cover art successfully saved to: data/cover_art_1234567890.png

👀 Step 3: Review
🎨 Cover art: data/cover_art_1234567890.png
🎬 Output will be: data/my-podcast-episode_video.mp4
🤔 Proceed with video creation? (y/n): y

🎬 Step 4: Creating Video
Creating video... Output will be saved to data/my-podcast-episode_video.mp4
Video created successfully.

🎉 Success! Video created:
📁 Location: data/my-podcast-episode_video.mp4
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
