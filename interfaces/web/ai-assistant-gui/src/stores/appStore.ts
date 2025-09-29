import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AppState {
  // 主题设置
  isDarkMode: boolean;
  toggleDarkMode: () => void;
  
  // 连接状态
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  setConnectionStatus: (status: AppState['connectionStatus']) => void;
  
  // 当前会话
  currentSessionId: string | null;
  setCurrentSessionId: (sessionId: string | null) => void;
  
  // 系统设置
  apiBaseUrl: string;
  setApiBaseUrl: (url: string) => void;
  
  // UI状态
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  
  // 通知
  notifications: Array<{
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    title: string;
    message: string;
    timestamp: number;
  }>;
  addNotification: (notification: Omit<AppState['notifications'][0], 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // 主题设置
      isDarkMode: true,
      toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
      
      // 连接状态
      isConnected: false,
      connectionStatus: 'disconnected',
      setConnectionStatus: (status) => set({ 
        connectionStatus: status,
        isConnected: status === 'connected'
      }),
      
      // 当前会话
      currentSessionId: null,
      setCurrentSessionId: (sessionId) => set({ currentSessionId: sessionId }),
      
      // 系统设置
      apiBaseUrl: 'http://localhost:8000',
      setApiBaseUrl: (url) => set({ apiBaseUrl: url }),
      
      // UI状态
      sidebarCollapsed: false,
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      
      // 通知
      notifications: [],
      addNotification: (notification) => {
        const id = Date.now().toString();
        const timestamp = Date.now();
        set((state) => ({
          notifications: [...state.notifications, { ...notification, id, timestamp }]
        }));
        
        // 自动移除通知
        setTimeout(() => {
          set((state) => ({
            notifications: state.notifications.filter(n => n.id !== id)
          }));
        }, 5000);
      },
      removeNotification: (id) => set((state) => ({
        notifications: state.notifications.filter(n => n.id !== id)
      })),
    }),
    {
      name: 'ai-assistant-app-store',
      partialize: (state) => ({
        isDarkMode: state.isDarkMode,
        apiBaseUrl: state.apiBaseUrl,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
);