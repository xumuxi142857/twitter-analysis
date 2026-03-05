<template>
  <div class="dashboard-container">
    <div class="header-section">
      <h1 class="page-title">智能体</h1>
      <p class="subtitle"></p>
    </div>
    
    <div class="control-panel">
      <div class="left-controls">
        <el-tabs v-model="activeTab" class="custom-tabs" @tab-change="handleTabChange">
          <el-tab-pane label=" NBA & 中美" name="US_NBA"></el-tab-pane>
          <el-tab-pane label=" 好莱坞 & 两岸" name="Taiwan_Hollywood"></el-tab-pane>
          <el-tab-pane label=" 马斯克 & 中日" name="Japan_Musk"></el-tab-pane>
          <el-tab-pane label=" AI & 中菲" name="PH_AI"></el-tab-pane>
        </el-tabs>
      </div>
      <div class="right-controls">
         <span class="label">日期:</span>
         <el-date-picker 
           v-model="selectedDate" 
           type="date" 
           value-format="YYYY-MM-DD" 
           :clearable="false" 
           :disabled-date="disabledDate"
           @change="fetchData" 
         />
      </div>
    </div>

    <div v-loading="loading" style="min-height: 500px;">
      <div v-if="hasData && currentAgentData && currentAgentData.top_topics">
        <el-row :gutter="24">
          
          <el-col :span="14">
            <el-card class="modern-card list-card" :body-style="{ padding: '0' }">
              <template #header>
                <div class="card-header">
                  <span class="title-text">焦点话题</span>
                </div>
              </template>
              
              <el-scrollbar height="600px">
                <div class="topic-list">
                  <div 
                    v-for="(item, index) in currentAgentData.top_topics" 
                    :key="index" 
                    class="topic-item"
                    :class="{ active: selectedTopicIndex === index }"
                    @click="selectedTopicIndex = index"
                  >
                    <div class="topic-rank" :class="{'top-3': index < 3}">{{ item.rank || (index + 1) }}</div>
                    <div class="topic-content">
                      <div class="topic-title">{{ item.topic }}</div>
                      <div class="topic-summary">{{ item.summary }}</div>
                    </div>
                  </div>
                </div>
              </el-scrollbar>
            </el-card>
          </el-col>

          <el-col :span="10">
            <el-card class="modern-card draft-card">
              <template #header>
                <div class="card-header">
                  <span class="title-text"><el-icon><Promotion /></el-icon> 推文引导拟写</span>
                  <el-tag v-if="generatingTweet" effect="dark" type="warning" class="blink-tag">生成中...</el-tag>
                  <el-tag v-else-if="dynamicTweet" effect="dark" type="success">就绪</el-tag>
                  <el-tag v-else effect="dark" type="info">待生成</el-tag>
                </div>
              </template>

              <div v-if="generatingTweet" class="loading-state">
                <el-skeleton :rows="5" animated />
                <p class="loading-text">🤖 智能体正在针对该焦点构思犀利推文...</p>
              </div>

              <div v-else-if="dynamicTweet" class="draft-content">
                <div class="draft-zh-only">
                  <p>{{ dynamicTweet }}</p>
                </div>
                
                <div class="action-bar">
                  <el-button type="info" plain round icon="Refresh" @click="triggerTweetGeneration">
                    重新生成
                  </el-button>
                  <el-button type="primary" round icon="DocumentCopy" @click="copyTweet">
                    复制中文推文
                  </el-button>
                </div>
              </div>

              <div v-else class="empty-state">
                <el-empty description="点击下方按钮，针对左侧选中的话题生成专递推文" :image-size="100">
                  <el-button type="primary" size="large" icon="MagicStick" @click="triggerTweetGeneration" round>
                    ✨ 为选中话题拟写推文
                  </el-button>
                </el-empty>
              </div>
            </el-card>
          </el-col>

        </el-row>
      </div>
      <el-empty v-else description="该日期暂无智能体研判数据 (请先运行批处理脚本)" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import axios from 'axios';
import { Promotion, DocumentCopy, MagicStick, Refresh } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

const activeTab = ref('US_NBA');

// ================= 日期逻辑 =================
const disabledDate = (time: Date) => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return time.getTime() >= today.getTime();
};

