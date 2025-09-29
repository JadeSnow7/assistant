import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Progress, Button, Typography, Space, Badge } from 'antd';
import { 
  MessageOutlined, 
  RobotOutlined, 
  ThunderboltOutlined,
  AppstoreOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  PlayCircleOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../stores/appStore';
import { apiClient, type SystemStatus } from '../services/apiClient';

const { Title, Text, Paragraph } = Typography;

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { isDarkMode, addNotification, setCurrentSessionId } = useAppStore();
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSystemStatus();
    // 每30秒刷新一次状态
    const interval = setInterval(loadSystemStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadSystemStatus = async () => {
    try {
      const status = await apiClient.getSystemStatus();
      setSystemStatus(status);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load system status:', error);
      setLoading(false);
      addNotification({
        type: 'warning',
        title: '状态获取失败',
        message: '无法获取系统状态，可能服务未启动'
      });
    }
  };

  const handleQuickStart = async (action: string) => {
    switch (action) {
      case 'newChat':
        try {
          const session = await apiClient.createSession();
          setCurrentSessionId(session.id);
          navigate(`/chat/${session.id}`);
        } catch (error) {
          addNotification({
            type: 'error',
            title: '创建失败',
            message: '无法创建新对话'
          });
        }
        break;
      case 'plugins':
        navigate('/plugins');
        break;
      case 'monitor':
        navigate('/monitor');
        break;
      default:
        break;
    }
  };

  const getStatusColor = (usage: number) => {
    if (usage < 50) return '#52c41a';
    if (usage < 80) return '#faad14';
    return '#ff4d4f';
  };

  const getHealthStatus = (healthy: boolean) => {
    return healthy ? 'success' : 'error';
  };

  return (
    <div style={{ padding: 24 }}>
      {/* 欢迎标题 */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0, color: isDarkMode ? '#fff' : '#000' }}>
          👋 欢迎使用 AI Assistant
        </Title>
        <Paragraph style={{ color: isDarkMode ? '#a0a0a0' : '#666', marginTop: 8 }}>
          您的智能助手已准备就绪，开始您的AI之旅吧！
        </Paragraph>
      </div>

      {/* 系统状态卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="CPU使用率"
              value={systemStatus?.cpu_usage || 0}
              precision={1}
              suffix="%"
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: getStatusColor(systemStatus?.cpu_usage || 0) }}
            />
            <Progress 
              percent={systemStatus?.cpu_usage || 0} 
              strokeColor={getStatusColor(systemStatus?.cpu_usage || 0)}
              showInfo={false} 
              size="small"
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="内存使用率"
              value={systemStatus?.memory_usage || 0}
              precision={1}
              suffix="%"
              prefix={<RobotOutlined />}
              valueStyle={{ color: getStatusColor(systemStatus?.memory_usage || 0) }}
            />
            <Progress 
              percent={systemStatus?.memory_usage || 0} 
              strokeColor={getStatusColor(systemStatus?.memory_usage || 0)}
              showInfo={false} 
              size="small"
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活跃会话"
              value={systemStatus?.active_sessions || 0}
              prefix={<MessageOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总请求数"
              value={systemStatus?.total_requests || 0}
              prefix={<ArrowUpOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 快速开始 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={16}>
          <Card title="🚀 快速开始" loading={loading}>
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={8}>
                <Card 
                  hoverable
                  style={{ textAlign: 'center', cursor: 'pointer' }}
                  bodyStyle={{ padding: 24 }}
                  onClick={() => handleQuickStart('newChat')}
                >
                  <MessageOutlined style={{ fontSize: 32, color: '#1890ff', marginBottom: 16 }} />
                  <Title level={4} style={{ margin: 0 }}>开始对话</Title>
                  <Text type="secondary">与AI助手开始新的对话</Text>
                </Card>
              </Col>
              
              <Col xs={24} sm={8}>
                <Card 
                  hoverable
                  style={{ textAlign: 'center', cursor: 'pointer' }}
                  bodyStyle={{ padding: 24 }}
                  onClick={() => handleQuickStart('plugins')}
                >
                  <AppstoreOutlined style={{ fontSize: 32, color: '#52c41a', marginBottom: 16 }} />
                  <Title level={4} style={{ margin: 0 }}>管理插件</Title>
                  <Text type="secondary">查看和管理AI插件</Text>
                </Card>
              </Col>
              
              <Col xs={24} sm={8}>
                <Card 
                  hoverable
                  style={{ textAlign: 'center', cursor: 'pointer' }}
                  bodyStyle={{ padding: 24 }}
                  onClick={() => handleQuickStart('monitor')}
                >
                  <ThunderboltOutlined style={{ fontSize: 32, color: '#faad14', marginBottom: 16 }} />
                  <Title level={4} style={{ margin: 0 }}>系统监控</Title>
                  <Text type="secondary">查看系统运行状态</Text>
                </Card>
              </Col>
            </Row>
          </Card>
        </Col>
        
        <Col xs={24} lg={8}>
          <Card title="🔧 系统组件" loading={loading}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {systemStatus?.components_health && Object.entries(systemStatus.components_health).map(([component, healthy]) => (
                <div key={component} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  padding: '8px 0'
                }}>
                  <Text>{component}</Text>
                  <Badge 
                    status={getHealthStatus(healthy)} 
                    text={healthy ? '正常' : '异常'}
                  />
                </div>
              ))}
              
              {(!systemStatus?.components_health || Object.keys(systemStatus.components_health).length === 0) && (
                <Text type="secondary" style={{ textAlign: 'center', display: 'block', padding: 20 }}>
                  暂无组件状态信息
                </Text>
              )}
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 性能统计 */}
      <Row gutter={[16, 16]}>
        <Col xs={24}>
          <Card title="📊 性能统计" loading={loading}>
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={8}>
                <Statistic
                  title="平均响应时间"
                  value={systemStatus?.avg_response_time || 0}
                  precision={1}
                  suffix="ms"
                  prefix={<PlayCircleOutlined />}
                  valueStyle={{ 
                    color: (systemStatus?.avg_response_time || 0) < 1000 ? '#52c41a' : 
                           (systemStatus?.avg_response_time || 0) < 3000 ? '#faad14' : '#ff4d4f'
                  }}
                />
              </Col>
              
              <Col xs={24} sm={8}>
                <Statistic
                  title="GPU使用率"
                  value={systemStatus?.gpu_usage || 0}
                  precision={1}
                  suffix="%"
                  prefix={<ThunderboltOutlined />}
                  valueStyle={{ color: getStatusColor(systemStatus?.gpu_usage || 0) }}
                />
              </Col>
              
              <Col xs={24} sm={8}>
                <div style={{ textAlign: 'center' }}>
                  <Button 
                    type="primary" 
                    icon={<ThunderboltOutlined />}
                    onClick={loadSystemStatus}
                    loading={loading}
                  >
                    刷新状态
                  </Button>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;