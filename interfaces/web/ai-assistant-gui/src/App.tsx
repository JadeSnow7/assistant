import React from 'react';
import { ConfigProvider, Layout, theme, Space } from 'antd';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import Plugins from './pages/Plugins';
import SystemMonitor from './pages/SystemMonitor';
import Settings from './pages/Settings';
import { useAppStore } from './stores/appStore';
import logoImg from './assets/logo.png';
import './App.css';

const { Header, Content } = Layout;

const App: React.FC = () => {
  const { isDarkMode, sidebarCollapsed } = useAppStore();
  
  return (
    <ConfigProvider
      theme={{
        algorithm: isDarkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 8,
        },
      }}
    >
      <Router>
        <Layout style={{ minHeight: '100vh' }}>
          <Sidebar />
          <Layout style={{ marginLeft: sidebarCollapsed ? 80 : 250, transition: 'margin-left 0.2s' }}>
            <Header 
              style={{ 
                padding: '0 24px', 
                background: isDarkMode ? '#141414' : '#fff',
                borderBottom: `1px solid ${isDarkMode ? '#303030' : '#f0f0f0'}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}
            >
              <Space align="center">
                <img 
                  src={logoImg} 
                  alt="HuShell Logo" 
                  style={{ height: '32px', width: '32px' }}
                />
                <span style={{ 
                  margin: 0, 
                  color: isDarkMode ? '#fff' : '#000',
                  fontSize: '20px',
                  fontWeight: 600
                }}>
                  HuShell | 互协AI
                </span>
              </Space>
            </Header>
            <Content style={{ 
              margin: '24px',
              background: isDarkMode ? '#000' : '#fff',
              borderRadius: 8,
              overflow: 'auto'
            }}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/chat" element={<Chat />} />
                <Route path="/chat/:sessionId" element={<Chat />} />
                <Route path="/plugins" element={<Plugins />} />
                <Route path="/monitor" element={<SystemMonitor />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </Content>
          </Layout>
        </Layout>
      </Router>
    </ConfigProvider>
  );
};

export default App;
