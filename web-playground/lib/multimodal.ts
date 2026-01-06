// Multimodal Utilities for Genesis Playground

// Web Speech API for voice recognition
export class VoiceInput {
  private recognition: any;
  private isListening = false;
  private onResult?: (text: string) => void;
  private onError?: (error: string) => void;

  constructor() {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.lang = 'en-US';

        this.recognition.onresult = (event: any) => {
          const transcript = event.results[0][0].transcript;
          this.onResult?.(transcript);
        };

        this.recognition.onerror = (event: any) => {
          this.onError?.(event.error);
          this.isListening = false;
        };

        this.recognition.onend = () => {
          this.isListening = false;
        };
      }
    }
  }

  start(onResult: (text: string) => void, onError?: (error: string) => void) {
    if (!this.recognition) {
      onError?.('Speech recognition not supported');
      return;
    }

    this.onResult = onResult;
    this.onError = onError;
    this.isListening = true;
    this.recognition.start();
  }

  stop() {
    if (this.recognition && this.isListening) {
      this.recognition.stop();
      this.isListening = false;
    }
  }

  isActive() {
    return this.isListening;
  }
}

// Pollinations.AI TTS for text-to-speech
export class VoiceOutput {
  private currentAudio: HTMLAudioElement | null = null;
  private selectedVoice: string = 'nova'; // Default to nova (female)
  private isSpeakingFlag: boolean = false;

  constructor() {
    // No initialization needed for Pollinations
  }

  async speak(text: string, options?: { voice?: string; speed?: number }) {
    try {
      // Cancel any ongoing speech
      this.stop();

      // Clean the text - remove markdown formatting that might cause issues
      const cleanText = text
        .replace(/\*\*/g, '') // Remove bold
        .replace(/\*/g, '')   // Remove italics
        .replace(/\[|\]/g, '') // Remove brackets
        .replace(/\n/g, ' ')   // Replace newlines with spaces
        .trim();

      const voice = options?.voice || this.selectedVoice;
      
      // Use a simpler, more reliable TTS approach
      // Try ResponsiveVoice as fallback if available
      if (typeof window !== 'undefined' && (window as any).responsiveVoice) {
        console.log('Using ResponsiveVoice for TTS:', cleanText.substring(0, 50));
        this.isSpeakingFlag = true;
        (window as any).responsiveVoice.speak(cleanText, voice, {
          onend: () => {
            this.isSpeakingFlag = false;
            console.log('Audio playback ended (ResponsiveVoice)');
          },
          onerror: (error: any) => {
            console.error('ResponsiveVoice error:', error);
            this.isSpeakingFlag = false;
          }
        });
        return;
      }

      // Fallback to Pollinations.AI TTS
      const encodedText = encodeURIComponent(cleanText);
      // Use a more reliable format
      const audioUrl = `https://text.pollinations.ai/${encodedText}?model=openai&voice=${voice}`;

      console.log('Playing audio:', { text: cleanText.substring(0, 50), voice, url: audioUrl });

      this.isSpeakingFlag = true;
      this.currentAudio = new Audio();
      
      // Set up error handling before setting src
      this.currentAudio.onerror = (error) => {
        console.error('Audio playback error:', error);
        this.isSpeakingFlag = false;
        this.currentAudio = null;
        
        // Try browser's built-in speech synthesis as last resort
        this.useBrowserTTS(cleanText);
      };

      // Handle playback end
      this.currentAudio.onended = () => {
        console.log('Audio playback ended');
        this.isSpeakingFlag = false;
        this.currentAudio = null;
      };

      // Ensure audio is NOT muted and volume is at 100%
      this.currentAudio.muted = false;
      this.currentAudio.volume = 1.0;
      this.currentAudio.src = audioUrl;

      // Load and play
      await this.currentAudio.play();
      console.log('Audio playback started');
    } catch (error) {
      console.error('Speech synthesis failed:', error);
      this.isSpeakingFlag = false;
      
      // Fallback to browser TTS
      this.useBrowserTTS(text);
    }
  }

