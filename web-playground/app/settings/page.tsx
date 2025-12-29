'use client';

import { useState, useEffect } from 'react';
import AuthRequired from '@/components/AuthRequired';
import { api } from '@/lib/api';
import Link from 'next/link';

export default function SettingsPage() {
  const [geminiApiKey, setGeminiApiKey] = useState('');
  const [elevenLabsApiKey, setElevenLabsApiKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [testingGemini, setTestingGemini] = useState(false);
  const [geminiTestResult, setGeminiTestResult] = useState<{success: boolean, message: string} | null>(null);

  useEffect(() => {
    loadKeys();
  }, []);

  const loadKeys = async () => {
    try {
      const data = await api.getApiKeys();
      setGeminiApiKey(data.gemini_api_key || '');
      setElevenLabsApiKey(data.elevenlabs_api_key || '');
    } catch (error) {
      console.error('Error loading API keys:', error);
    }
  };

  const testGeminiConnection = async () => {
    setTestingGemini(true);
    setGeminiTestResult(null);

    try {
      const result = await api.testGeminiConnection(geminiApiKey);
      setGeminiTestResult({
        success: true,
        message: `✓ Connection successful! Model: ${result.model || 'gemini-pro'}`
      });
    } catch (error: any) {
      setGeminiTestResult({
        success: false,
        message: `✗ Connection failed: ${error.message}`
      });
    } finally {
      setTestingGemini(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage('');

    try {
      await api.updateApiKeys({
        gemini_api_key: geminiApiKey || undefined,
        elevenlabs_api_key: elevenLabsApiKey || undefined,
      });
      setMessage('Settings saved successfully!');
    } catch (error: any) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <AuthRequired>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <Link href="/" className="text-sm text-gray-300 hover:text-white mb-2 inline-block">
            ← Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold text-white">Settings</h1>
          <p className="text-gray-300 mt-2">Configure API keys for multimodal features</p>
        </div>

        {message && (
          <div
            className={`mb-6 p-4 rounded-lg ${
              message.startsWith('Error')
                ? 'bg-red-900/30 text-red-300 border border-red-700'
                : 'bg-green-900/30 text-green-300 border border-green-700'
            }`}
          >
            {message}
          </div>
        )}

        <div className="space-y-6">
          {/* Image Generation - Google Gemini */}
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-white mb-4">
              🖼️ Image Generation (Google Gemini/Imagen)
            </h2>
            <p className="text-sm text-gray-300 mb-4">
              Uses Google's Gemini API for both text generation and image generation (Imagen).
              Configure your API key here or in the .env file.
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-200 mb-2">
                Google Gemini API Key
              </label>
              <input
                type="password"
                value={geminiApiKey}
                onChange={(e) => setGeminiApiKey(e.target.value)}
                placeholder="Enter your Google Gemini API key"
                className="input w-full"
              />
              <p className="text-xs text-gray-400 mt-1">
                Get a free API key at{' '}
                <a
                  href="https://makersuite.google.com/app/apikey"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-purple-400 hover:underline"
                >
                  Google AI Studio
                </a>
              </p>
              <button
                onClick={testGeminiConnection}
                disabled={!geminiApiKey || testingGemini}
                className="btn-ghost mt-3"
              >
                {testingGemini ? '🔄 Testing...' : '🔌 Test Connection'}
              </button>
              {geminiTestResult && (
                <div className={`mt-3 p-3 rounded-lg text-sm ${
                  geminiTestResult.success 
                    ? 'bg-green-900/30 text-green-300 border border-green-700'
                    : 'bg-red-900/30 text-red-300 border border-red-700'
                }`}>
                  {geminiTestResult.message}
                </div>
              )}
            </div>
          </div>

          {/* Voice Synthesis (Optional) */}
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-white mb-4">
              🔊 Advanced Voice (ElevenLabs) - Optional
            </h2>
            <p className="text-sm text-gray-300 mb-4">
              For premium voice quality, use ElevenLabs. Otherwise, the system uses browser-native TTS.
              Get your API key from{' '}
              <a
                href="https://elevenlabs.io/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-purple-400 hover:underline"
              >
                elevenlabs.io
              </a>
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-200 mb-2">
                ElevenLabs API Key (Optional)
              </label>
              <input
                type="password"
                value={elevenLabsApiKey}
                onChange={(e) => setElevenLabsApiKey(e.target.value)}
                placeholder="Enter your ElevenLabs API key (optional)"
                className="input w-full"
              />
              <p className="text-xs text-gray-400 mt-1">
                Leave empty to use browser's built-in text-to-speech
              </p>
            </div>
          </div>

          {/* Built-in Features */}
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-white mb-4">
              ✨ Built-in Features (No API Key Needed)
            </h2>
            <div className="space-y-3 text-sm">
              <div className="flex items-start gap-3">
                <span className="text-2xl">🎤</span>
                <div>
                  <div className="font-medium text-white">Voice Input</div>
                  <div className="text-gray-300">
                    Uses browser's Web Speech API or Groq Whisper for transcription
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-2xl">🔊</span>
                <div>
                  <div className="font-medium text-white">Voice Output</div>
                  <div className="text-gray-300">
                    Browser-native text-to-speech (upgradable with ElevenLabs)
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-2xl">📹</span>
                <div>
                  <div className="font-medium text-white">Video & Emotion Detection</div>
                  <div className="text-gray-300">
                    Uses webcam and Python packages for real-time emotion analysis
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end gap-3">
            <button onClick={loadKeys} className="btn-ghost">
              Reset
            </button>
            <button onClick={handleSave} disabled={saving} className="btn-primary">
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>

        {/* Info Box */}
        <div className="mt-8 bg-blue-900/20 border border-blue-700 rounded-lg p-4">
          <h3 className="font-medium text-blue-300 mb-2">💡 About Multimodal Features</h3>
          <p className="text-sm text-blue-200">
            Genesis Minds support multiple interaction modes to create a truly immersive experience:
          </p>
          <ul className="mt-2 text-sm text-blue-200 space-y-1 ml-4 list-disc">
            <li><strong>Voice:</strong> Speak naturally and hear Mind responses</li>
            <li><strong>Video:</strong> Your emotions are analyzed for better context</li>
            <li><strong>Images:</strong> Minds generate consistent avatars that express emotions</li>
            <li><strong>Files:</strong> Share documents and images with Minds</li>
          </ul>
        </div>
      </div>
    </AuthRequired>
  );
}
