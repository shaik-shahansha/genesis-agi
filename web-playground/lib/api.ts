/**
 * Genesis API Client - Complete API integration
 */

import { getFirebaseToken } from './firebase';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Request cache to deduplicate in-flight requests
interface CacheEntry {
  promise: Promise<any>;
  timestamp: number;
}

export class GenesisAPI {
  private baseURL: string;
  private token: string | null = null;
  private requestCache: Map<string, CacheEntry> = new Map();
  private readonly CACHE_TTL = 1000; // 1 second deduplication window

  constructor() {
    this.baseURL = API_URL;
    // Load token from localStorage if available (legacy support)
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('genesis_token');
    }
  }

  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('genesis_token', token);
    }
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('genesis_token');
      localStorage.removeItem('genesis_firebase_token');
    }
  }

  private async request(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<any> {
    // Only cache GET requests to avoid deduplicating mutations
    const shouldCache = !options.method || options.method === 'GET';
    const cacheKey = `${options.method || 'GET'}:${endpoint}`;

    // Check cache for in-flight requests
    if (shouldCache) {
      const cached = this.requestCache.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < this.CACHE_TTL) {
        return cached.promise;
      }
    }

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // Try to get Firebase token first, then fall back to legacy token
    const firebaseToken = await getFirebaseToken();
    const authToken = firebaseToken || this.token;
    
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }

    const requestPromise = (async () => {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `API Error: ${response.status}`);
      }

      return response.json();
    })();

    // Cache the promise
    if (shouldCache) {
      this.requestCache.set(cacheKey, {
        promise: requestPromise,
        timestamp: Date.now(),
      });

      // Clean up cache after request completes
      requestPromise.finally(() => {
        setTimeout(() => {
          const entry = this.requestCache.get(cacheKey);
          if (entry && Date.now() - entry.timestamp >= this.CACHE_TTL) {
            this.requestCache.delete(cacheKey);
          }
        }, this.CACHE_TTL);
      });
    }

    return requestPromise;
  }

  // ==================== Authentication ====================

  async login(username: string, password: string) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch(`${this.baseURL}/api/v1/auth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json();
    this.setToken(data.access_token);
    return data;
  }

  async getCurrentUser() {
    return this.request('/api/v1/auth/me');
  }

  logout() {
    this.clearToken();
  }

  isAuthenticated(): boolean {
    return this.token !== null;
  }

  // ==================== Minds ====================

  async getMinds() {
    return this.request('/api/v1/minds');
  }

  async getMind(mindId: string) {
    return this.request(`/api/v1/minds/${mindId}`);
  }

  async createMind(data: any) {
    return this.request('/api/v1/minds/create', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async chat(mindId: string, message: string) {
    return this.request(`/api/v1/minds/${mindId}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  }

  async chatWithUser(mindId: string, message: string, userEmail?: string) {
    return this.request(`/api/v1/minds/${mindId}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message, user_email: userEmail }),
    });
  }

  async chatWithEnvironment(mindId: string, message: string, userEmail?: string, environmentId?: string) {
    return this.request(`/api/v1/minds/${mindId}/chat`, {
      method: 'POST',
      body: JSON.stringify({ 
        message, 
        user_email: userEmail,
        environment_id: environmentId 
      }),
    });
  }

  async getMindMemories(mindId: string, limit = 50) {
    return this.request(`/api/v1/minds/${mindId}/memories?limit=${limit}`);
  }

  async getMindThoughts(mindId: string, limit = 10) {
    return this.request(`/api/v1/minds/${mindId}/thoughts?limit=${limit}`);
  }

  async generateThought(mindId: string) {
    return this.request(`/api/v1/minds/${mindId}/thought`, {
      method: 'POST',
    });
  }

  // ==================== Daemon Control ====================

  async getDaemonStatus(mindId: string) {
    return this.request(`/api/v1/minds/${mindId}/daemon/status`);
  }

  async startDaemon(mindId: string) {
    return this.request(`/api/v1/minds/${mindId}/daemon/start`, {
      method: 'POST',
    });
  }

  async stopDaemon(mindId: string) {
    return this.request(`/api/v1/minds/${mindId}/daemon/stop`, {
      method: 'POST',
    });
  }

  async deleteMind(mindId: string) {
    return this.request(`/api/v1/minds/${mindId}`, {
      method: 'DELETE',
    });
  }

  // ==================== Logs ====================

  async getMindLogs(mindId: string, limit = 100) {
    return this.request(`/api/v1/minds/${mindId}/logs?limit=${limit}`);
  }

  async clearMindLogs(mindId: string) {
    return this.request(`/api/v1/minds/${mindId}/logs`, {
      method: 'DELETE',
    });
  }

  // ==================== Multimodal ====================

  async transcribeAudio(audioBlob: Blob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'audio.webm');

    const headers: HeadersInit = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseURL}/api/v1/multimodal/transcribe`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || 'Transcription failed');
    }

    return response.json();
  }

  async analyzeEmotion(imageData: string) {
    return this.request('/api/v1/multimodal/analyze-emotion', {
      method: 'POST',
      body: JSON.stringify({ image: imageData }),
    });
  }

  async generateMindAvatar(mindId: string, params: {
    expression?: string;
    background?: string;
    style?: string;
  }) {
    return this.request(`/api/v1/minds/${mindId}/avatar/generate`, {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async generateImage(prompt: string, style?: string) {
    return this.request('/api/v1/multimodal/generate-image', {
      method: 'POST',
      body: JSON.stringify({ prompt, style }),
    });
  }

  async chatWithContext(mindId: string, message: string, context?: {
    emotion?: any;
    tone?: string;
    voice_input?: boolean;
    video_context?: any;
  }) {
    return this.request(`/api/v1/minds/${mindId}/chat/multimodal`, {
      method: 'POST',
      body: JSON.stringify({ message, context }),
    });
  }

  // ==================== Settings ====================

  async updateApiKeys(keys: {
    gemini_api_key?: string;
    elevenlabs_api_key?: string;
  }) {
    return this.request('/api/v1/settings/api-keys', {
      method: 'POST',
      body: JSON.stringify(keys),
    });
  }

  async testGeminiConnection(apiKey: string) {
    return this.request('/api/v1/settings/test-gemini', {
      method: 'POST',
      body: JSON.stringify({ api_key: apiKey }),
    });
  }

  async updateMindSettings(mindId: string, settings: any) {
    return this.request(`/api/v1/minds/${mindId}/settings`, {
      method: 'PATCH',
      body: JSON.stringify(settings),
    });
  }

  async getApiKeys() {
    return this.request('/api/v1/settings/api-keys');
  }

  // ==================== Marketplace ====================

  async getMarketplaceListings(params: {
    query?: string;
    item_type?: string;
    category?: string;
    tags?: string;
    min_price?: number;
    max_price?: number;
    min_rating?: number;
    sort_by?: string;
    order?: string;
    limit?: number;
    offset?: number;
  } = {}) {
    const queryString = new URLSearchParams(
      Object.entries(params)
        .filter(([_, v]) => v !== undefined)
        .map(([k, v]) => [k, String(v)])
    ).toString();

    return this.request(`/api/v1/marketplace/listings?${queryString}`);
  }

  async getListing(listingId: string) {
    return this.request(`/api/v1/marketplace/listings/${listingId}`);
  }

  async getTrending(itemType?: string, limit = 10) {
    const query = itemType ? `?item_type=${itemType}&limit=${limit}` : `?limit=${limit}`;
    return this.request(`/api/v1/marketplace/trending${query}`);
  }

  async getFeatured(limit = 10) {
    return this.request(`/api/v1/marketplace/featured?limit=${limit}`);
  }

  async purchaseItem(listingId: string, targetMindId?: string) {
    return this.request('/api/v1/marketplace/purchase', {
      method: 'POST',
      body: JSON.stringify({ listing_id: listingId, target_mind_id: targetMindId }),
    });
  }

  async getMyPurchases() {
    return this.request('/api/v1/marketplace/my-purchases');
  }

  async getMyListings() {
    return this.request('/api/v1/marketplace/my-listings');
  }

  async createListing(data: any) {
    return this.request('/api/v1/marketplace/listings', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async addReview(transactionId: string, rating: number, comment?: string) {
    return this.request('/api/v1/marketplace/reviews', {
      method: 'POST',
      body: JSON.stringify({ transaction_id: transactionId, rating, comment }),
    });
  }

  async getListingReviews(listingId: string, limit = 50) {
    return this.request(`/api/v1/marketplace/listings/${listingId}/reviews?limit=${limit}`);
  }

  async addFavorite(listingId: string) {
    return this.request(`/api/v1/marketplace/favorites/${listingId}`, {
      method: 'POST',
    });
  }

  async removeFavorite(listingId: string) {
    return this.request(`/api/v1/marketplace/favorites/${listingId}`, {
      method: 'DELETE',
    });
  }

  async getFavorites() {
    return this.request('/api/v1/marketplace/favorites');
  }

  async getMarketplaceStats() {
    return this.request('/api/v1/marketplace/stats');
  }

  // ==================== Environments ====================

  async getEnvironments(params: {
    is_public?: boolean;
    env_type?: string;
    limit?: number;
    offset?: number;
  } = {}) {
    const queryString = new URLSearchParams(
      Object.entries(params)
        .filter(([_, v]) => v !== undefined)
        .map(([k, v]) => [k, String(v)])
    ).toString();

    return this.request(`/api/v1/environments/list?${queryString}`);
  }

  async getEnvironment(envId: string) {
    return this.request(`/api/v1/environments/${envId}`);
  }

  async createEnvironment(data: {
    name: string;
    env_type?: string;
    description?: string;
    is_public?: boolean;
    max_occupancy?: number;
    template?: string;
  }) {
    return this.request('/api/v1/environments/create', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateEnvironment(envId: string, data: any) {
    return this.request(`/api/v1/environments/${envId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteEnvironment(envId: string) {
    return this.request(`/api/v1/environments/${envId}`, {
      method: 'DELETE',
    });
  }

  async getEnvironmentTemplates() {
    return this.request('/api/v1/environments/templates/list');
  }

  async getTemplate(templateName: string) {
    return this.request(`/api/v1/environments/templates/${templateName}`);
  }

  async getActiveEnvironments() {
    return this.request('/api/v1/environments/active');
  }

  async getAccessibleEnvironments(userEmail: string, mindGmid?: string) {
    const params = mindGmid 
      ? `?user_email=${encodeURIComponent(userEmail)}&mind_gmid=${encodeURIComponent(mindGmid)}`
      : `?user_email=${encodeURIComponent(userEmail)}`;
    return this.request(`/api/v1/environments/accessible${params}`);
  }

  async addUserToEnvironment(envId: string, userEmail: string) {
    return this.request(`/api/v1/environments/${envId}/add-user?user_email=${encodeURIComponent(userEmail)}`, {
      method: 'POST',
    });
  }

  async removeUserFromEnvironment(envId: string, userEmail: string) {
    return this.request(`/api/v1/environments/${envId}/remove-user?user_email=${encodeURIComponent(userEmail)}`, {
      method: 'DELETE',
    });
  }

  async addMindToEnvironment(envId: string, mindGmid: string) {
    return this.request(`/api/v1/environments/${envId}/add-mind?mind_gmid=${encodeURIComponent(mindGmid)}`, {
      method: 'POST',
    });
  }

  async removeMindFromEnvironment(envId: string, mindGmid: string) {
    return this.request(`/api/v1/environments/${envId}/remove-mind?mind_gmid=${encodeURIComponent(mindGmid)}`, {
      method: 'DELETE',
    });
  }

  // ==================== WebSocket ====================

  createEnvironmentWebSocket(
    envId: string,
    mindId: string,
    mindName: string
  ): WebSocket {
    const wsURL = this.baseURL.replace('http', 'ws');
    return new WebSocket(
      `${wsURL}/api/v1/environments/ws/${envId}?mind_id=${mindId}&mind_name=${mindName}`
    );
  }

  // ==================== Metaverse ====================

  async getMetaverseStats() {
    return this.request('/api/v1/metaverse/stats');
  }

  async searchMinds(query?: string, limit = 20) {
    const params = query ? `?query=${query}&limit=${limit}` : `?limit=${limit}`;
    return this.request(`/api/v1/metaverse/search${params}`);
  }

  // ==================== Autonomy ====================

  async getAutonomousActions(mindId: string, limit = 20) {
    return this.request(`/api/v1/minds/${mindId}/autonomous-actions?limit=${limit}`);
  }

  // ==================== LLM Calls ====================

  async getLLMCalls(mindId: string, limit = 50) {
    return this.request(`/api/v1/minds/${mindId}/llm-calls?limit=${limit}`);
  }

  // ==================== Plugins ====================

  async getPlugins(mindId: string) {
    return this.request(`/api/v1/minds/${mindId}/plugins`);
  }

  async addPlugin(mindId: string, pluginName: string, config?: any) {
    return this.request(`/api/v1/minds/${mindId}/plugins`, {
      method: 'POST',
      body: JSON.stringify({ plugin_name: pluginName, config }),
    });
  }

  async removePlugin(mindId: string, pluginName: string) {
    return this.request(`/api/v1/minds/${mindId}/plugins/${pluginName}`, {
      method: 'DELETE',
    });
  }

  async enablePlugin(mindId: string, pluginName: string) {
    return this.request(`/api/v1/minds/${mindId}/plugins/${pluginName}/enable`, {
      method: 'POST',
    });
  }

  async disablePlugin(mindId: string, pluginName: string) {
    return this.request(`/api/v1/minds/${mindId}/plugins/${pluginName}/disable`, {
      method: 'POST',
    });
  }

  // ==================== Workspace ====================

  async uploadFile(mindId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);

    const headers: HeadersInit = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseURL}/api/v1/minds/${mindId}/workspace/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `File upload failed: ${response.status}`);
    }

    return response.json();
  }

  async getWorkspaceFiles(mindId: string) {
    return this.request(`/api/v1/minds/${mindId}/workspace/files`);
  }

  async getWorkspaceFile(mindId: string, fileId: string) {
    return this.request(`/api/v1/minds/${mindId}/workspace/files/${fileId}`);
  }

  async deleteWorkspaceFile(mindId: string, fileId: string) {
    return this.request(`/api/v1/minds/${mindId}/workspace/files/${fileId}`, {
      method: 'DELETE',
    });
  }

  async searchWorkspaceFiles(mindId: string, query: string) {
    return this.request(`/api/v1/minds/${mindId}/workspace/search?query=${encodeURIComponent(query)}`);
  }

  // ==================== Feedback ====================

  async submitFeedback(
    mindId: string,
    feedbackType: 'positive' | 'negative',
    message?: string,
    context?: string
  ) {
    return this.request(`/api/v1/minds/${mindId}/feedback`, {
      method: 'POST',
      body: JSON.stringify({
        feedback_type: feedbackType,
        message,
        context,
      }),
    });
  }
}

// Export singleton instance
export const api = new GenesisAPI();
