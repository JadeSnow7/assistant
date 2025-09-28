import axios, { AxiosInstance, AxiosResponse } from 'axios';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  metadata?: {
    model_used?: string;
    response_time?: number;
    cost?: number;
    plugins_used?: string[];
  };
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  metadata?: Record<string, any>;
}

export interface SystemStatus {
  cpu_usage: number;
  memory_usage: number;
  gpu_usage: number;
  active_sessions: number;
  total_requests: number;
  avg_response_time: number;
  components_health: Record<string, boolean>;
}

export interface Plugin {
  name: string;
  version: string;
  description: string;
  enabled: boolean;
  capabilities: string[];
  metadata?: Record<string, any>;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  stream?: boolean;
  model?: string;
  plugins?: string[];
}

export interface ChatResponse {
  content: string;
  session_id: string;
  model_used?: string;
  reasoning?: string;
  response_time?: number;
  cost?: number;
  plugins_used?: string[];
}

class APIClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor(baseURL: string = 'http://localhost:8000') {
    this.baseURL = baseURL;
    this.client = axios.create({
      baseURL: `${baseURL}/api/v1`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 请求拦截器
    this.client.interceptors.request.use(
      (config) => {
        // 添加认证token等
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // 响应拦截器
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error);
        return Promise.reject(error);
      }
    );
  }

  // 健康检查
  async healthCheck(): Promise<{ status: string; components?: Record<string, any> }> {
    try {
      const response = await axios.get(`${this.baseURL}/health`, { timeout: 5000 });
      return response.data;
    } catch (error) {
      return { 
        status: 'unhealthy', 
        error: error instanceof Error ? error.message : 'Unknown error' 
      };
    }
  }

  // 聊天相关
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post('/chat', request);
    return response.data;
  }

  async sendStreamMessage(
    request: ChatRequest,
    onChunk: (chunk: Partial<ChatResponse>) => void
  ): Promise<void> {
    const response = await fetch(`${this.baseURL}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    
    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              onChunk(data);
            } catch (e) {
              console.warn('Failed to parse chunk:', line);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  // 会话管理
  async getSessions(limit: number = 50): Promise<ChatSession[]> {
    const response = await this.client.get('/sessions', { params: { limit } });
    return response.data;
  }

  async createSession(title?: string): Promise<ChatSession> {
    const response = await this.client.post('/sessions', { title });
    return response.data;
  }

  async getSession(sessionId: string): Promise<ChatSession> {
    const response = await this.client.get(`/sessions/${sessionId}`);
    return response.data;
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.client.delete(`/sessions/${sessionId}`);
  }

  async getSessionHistory(sessionId: string, limit: number = 100): Promise<ChatMessage[]> {
    const response = await this.client.get(`/sessions/${sessionId}/history`, {
      params: { limit }
    });
    return response.data;
  }

  // 系统状态
  async getSystemStatus(): Promise<SystemStatus> {
    const response = await this.client.get('/system/status');
    return response.data;
  }

  // 插件管理
  async getPlugins(): Promise<Plugin[]> {
    const response = await this.client.get('/plugins');
    return response.data;
  }

  async getPlugin(pluginName: string): Promise<Plugin> {
    const response = await this.client.get(`/plugins/${pluginName}`);
    return response.data;
  }

  async executePlugin(
    pluginName: string, 
    command: string, 
    args?: Record<string, any>
  ): Promise<any> {
    const response = await this.client.post('/plugins/execute', {
      plugin: pluginName,
      command,
      args: args || {}
    });
    return response.data;
  }

  async enablePlugin(pluginName: string): Promise<void> {
    await this.client.post(`/plugins/${pluginName}/enable`);
  }

  async disablePlugin(pluginName: string): Promise<void> {
    await this.client.post(`/plugins/${pluginName}/disable`);
  }

  // WebSocket连接
  createWebSocket(sessionId?: string): WebSocket {
    const wsUrl = this.baseURL.replace('http', 'ws') + '/ws/chat';
    const url = sessionId ? `${wsUrl}?session_id=${sessionId}` : wsUrl;
    return new WebSocket(url);
  }

  // 更新基础URL
  updateBaseURL(newBaseURL: string): void {
    this.baseURL = newBaseURL;
    this.client.defaults.baseURL = `${newBaseURL}/api/v1`;
  }
}

// 创建单例实例
export const apiClient = new APIClient();

export default APIClient;