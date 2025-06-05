import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Typography,
  Select,
  Spin,
  message,
  Button,
  Tag,
  Statistic
} from 'antd';
import {
  TeamOutlined,
  ReloadOutlined,
  BarChartOutlined,
  PieChartOutlined
} from '@ant-design/icons';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { dataAPI } from '../services/api';

const { Title } = Typography;
const { Option } = Select;

const TeamWorkload = () => {
  const [loading, setLoading] = useState(false);
  const [workloadData, setWorkloadData] = useState(null);
  const [days, setDays] = useState(7);
  const [chartType, setChartType] = useState('bar');

  // 团队成员颜色映射
  const memberColors = {
    'Michael': '#1890ff',
    '小钟': '#52c41a',
    '国伟': '#fa8c16',
    '云起': '#722ed1',
    'Gauz': '#eb2f96',
    '团队': '#13c2c2'
  };

  // 获取工作负载数据
  const fetchWorkloadData = async () => {
    try {
      setLoading(true);
      const response = await dataAPI.getMemberWorkload(days);
      
      if (response.data.success) {
        setWorkloadData(response.data.data);
      } else {
        message.warning('暂无工作负载数据');
      }
    } catch (error) {
      console.error('获取工作负载数据失败:', error);
      message.error('获取工作负载数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkloadData();
  }, [days]);

  // 转换数据为图表格式
  const transformDataForChart = () => {
    if (!workloadData) return [];

    const members = ['Michael', '小钟', '国伟', '云起', 'Gauz'];
    return members.map(member => {
      const memberData = {
        name: member,
        待办任务: 0,
        已完成: 0,
        问题: 0,
        总计: 0
      };

      // 统计各类任务数量
      if (workloadData.todo && workloadData.todo[member]) {
        memberData.待办任务 = workloadData.todo[member].length;
      }
      if (workloadData.done && workloadData.done[member]) {
        memberData.已完成 = workloadData.done[member].length;
      }
      if (workloadData.issue && workloadData.issue[member]) {
        memberData.问题 = workloadData.issue[member].length;
      }

      memberData.总计 = memberData.待办任务 + memberData.已完成 + memberData.问题;
      return memberData;
    });
  };

  // 转换数据为饼图格式
  const transformDataForPieChart = () => {
    if (!workloadData) return [];

    const chartData = transformDataForChart();
    return chartData.map(item => ({
      name: item.name,
      value: item.总计,
      fill: memberColors[item.name]
    }));
  };

  // 计算总体统计
  const calculateTotalStats = () => {
    if (!workloadData) return { totalTasks: 0, totalMembers: 0, avgTasks: 0 };

    const chartData = transformDataForChart();
    const totalTasks = chartData.reduce((sum, item) => sum + item.总计, 0);
    const activeMembers = chartData.filter(item => item.总计 > 0).length;
    const avgTasks = activeMembers > 0 ? (totalTasks / activeMembers).toFixed(1) : 0;

    return {
      totalTasks,
      totalMembers: activeMembers,
      avgTasks
    };
  };

  const stats = calculateTotalStats();
  const chartData = transformDataForChart();
  const pieData = transformDataForPieChart();

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Title level={2}>
            <TeamOutlined /> 团队工作负载
          </Title>
        </Col>
        <Col span={12} style={{ textAlign: 'right' }}>
          <Select
            value={days}
            onChange={setDays}
            style={{ width: 120, marginRight: 8 }}
          >
            <Option value={3}>最近3天</Option>
            <Option value={7}>最近7天</Option>
            <Option value={14}>最近14天</Option>
            <Option value={30}>最近30天</Option>
          </Select>
          <Select
            value={chartType}
            onChange={setChartType}
            style={{ width: 120, marginRight: 8 }}
          >
            <Option value="bar">柱状图</Option>
            <Option value="pie">饼图</Option>
          </Select>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={fetchWorkloadData}
            loading={loading}
          >
            刷新
          </Button>
        </Col>
      </Row>

      {/* 统计概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="总任务数"
              value={stats.totalTasks}
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="活跃成员"
              value={stats.totalMembers}
              prefix={<TeamOutlined />}
              suffix="人"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="平均任务"
              value={stats.avgTasks}
              prefix={<PieChartOutlined />}
              suffix="个/人"
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      <Spin spinning={loading}>
        {/* 图表展示 */}
        <Row gutter={[16, 16]}>
          <Col span={16}>
            <Card 
              title={
                chartType === 'bar' ? 
                  <span><BarChartOutlined /> 任务分布 - 柱状图</span> :
                  <span><PieChartOutlined /> 任务分布 - 饼图</span>
              }
              className="chart-container"
            >
              {chartType === 'bar' ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="待办任务" fill="#1890ff" />
                    <Bar dataKey="已完成" fill="#52c41a" />
                    <Bar dataKey="问题" fill="#ff4d4f" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, value, percent }) => `${name}: ${value} (${(percent * 100).toFixed(0)}%)`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </Card>
          </Col>

          {/* 成员详情 */}
          <Col span={8}>
            <Card title="成员详情" style={{ height: '400px', overflow: 'auto' }}>
              {chartData.map(member => (
                <Card key={member.name} size="small" style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong style={{ color: memberColors[member.name] }}>
                        {member.name}
                      </strong>
                      <div style={{ marginTop: 4 }}>
                        <Tag color="blue">待办: {member.待办任务}</Tag>
                        <Tag color="green">完成: {member.已完成}</Tag>
                        <Tag color="red">问题: {member.问题}</Tag>
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
                        {member.总计}
                      </div>
                      <div style={{ fontSize: '12px', color: '#666' }}>
                        总任务
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </Card>
          </Col>
        </Row>

        {/* 任务类型分布 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={8}>
            <Card title="待办任务" bodyStyle={{ padding: '12px' }}>
              {workloadData?.todo ? Object.entries(workloadData.todo).map(([member, tasks]) => (
                <div key={member} style={{ marginBottom: 8 }}>
                  <Tag color="blue">{member}: {tasks.length}</Tag>
                </div>
              )) : <div>暂无数据</div>}
            </Card>
          </Col>
          <Col span={8}>
            <Card title="已完成任务" bodyStyle={{ padding: '12px' }}>
              {workloadData?.done ? Object.entries(workloadData.done).map(([member, tasks]) => (
                <div key={member} style={{ marginBottom: 8 }}>
                  <Tag color="green">{member}: {tasks.length}</Tag>
                </div>
              )) : <div>暂无数据</div>}
            </Card>
          </Col>
          <Col span={8}>
            <Card title="问题" bodyStyle={{ padding: '12px' }}>
              {workloadData?.issue ? Object.entries(workloadData.issue).map(([member, tasks]) => (
                <div key={member} style={{ marginBottom: 8 }}>
                  <Tag color="red">{member}: {tasks.length}</Tag>
                </div>
              )) : <div>暂无数据</div>}
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  );
};

export default TeamWorkload; 