import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Typography,
  Badge,
  Button,
  message,
  Descriptions,
  Alert,
  Progress,
  Tag,
  Divider
} from 'antd';
import {
  MonitorOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  DatabaseOutlined,
  RobotOutlined,
  CloudServerOutlined
} from '@ant-design/icons';
import { systemAPI } from '../services/api';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

const SystemMonitor = () => {
  const [loading, setLoading] = useState(false);
  const [systemHealth, setSystemHealth] = useState(null);
  const [dbHealth, setDbHealth] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  // 获取系统健康状态
  const fetchSystemHealth = async () => {
    try {
      setLoading(true);
      const response = await systemAPI.health();
      setSystemHealth(response.data);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('获取系统状态失败:', error);
      setSystemHealth({
        status: 'error',
        message: '系统连接失败',
        ai_available: false
      });
      message.error('系统连接失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取数据库健康状态
  const fetchDbHealth = async () => {
    try {
      const response = await systemAPI.dbHealth();
      setDbHealth(response.data);
    } catch (error) {
      console.error('获取数据库状态失败:', error);
      setDbHealth({
        status: 'error',
        message: '数据库连接失败'
      });
    }
  };

  // 刷新所有状态
  const refreshAll = async () => {
    await Promise.all([
      fetchSystemHealth(),
      fetchDbHealth()
    ]);
  };

  useEffect(() => {
    refreshAll();
  }, []);

  // 自动刷新
  useEffect(() => {
    let interval;
    if (autoRefresh) {
      interval = setInterval(refreshAll, 30000); // 30秒刷新一次
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  // 获取状态颜色和图标
  const getStatusInfo = (status) => {
    switch (status) {
      case 'healthy':
      case 'success':
        return {
          color: 'success',
          icon: <CheckCircleOutlined />,
          text: '正常'
        };
      case 'warning':
        return {
          color: 'warning',
          icon: <WarningOutlined />,
          text: '警告'
        };
      case 'error':
      default:
        return {
          color: 'error',
          icon: <CloseCircleOutlined />,
          text: '异常'
        };
    }
  };

  const systemStatusInfo = getStatusInfo(systemHealth?.status);
  const dbStatusInfo = getStatusInfo(dbHealth?.status);

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Title level={2}>
            <MonitorOutlined /> 系统监控
          </Title>
        </Col>
        <Col span={12} style={{ textAlign: 'right' }}>
          <Button
            type={autoRefresh ? 'primary' : 'default'}
            onClick={() => setAutoRefresh(!autoRefresh)}
            style={{ marginRight: 8 }}
          >
            {autoRefresh ? '停止自动刷新' : '开启自动刷新'}
          </Button>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={refreshAll}
            loading={loading}
          >
            刷新状态
          </Button>
        </Col>
      </Row>

      {/* 系统概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '48px', marginBottom: 8 }}>
                {systemStatusInfo.icon}
              </div>
              <Title level={4} style={{ margin: 0 }}>
                系统状态
              </Title>
              <Badge status={systemStatusInfo.color} text={systemStatusInfo.text} />
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '48px', marginBottom: 8 }}>
                <DatabaseOutlined />
              </div>
              <Title level={4} style={{ margin: 0 }}>
                数据库状态
              </Title>
              <Badge status={dbStatusInfo.color} text={dbStatusInfo.text} />
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '48px', marginBottom: 8 }}>
                <RobotOutlined />
              </div>
              <Title level={4} style={{ margin: 0 }}>
                AI服务状态
              </Title>
              <Badge 
                status={systemHealth?.ai_available ? 'success' : 'error'} 
                text={systemHealth?.ai_available ? '正常' : '异常'} 
              />
            </div>
          </Card>
        </Col>
      </Row>

      {/* 详细信息 */}
      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card title={<span><CloudServerOutlined /> 系统信息</span>}>
            {systemHealth ? (
              <Descriptions column={1} size="small">
                <Descriptions.Item label="系统状态">
                  <Badge status={systemStatusInfo.color} text={systemStatusInfo.text} />
                </Descriptions.Item>
                <Descriptions.Item label="版本">
                  <Tag color="blue">{systemHealth.version || 'N/A'}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="AI服务">
                  <Tag color={systemHealth.ai_available ? 'green' : 'red'}>
                    {systemHealth.ai_available ? '可用' : '不可用'}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="AI提供商">
                  <Text code>{systemHealth.ai_provider || 'N/A'}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="AI模型">
                  <Text code>{systemHealth.ai_model || 'N/A'}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="最后更新">
                  <Text type="secondary">
                    {lastUpdate ? dayjs(lastUpdate).format('YYYY-MM-DD HH:mm:ss') : 'N/A'}
                  </Text>
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <div>加载中...</div>
            )}
          </Card>
        </Col>

        <Col span={12}>
          <Card title={<span><DatabaseOutlined /> 数据库信息</span>}>
            {dbHealth ? (
              <Descriptions column={1} size="small">
                <Descriptions.Item label="连接状态">
                  <Badge status={dbStatusInfo.color} text={dbStatusInfo.text} />
                </Descriptions.Item>
                <Descriptions.Item label="数据库类型">
                  <Tag color="purple">MySQL</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="响应时间">
                  <Progress 
                    percent={dbHealth.response_time ? Math.min(100, (1000 - dbHealth.response_time) / 10) : 0}
                    size="small"
                    status={dbHealth.response_time < 500 ? 'success' : 'exception'}
                    format={(percent) => `${dbHealth.response_time || 0}ms`}
                  />
                </Descriptions.Item>
                <Descriptions.Item label="表状态">
                  <div>
                    <Tag color="blue">meeting_summaries: 正常</Tag>
                    <Tag color="green">feishu_todolist: 正常</Tag>
                  </div>
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <div>加载中...</div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 功能模块状态 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="功能模块状态">
            {systemHealth?.features ? (
              <Row gutter={[16, 16]}>
                {Object.entries(systemHealth.features).map(([feature, status]) => (
                  <Col span={6} key={feature}>
                    <Card size="small">
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '24px', marginBottom: 8 }}>
                          {status ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
                        </div>
                        <div style={{ fontSize: '12px', marginBottom: 4 }}>
                          {feature.replace(/_/g, ' ').toUpperCase()}
                        </div>
                        <Badge status={status ? 'success' : 'error'} text={status ? '正常' : '异常'} />
                      </div>
                    </Card>
                  </Col>
                ))}
              </Row>
            ) : (
              <div>加载中...</div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 系统警告 */}
      {(!systemHealth?.ai_available || systemHealth?.status !== 'healthy') && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={24}>
            <Alert
              message="系统警告"
              description={
                <div>
                  {!systemHealth?.ai_available && <div>• AI服务不可用，请检查AI服务配置</div>}
                  {systemHealth?.status !== 'healthy' && <div>• 系统状态异常，请检查服务状态</div>}
                </div>
              }
              type="warning"
              showIcon
              action={
                <Button size="small" onClick={refreshAll}>
                  重新检查
                </Button>
              }
            />
          </Col>
        </Row>
      )}

      {/* 系统日志 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="系统日志" size="small">
            <div style={{ maxHeight: '200px', overflow: 'auto', fontFamily: 'monospace', fontSize: '12px' }}>
              <div>[{dayjs().format('HH:mm:ss')}] 系统监控页面已加载</div>
              <div>[{dayjs().format('HH:mm:ss')}] 正在检查系统状态...</div>
              {systemHealth && (
                <div>[{dayjs().format('HH:mm:ss')}] 系统状态: {systemHealth.status}</div>
              )}
              {dbHealth && (
                <div>[{dayjs().format('HH:mm:ss')}] 数据库状态: {dbHealth.status}</div>
              )}
              {autoRefresh && (
                <div>[{dayjs().format('HH:mm:ss')}] 自动刷新已启用 (30秒间隔)</div>
              )}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default SystemMonitor; 