/**
 * WebSocket Manager for real-time environment interaction
 */

export type EnvironmentMessage =
  | { type: 'welcome'; environment: any; message: string }
  | { type: 'mind_joined'; mind_id: string; mind_name: string; present_minds: string[]; count: number; timestamp: string }
  | { type: 'mind_left'; mind_id: string; mind_name: string; present_minds: string[]; count: number; timestamp: string }
  | { type: 'chat_message'; from_mind_id: string; from_mind_name: string; content: string; emotion?: string; timestamp: string }
  | { type: 'object_updated'; object_id: string; data: any; updated_by: string; timestamp: string }
  | { type: 'variable_set'; name: string; value: any; set_by: string; timestamp: string }
  | { type: 'state_update'; state: any }
  | { type: 'typing'; mind_id: string; mind_name: string; is_typing: boolean };

export interface EnvironmentWebSocketOptions {
  onMessage?: (message: EnvironmentMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

export class EnvironmentWebSocket {
  private ws: WebSocket | null = null;
  private options: EnvironmentWebSocketOptions;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(
    private envId: string,
    private mindId: string,
    private mindName: string,
    options: EnvironmentWebSocketOptions = {}
  ) {
    this.options = options;
  }

  connect() {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const wsURL = API_URL.replace('http', 'ws');
    const url = `${wsURL}/api/v1/environments/ws/${this.envId}?mind_id=${this.mindId}&mind_name=${encodeURIComponent(this.mindName)}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.options.onConnect?.();
    };

    this.ws.onmessage = (event) => {
      try {
        const message: EnvironmentMessage = JSON.parse(event.data);
        this.options.onMessage?.(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.options.onError?.(error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.options.onDisconnect?.();

      // Attempt to reconnect
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        setTimeout(() => {
          console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
          this.connect();
        }, this.reconnectDelay * this.reconnectAttempts);
      }
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  sendChat(content: string, emotion?: string) {
    this.send({
      type: 'chat',
      content,
      emotion,
    });
  }

  updateObject(objectId: string, data: any) {
    this.send({
      type: 'action',
      action: 'update_object',
      data: {
        object_id: objectId,
        data,
      },
    });
  }

  setVariable(name: string, value: any) {
    this.send({
      type: 'action',
      action: 'set_variable',
      data: {
        name,
        value,
      },
    });
  }

  requestState() {
    this.send({
      type: 'request_state',
    });
  }

  setTyping(isTyping: boolean) {
    this.send({
      type: 'typing',
      is_typing: isTyping,
    });
  }

  private send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket not connected');
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
