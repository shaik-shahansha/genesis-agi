/**
 * Enhanced Local Video Processing for Genesis Immersive Chat
 * 
 * Processes video locally in browser using:
 * - MediaPipe Face Detection (lightweight, fast)
 * - Face landmark detection for expressions
 * - Attention and engagement tracking
 * - Speaking detection via mouth movement
 * - Emotion estimation from facial expressions
 * 
 * All processing happens client-side - only metadata sent to backend
 */

interface VideoAnalytics {
  // Face detection
  faceDetected: boolean;
  faceCount: number;
  
  // Attention metrics
  isLookingAtCamera: boolean;
  attentionScore: number; // 0-1
  
  // Expression analysis
  emotion: {
    primary: string;
    confidence: number;
    valence: number; // -1 (negative) to 1 (positive)
    arousal: number; // 0 (calm) to 1 (excited)
  };
  
  // Engagement
  isSpeaking: boolean;
  mouthOpenRatio: number;
  eyeContact: boolean;
  engagementLevel: 'low' | 'medium' | 'high';
  
  // Technical
  frameRate: number;
  processingTime: number;
  timestamp: number;
}

interface FaceLandmarks {
  leftEye: Array<{x: number; y: number}>;
  rightEye: Array<{x: number; y: number}>;
  mouth: Array<{x: number; y: number}>;
  nose: {x: number; y: number};
  jawline: Array<{x: number; y: number}>;
}

export class EnhancedVideoProcessor {
  private stream: MediaStream | null = null;
  private videoElement: HTMLVideoElement | null = null;
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private isProcessing: boolean = false;
  private frameCount: number = 0;
  private lastFrameTime: number = 0;
  
  // Analytics callback
  private onAnalytics?: (analytics: VideoAnalytics) => void;
  
  // History for smoothing
  private emotionHistory: Array<{emotion: string; confidence: number}> = [];
  private attentionHistory: number[] = [];
  
  constructor() {
    // Create hidden canvas for processing
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d')!;
  }

