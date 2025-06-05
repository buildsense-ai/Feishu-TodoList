import React from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  FileTextOutlined,
  TeamOutlined,
  BarChartOutlined,
  MonitorOutlined,
  HistoryOutlined
} from '@ant-design/icons';
import Dashboard from './components/Dashboard';
import MeetingUpload from './components/MeetingUpload';
import TeamWorkload from './components/TeamWorkload';
import SystemMonitor from './components/SystemMonitor';
import DailyHistory from './components/DailyHistory';
import 'antd/dist/reset.css';

const { Header, Sider, Content } = Layout;

function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();
  
  // 根据当前路径设置选中的菜单项
  const getCurrentKey = () => {
    const path = location.pathname;
    switch (path) {
      case '/': return 'dashboard';
      case '/meeting': return 'meeting';
      case '/workload': return 'workload';
      case '/history': return 'history';
      case '/monitor': return 'monitor';
      default: return 'dashboard';
    }
  };
  
  const [current, setCurrent] = React.useState(getCurrentKey());
  
  React.useEffect(() => {
    setCurrent(getCurrentKey());
  }, [location.pathname]);

  const menuItems = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: '控制台',
      path: '/'
    },
    {
      key: 'meeting',
      icon: <FileTextOutlined />,
      label: '会议记录',
      path: '/meeting'
    },
    {
      key: 'workload',
      icon: <TeamOutlined />,
      label: '团队工作负载',
      path: '/workload'
    },
    {
      key: 'history',
      icon: <HistoryOutlined />,
      label: '历史记录',
      path: '/history'
    },
    {
      key: 'monitor',
      icon: <MonitorOutlined />,
      label: '系统监控',
      path: '/monitor'
    }
  ];

  return (
    <Layout>
      <Sider
        breakpoint="lg"
        collapsedWidth="0"
        style={{
          background: '#001529'
        }}
      >
        <div className="logo">
          <BarChartOutlined /> 飞书AI系统
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[current]}
          onClick={({ key }) => {
            setCurrent(key);
            const item = menuItems.find(item => item.key === key);
            if (item) {
              navigate(item.path);
            }
          }}
          items={menuItems.map(item => ({
            key: item.key,
            icon: item.icon,
            label: item.label
          }))}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: 0,
            background: '#fff',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
          }}
        />
        <Content className="site-layout-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/meeting" element={<MeetingUpload />} />
            <Route path="/workload" element={<TeamWorkload />} />
            <Route path="/history" element={<DailyHistory />} />
            <Route path="/monitor" element={<SystemMonitor />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App; 