  private useBrowserTTS(text: string) {
    console.log('Attempting browser built-in TTS as fallback...');
    try {
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.voice = speechSynthesis.getVoices().find(v => v.name.includes('Female')) || speechSynthesis.getVoices()[0];
        utterance.onend = () => {
          this.isSpeakingFlag = false;
          console.log('Browser TTS ended');
        };
        utterance.onerror = () => {
          this.isSpeakingFlag = false;
          console.log('Browser TTS failed');
        };
        this.isSpeakingFlag = true;
        speechSynthesis.speak(utterance);
        console.log('Browser TTS started');
      }
    } catch (err) {
      console.error('Browser TTS also failed:', err);
      this.isSpeakingFlag = false;
    }
  }

  stop() {
    // Stop audio element
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
    }
    
    // Stop browser TTS
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      speechSynthesis.cancel();
    }
    
    // Stop ResponsiveVoice if available
    if (typeof window !== 'undefined' && (window as any).responsiveVoice) {
      (window as any).responsiveVoice.cancel();
    }
    
    this.isSpeakingFlag = false;
  }

  isSpeaking() {
    return this.isSpeakingFlag;
  }

  getAvailableVoices() {
    // Pollinations.AI supported voices
    return [
      { name: 'alloy', label: 'Alloy (Neutral)' },
      { name: 'echo', label: 'Echo (Male)' },
      { name: 'fable', label: 'Fable (British Male)' },
      { name: 'onyx', label: 'Onyx (Deep Male)' },
      { name: 'nova', label: 'Nova (Female)' },
      { name: 'shimmer', label: 'Shimmer (Soft Female)' },
    ];
  }

  setVoice(voiceName: string) {
    const availableVoices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'];
    if (availableVoices.includes(voiceName)) {
      this.selectedVoice = voiceName;
    }
  }

  getSelectedVoice() {
    return this.selectedVoice;
  }
}

// Webcam utilities
export class WebcamCapture {
  private stream: MediaStream | null = null;
  private videoElement: HTMLVideoElement | null = null;

  async start(videoElement: HTMLVideoElement) {
    try {
      this.videoElement = videoElement;
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        },
        audio: false
      });

      videoElement.srcObject = this.stream;
      await videoElement.play();
      
      return true;
    } catch (error) {
      console.error('Error accessing webcam:', error);
      return false;
    }
  }

  stop() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    if (this.videoElement) {
      this.videoElement.srcObject = null;
    }
  }

  captureFrame(): string | null {
    if (!this.videoElement) return null;

    const canvas = document.createElement('canvas');
    canvas.width = this.videoElement.videoWidth;
    canvas.height = this.videoElement.videoHeight;
    const ctx = canvas.getContext('2d');
    
    if (ctx) {
      ctx.drawImage(this.videoElement, 0, 0);
      return canvas.toDataURL('image/jpeg', 0.8);
    }

    return null;
  }

  isActive() {
    return this.stream !== null && this.stream.active;
  }
}

// Audio recording for Groq Whisper transcription
export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private stream: MediaStream | null = null;

  async start() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(this.stream);
      this.audioChunks = [];

      this.mediaRecorder.ondataavailable = (event) => {
        this.audioChunks.push(event.data);
      };

      this.mediaRecorder.start();
      return true;
    } catch (error) {
      console.error('Error starting audio recording:', error);
      return false;
    }
  }

  async stop(): Promise<Blob | null> {
    return new Promise((resolve) => {
      if (!this.mediaRecorder) {
        resolve(null);
        return;
      }

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.cleanup();
        resolve(audioBlob);
      };

      this.mediaRecorder.stop();
    });
  }

  private cleanup() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.mediaRecorder = null;
    this.audioChunks = [];
  }

  isRecording() {
    return this.mediaRecorder?.state === 'recording';
  }
}

// Emotion detection placeholder (will be processed by backend)
export interface EmotionData {
  emotion: string;
  confidence: number;
  valence: number; // positive/negative
  arousal: number; // energy level
  facial_features?: {
    smile: number;
    eyebrows_raised: boolean;
    eyes_open: number;
  };
}

export interface UserContext {
  emotion?: EmotionData;
  tone?: string;
  energy_level?: number;
  engagement?: number;
  timestamp: string;
}
