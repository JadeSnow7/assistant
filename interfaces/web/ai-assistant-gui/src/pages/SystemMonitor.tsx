import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Row, 
  Col, 
  Statistic, 
  Progress, 
  Typography, 
  Space, 
  Table, 
  Tag, 
  Button,
  Alert,
  Spin
} from 'antd';
import {
  ThunderboltOutlined,
  MemoryOutlined,
  DatabaseOutlined,
  WifiOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { useAppStore } from '../stores/appStore';
import { apiClient, type SystemStatus } from '../services/apiClient';

const { Title, Text } = Typography;

interface PerformanceData {
  timestamp: string;
  cpu: number;
  memory: number;
  gpu: number;
  responseTime: number;
}

const SystemMonitor: React.FC = () => {
  const { isDarkMode, addNotification } = useAppStore();
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [performanceData, setPerformanceData] = useState<PerformanceData[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    loadSystemStatus();
    
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(loadSystemStatus, 5000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const loadSystemStatus = async () => {
    try {
      const status = await apiClient.getSystemStatus();
      setSystemStatus(status);
      
      // 添加到性能数据历史
      const newDataPoint: PerformanceData = {
        timestamp: new Date().toLocaleTimeString(),
        cpu: status.cpu_usage || 0,
        memory: status.memory_usage || 0,
        gpu: status.gpu_usage || 0,
        responseTime: status.avg_response_time || 0
      };
      
      setPerformanceData(prev => {
        const updated = [...prev, newDataPoint];
        // 保持最近20个数据点
        return updated.slice(-20);
      });
      
      setLoading(false);
    } catch (error) {
      console.error('Failed to load system status:', error);
      setLoading(false);
      if (performanceData.length === 0) {
        addNotification({
          type: 'error',
          title: '连接失败',
          message: '无法连接到系统监控服务'
        });
      }
    }
  };

  const getStatusColor = (usage: number): string => {
    if (usage < 50) return '#52c41a';
    if (usage < 80) return '#faad14';
    return '#ff4d4f';
  };

  const getStatusText = (usage: number): string => {
    if (usage < 50) return '正常';
    if (usage < 80) return '繁忙';
    return '过载';
  };

  const componentColumns = [
    {
      title: '组件名称',
      dataIndex: 'component',
      key: 'component',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (healthy: boolean) => (
        <Tag 
          icon={healthy ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
          color={healthy ? 'green' : 'red'}
        >
          {healthy ? '正常' : '异常'}
        </Tag>
      ),
    },
    {
      title: '最后检查',
      dataIndex: 'lastCheck',
      key: 'lastCheck',
      render: () => (
        <Space>
          <ClockCircleOutlined />
          <Text type="secondary">{new Date().toLocaleTimeString()}</Text>
        </Space>
      ),
    },
  ];

  const componentData = systemStatus?.components_health ? 
    Object.entries(systemStatus.components_health).map(([component, healthy]) => ({
      key: component,
      component,
      status: healthy,
      lastCheck: new Date().toISOString()
    })) : [];

  if (loading && performanceData.length === 0) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '400px'
      }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      {/* 页面标题和控制 */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: 24
      }}>
        <Title level={2} style={{ margin: 0, color: isDarkMode ? '#fff' : '#000' }}>
          📈 系统监控
        </Title>
        <Space>
          <Button 
            icon={<ReloadOutlined />}
            onClick={loadSystemStatus}
            loading={loading}
          >
            刷新
          </Button>
          <Button 
            type={autoRefresh ? 'primary' : 'default'}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? '停止自动刷新' : '开启自动刷新'}
          </Button>
        </Space>
      </div>

      {/* 连接状态提示 */}
      {!systemStatus && (
        <Alert
          message="服务连接异常"
          description="无法获取系统状态信息，请检查后端服务是否正常运行。"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 核心指标卡片 */}
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
              style={{ marginTop: 8 }}
            />
            <Text type="secondary" style={{ fontSize: '12px' }}>
              状态: {getStatusText(systemStatus?.cpu_usage || 0)}
            </Text>
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="内存使用率"
              value={systemStatus?.memory_usage || 0}
              precision={1}
              suffix="%"
              prefix={<MemoryOutlined />}
              valueStyle={{ color: getStatusColor(systemStatus?.memory_usage || 0) }}
            />
            <Progress 
              percent={systemStatus?.memory_usage || 0} 
              strokeColor={getStatusColor(systemStatus?.memory_usage || 0)}
              showInfo={false} 
              size="small"
              style={{ marginTop: 8 }}
            />
            <Text type="secondary" style={{ fontSize: '12px' }}>
              状态: {getStatusText(systemStatus?.memory_usage || 0)}
            </Text>
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="GPU使用率"
              value={systemStatus?.gpu_usage || 0}
              precision={1}
              suffix="%"
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: getStatusColor(systemStatus?.gpu_usage || 0) }}
            />
            <Progress 
              percent={systemStatus?.gpu_usage || 0} 
              strokeColor={getStatusColor(systemStatus?.gpu_usage || 0)}
              showInfo={false} 
              size="small"
              style={{ marginTop: 8 }}
            />
            <Text type="secondary" style={{ fontSize: '12px' }}>
              状态: {getStatusText(systemStatus?.gpu_usage || 0)}
            </Text>
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均响应时间"
              value={systemStatus?.avg_response_time || 0}
              precision={1}
              suffix="ms"
              prefix={<ClockCircleOutlined />}
              valueStyle={{ 
                color: (systemStatus?.avg_response_time || 0) < 1000 ? '#52c41a' : 
                       (systemStatus?.avg_response_time || 0) < 3000 ? '#faad14' : '#ff4d4f'
              }}
            />
            <Text type="secondary" style={{ fontSize: '12px', display: 'block', marginTop: 8 }}>
              {(systemStatus?.avg_response_time || 0) < 1000 ? '响应快速' : 
               (systemStatus?.avg_response_time || 0) < 3000 ? '响应一般' : '响应较慢'}
            </Text>
          </Card>
        </Col>
      </Row>

      {/* 性能趋势图表 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="📊 资源使用趋势" size="small">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="cpu" 
                  stroke="#1890ff" 
                  strokeWidth={2}
                  name="CPU %"
                />
                <Line 
                  type="monotone" 
                  dataKey="memory" 
                  stroke="#52c41a" 
                  strokeWidth={2}
                  name="内存 %"
                />
                <Line 
                  type="monotone" 
                  dataKey="gpu" 
                  stroke="#faad14" 
                  strokeWidth={2}
                  name="GPU %"
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="⚡ 响应时间趋势" size="small">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis />
                <Tooltip formatter={(value) => [`${value} ms`, '响应时间']} />
                <Area 
                  type="monotone" 
                  dataKey="responseTime" 
                  stroke="#722ed1" 
                  fill="#722ed1"
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* 系统信息 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="💻 系统信息" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>活跃会话:</Text>
                <Text strong>{systemStatus?.active_sessions || 0}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>总请求数:</Text>
                <Text strong>{systemStatus?.total_requests || 0}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>系统状态:</Text>
                <Tag color="green" icon={<WifiOutlined />}>在线</Tag>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>最后更新:</Text>
                <Text type="secondary">{new Date().toLocaleString()}</Text>
              </div>
            </Space>
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="🔧 组件健康状态" size="small">
            <Table 
              columns={componentColumns}
              dataSource={componentData}
              pagination={false}
              size="small"
              locale={{ emptyText: '暂无组件信息' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default SystemMonitor;