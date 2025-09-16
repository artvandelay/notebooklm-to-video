#!/bin/bash
set -e

echo "🎙️ NotebookLM to YouTube Video Converter Setup"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3 is installed
print_status "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8+ and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
print_status "Found Python $PYTHON_VERSION"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed. Please install pip and try again."
    exit 1
fi

# Install Python dependencies
print_status "Installing Python dependencies..."
pip3 install -r requirements.txt

# Check if FFmpeg is installed
print_status "Checking FFmpeg installation..."
if ! command -v ffmpeg &> /dev/null; then
    print_warning "FFmpeg is not installed."
    echo "Please install FFmpeg:"
    echo "  macOS: brew install ffmpeg"
    echo "  Ubuntu: sudo apt install ffmpeg"
    echo "  Windows: Download from https://ffmpeg.org/download.html"
    echo ""
else
    print_status "FFmpeg is installed"
fi

# Check whisper.cpp installation
WHISPER_PATH="$HOME/LLM-apps/whisper.cpp"
print_status "Checking whisper.cpp installation..."

if [ ! -d "$WHISPER_PATH" ]; then
    print_warning "whisper.cpp not found at $WHISPER_PATH"
    echo ""
    echo "Setting up whisper.cpp..."
    
    # Create directory
    mkdir -p "$HOME/LLM-apps"
    cd "$HOME/LLM-apps"
    
    # Clone whisper.cpp
    print_status "Cloning whisper.cpp..."
    git clone https://github.com/ggerganov/whisper.cpp.git
    cd whisper.cpp
    
    # Compile
    print_status "Compiling whisper.cpp..."
    make
    
    # Download model
    print_status "Downloading tiny.en model..."
    bash models/download-ggml-model.sh tiny.en
    
    print_status "whisper.cpp setup complete!"
else
    print_status "whisper.cpp found at $WHISPER_PATH"
    
    # Check if executable exists
    if [ ! -f "$WHISPER_PATH/build/bin/whisper-cli" ]; then
        print_warning "whisper-cli executable not found. Compiling..."
        cd "$WHISPER_PATH"
        make
    fi
    
    # Check if model exists
    if [ ! -f "$WHISPER_PATH/models/ggml-tiny.en.bin" ]; then
        print_warning "tiny.en model not found. Downloading..."
        cd "$WHISPER_PATH"
        bash models/download-ggml-model.sh tiny.en
    fi
fi

# Setup environment file
if [ ! -f ".env" ]; then
    print_status "Creating .env file..."
    cp .env.example .env
    print_warning "Please edit .env and add your OpenRouter API key"
    print_warning "Get your API key from: https://openrouter.ai/"
else
    print_status ".env file already exists"
fi

# Create data directory if it doesn't exist
mkdir -p data

print_status "Setup complete! 🎉"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your OpenRouter API key"
echo "2. Test the installation: python3 src/main.py --help"
echo "3. Process your first audio file: python3 src/main.py path/to/audio.file"
echo ""
echo "For troubleshooting, see: README.md"
