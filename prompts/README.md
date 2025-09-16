# Prompts Configuration

This directory contains customizable prompts for different parts of the audio-to-video workflow.

## System Diagram

```
Audio File
    ↓
[Whisper Transcription]
    ↓
Transcript Text
    ↓
┌─────────────────────────────────────────────────────────────┐
│                 PROMPT SYSTEM                               │
│                                                             │
│  system_instructions.txt                                    │
│         ↓                                                   │
│  transcript_to_image_prompt.txt  ← Transcript Text          │
│         ↓                                                   │
│  image_aesthetic.txt                                        │
│         ↓                                                   │
│  Combined AI Prompt                                         │
└─────────────────────────────────────────────────────────────┘
    ↓
[OpenRouter API Call]
    ↓
Generated Cover Art
    ↓
[FFmpeg Video Creation]
    ↓
Final MP4 Video
```

### Prompt Flow:
1. **Audio** → **Transcript** (via whisper.cpp)
2. **system_instructions.txt** sets the AI's personality and behavior
3. **transcript_to_image_prompt.txt** analyzes the transcript content and creates a detailed visual concept
4. **image_aesthetic.txt** adds style requirements and visual guidelines
5. All prompts combine into a sophisticated image generation request
6. **OpenRouter API** generates cover art based on the combined prompt
7. **FFmpeg** combines audio + cover art → final video

## Files

### `image_aesthetic.txt`
Defines the visual style and aesthetic requirements for generated cover art.
- Controls: colors, style, typography, overall visual appeal
- Example: "Use vibrant colors, clean typography, modern design"

### `transcript_to_image_prompt.txt` 
Instructions for converting audio transcripts into detailed image generation prompts.
- Controls: how the AI interprets transcript content for visual representation
- Focus: themes, mood, visual metaphors, professional appearance

### `system_instructions.txt`
General system behavior and personality for the AI assistant.
- Controls: tone, helpfulness, focus areas
- Sets overall behavior for the workflow

## Customization

Edit any of these files to customize how your tool generates cover art:

1. **Quick style changes**: Edit `image_aesthetic.txt`
2. **Change how content is interpreted**: Edit `transcript_to_image_prompt.txt` 
3. **Adjust AI personality**: Edit `system_instructions.txt`

Changes take effect immediately on the next run - no restart required.

## Example Customizations

**For podcast style**: Add "podcast microphone, sound waves" to `image_aesthetic.txt`

**For tech content**: Add "futuristic, digital, technology themes" to `image_aesthetic.txt`

**For educational content**: Modify `transcript_to_image_prompt.txt` to emphasize learning and knowledge themes.
