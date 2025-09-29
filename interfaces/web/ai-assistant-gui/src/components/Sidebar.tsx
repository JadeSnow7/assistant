import React from 'react';
import { Layout, Menu, Switch, Tooltip, Button } from 'antd';
import { 
  HomeOutlined, 
  MessageOutlined, 
  AppstoreOutlined, 
  MonitorOutlined,
  SettingOutlined,
  BulbOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlusOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAppStore } from '../stores/appStore';
import { apiClient } from '../services/apiClient';

const { Sider } = Layout;

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { 
    isDarkMode, 
    toggleDarkMode, 
    sidebarCollapsed, 
    setSidebarCollapsed,
    addNotification,
    setCurrentSessionId
  } = useAppStore();

  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '仪表板',
    },
    {
      key: '/chat',
      icon: <MessageOutlined />,
      label: '对话',
    },
    {
      key: '/plugins',
      icon: <AppstoreOutlined />,
      label: '插件',
    },
    {
      key: '/monitor',
      icon: <MonitorOutlined />,
      label: '系统监控',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  const handleNewChat = async () => {
    try {
      const session = await apiClient.createSession();
      setCurrentSessionId(session.id);
      navigate(`/chat/${session.id}`);
      addNotification({
        type: 'success',
        title: '新建对话',
        message: '已创建新的对话会话'
      });
    } catch (error) {
      addNotification({
        type: 'error',
        title: '创建失败',
        message: '无法创建新的对话会话，请检查网络连接'
      });
    }
  };

  return (
    <Sider 
      collapsed={sidebarCollapsed}
      onCollapse={setSidebarCollapsed}
      theme={isDarkMode ? 'dark' : 'light'}
      width={250}
      style={{
        overflow: 'auto',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
      }}
    >
      {/* Logo区域 */}
      <div style={{ 
        height: 64, 
        margin: 16, 
        display: 'flex', 
        alignItems: 'center',
        justifyContent: sidebarCollapsed ? 'center' : 'flex-start'
      }}>
        {!sidebarCollapsed && (
          <span style={{ 
            color: isDarkMode ? '#fff' : '#000',
            fontSize: '18px',
            fontWeight: 'bold'
          }}>
            🤖 AI Assistant
          </span>
        )}
        {sidebarCollapsed && (
          <span style={{ fontSize: '24px' }}>🤖</span>
        )}
      </div>

      {/* 新建对话按钮 */}
      <div style={{ padding: '0 16px', marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          block
          onClick={handleNewChat}
          style={{ 
            height: 40,
            borderRadius: 8,
          }}
        >
          {!sidebarCollapsed && '新建对话'}
        </Button>
      </div>

      {/* 导航菜单 */}
      <Menu
        theme={isDarkMode ? 'dark' : 'light'}
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={handleMenuClick}
        style={{ borderRight: 0 }}
      />

      {/* 底部控制区域 */}
      <div style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        padding: 16,
        borderTop: `1px solid ${isDarkMode ? '#303030' : '#f0f0f0'}`,
      }}>
        {/* 主题切换 */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: sidebarCollapsed ? 'center' : 'space-between',
          marginBottom: 16
        }}>
          {!sidebarCollapsed && (
            <span style={{ 
              color: isDarkMode ? '#fff' : '#000',
              fontSize: '14px'
            }}>
              <BulbOutlined style={{ marginRight: 8 }} />
              深色模式
            </span>
          )}
          <Tooltip title={sidebarCollapsed ? (isDarkMode ? '切换到浅色模式' : '切换到深色模式') : ''}>
            <Switch
              checked={isDarkMode}
              onChange={toggleDarkMode}
              size={sidebarCollapsed ? 'default' : 'small'}
            />
          </Tooltip>
        </div>

        {/* 折叠按钮 */}
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <Tooltip title={sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'}>
            <Button
              type="text"
              icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              style={{
                color: isDarkMode ? '#fff' : '#000'
              }}
            />
          </Tooltip>
        </div>
      </div>
    </Sider>
  );
};

export default Sidebar;