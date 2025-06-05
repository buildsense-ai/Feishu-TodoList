import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Typography,
  Badge,
  Spin,
  Button,
  message,
  Tag,
  Divider,
  Empty
} from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  RocketOutlined
} from '@ant-design/icons';
import { dataAPI, todoAPI, systemAPI } from '../services/api';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

const Dashboard = () => {
  const [loading, setLoading] = useState(false);
  const [todoData, setTodoData] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  // 获取最新TodoList
  const fetchLatestTodo = async () => {
    setLoading(true);
    try {
      const response = await dataAPI.getLatestTodoList();
      console.log('获取到的数据:', response.data);
      if (response.data.success) {
        setTodoData(response.data.data);
        setLastUpdate(new Date());
      }
    } catch (error) {
      console.error('获取TodoList失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 获取系统状态
  const fetchSystemStatus = async () => {
    try {
      const response = await systemAPI.health();
      setSystemStatus(response.data);
    } catch (error) {
      console.error('获取系统状态失败:', error);
    }
  };

  // 生成新的TodoList
  const generateTodoList = async () => {
    setLoading(true);
    try {
      const response = await todoAPI.generateDaily();
      console.log('生成的数据:', response.data);
      if (response.data.success) {
        setTodoData(response.data.data);
        setLastUpdate(new Date());
      }
    } catch (error) {
      console.error('生成TodoList失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLatestTodo();
    fetchSystemStatus();
  }, []);

  // 获取兼容的数据结构
  const getCompatibleTodoData = (data) => {
    if (!data) return null;
    
    // 优先使用 daily_todolist，如果没有则使用 todolist
    const todolistData = data.daily_todolist || data.todolist;
    return todolistData;
  };

  // 渲染任务列表
  const renderTaskList = (tasks, type) => {
    const colors = {
      todo: 'blue',
      done: 'green',
      issue: 'red'
    };

    const icons = {
      todo: <ClockCircleOutlined />,
      done: <CheckCircleOutlined />,
      issue: <ExclamationCircleOutlined />
    };

    if (!tasks || Object.keys(tasks).length === 0) {
      return <Empty description="暂无数据" />;
    }

    return Object.entries(tasks).map(([member, taskList]) => (
      <div key={member} className="team-member-card">
        <Title level={5}>
          <Badge color={colors[type]} />
          {member}
        </Title>
        {taskList && taskList.length > 0 ? (
          taskList.map((task, index) => (
            <div key={index} className={`task-item ${type}`}>
              {icons[type]} {task}
            </div>
          ))
        ) : (
          <Text type="secondary">暂无{type === 'todo' ? '待办' : type === 'done' ? '已完成' : '问题'}任务</Text>
        )}
      </div>
    ));
  };

  // 获取兼容的数据以供显示
  const compatibleData = getCompatibleTodoData(todoData);

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Title level={2}>
            <RocketOutlined /> 控制台
          </Title>
        </Col>
        <Col span={12} style={{ textAlign: 'right' }}>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={fetchLatestTodo}
            loading={loading}
          >
            刷新数据
          </Button>
          <Button
            style={{ marginLeft: 8 }}
            onClick={generateTodoList}
            loading={loading}
          >
            生成新ToDoList
          </Button>
        </Col>
      </Row>

      {/* 系统状态卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={24}>
          <Card title="系统状态" size="small">
            {systemStatus ? (
              <Row gutter={16}>
                <Col span={6}>
                  <div className="status-badge">
                    <Badge
                      status={systemStatus.status === 'healthy' ? 'success' : 'error'}
                      text={systemStatus.status === 'healthy' ? '系统正常' : '系统异常'}
                    />
                  </div>
                </Col>
                <Col span={6}>
                  <Tag color={systemStatus.ai_available ? 'green' : 'red'}>
                    AI服务: {systemStatus.ai_available ? '正常' : '异常'}
                  </Tag>
                </Col>
                <Col span={6}>
                  <Text type="secondary">版本: {systemStatus.version || 'N/A'}</Text>
                </Col>
                <Col span={6}>
                  <Text type="secondary">
                    更新时间: {lastUpdate ? dayjs(lastUpdate).format('HH:mm:ss') : '未知'}
                  </Text>
                </Col>
              </Row>
            ) : (
              <Spin />
            )}
          </Card>
        </Col>
      </Row>

      {/* ToDoList展示 */}
      <Spin spinning={loading}>
        {todoData && compatibleData ? (
          <Row gutter={[16, 16]}>
            <Col span={8}>
              <Card
                title={
                  <span>
                    <ClockCircleOutlined style={{ color: '#1890ff' }} /> 待办任务 (ToDo)
                  </span>
                }
                className="card-container"
              >
                {renderTaskList(compatibleData.ToDo, 'todo')}
              </Card>
            </Col>
            <Col span={8}>
              <Card
                title={
                  <span>
                    <CheckCircleOutlined style={{ color: '#52c41a' }} /> 已完成 (Done)
                  </span>
                }
                className="card-container"
              >
                {renderTaskList(compatibleData.Done, 'done')}
              </Card>
            </Col>
            <Col span={8}>
              <Card
                title={
                  <span>
                    <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} /> 问题 (Issue)
                  </span>
                }
                className="card-container"
              >
                {renderTaskList(compatibleData.Issue, 'issue')}
              </Card>
            </Col>
          </Row>
        ) : (
          <Card>
            <Empty
              description="暂无ToDoList数据"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              <Button type="primary" onClick={generateTodoList}>
                生成今日ToDoList
              </Button>
            </Empty>
          </Card>
        )}
      </Spin>

      {/* 统计信息 */}
      {todoData && (
        <Card title="统计信息" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={6}>
              <div style={{ textAlign: 'center' }}>
                <Title level={3} style={{ color: '#1890ff', margin: 0 }}>
                  {todoData.message_count || todoData.analysis_info?.total_messages || 0}
                </Title>
                <Text>消息数量</Text>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center' }}>
                <Title level={3} style={{ color: '#52c41a', margin: 0 }}>
                  {todoData.status === 'success' ? '成功' : '失败'}
                </Title>
                <Text>分析状态</Text>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center' }}>
                <Title level={3} style={{ color: '#722ed1', margin: 0 }}>
                  {todoData.model || todoData.analysis_info?.ai_model || 'DeepSeek'}
                </Title>
                <Text>AI模型</Text>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center' }}>
                <Title level={3} style={{ color: '#fa8c16', margin: 0 }}>
                  {todoData.analysis_timestamp || todoData.analysis_info?.analysis_timestamp ? 
                    dayjs(todoData.analysis_timestamp || todoData.analysis_info.analysis_timestamp).format('MM-DD HH:mm') : 'N/A'}
                </Title>
                <Text>分析时间</Text>
              </div>
            </Col>
          </Row>
        </Card>
      )}
    </div>
  );
};

export default Dashboard; 