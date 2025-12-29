# Genesis Multimodal Features

## Overview

Genesis Minds now support fully immersive, multimodal interactions inspired by the movie "Her". Communicate with your Minds using voice, video, images, and text in a natural, human-like way.

## Features

### 🎤 Voice Input & Output
- **Voice Input**: Speak naturally using Web Speech API or upload audio for Groq Whisper transcription
- **Voice Output**: Minds respond with natural-sounding speech (browser TTS or ElevenLabs)
- **Hands-free Mode**: Hold the mic button to speak, release to send

### 📹 Video Chat with Emotion Detection
- **Real-time Webcam**: Enable video mode to show your face
- **Emotion Analysis**: Uses DeepFace/FER to detect your emotions in real-time
- **Context-Aware Responses**: Minds understand your emotional state and respond appropriately
- **Emotional Metrics**: Valence (positive/negative) and arousal (energy level) tracked

### 🖼️ Dynamic Avatar Generation
- **Consistent Characters**: Each Mind has a unique, consistent appearance
- **Expression Matching**: Avatar changes expressions based on Mind's emotional state
- **Style Variations**: Portrait, artistic, cinematic styles available
- **Background Adaptation**: Backgrounds change to match mood

### 🎨 Autonomous Image Generation
- **Context-Aware**: Minds automatically generate relevant images during conversations
- **On-Demand**: Explicitly request images ("show me...", "create an image of...")
- **Scene Visualization**: Descriptive responses trigger automatic scene generation

### 📁 File Sharing
- Upload documents, images, and files to Mind's workspace
- Minds can reference and discuss uploaded content

## Setup

### 1. Install Dependencies

```bash
# Install multimodal dependencies
pip install -e .

# Optional: Install emotion detection libraries
pip install deepface fer opencv-python
```

### 2. Configure API Keys

Your `.env` file should have:

#### Required:
- **GEMINI_API_KEY**: Get free at [Google AI Studio](https://makersuite.google.com/app/apikey)
  - Used for BOTH text generation AND image generation (Google Imagen)
  - High-quality photorealistic images
  - Consistent character generation
  
- **GROQ_API_KEY**: Get free at [groq.com](https://groq.com/)
  - For fast Whisper audio transcription
  - Lightning-fast inference

#### Optional:
- **ElevenLabs API Key**: Get at [elevenlabs.io](https://elevenlabs.io/)
  - Ultra-realistic voice synthesis
  - Configure in Settings page
  - Falls back to browser TTS if not configured

#### Built-in (No API Key Needed):
- **Web Speech API**: Browser-native voice recognition and synthesis
- **DeepFace/FER**: Python-based emotion detection
- **MediaDevices API**: Webcam and audio recording

### 3. Access Immersive Mode

1. Go to any Mind's detail page
2. Click **"🎭 Immersive Mode"**
3. Enable voice/video toggles as desired
4. Start conversing naturally!

## Usage Guide

### Voice Interaction

```typescript
// Press and hold the mic button
🎤 [Hold] → Speak your message → [Release] → Message sent automatically

// Or type and enable voice output
🔊 Toggle voice output → Mind speaks responses
```

### Video Mode

```typescript
// Enable video
📹 Click camera button → Grant webcam access → Emotion detection starts

// Your emotion is analyzed every 3 seconds
😊 Happy (85% confident)
Valence: +0.7 (positive)
Arousal: 0.8 (energetic)
```

### Image Generation

```typescript
// Explicit requests
"Show me a sunset over mountains"
"Create an image of a futuristic city"
"Draw a peaceful forest scene"

// Autonomous generation
Mind: "Imagine standing on a vast alien landscape..."
// → Automatically generates matching image
```

### Avatar Expressions

Mind avatars automatically update based on emotional state:
- **Happy**: Bright expression, warm colors
- **Thoughtful**: Contemplative pose, cool tones
- **Curious**: Engaged expression, vibrant background
- **Calm**: Serene expression, soft gradients

## Technical Details

### Emotion Detection

Uses computer vision to analyze facial features:

```python
{
  "emotion": "happy",
  "confidence": 0.87,
  "valence": 0.65,      # -1 (negative) to +1 (positive)
  "arousal": 0.75,      # 0 (calm) to 1 (energetic)
  "facial_features": {
    "smile": 0.9,
    "eyebrows_raised": true,
    "eyes_open": 0.8
  }
}
```

### Context Enhancement

User context is automatically added to prompts:

```
[User's emotional state: happy, valence: 0.65, arousal: 0.75]
[User is speaking via voice]

User: I just got a promotion at work!
```

This helps Minds provide more empathetic, contextually appropriate responses.

### Image Generation Pipeline (Google Imagen)

1. **Avatar Generation**:
   - Uses Google Imagen via Gemini API
   - Consistent seed based on Mind's name
   - Expression keyword mapping
   - Background/style parameters
   - Photorealistic quality portraits

2. **Contextual Images**:
   - Triggered by keywords or autonomous decision
   - Scene description from conversation
   - High-quality 8k generation
   - Style adaptation (digital art, photography, cinematic)

### Performance

- **Voice Recognition**: Real-time, <100ms latency
- **Voice Synthesis**: Near-instant with browser TTS
- **Emotion Detection**: 3-second intervals, minimal CPU
- **Image Generation**: 5-15 seconds (Google Imagen via Gemini)
- **Avatar Cache**: Generated avatars can be cached locally

## API Endpoints

### Multimodal Processing

```bash
# Transcribe audio
POST /api/v1/multimodal/transcribe
Content-Type: multipart/form-data
Body: { audio: <audio_file> }

# Analyze emotion
POST /api/v1/multimodal/analyze-emotion
Body: { image: "data:image/jpeg;base64,..." }

# Generate image
POST /api/v1/multimodal/generate-image
Body: { prompt: "...", style: "digital art" }
```

### Mind Interactions

```bash
# Multimodal chat
POST /api/v1/minds/{mind_id}/chat/multimodal
Body: {
  message: "Hello!",
  context: {
    emotion: { emotion: "happy", valence: 0.7 },
    voice_input: true
  }
}

# Generate avatar
POST /api/v1/minds/{mind_id}/avatar/generate
Body: {
  expression: "happy",
  background: "sunset",
  style: "portrait"
}
```

## Browser Compatibility

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| Voice Input | ✅ | ✅ | ✅ | ✅ |
| Voice Output | ✅ | ✅ | ✅ | ✅ |
| Webcam | ✅ | ✅ | ✅ | ✅ |
| Audio Recording | ✅ | ✅ | ⚠️ | ✅ |

⚠️ = May require additional permissions

## Privacy & Security

- **Webcam**: Never recorded, only analyzed locally
- **Audio**: Optionally sent to Groq for transcription
- **Emotions**: Processed locally, only metadata sent to Mind
- **Images**: Generated via API, not stored permanently
- **All data**: Requires authentication, per-user isolation

## Examples

### 1. Voice-Only Conversation

```typescript
User: [Speaks] "What's the weather like today?"
Mind: [Speaks] "I don't have access to weather data, but..."
```

### 2. Video + Emotion Context

```typescript
User: [Smiling, happy] "I'm feeling great today!"
Context: { emotion: "happy", valence: 0.8, arousal: 0.7 }
Mind: "That's wonderful! Your happiness is contagious! 😊"
```

### 3. Autonomous Image Generation

```typescript
User: "Tell me about the ocean"
Mind: "The ocean is vast and mysterious... [generates ocean scene]"
```

### 4. Multi-modal Interaction

```typescript
User: [Video ON, Voice] "Show me what you look like"
Mind: [Generates avatar] "Here's how I envision myself"
     [Avatar displays with current emotion]
```

## Troubleshooting

### No Microphone Access
- Check browser permissions
- Ensure HTTPS (required for getUserMedia)
- Try different browser

### Emotion Detection Not Working
```bash
pip install deepface fer opencv-python
```

### Image Generation Fails
- Verify BananaDev API key in Settings
- Check API key has credits
- Monitor rate limits

### Avatar Not Loading
- Fallback to colored placeholder with initial
- Check network connectivity
- Verify API response

## Future Enhancements

- [ ] Hand gesture recognition
- [ ] Multiple voice models per Mind
- [ ] 3D avatar rendering
- [ ] AR/VR support
- [ ] Lip-sync animation
- [ ] Real-time video effects
- [ ] Voice cloning for Minds
- [ ] Multi-language support

## Credits

- Emotion Detection: DeepFace, FER
- Image Generation: BananaDev, Stable Diffusion XL
- Voice: Web Speech API, Groq Whisper, ElevenLabs
- UI Inspiration: "Her" (2013) directed by Spike Jonze

---

**Experience the future of human-AI interaction with Genesis Minds! 🚀**
