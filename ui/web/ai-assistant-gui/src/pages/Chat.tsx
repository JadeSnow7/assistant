import React, { useState, useEffect, useRef } from 'react';
import { 
  Layout, 
  Input, 
  Button, 
  Avatar, 
  List, 
  Typography, 
  Card,
  Space,
  Tag,
  Spin,
  Empty,
  message,
  Tooltip
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  DollarOutlined,
  ToolOutlined
} from '@ant-design/icons';
import { useParams } from 'react-router-dom';
import { useAppStore } from '../stores/appStore';
import { apiClient, type ChatMessage, type ChatResponse } from '../services/apiClient';

const { Content } = Layout;
const { TextArea } = Input;
const { Text, Paragraph } = Typography;

interface MessageWithUI extends ChatMessage {
  isStreaming?: boolean;
  streamContent?: string;
}

const Chat: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { 
    currentSessionId, 
    setCurrentSessionId, 
    addNotification,
    isDarkMode 
  } = useAppStore();
  
  const [messages, setMessages] = useState<MessageWithUI[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const currentStreamingId = useRef<string | null>(null);

  // 初始化会话
  useEffect(() => {
    if (sessionId && sessionId !== currentSessionId) {
      setCurrentSessionId(sessionId);
      loadSessionHistory(sessionId);
    } else if (!sessionId && !currentSessionId) {
      // 创建新会话
      createNewSession();
    }
  }, [sessionId, currentSessionId]);

  // 自动滚动到底部
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const createNewSession = async () => {
    try {
      const session = await apiClient.createSession();
      setCurrentSessionId(session.id);
      // 更新URL
      window.history.pushState(null, '', `/chat/${session.id}`);
      addNotification({
        type: 'success',
        title: '新建对话',
        message: '已创建新的对话会话'
      });
    } catch (error) {
      addNotification({
        type: 'error',
        title: '创建失败',
        message: '无法创建新的对话会话'
      });
    }
  };

  const loadSessionHistory = async (sessionId: string) => {
    try {
      setIsLoading(true);
      const history = await apiClient.getSessionHistory(sessionId);
      const formattedMessages: MessageWithUI[] = history.map(msg => ({
        ...msg,
        id: msg.id || Date.now().toString()
      }));
      setMessages(formattedMessages);
    } catch (error) {
      addNotification({
        type: 'error',
        title: '加载失败',
        message: '无法加载对话历史'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isStreaming) return;

    const userMessage: MessageWithUI = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsStreaming(true);

    // 创建AI回复消息占位符
    const aiMessageId = (Date.now() + 1).toString();
    currentStreamingId.current = aiMessageId;
    
    const aiMessage: MessageWithUI = {
      id: aiMessageId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      isStreaming: true,
      streamContent: ''
    };

    setMessages(prev => [...prev, aiMessage]);

    try {
      let fullResponse = '';
      let responseMetadata: any = {};

      await apiClient.sendStreamMessage(
        {
          message: userMessage.content,
          session_id: currentSessionId || undefined,
          stream: true
        },
        (chunk) => {
          if (currentStreamingId.current !== aiMessageId) return;
          
          const content = chunk.content || '';
          fullResponse += content;
          
          // 收集元数据
          if (chunk.model_used) responseMetadata.model_used = chunk.model_used;
          if (chunk.response_time) responseMetadata.response_time = chunk.response_time;
          if (chunk.cost !== undefined) responseMetadata.cost = chunk.cost;
          if (chunk.plugins_used) responseMetadata.plugins_used = chunk.plugins_used;
          
          // 更新流式内容
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId 
              ? { ...msg, streamContent: fullResponse, metadata: responseMetadata }
              : msg
          ));
        }
      );

      // 完成流式响应
      if (currentStreamingId.current === aiMessageId) {
        setMessages(prev => prev.map(msg => 
          msg.id === aiMessageId 
            ? { 
                ...msg, 
                content: fullResponse, 
                isStreaming: false, 
                streamContent: undefined,
                metadata: responseMetadata
              }
            : msg
        ));
      }

    } catch (error) {
      console.error('Send message error:', error);
      
      if (currentStreamingId.current === aiMessageId) {
        setMessages(prev => prev.map(msg => 
          msg.id === aiMessageId 
            ? { 
                ...msg, 
                content: '抱歉，发生了错误，请稍后重试。', 
                isStreaming: false,
                streamContent: undefined
              }
            : msg
        ));
      }

      addNotification({
        type: 'error',
        title: '发送失败',
        message: '消息发送失败，请检查网络连接'
      });
    } finally {
      setIsStreaming(false);
      currentStreamingId.current = null;
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderMessageMetadata = (metadata?: any) => {
    if (!metadata) return null;

    return (
      <Space size={[0, 4]} wrap style={{ marginTop: 8 }}>
        {metadata.model_used && (
          <Tag icon={<ThunderboltOutlined />} color="blue">
            {metadata.model_used}
          </Tag>
        )}
        {metadata.response_time && (
          <Tag icon={<ClockCircleOutlined />} color="green">
            {metadata.response_time.toFixed(1)}s
          </Tag>
        )}
        {metadata.cost !== undefined && (
          <Tag icon={<DollarOutlined />} color={metadata.cost === 0 ? 'green' : 'orange'}>
            {metadata.cost === 0 ? '免费' : `$${metadata.cost.toFixed(4)}`}
          </Tag>
        )}
        {metadata.plugins_used && metadata.plugins_used.length > 0 && (
          <Tag icon={<ToolOutlined />} color="purple">
            {Array.isArray(metadata.plugins_used) ? metadata.plugins_used.join(', ') : metadata.plugins_used}
          </Tag>
        )}
      </Space>
    );
  };

  const renderMessage = (msg: MessageWithUI) => {
    const isUser = msg.role === 'user';
    const content = msg.isStreaming ? (msg.streamContent || '') : msg.content;
    
    return (
      <div 
        key={msg.id}
        style={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          marginBottom: 16
        }}
      >
        <div style={{ 
          maxWidth: '70%',
          display: 'flex',
          flexDirection: isUser ? 'row-reverse' : 'row',
          alignItems: 'flex-start',
          gap: 8
        }}>
          <Avatar 
            icon={isUser ? <UserOutlined /> : <RobotOutlined />}
            style={{ 
              backgroundColor: isUser ? '#1890ff' : '#52c41a',
              flexShrink: 0
            }}
          />
          
          <div style={{ minWidth: 0 }}>
            <Card 
              size="small"
              style={{
                backgroundColor: isUser 
                  ? (isDarkMode ? '#1890ff' : '#e6f7ff')
                  : (isDarkMode ? '#262626' : '#f6ffed'),
                border: isUser 
                  ? '1px solid #1890ff'
                  : `1px solid ${isDarkMode ? '#434343' : '#d9f7be'}`,
                borderRadius: 12,
                ...(isUser ? {} : { marginLeft: 0 })
              }}
              bodyStyle={{ padding: 12 }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Paragraph 
                  style={{ 
                    margin: 0,
                    color: isUser 
                      ? (isDarkMode ? '#fff' : '#1890ff')
                      : (isDarkMode ? '#fff' : '#000'),
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                  }}
                >
                  {content}
                  {msg.isStreaming && (
                    <Text 
                      style={{ 
                        color: '#1890ff',
                        animation: 'blink 1s infinite'
                      }}
                    >
                      ▊
                    </Text>
                  )}
                </Paragraph>
                
                {msg.isStreaming && (
                  <Spin size="small" style={{ marginLeft: 8, flexShrink: 0 }} />
                )}
              </div>
              
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginTop: content ? 8 : 0
              }}>
                <Text 
                  type="secondary" 
                  style={{ 
                    fontSize: '12px',
                    color: isUser 
                      ? (isDarkMode ? 'rgba(255,255,255,0.7)' : '#1890ff')
                      : undefined
                  }}
                >
                  {formatTimestamp(msg.timestamp)}
                </Text>
              </div>
              
              {!isUser && renderMessageMetadata(msg.metadata)}
            </Card>
          </div>
        </div>
      </div>
    );
  };

  return (
    <Layout style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Content 
        style={{ 
          padding: 24,
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
      >
        {/* 消息列表 */}
        <div 
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '0 16px',
            marginBottom: 16
          }}
        >
          {isLoading ? (
            <div style={{ 
              display: 'flex', 
              justifyContent: 'center', 
              alignItems: 'center', 
              height: '200px'
            }}>
              <Spin size="large" />
            </div>
          ) : messages.length === 0 ? (
            <div style={{ 
              display: 'flex', 
              justifyContent: 'center', 
              alignItems: 'center', 
              height: '100%',
              flexDirection: 'column'
            }}>
              <Empty 
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="还没有对话消息"
              >
                <Text type="secondary">开始与AI助手的对话吧！</Text>
              </Empty>
            </div>
          ) : (
            <>
              {messages.map(renderMessage)}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* 输入区域 */}
        <div style={{ borderTop: `1px solid ${isDarkMode ? '#303030' : '#f0f0f0'}`, paddingTop: 16 }}>
          <Space.Compact style={{ width: '100%', display: 'flex' }}>
            <TextArea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={isStreaming ? '正在等待AI回复...' : '输入消息... (Enter发送, Shift+Enter换行)'}
              disabled={isStreaming}
              autoSize={{ minRows: 1, maxRows: 4 }}
              style={{ flex: 1, resize: 'none' }}
            />
            <Tooltip title="发送消息">
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isStreaming}
                style={{ height: 'auto', minHeight: 32 }}
              >
                发送
              </Button>
            </Tooltip>
          </Space.Compact>
        </div>
      </Content>

      <style>
        {`
          @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0; }
          }
        `}
      </style>
    </Layout>
  );
};

export default Chat;