import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Typography,
  Button,
  Upload,
  message,
  Steps,
  Alert,
  Divider,
  Tag,
  Timeline,
  Input
} from 'antd';
import {
  InboxOutlined,
  FileTextOutlined,
  CloudUploadOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  SendOutlined
} from '@ant-design/icons';
import { meetingAPI } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Dragger } = Upload;
const { TextArea } = Input;

const MeetingUpload = () => {
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [processResult, setProcessResult] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [mode, setMode] = useState('upload');

  const handleFileUpload = async (file) => {
    try {
      setLoading(true);
      setCurrentStep(0);
      message.loading('正在处理会议记录...', 0);

      const response = await meetingAPI.processComplete(file);
      message.destroy();

      if (response.data.success) {
        setProcessResult(response.data);
        setCurrentStep(4);
        message.success('会议记录处理完成！');
      } else {
        message.error('处理失败');
      }
    } catch (error) {
      message.destroy();
      console.error('文件上传失败:', error);
      message.error('文件上传失败');
      setCurrentStep(0);
    } finally {
      setLoading(false);
    }
  };

  const handleTextAnalysis = async () => {
    if (!fileContent.trim()) {
      message.warning('请输入会议记录内容');
      return;
    }

    try {
      setLoading(true);
      message.loading('正在分析会议记录...', 0);

      const response = await meetingAPI.analyze(fileContent);
      message.destroy();

      if (response.data.success) {
        setAnalysisResult(response.data.data);
        message.success('会议记录分析完成！');
      } else {
        message.error('分析失败');
      }
    } catch (error) {
      message.destroy();
      console.error('分析失败:', error);
      message.error('分析失败');
    } finally {
      setLoading(false);
    }
  };

  const sendToFeishu = async () => {
    if (!analysisResult) return;

    try {
      setLoading(true);
      message.loading('正在发送到飞书群...', 0);

      const response = await meetingAPI.sendFeishu(analysisResult);
      message.destroy();

      if (response.data.success) {
        message.success('已成功发送到飞书群！');
      } else {
        message.error('发送失败');
      }
    } catch (error) {
      message.destroy();
      console.error('发送失败:', error);
      message.error('发送失败');
    } finally {
      setLoading(false);
    }
  };

  const uploadProps = {
    name: 'file',
    multiple: false,
    accept: '.txt,.md,.doc,.docx',
    beforeUpload: (file) => {
      handleFileUpload(file);
      return false;
    },
    showUploadList: false,
  };

  const steps = [
    {
      title: '上传文件',
      icon: <CloudUploadOutlined />,
    },
    {
      title: 'AI分析',
      icon: currentStep >= 1 ? <CheckCircleOutlined /> : <LoadingOutlined />,
    },
    {
      title: '保存数据库',
      icon: currentStep >= 2 ? <CheckCircleOutlined /> : <LoadingOutlined />,
    },
    {
      title: '发送飞书群',
      icon: currentStep >= 3 ? <CheckCircleOutlined /> : <LoadingOutlined />,
    },
    {
      title: '完成',
      icon: currentStep >= 4 ? <CheckCircleOutlined /> : <LoadingOutlined />,
    }
  ];

  return (
    <div>
      <Title level={2}>
        <FileTextOutlined /> 会议记录处理
      </Title>

      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Button
                type={mode === 'upload' ? 'primary' : 'default'}
                onClick={() => setMode('upload')}
                style={{ marginRight: 8 }}
              >
                文件上传
              </Button>
              <Button
                type={mode === 'text' ? 'primary' : 'default'}
                onClick={() => setMode('text')}
              >
                文本输入
              </Button>
            </div>

            {mode === 'upload' ? (
              <div>
                <Dragger {...uploadProps} className="upload-area">
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined />
                  </p>
                  <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                  <p className="ant-upload-hint">
                    支持 .txt, .md, .doc, .docx 格式的会议记录文件
                  </p>
                </Dragger>

                {loading && (
                  <div style={{ marginTop: 24 }}>
                    <Steps current={currentStep} items={steps} />
                  </div>
                )}
              </div>
            ) : (
              <div>
                <TextArea
                  placeholder="请输入会议记录内容..."
                  value={fileContent}
                  onChange={(e) => setFileContent(e.target.value)}
                  rows={10}
                  style={{ marginBottom: 16 }}
                />
                <Button
                  type="primary"
                  onClick={handleTextAnalysis}
                  loading={loading}
                  icon={<FileTextOutlined />}
                >
                  分析会议记录
                </Button>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {processResult && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={24}>
            <Card title="处理结果">
              <Alert
                message="会议记录处理完成"
                description={processResult.message}
                type="success"
                showIcon
                style={{ marginBottom: 16 }}
              />

              <Timeline>
                <Timeline.Item color="green">
                  <strong>文件上传:</strong> ✅ 完成
                </Timeline.Item>
                <Timeline.Item color="green">
                  <strong>AI分析:</strong> ✅ 完成
                </Timeline.Item>
                <Timeline.Item color="green">
                  <strong>数据库保存:</strong> ✅ 完成 (ID: {processResult.data?.meeting_id})
                </Timeline.Item>
                <Timeline.Item color="green">
                  <strong>飞书群发送:</strong> ✅ 完成
                </Timeline.Item>
              </Timeline>

              <Divider />

              <Row gutter={16}>
                <Col span={12}>
                  <Tag color="blue">记录长度: {processResult.data?.transcript_length} 字符</Tag>
                </Col>
                <Col span={12}>
                  <Tag color="green">飞书发送: {processResult.data?.feishu_sent ? '成功' : '失败'}</Tag>
                </Col>
              </Row>

              {processResult.next_steps && (
                <div style={{ marginTop: 16 }}>
                  <Title level={5}>下一步操作:</Title>
                  <ul>
                    {processResult.next_steps.map((step, index) => (
                      <li key={index}>{step}</li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          </Col>
        </Row>
      )}

      {analysisResult && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={24}>
            <Card 
              title="分析结果"
              extra={
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={sendToFeishu}
                  loading={loading}
                >
                  发送到飞书群
                </Button>
              }
            >
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Card title="会议摘要" size="small">
                    <Paragraph>{analysisResult.summary}</Paragraph>
                  </Card>
                </Col>
                <Col span={12}>
                  <Card title="参与者" size="small">
                    {analysisResult.participants?.map((participant, index) => (
                      <Tag key={index} color="blue" style={{ marginBottom: 4 }}>
                        {participant}
                      </Tag>
                    ))}
                  </Card>
                </Col>
              </Row>

              {analysisResult.todos && analysisResult.todos.length > 0 && (
                <Card title="待办事项" size="small" style={{ marginTop: 16 }}>
                  {analysisResult.todos.map((todo, index) => (
                    <div key={index} className="task-item todo" style={{ marginBottom: 8 }}>
                      <strong>{todo.task}</strong>
                      <div>
                        <Tag color="orange">负责人: {todo.assignee}</Tag>
                        <Tag color="purple">优先级: {todo.priority}</Tag>
                        {todo.deadline && <Tag color="red">截止: {todo.deadline}</Tag>}
                      </div>
                    </div>
                  ))}
                </Card>
              )}
            </Card>
          </Col>
        </Row>
      )}

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="使用说明" size="small">
            <Timeline size="small">
              <Timeline.Item>
                <strong>步骤1:</strong> 选择文件上传或文本输入方式
              </Timeline.Item>
              <Timeline.Item>
                <strong>步骤2:</strong> 上传会议记录文件或输入会议内容
              </Timeline.Item>
              <Timeline.Item>
                <strong>步骤3:</strong> 系统自动进行AI分析并保存到数据库
              </Timeline.Item>
              <Timeline.Item>
                <strong>步骤4:</strong> 会议摘要自动发送到飞书群
              </Timeline.Item>
              <Timeline.Item>
                <strong>步骤5:</strong> 可在控制台页面生成包含会议内容的ToDoList
              </Timeline.Item>
            </Timeline>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default MeetingUpload; 