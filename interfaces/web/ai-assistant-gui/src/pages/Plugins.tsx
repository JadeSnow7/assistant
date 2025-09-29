import React, { useState, useEffect } from 'react';
import { 
  Card, 
  List, 
  Typography, 
  Space, 
  Tag, 
  Button, 
  Switch,
  Modal,
  Descriptions,
  Alert,
  Input,
  Select,
  Badge,
  Tooltip,
  message,
  Row,
  Col,
  Spin
} from 'antd';
import {
  AppstoreOutlined,
  SettingOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  InfoCircleOutlined,
  SearchOutlined,
  FilterOutlined,
  ReloadOutlined,
  ToolOutlined
} from '@ant-design/icons';
import { useAppStore } from '../stores/appStore';
import { apiClient, type Plugin } from '../services/apiClient';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;
const { Option } = Select;

interface PluginStats {
  total: number;
  enabled: number;
  disabled: number;
  capabilities: Record<string, number>;
}

const Plugins: React.FC = () => {
  const { isDarkMode, addNotification } = useAppStore();
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPlugin, setSelectedPlugin] = useState<Plugin | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [filterCapability, setFilterCapability] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [operationLoading, setOperationLoading] = useState<Record<string, boolean>>({});
  
  useEffect(() => {
    loadPlugins();
  }, []);

  const loadPlugins = async () => {
    try {
      setLoading(true);
      const pluginData = await apiClient.getPlugins();
      setPlugins(pluginData);
    } catch (error) {
      console.error('Failed to load plugins:', error);
      addNotification({
        type: 'error',
        title: '加载失败',
        message: '无法加载插件列表'
      });
    } finally {
      setLoading(false);
    }
  };

  const handlePluginToggle = async (plugin: Plugin) => {
    setOperationLoading(prev => ({ ...prev, [plugin.name]: true }));
    
    try {
      if (plugin.enabled) {
        await apiClient.disablePlugin(plugin.name);
        addNotification({
          type: 'success',
          title: '插件已禁用',
          message: `${plugin.name} 已成功禁用`
        });
      } else {
        await apiClient.enablePlugin(plugin.name);
        addNotification({
          type: 'success',
          title: '插件已启用',
          message: `${plugin.name} 已成功启用`
        });
      }
      
      // 更新本地状态
      setPlugins(prev => prev.map(p => 
        p.name === plugin.name 
          ? { ...p, enabled: !p.enabled }
          : p
      ));
      
    } catch (error) {
      addNotification({
        type: 'error',
        title: '操作失败',
        message: `无法${plugin.enabled ? '禁用' : '启用'}插件 ${plugin.name}`
      });
    } finally {
      setOperationLoading(prev => ({ ...prev, [plugin.name]: false }));
    }
  };

  const showPluginDetails = async (plugin: Plugin) => {
    try {
      const details = await apiClient.getPlugin(plugin.name);
      setSelectedPlugin(details);
      setModalVisible(true);
    } catch (error) {
      addNotification({
        type: 'error',
        title: '加载失败',
        message: `无法获取插件 ${plugin.name} 的详细信息`
      });
    }
  };

  // 算统计数据
  const getPluginStats = (): PluginStats => {
    const total = plugins.length;
    const enabled = plugins.filter(p => p.enabled).length;
    const disabled = total - enabled;
    
    const capabilities: Record<string, number> = {};
    plugins.forEach(plugin => {
      plugin.capabilities.forEach(cap => {
        capabilities[cap] = (capabilities[cap] || 0) + 1;
      });
    });
    
    return { total, enabled, disabled, capabilities };
  };

  // 筛选插件
  const getFilteredPlugins = () => {
    return plugins.filter(plugin => {
      const matchesSearch = plugin.name.toLowerCase().includes(searchText.toLowerCase()) ||
                           plugin.description.toLowerCase().includes(searchText.toLowerCase());
      
      const matchesCapability = filterCapability === 'all' ||
                               plugin.capabilities.includes(filterCapability);
      
      const matchesStatus = filterStatus === 'all' ||
                           (filterStatus === 'enabled' && plugin.enabled) ||
                           (filterStatus === 'disabled' && !plugin.enabled);
      
      return matchesSearch && matchesCapability && matchesStatus;
    });
  };

  const stats = getPluginStats();
  const filteredPlugins = getFilteredPlugins();
  const allCapabilities = Array.from(new Set(plugins.flatMap(p => p.capabilities)));

  return (
    <div style={{ padding: 24 }}>
      {/* 页面标题 */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: 24
      }}>
        <Title level={2} style={{ margin: 0, color: isDarkMode ? '#fff' : '#000' }}>
          🔌 插件管理
        </Title>
        <Button 
          icon={<ReloadOutlined />}
          onClick={loadPlugins}
          loading={loading}
        >
          刷新
        </Button>
      </div>

      {/* 统计信息 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '32px', color: '#1890ff', marginBottom: 8 }}>
                <AppstoreOutlined />
              </div>
              <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{stats.total}</div>
              <div style={{ color: '#666' }}>总插件数</div>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '32px', color: '#52c41a', marginBottom: 8 }}>
                <PlayCircleOutlined />
              </div>
              <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{stats.enabled}</div>
              <div style={{ color: '#666' }}>已启用</div>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '32px', color: '#faad14', marginBottom: 8 }}>
                <PauseCircleOutlined />
              </div>
              <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{stats.disabled}</div>
              <div style={{ color: '#666' }}>已禁用</div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 能力统计 */}
      {Object.keys(stats.capabilities).length > 0 && (
        <Card title="🎯 插件能力分布" size="small" style={{ marginBottom: 24 }}>
          <Space size={[8, 8]} wrap>
            {Object.entries(stats.capabilities).map(([capability, count]) => (
              <Tag key={capability} color="blue">
                {capability} ({count})
              </Tag>
            ))}
          </Space>
        </Card>
      )}

      {/* 筛选条 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col xs={24} sm={8}>
            <Search
              placeholder="搜索插件名称或描述"
              allowClear
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              prefix={<SearchOutlined />}
            />
          </Col>
          
          <Col xs={24} sm={8}>
            <Select
              style={{ width: '100%' }}
              placeholder="筛选能力"
              value={filterCapability}
              onChange={setFilterCapability}
              suffixIcon={<FilterOutlined />}
            >
              <Option value="all">所有能力</Option>
              {allCapabilities.map(cap => (
                <Option key={cap} value={cap}>{cap}</Option>
              ))}
            </Select>
          </Col>
          
          <Col xs={24} sm={8}>
            <Select
              style={{ width: '100%' }}
              placeholder="筛选状态"
              value={filterStatus}
              onChange={setFilterStatus}
            >
              <Option value="all">所有状态</Option>
              <Option value="enabled">已启用</Option>
              <Option value="disabled">已禁用</Option>
            </Select>
          </Col>
        </Row>
      </Card>

      {/* 插件列表 */}
      <Card>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        ) : filteredPlugins.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <AppstoreOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />
            <div style={{ marginTop: 16, color: '#666' }}>
              {plugins.length === 0 ? '暂无插件' : '没有找到匹配的插件'}
            </div>
          </div>
        ) : (
          <List
            itemLayout="vertical"
            dataSource={filteredPlugins}
            renderItem={plugin => (
              <List.Item
                key={plugin.name}
                actions={[
                  <Tooltip title={plugin.enabled ? '禁用插件' : '启用插件'}>
                    <Switch
                      checked={plugin.enabled}
                      onChange={() => handlePluginToggle(plugin)}
                      loading={operationLoading[plugin.name]}
                      checkedChildren="开"
                      unCheckedChildren="关"
                    />
                  </Tooltip>,
                  <Tooltip title="查看详情">
                    <Button
                      type="text"
                      icon={<InfoCircleOutlined />}
                      onClick={() => showPluginDetails(plugin)}
                    >
                      详情
                    </Button>
                  </Tooltip>
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <div style={{ 
                      width: 48, 
                      height: 48, 
                      borderRadius: 8,
                      backgroundColor: plugin.enabled ? '#52c41a' : '#d9d9d9',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#fff',
                      fontSize: 20
                    }}>
                      <ToolOutlined />
                    </div>
                  }
                  title={
                    <Space>
                      <Text strong style={{ fontSize: 16 }}>{plugin.name}</Text>
                      <Tag color={plugin.enabled ? 'green' : 'default'}>
                        v{plugin.version}
                      </Tag>
                      <Badge 
                        status={plugin.enabled ? 'processing' : 'default'}
                        text={plugin.enabled ? '已启用' : '已禁用'}
                      />
                    </Space>
                  }
                  description={
                    <div>
                      <Paragraph 
                        style={{ margin: '8px 0', color: isDarkMode ? '#a0a0a0' : '#666' }}
                        ellipsis={{ rows: 2, expandable: true }}
                      >
                        {plugin.description}
                      </Paragraph>
                      
                      <Space size={[4, 4]} wrap>
                        {plugin.capabilities.map(cap => (
                          <Tag key={cap} color="blue" size="small">
                            {cap}
                          </Tag>
                        ))}
                      </Space>
                    </div>
                  }
                />
              </List.Item>
            )}
            pagination={{
              pageSize: 6,
              showSizeChanger: false,
              showQuickJumper: true,
              showTotal: (total, range) => 
                `第 ${range[0]}-${range[1]} 项，共 ${total} 个插件`
            }}
          />
        )}
      </Card>

      {/* 插件详情模态框 */}
      <Modal
        title={
          <Space>
            <ToolOutlined />
            插件详情
          </Space>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setModalVisible(false)}>
            关闭
          </Button>,
          selectedPlugin && (
            <Button
              key="toggle"
              type={selectedPlugin.enabled ? 'default' : 'primary'}
              loading={operationLoading[selectedPlugin.name]}
              onClick={() => {
                handlePluginToggle(selectedPlugin);
                setModalVisible(false);
              }}
            >
              {selectedPlugin.enabled ? '禁用插件' : '启用插件'}
            </Button>
          )
        ]}
        width={600}
      >
        {selectedPlugin && (
          <div>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="插件名称">
                {selectedPlugin.name}
              </Descriptions.Item>
              <Descriptions.Item label="版本">
                {selectedPlugin.version}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Badge 
                  status={selectedPlugin.enabled ? 'processing' : 'default'}
                  text={selectedPlugin.enabled ? '已启用' : '已禁用'}
                />
              </Descriptions.Item>
              <Descriptions.Item label="描述">
                {selectedPlugin.description}
              </Descriptions.Item>
              <Descriptions.Item label="能力">
                <Space size={[4, 4]} wrap>
                  {selectedPlugin.capabilities.map(cap => (
                    <Tag key={cap} color="blue">{cap}</Tag>
                  ))}
                </Space>
              </Descriptions.Item>
              {selectedPlugin.metadata && Object.keys(selectedPlugin.metadata).length > 0 && (
                <Descriptions.Item label="附加信息">
                  <pre style={{ 
                    background: isDarkMode ? '#1f1f1f' : '#f5f5f5',
                    padding: 8,
                    borderRadius: 4,
                    fontSize: 12,
                    margin: 0,
                    overflow: 'auto'
                  }}>
                    {JSON.stringify(selectedPlugin.metadata, null, 2)}
                  </pre>
                </Descriptions.Item>
              )}
            </Descriptions>
            
            {!selectedPlugin.enabled && (
              <Alert
                message="插件已禁用"
                description="该插件当前处于禁用状态，无法提供相关功能。"
                type="warning"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Plugins;