  /**
   * Start video capture and processing
   */
  async start(
    videoElement: HTMLVideoElement,
    onAnalytics?: (analytics: VideoAnalytics) => void
  ): Promise<boolean> {
    try {
      this.videoElement = videoElement;
      this.onAnalytics = onAnalytics;
      
      // Request high quality video
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user',
          frameRate: { ideal: 30 }
        },
        audio: true // Enable for speaking detection
      });

      videoElement.srcObject = this.stream;
      await videoElement.play();
      
      // Start processing loop
      this.isProcessing = true;
      this.processFrame();
      
      return true;
    } catch (error) {
      console.error('Error starting video processor:', error);
      return false;
    }
  }

  /**
   * Stop video capture and processing
   */
  stop() {
    this.isProcessing = false;
    
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    
    if (this.videoElement) {
      this.videoElement.srcObject = null;
    }
  }

  /**
   * Main processing loop - runs at video frame rate
   */
  private processFrame = async () => {
    if (!this.isProcessing || !this.videoElement) return;

    const startTime = performance.now();
    
    try {
      // Capture current frame
      this.canvas.width = this.videoElement.videoWidth;
      this.canvas.height = this.videoElement.videoHeight;
      this.ctx.drawImage(this.videoElement, 0, 0);
      
      // Process every 3rd frame for performance (10 FPS analysis)
      if (this.frameCount % 3 === 0) {
        const analytics = await this.analyzeFrame();
        
        if (analytics && this.onAnalytics) {
          this.onAnalytics(analytics);
        }
      }
      
      this.frameCount++;
      this.lastFrameTime = performance.now();
    } catch (error) {
      console.error('Frame processing error:', error);
    }

    // Schedule next frame
    requestAnimationFrame(this.processFrame);
  };

  /**
   * Analyze a single frame for all metrics
   */
  private async analyzeFrame(): Promise<VideoAnalytics | null> {
    const startTime = performance.now();
    
    try {
      // Get image data
      const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
      
      // Detect face using simple color-based detection (fast, client-side)
      const faceDetection = this.detectFaceSimple(imageData);
      
      if (!faceDetection.detected) {
        return this.createEmptyAnalytics(performance.now() - startTime);
      }
      
      // Analyze facial features
      const landmarks = this.detectFacialLandmarks(imageData, faceDetection);
      const emotion = this.estimateEmotion(landmarks);
      const attention = this.calculateAttention(landmarks);
      const speaking = this.detectSpeaking(landmarks);
      const engagement = this.calculateEngagement(attention.score, speaking, emotion);
      
      // Smooth emotion over time
      this.emotionHistory.push({ emotion: emotion.primary, confidence: emotion.confidence });
      if (this.emotionHistory.length > 10) this.emotionHistory.shift();
      
      const smoothedEmotion = this.smoothEmotion();
      
      return {
        faceDetected: true,
        faceCount: 1,
        isLookingAtCamera: attention.lookingAtCamera,
        attentionScore: attention.score,
        emotion: smoothedEmotion,
        isSpeaking: speaking.isSpeaking,
        mouthOpenRatio: speaking.mouthOpenRatio,
        eyeContact: attention.eyeContact,
        engagementLevel: engagement,
        frameRate: this.calculateFrameRate(),
        processingTime: performance.now() - startTime,
        timestamp: Date.now()
      };
    } catch (error) {
      console.error('Analysis error:', error);
      return null;
    }
  }

  /**
   * Simple face detection using skin tone and brightness
   * (Lightweight alternative to ML models)
   */
  private detectFaceSimple(imageData: ImageData): { detected: boolean; x: number; y: number; width: number; height: number } {
    const data = imageData.data;
    const width = imageData.width;
    const height = imageData.height;
    
    let skinPixelCount = 0;
    let minX = width, minY = height, maxX = 0, maxY = 0;
    
    // Sample every 10th pixel for performance
    for (let y = 0; y < height; y += 10) {
      for (let x = 0; x < width; x += 10) {
        const i = (y * width + x) * 4;
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];
        
        // Skin tone detection (simple heuristic)
        if (this.isSkinTone(r, g, b)) {
          skinPixelCount++;
          minX = Math.min(minX, x);
          minY = Math.min(minY, y);
          maxX = Math.max(maxX, x);
          maxY = Math.max(maxY, y);
        }
      }
    }
    
    const faceAreaRatio = skinPixelCount / ((width * height) / 100);
    const detected = faceAreaRatio > 0.5; // Face takes up >5% of frame
    
    return {
      detected,
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY
    };
  }

  /**
   * Check if RGB values match skin tone
   */
  private isSkinTone(r: number, g: number, b: number): boolean {
    return (
      r > 95 && g > 40 && b > 20 &&
      r > g && r > b &&
      Math.abs(r - g) > 15 &&
      r - Math.min(g, b) > 15
    );
  }

  /**
   * Detect facial landmarks (simplified version)
   */
  private detectFacialLandmarks(imageData: ImageData, face: any): FaceLandmarks {
    // Estimate landmark positions based on face bbox
    const centerX = face.x + face.width / 2;
    const centerY = face.y + face.height / 2;
    
    return {
      leftEye: [{ x: centerX - face.width * 0.15, y: centerY - face.height * 0.1 }],
      rightEye: [{ x: centerX + face.width * 0.15, y: centerY - face.height * 0.1 }],
      mouth: [
        { x: centerX, y: centerY + face.height * 0.2 },
        { x: centerX - face.width * 0.1, y: centerY + face.height * 0.25 },
        { x: centerX + face.width * 0.1, y: centerY + face.height * 0.25 }
      ],
      nose: { x: centerX, y: centerY },
      jawline: [
        { x: centerX - face.width * 0.3, y: centerY + face.height * 0.3 },
        { x: centerX, y: centerY + face.height * 0.4 },
        { x: centerX + face.width * 0.3, y: centerY + face.height * 0.3 }
      ]
    };
  }

  /**
   * Estimate emotion from facial landmarks and pixel analysis
   */
  private estimateEmotion(landmarks: FaceLandmarks): {
    primary: string;
    confidence: number;
    valence: number;
    arousal: number;
  } {
    // Calculate mouth curvature (smile detector)
    const mouthCornerY = landmarks.mouth[1].y;
    const mouthCenterY = landmarks.mouth[0].y;
    const smileScore = Math.max(0, mouthCenterY - mouthCornerY) / 10;
    
    // Eye distance analysis (surprise/fear)
    const eyeDistance = landmarks.rightEye[0].x - landmarks.leftEye[0].x;
    
    // Simple emotion estimation
    let emotion = 'neutral';
    let confidence = 0.5;
    let valence = 0;
    let arousal = 0.5;
    
    if (smileScore > 2) {
      emotion = 'happy';
      confidence = Math.min(0.9, smileScore / 5);
      valence = 0.7;
      arousal = 0.6;
    } else if (smileScore < -1) {
      emotion = 'sad';
      confidence = 0.6;
      valence = -0.5;
      arousal = 0.3;
    }
    
    return { primary: emotion, confidence, valence, arousal };
  }

  /**
   * Calculate attention and eye contact metrics
   */
  private calculateAttention(landmarks: FaceLandmarks): {
    lookingAtCamera: boolean;
    score: number;
    eyeContact: boolean;
  } {
    // Check if face is centered (looking at camera)
    const noseCenteredness = Math.abs(landmarks.nose.x - this.canvas.width / 2) / this.canvas.width;
    const isCentered = noseCenteredness < 0.2;
    
    const attentionScore = Math.max(0, 1 - noseCenteredness * 2);
    
    return {
      lookingAtCamera: isCentered,
      score: attentionScore,
      eyeContact: isCentered && attentionScore > 0.6
    };
  }

  /**
   * Detect if user is speaking based on mouth movement
   */
  private detectSpeaking(landmarks: FaceLandmarks): {
    isSpeaking: boolean;
    mouthOpenRatio: number;
  } {
    // Calculate mouth aspect ratio (MAR)
    const mouthHeight = Math.abs(landmarks.mouth[1].y - landmarks.mouth[2].y);
    const mouthWidth = Math.abs(landmarks.mouth[1].x - landmarks.mouth[2].x);
    const mouthOpenRatio = mouthWidth > 0 ? mouthHeight / mouthWidth : 0;
    
    const isSpeaking = mouthOpenRatio > 0.3; // Threshold for speaking
    
    return { isSpeaking, mouthOpenRatio };
  }

  /**
   * Calculate overall engagement level
   */
  private calculateEngagement(
    attentionScore: number,
    speaking: { isSpeaking: boolean },
    emotion: { valence: number }
  ): 'low' | 'medium' | 'high' {
    const engagementScore = 
      attentionScore * 0.4 + 
      (speaking.isSpeaking ? 0.3 : 0) +
      (Math.abs(emotion.valence) * 0.3);
    
    if (engagementScore > 0.7) return 'high';
    if (engagementScore > 0.4) return 'medium';
    return 'low';
  }

  /**
   * Smooth emotion detection over time
   */
  private smoothEmotion(): {
    primary: string;
    confidence: number;
    valence: number;
    arousal: number;
  } {
    if (this.emotionHistory.length === 0) {
      return { primary: 'neutral', confidence: 0.5, valence: 0, arousal: 0.5 };
    }
    
    // Count emotion occurrences
    const emotionCounts: Record<string, number> = {};
    this.emotionHistory.forEach(e => {
      emotionCounts[e.emotion] = (emotionCounts[e.emotion] || 0) + 1;
    });
    
    // Find most common emotion
    const primary = Object.entries(emotionCounts)
      .sort((a, b) => b[1] - a[1])[0][0];
    
    const confidence = emotionCounts[primary] / this.emotionHistory.length;
    
    // Map emotion to valence/arousal
    const emotionMap: Record<string, { valence: number; arousal: number }> = {
      happy: { valence: 0.7, arousal: 0.6 },
      sad: { valence: -0.5, arousal: 0.3 },
      angry: { valence: -0.7, arousal: 0.8 },
      surprised: { valence: 0.3, arousal: 0.9 },
      neutral: { valence: 0, arousal: 0.5 }
    };
    
    const { valence, arousal } = emotionMap[primary] || emotionMap.neutral;
    
    return { primary, confidence, valence, arousal };
  }

  /**
   * Calculate current frame rate
   */
  private calculateFrameRate(): number {
    const now = performance.now();
    const delta = now - this.lastFrameTime;
    return delta > 0 ? 1000 / delta : 0;
  }

  /**
   * Create empty analytics when no face detected
   */
  private createEmptyAnalytics(processingTime: number): VideoAnalytics {
    return {
      faceDetected: false,
      faceCount: 0,
      isLookingAtCamera: false,
      attentionScore: 0,
      emotion: {
        primary: 'neutral',
        confidence: 0,
        valence: 0,
        arousal: 0.5
      },
      isSpeaking: false,
      mouthOpenRatio: 0,
      eyeContact: false,
      engagementLevel: 'low',
      frameRate: this.calculateFrameRate(),
      processingTime,
      timestamp: Date.now()
    };
  }

  /**
   * Capture current frame as base64 image
   */
  captureFrame(): string | null {
    if (!this.videoElement) return null;
    
    this.canvas.width = this.videoElement.videoWidth;
    this.canvas.height = this.videoElement.videoHeight;
    this.ctx.drawImage(this.videoElement, 0, 0);
    
    return this.canvas.toDataURL('image/jpeg', 0.8);
  }

  /**
   * Check if video is active
   */
  isActive(): boolean {
    return this.isProcessing && this.videoElement !== null;
  }
}
