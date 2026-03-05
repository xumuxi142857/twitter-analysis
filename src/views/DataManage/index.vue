<template>
  <div class="data-manage-container">
    <div class="header">
      <h1>🎛️ 数据中台控制面板</h1>
      <p>后台异步处理系统：支持长时间任务挂机运行</p>
    </div>

    <div class="main-card">
      <div class="date-selector">
        <span class="label">处理日期：</span>
        <el-date-picker
          v-model="selectedDate"
          type="date"
          placeholder="选择数据日期"
          value-format="YYYY-MM-DD"
          :clearable="false"
          :disabled="!!currentTaskId" 
        />
      </div>

      <el-divider />

      <div class="task-grid">
        <div class="task-item" v-for="task in taskList" :key="task.type">
          <div class="task-info">
            <h3>{{ task.name }}</h3>
            <p>脚本: <code>{{ task.script }}</code></p>
            <p class="desc">{{ task.desc }}</p>
          </div>
          
          <div class="task-action">
            <el-button 
              v-if="!task.running"
              type="primary" 
              @click="startTask(task.type)"
              :disabled="!!currentTaskId"
            >
              开始执行
            </el-button>
            <div v-else class="running-state">
              <span class="timer">⏱️ {{ formatTime(elapsedTime) }}</span>
              <el-button type="warning" loading disabled>
                运行中...
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="log-panel" v-if="currentTaskId">
      <div class="log-header">
        <div class="lh-left">
          <span>>_ 终端输出: {{ getCurrentScriptName() }}</span>
          <span v-if="currentStatus === 'running'" class="status-badge running">RUNNING</span>
          <span v-else-if="currentStatus === 'terminated'" class="status-badge error">TERMINATED</span>
          <span v-else-if="currentStatus === 'success'" class="status-badge success">SUCCESS</span>
          <span v-else-if="currentStatus === 'error'" class="status-badge error">ERROR</span>
        </div>
        <div class="lh-right">
           <el-button 
             v-if="currentStatus === 'running'" 
             type="danger" 
             size="small" 
             plain 
             @click="terminateTask"
           >
             🛑 强制终止
           </el-button>

           <el-button link type="info" @click="stopPolling(true)">关闭监控</el-button>
        </div>
      </div>
      
      <div class="log-content-wrapper" ref="logContainer">
        <pre class="log-content">{{ currentLogs }}</pre>
        <div v-if="currentStatus === 'running'" class="typing-cursor">_</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, nextTick, onUnmounted } from 'vue';
import axios from 'axios';
import { ElMessage } from 'element-plus';

// 基础状态
const selectedDate = ref(new Date().toISOString().split('T')[0]);
const currentTaskId = ref('');
const currentStatus = ref('');
const currentLogs = ref(''); // 这里接收后端传来的 print 输出
const logContainer = ref<HTMLElement | null>(null);

// 计时器相关
const elapsedTime = ref(0);
let timerInterval: any = null;
let pollingInterval: any = null;

// 定义支持的任务类型
const taskList = reactive([
  { type: 'topic', name: '🔥 话题分析', script: 'topic.py', desc: '聚类分析、热词提取、立场统计', running: false },
  { type: 'target', name: '🎯 目标监测', script: 'detect.py', desc: '监测特定敏感目标的最新动态', running: false },
  { type: 'account', name: '👥 账号推荐', script: 'account.py', desc: '生成重点人物画像报告', running: false },
  { type: 'agent', name: '🤖 智能体', script: 'agent_task.py', desc: '基于 Agent 的自动化任务执行', running: false }
]);

// 获取当前运行的脚本名称（用于显示在终端标题）
const getCurrentScriptName = () => {
  const task = taskList.find(t => t.running);
  return task ? task.script : 'Console';
};

// 格式化时间 (秒 -> mm:ss)
const formatTime = (seconds: number) => {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
};

