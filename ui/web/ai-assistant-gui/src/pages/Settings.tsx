import React from 'react';
import { Typography } from 'antd';

const { Title } = Typography;

const Settings: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>⚙️ 设置</Title>
      <p>设置界面正在开发中...</p>
    </div>
  );
};

export default Settings;