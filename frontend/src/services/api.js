import axios from 'axios';

// 在开发环境使用代理，生产环境使用完整URL
const API_BASE_URL = process.env.NODE_ENV === 'development' 
  ? '' // 使用代理
  : (process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000');

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    console.log('API请求:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log('API响应:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('响应错误:', error.response?.status, error.response?.data);
    return Promise.reject(error);
  }
);

// 会议记录处理接口
export const meetingAPI = {
  // 完整会议记录处理流程
  processComplete: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/meeting/process-complete', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // 分析会议记录
  analyze: (transcript) => {
    return apiClient.post('/meeting/analyze', { transcript });
  },

  // 保存会议摘要
  save: (summary, transcript) => {
    return apiClient.post('/meeting/save', { summary, transcript });
  },

  // 发送到飞书群
  sendFeishu: (summary) => {
    return apiClient.post('/meeting/send-feishu', { summary });
  },
};

// ToDoList生成接口
export const todoAPI = {
  // 生成每日ToDoList
  generateDaily: (container_id = 'oc_58605a887f1e11e359ceec1782c2d12d', download_files = false) => {
    return apiClient.post('/daily-todolist', { container_id, download_files });
  },
};

// 数据查询接口
export const dataAPI = {
  // 获取最新ToDoList
  getLatestTodoList: () => {
    return apiClient.get('/db/latest-todolist');
  },

  // 获取成员工作负载统计
  getMemberWorkload: (days = 7) => {
    return apiClient.get(`/db/member-workload?days=${days}`);
  },

  // 获取指定日期ToDoList汇总
  getDailySummary: (target_date) => {
    return apiClient.get(`/db/daily-summary?target_date=${target_date}`);
  },
};

// 系统监控接口
export const systemAPI = {
  // 健康检查
  health: () => {
    return apiClient.get('/health');
  },

  // 数据库健康检查
  dbHealth: () => {
    return apiClient.get('/db/health');
  },
};

// 消息获取接口
export const messageAPI = {
  // 获取今天消息
  fetchToday: (container_id) => {
    return apiClient.post('/fetch-today', { container_id });
  },

  // 获取昨天消息
  fetchYesterday: (container_id) => {
    return apiClient.post('/fetch-yesterday', { container_id });
  },

  // 自定义时间范围获取消息
  fetchMessages: (container_id, start_time, end_time) => {
    return apiClient.post('/fetch-messages', {
      container_id,
      start_time,
      end_time,
    });
  },
};

// AI分析接口
export const aiAPI = {
  // AI项目分析
  analyze: (container_id, messages) => {
    return apiClient.post('/ai-analyze', { container_id, messages });
  },

  // AI分析今天讨论
  analyzeToday: (container_id) => {
    return apiClient.post('/ai-analyze-today', { container_id });
  },
};

// 异步任务接口
export const taskAPI = {
  // 异步获取消息
  fetchAsync: (container_id, start_time, end_time) => {
    return apiClient.post('/fetch-async', {
      container_id,
      start_time,
      end_time,
    });
  },

  // 查询任务状态
  getTaskStatus: (task_id) => {
    return apiClient.get(`/task-status/${task_id}`);
  },
};

export default apiClient; 