const getYesterdayDate = () => {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const year = yesterday.getFullYear();
  const month = String(yesterday.getMonth() + 1).padStart(2, '0');
  const day = String(yesterday.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const selectedDate = ref<string>(getYesterdayDate());

// ================= 状态变量 =================
const loading = ref(false);
const hasData = ref(false);
const agentDataStore = ref<Record<string, any>>({});
const selectedTopicIndex = ref<number>(0); // 记录当前选中的话题索引
const generatingTweet = ref(false);
const dynamicTweet = ref<string | null>(null);

// ================= 计算属性 =================
const currentAgentData = computed(() => {
  return agentDataStore.value[activeTab.value] || null;
});

// ================= 监听与事件 =================
const handleTabChange = () => {
  dynamicTweet.value = null; 
  selectedTopicIndex.value = 0; // 切换 Tab 时重置选中项
};

watch(selectedDate, () => {
  dynamicTweet.value = null; 
  selectedTopicIndex.value = 0; // 切换日期时重置选中项
});

watch(selectedTopicIndex, () => {
  dynamicTweet.value = null; // 用户点击不同话题时，清空旧推文，提示重新生成
});

// ================= 核心方法 =================
const fetchData = async () => {
  if (!selectedDate.value) return;
  loading.value = true;
  hasData.value = false;
  
  try {
    const res = await axios.get(`/db/agents/${selectedDate.value}.json?t=${Date.now()}`);
    if (res.data) {
      agentDataStore.value = res.data;
      hasData.value = !!agentDataStore.value[activeTab.value];
      selectedTopicIndex.value = 0; // 数据加载完默认选中第一个
    }
  } catch (error) {
    console.warn('Load failed:', error);
    hasData.value = false;
  } finally {
    loading.value = false;
  }
};

const triggerTweetGeneration = async () => {
  if (!currentAgentData.value || !currentAgentData.value.top_topics) return;
  
  const targetTopic = currentAgentData.value.top_topics[selectedTopicIndex.value];
  if (!targetTopic) {
    ElMessage.warning('请先选择一个话题');
    return;
  }
  
  generatingTweet.value = true;
  dynamicTweet.value = null;

  let domainName = "";
  if (activeTab.value === 'US_NBA') domainName = "NBA与中美关系";
  else if (activeTab.value === 'Taiwan_Hollywood') domainName = "好莱坞与两岸关系";
  else if (activeTab.value === 'Japan_Musk') domainName = "马斯克与中日关系";
  else if (activeTab.value === 'PH_AI') domainName = "AI技术与中菲关系";

  try {
    // 呼叫后端单点精准生成接口
    const res = await axios.post('/api/generate_agent_tweet', {
      domains: domainName,
      topic_title: targetTopic.topic,
      topic_summary: targetTopic.summary
    });
    
    if (res.data && res.data.tweet) {
      dynamicTweet.value = res.data;
      ElMessage.success('🎉 舆论引导推文生成成功！');
    } else {
      ElMessage.error('生成内容格式异常，请重试');
    }
  } catch (error) {
    ElMessage.error('推文生成失败，请检查网络或后端接口状态');
    console.error(error);
  } finally {
    generatingTweet.value = false;
  }
};

// 修改 copyTweet 函数
const copyTweet = () => {
  if (dynamicTweet.value) {
    navigator.clipboard.writeText(dynamicTweet.value);
    ElMessage.success('中文推文已复制到剪贴板！');
  }
};

onMounted(() => fetchData());
</script>

<style scoped lang="scss">
.dashboard-container { padding: 30px 40px; background-color: #f0f4f8; min-height: 100vh; }
.header-section { margin-bottom: 20px; }
.page-title { font-size: 26px; font-weight: 700; color: #1f2937; margin: 0 0 5px 0; }
.subtitle { color: #6b7280; font-size: 14px; margin: 0; }
.control-panel { display: flex; justify-content: space-between; margin-bottom: 20px; background: #fff; padding: 10px 20px; border-radius: 12px; }

.modern-card { border: none; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
.card-header { font-weight: 700; color: #374151; display: flex; justify-content: space-between; align-items: center; }

/* 话题列表 (交互升级) */
.topic-item {
  display: flex; padding: 20px; border-bottom: 1px solid #f3f4f6; transition: all 0.2s; cursor: pointer;
  
  &:hover { background-color: #f9fafb; }
  /* 选中状态的高亮效果 */
  &.active { 
    background-color: #eff6ff; 
    border-left: 4px solid #3b82f6; 
    .topic-title { color: #1d4ed8; }
  }
}
.topic-rank { 
  width: 32px; height: 32px; background: #e5e7eb; border-radius: 8px; 
  display: flex; align-items: center; justify-content: center; 
  font-size: 16px; font-weight: bold; margin-right: 15px; color: #4b5563; flex-shrink: 0;
  &.top-3 { background: #3b82f6; color: white; }
}
.topic-content { flex: 1; }
.topic-title { font-weight: 700; font-size: 16px; color: #1f2937; margin-bottom: 6px; transition: color 0.2s; }
.topic-summary { font-size: 14px; color: #6b7280; line-height: 1.6; }

/* 动态推文卡片 */
.draft-card { background: linear-gradient(to bottom right, #ffffff, #f8fafc); border: 1px solid #e2e8f0; height: 100%; min-height: 600px;}
.empty-state { padding: 60px 0; text-align: center; }
.draft-content { padding: 10px 20px; }
.draft-en {
  background: #1e293b; color: #f8fafc; padding: 25px; border-radius: 12px;
  font-size: 18px; line-height: 1.6; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  margin-bottom: 25px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
}
/* 删除原来的 .draft-en 和 .draft-zh，替换为以下样式 */
.draft-zh-only {
  background: #f8fafc; 
  border-left: 5px solid #3b82f6; 
  padding: 25px 30px; 
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.05);
  margin-bottom: 25px;
}
.draft-zh-only p { 
  margin: 0; 
  font-size: 18px; 
  color: #1e293b; 
  line-height: 1.8; 
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
  letter-spacing: 0.5px;
}
.action-bar { margin-top: 30px; display: flex; justify-content: flex-end; gap: 15px;}

/* 加载动画 */
.loading-state { padding: 40px 30px; text-align: center; }
.loading-text { color: #6b7280; font-size: 15px; margin-top: 25px; animation: pulse 2s infinite; font-weight: 500;}
@keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
.blink-tag { animation: pulse 1.5s infinite; }
</style>