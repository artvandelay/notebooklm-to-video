# Project: NotebookLM Audio to YouTube Video

## Objective
Automate the process of converting an audio recording from NotebookLM into a YouTube-ready video with AI-generated cover art and transcription.

## Core Components & Options

### 1. Audio Transcription
The first step is to transcribe the 5 to 50-minute audio files accurately and efficiently.

*   **Tool: Self-hosted `whisper.cpp`**
    *   **Location:** `~/LLM-apps/whisper.cpp`
    *   **Pros:** No per-use cost, full control over data privacy, highly performant C++ implementation.
    *   **Cons:** Requires initial setup and maintenance; performance is dependent on local hardware. We will interact with it as a command-line subprocess.

**Decision:** We will use your local, self-hosted **`whisper.cpp`** instance for transcription.

### 2. Cover Art Generation
Next, we need to generate compelling cover art based on the audio's content.

*   **Service: OpenRouter API**
    *   **Pros:** Access to a wide variety of image generation models from different providers through a single API, potentially lower costs, and flexibility to switch models easily. You have an existing API key.
    *   **Cons:** Requires selecting a specific model that supports image generation from the available options on OpenRouter.

**Decision:** We will use the **OpenRouter API** for image generation. We will make HTTP requests directly to their `/api/v1/chat/completions` endpoint as documented.

### 3. Video Creation
The final technical step is to combine the audio and the approved cover art into a video file.

*   **Tool: `ffmpeg`**
    *   **Pros:** The industry-standard, open-source tool for audio/video manipulation. It is powerful, flexible, and can be easily called from a script.
    *   **Cons:** It is a command-line tool, so it must be wrapped in our application code.

**Recommendation:** **`ffmpeg`** is the definitive choice for this task.

### 4. Workflow & User Interface
How will you interact with the tool to manage the process?

*   **Phase 1: Command-Line Interface (CLI)**
    *   **Pros:** Fastest to build, ideal for personal use and can be easily scripted.
    *   **Cons:** Not as user-friendly for the visual step of approving cover art.
*   **Phase 2: Gradio Web Interface**
    *   **Pros:** Provides a simple and fast way to build a web-based UI for ML apps, making the cover art approval seamless.
    *   **Cons:** Less customizable than a full web framework like Flask or FastAPI.

**Decision:** Start with a **CLI** for the MVP (Phase 1), then build a **Gradio Interface** in Phase 2 for a better user experience.

## Phased Development Plan

### Phase 1: Minimum Viable Product (CLI)
*Goal: Create a working command-line tool that handles the core conversion process.*
1.  **Project Setup:** Create the project structure, initialize a Python environment, and set up a `.env` file for API keys.
2.  **Transcription Module:** Implement a Python function to call the local `whisper.cpp` executable as a subprocess and save the transcript.
3.  **Cover Art Module:** Implement a function to generate an image with the OpenRouter API from a user-provided prompt.
4.  **Video Module:** Create a function that uses `ffmpeg` to merge the audio and the generated image into an MP4 file.
5.  **Main Script:** Write a script that orchestrates the workflow:
    *   Accepts an audio file path as input.
    *   Calls the transcription module.
    *   Asks the user for a text prompt for the cover art.
    *   Calls the cover art module and saves the image.
    *   Opens the image and asks the user for approval via the terminal.
    *   If approved, calls the video module to create the final MP4.

### Phase 2: Automation and Web Interface
*Goal: Make the tool more intelligent and user-friendly with a simple web UI.*
1.  **Automated Prompting:** Use a text-generation model (e.g., GPT-4o-mini via OpenRouter) to summarize the transcript and automatically create a high-quality prompt for the image generation model.
2.  **Gradio UI:** Build a simple Gradio interface to replace the CLI.
3.  **UI Workflow:**
    *   Allow a user to upload an audio file.
    *   Display the progress of the transcription and image generation.
    *   Show the generated cover art with "Approve" and "Retry" buttons.
    *   Provide a download link for the final video file.

### ✅ COMPLETED: Phase 1 MVP + Phase 2 Enhancements

**🎉 Successfully Delivered:**
- ✅ Complete audio-to-video workflow (transcription → cover art → video)
- ✅ Local whisper.cpp integration with optimized tiny.en model  
- ✅ Sophisticated AI-generated podcast album art via OpenRouter
- ✅ Customizable prompt system for artistic branding
- ✅ Comprehensive CLI tool with multiple options
- ✅ Smart transcription skipping when using existing cover art
- ✅ Production-ready codebase with full documentation
- ✅ GitHub-ready project structure

**🛠️ Current Tools:**
- `src/main.py` - Interactive workflow script  
- `create_video.py` - Comprehensive tool with advanced options
- Customizable prompts for consistent podcast branding
- Efficient processing (only transcribes when needed)

### Phase 3: Future Enhancements (Optional)
*Goal: Additional advanced features as needed.*
1.  **Background Jobs:** For very long audio files, implement background processing
2.  **YouTube Upload Integration:** Direct upload to YouTube channels  
3.  **Batch Processing:** Process multiple files automatically
4.  **Web Interface:** Browser-based UI for non-technical users
5.  **Deployment:** Docker containers and cloud deployment scripts