// 1. 开始任务
const startTask = async (type: string) => {
  if (taskList.some(t => t.running)) {
    return ElMessage.warning('已有任务正在运行，请等待其结束');
  }

  const taskItem = taskList.find(t => t.type === type);
  if (!taskItem) return;

  try {
    // 重置状态
    taskItem.running = true;
    currentLogs.value = '>>> 系统正在初始化环境...\n>>> 准备执行脚本...\n';
    elapsedTime.value = 0;
    
    // 启动计时器
    timerInterval = setInterval(() => {
      elapsedTime.value++;
    }, 1000);

    // 发送启动请求
    // 注意：这里端口我保留了你代码里的 5001，如果后端是 5000 请自行修改
    const res = await axios.post('/api/run_script', {
      type: type,
      date: selectedDate.value // ⚠️ 修复了之前的 valaue 拼写错误
    });

    if (res.data.status === 'submitted') {
      currentTaskId.value = res.data.task_id;
      ElMessage.success('脚本启动成功，正在接入终端流...');
      // 开始轮询日志
      startPolling(taskItem);
    }

  } catch (error: any) {
    ElMessage.error('提交失败: ' + (error.response?.data?.error || error.message));
    taskItem.running = false;
    clearInterval(timerInterval);
  }
};
// 新增：强制终止任务
const terminateTask = async () => {
  try {
    await axios.post('/api/stop_task', { task_id: currentTaskId.value });
    ElMessage.warning('正在尝试终止后台进程...');
    // 不用手动设为 false，等下一次轮询时，后端状态变成 terminated，前端会自动更新 UI
  } catch (error) {
    ElMessage.error('终止失败');
  }
};
// 2. 轮询状态（获取终端日志）
const startPolling = (taskItem: any) => {
  if (pollingInterval) clearInterval(pollingInterval);

  pollingInterval = setInterval(async () => {
    try {
      const res = await axios.get(`/api/task_status/${currentTaskId.value}`);
      const data = res.data;

      currentStatus.value = data.status;
      currentLogs.value = data.logs;

      nextTick(() => {
        if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight;
      });

      // 判断结束 (增加了 'terminated')
      if (['success', 'error', 'terminated'].includes(data.status)) {
        stopPolling(false); 
        taskItem.running = false;
        
        if (data.status === 'success') ElMessage.success('执行完成！');
        else if (data.status === 'terminated') ElMessage.warning('任务已手动终止');
        else ElMessage.error('执行出错');
      }

    } catch (e) { console.error(e); }
  }, 2000);
};

// 停止监控
const stopPolling = (clearLogs = true) => {
  if (pollingInterval) clearInterval(pollingInterval);
  if (timerInterval) clearInterval(timerInterval);
  
  if (clearLogs) {
    currentTaskId.value = '';
    taskList.forEach(t => t.running = false);
  }
};

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped lang="scss">
.data-manage-container { padding: 40px; max-width: 1000px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
.header { text-align: center; margin-bottom: 30px; }
.main-card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
.date-selector { display: flex; align-items: center; gap: 15px; font-weight: bold; margin-bottom: 20px; }
.task-grid { display: grid; gap: 15px; }

.task-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;
  background: #f8fafc;
  .task-info h3 { margin: 0 0 5px 0; font-size: 16px; }
  .task-info p { margin: 2px 0; color: #64748b; font-size: 13px; }
  code { background: #e2e8f0; padding: 2px 5px; border-radius: 4px; color: #d63384; font-family: monospace; }
}

.running-state {
  display: flex; align-items: center; gap: 15px;
  .timer { font-family: 'Roboto Mono', monospace; font-weight: bold; color: #f59e0b; font-size: 16px; }
}

/* 终端样式优化 */
.log-panel {
  margin-top: 25px; background: #1e1e1e; border-radius: 8px; overflow: hidden;
  box-shadow: 0 10px 25px rgba(0,0,0,0.3); border: 1px solid #333;
  
  .log-header {
    background: #2d2d2d; padding: 10px 20px; color: #ccc; font-size: 13px; font-family: monospace;
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid #333;
    
    .lh-left { display: flex; align-items: center; gap: 10px; }
    
    .status-badge {
      padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; color: #1e1e1e;
      &.running { background: #3b82f6; color: white; animation: pulse 1.5s infinite; }
      &.success { background: #10b981; color: white; }
      &.error { background: #ef4444; color: white; }
    }
  }
  
  .log-content-wrapper {
    height: 500px; /* 增加高度，方便看长日志 */
    overflow-y: auto; padding: 15px;
    background-color: #0c0c0c; /* 更深邃的黑背景 */
    position: relative;
  }
  
  .log-content {
    color: #4ade80; /* 经典的终端绿 */
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace; 
    font-size: 13px; line-height: 1.5;
    white-space: pre-wrap; word-break: break-all; margin: 0;
  }
  
  .typing-cursor {
    display: inline-block; width: 8px; height: 16px; background: #4ade80;
    animation: blink 1s step-end infinite; vertical-align: middle;
  }
}

@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
</style>