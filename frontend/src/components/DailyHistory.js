import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Typography,
  DatePicker,
  Button,
  message,
  Spin,
  Empty,
  Timeline,
  Tag,
  Collapse,
  Table
} from 'antd';
import {
  HistoryOutlined,
  SearchOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { dataAPI } from '../services/api';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { Panel } = Collapse;

const DailyHistory = () => {
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [summaryData, setSummaryData] = useState(null);

  // 获取指定日期的ToDoList汇总
  const fetchDailySummary = async (date) => {
    try {
      setLoading(true);
      const dateString = date.format('YYYY-MM-DD');
      const response = await dataAPI.getDailySummary(dateString);

      if (response.data.success) {
        setSummaryData(response.data.data);
      } else {
        setSummaryData(null);
        message.info('该日期没有ToDoList数据');
      }
    } catch (error) {
      console.error('获取历史数据失败:', error);
      message.error('获取历史数据失败');
      setSummaryData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDailySummary(selectedDate);
  }, [selectedDate]);

  // 渲染任务统计表格
  const renderTaskTable = () => {
    if (!summaryData || !summaryData.daily_todolist) return null;

    const { ToDo, Done, Issue } = summaryData.daily_todolist;
    const members = ['Michael', '小钟', '国伟', '云起', 'Gauz', '团队'];

    const tableData = members.map(member => ({
      key: member,
      member,
      todo: (ToDo && ToDo[member]) ? ToDo[member].length : 0,
      done: (Done && Done[member]) ? Done[member].length : 0,
      issue: (Issue && Issue[member]) ? Issue[member].length : 0
    })).filter(item => item.todo > 0 || item.done > 0 || item.issue > 0);

    const columns = [
      {
        title: '成员',
        dataIndex: 'member',
        key: 'member',
        render: (text) => <strong>{text}</strong>
      },
      {
        title: '待办任务',
        dataIndex: 'todo',
        key: 'todo',
        render: (value) => <Tag color="blue">{value}</Tag>
      },
      {
        title: '已完成',
        dataIndex: 'done',
        key: 'done',
        render: (value) => <Tag color="green">{value}</Tag>
      },
      {
        title: '问题',
        dataIndex: 'issue',
        key: 'issue',
        render: (value) => <Tag color="red">{value}</Tag>
      },
      {
        title: '总计',
        key: 'total',
        render: (_, record) => (
          <strong>{record.todo + record.done + record.issue}</strong>
        )
      }
    ];

    return (
      <Table
        dataSource={tableData}
        columns={columns}
        pagination={false}
        size="small"
      />
    );
  };

  // 渲染任务详情
  const renderTaskDetails = (tasks, type, icon, color) => {
    if (!tasks || Object.keys(tasks).length === 0) {
      return <Empty description={`暂无${type}数据`} />;
    }

    return (
      <div>
        {Object.entries(tasks).map(([member, taskList]) => (
          taskList && taskList.length > 0 && (
            <div key={member} style={{ marginBottom: 16 }}>
              <Title level={5} style={{ color }}>
                {icon} {member} ({taskList.length}个)
              </Title>
              <div>
                {taskList.map((task, index) => (
                  <div key={index} className={`task-item ${type.toLowerCase()}`} style={{ marginBottom: 4 }}>
                    {task}
                  </div>
                ))}
              </div>
            </div>
          )
        ))}
      </div>
    );
  };

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Title level={2}>
            <HistoryOutlined /> 历史记录
          </Title>
        </Col>
        <Col span={12} style={{ textAlign: 'right' }}>
          <DatePicker
            value={selectedDate}
            onChange={setSelectedDate}
            placeholder="选择日期"
            style={{ marginRight: 8 }}
            suffixIcon={<CalendarOutlined />}
          />
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={() => fetchDailySummary(selectedDate)}
            loading={loading}
          >
            查询
          </Button>
        </Col>
      </Row>

      <Spin spinning={loading}>
        {summaryData ? (
          <div>
            {/* 基本信息 */}
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col span={24}>
                <Card title={`${selectedDate.format('YYYY年MM月DD日')} ToDoList汇总`}>
                  <Row gutter={16}>
                    <Col span={6}>
                      <div style={{ textAlign: 'center' }}>
                        <Title level={3} style={{ color: '#1890ff', margin: 0 }}>
                          {summaryData.message_count || 0}
                        </Title>
                        <Text>消息数量</Text>
                      </div>
                    </Col>
                    <Col span={6}>
                      <div style={{ textAlign: 'center' }}>
                        <Title level={3} style={{ color: '#52c41a', margin: 0 }}>
                          {summaryData.total_messages || 0}
                        </Title>
                        <Text>总消息数</Text>
                      </div>
                    </Col>
                    <Col span={6}>
                      <div style={{ textAlign: 'center' }}>
                        <Title level={3} style={{ color: '#722ed1', margin: 0 }}>
                          {summaryData.model?.split('/')[1] || 'AI'}
                        </Title>
                        <Text>AI模型</Text>
                      </div>
                    </Col>
                    <Col span={6}>
                      <div style={{ textAlign: 'center' }}>
                        <Title level={3} style={{ color: '#fa8c16', margin: 0 }}>
                          {summaryData.analysis_timestamp ? 
                            dayjs(summaryData.analysis_timestamp).format('HH:mm') : 'N/A'}
                        </Title>
                        <Text>分析时间</Text>
                      </div>
                    </Col>
                  </Row>
                </Card>
              </Col>
            </Row>

            {/* 任务统计表格 */}
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col span={24}>
                <Card title="任务统计">
                  {renderTaskTable()}
                </Card>
              </Col>
            </Row>

            {/* 任务详情 */}
            <Row gutter={[16, 16]}>
              <Col span={24}>
                <Card title="任务详情">
                  <Collapse defaultActiveKey={['1']}>
                    <Panel 
                      header={
                        <span>
                          <ClockCircleOutlined style={{ color: '#1890ff' }} /> 
                          待办任务
                          <Tag color="blue" style={{ marginLeft: 8 }}>
                            {summaryData.daily_todolist?.ToDo ? 
                              Object.values(summaryData.daily_todolist.ToDo)
                                .flat().length : 0}
                          </Tag>
                        </span>
                      } 
                      key="1"
                    >
                      {renderTaskDetails(
                        summaryData.daily_todolist?.ToDo,
                        'todo',
                        <ClockCircleOutlined />,
                        '#1890ff'
                      )}
                    </Panel>

                    <Panel 
                      header={
                        <span>
                          <CheckCircleOutlined style={{ color: '#52c41a' }} /> 
                          已完成任务
                          <Tag color="green" style={{ marginLeft: 8 }}>
                            {summaryData.daily_todolist?.Done ? 
                              Object.values(summaryData.daily_todolist.Done)
                                .flat().length : 0}
                          </Tag>
                        </span>
                      } 
                      key="2"
                    >
                      {renderTaskDetails(
                        summaryData.daily_todolist?.Done,
                        'done',
                        <CheckCircleOutlined />,
                        '#52c41a'
                      )}
                    </Panel>

                    <Panel 
                      header={
                        <span>
                          <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} /> 
                          问题
                          <Tag color="red" style={{ marginLeft: 8 }}>
                            {summaryData.daily_todolist?.Issue ? 
                              Object.values(summaryData.daily_todolist.Issue)
                                .flat().length : 0}
                          </Tag>
                        </span>
                      } 
                      key="3"
                    >
                      {renderTaskDetails(
                        summaryData.daily_todolist?.Issue,
                        'issue',
                        <ExclamationCircleOutlined />,
                        '#ff4d4f'
                      )}
                    </Panel>
                  </Collapse>
                </Card>
              </Col>
            </Row>

            {/* 时间线 */}
            {summaryData.time_range && (
              <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                <Col span={24}>
                  <Card title="时间范围" size="small">
                    <Timeline>
                      <Timeline.Item color="green">
                        <strong>开始时间:</strong> {summaryData.time_range.start}
                      </Timeline.Item>
                      <Timeline.Item color="blue">
                        <strong>结束时间:</strong> {summaryData.time_range.end}
                      </Timeline.Item>
                      <Timeline.Item color="orange">
                        <strong>分析完成:</strong> {summaryData.analysis_timestamp ? 
                          dayjs(summaryData.analysis_timestamp).format('YYYY-MM-DD HH:mm:ss') : 'N/A'}
                      </Timeline.Item>
                    </Timeline>
                  </Card>
                </Col>
              </Row>
            )}
          </div>
        ) : (
          <Card>
            <Empty 
              description={`${selectedDate.format('YYYY年MM月DD日')} 暂无ToDoList数据`}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              <Text type="secondary">
                请选择其他日期或先生成当日的ToDoList
              </Text>
            </Empty>
          </Card>
        )}
      </Spin>
    </div>
  );
};

export default DailyHistory; 