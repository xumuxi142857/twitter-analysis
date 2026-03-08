<template>
  <div class="dashboard-container">
    <div class="header-section">
      <h1 class="page-title">智能体研判</h1>
    </div>
    
    <div class="control-panel">
      <div class="left-controls">
        <el-tabs v-model="activeTab" class="custom-tabs" @tab-change="handleTabChange">
          <el-tab-pane label="NBA & 中美" name="US_NBA"></el-tab-pane>
          <el-tab-pane label="好莱坞 & 两岸" name="Taiwan_Hollywood"></el-tab-pane>
          <el-tab-pane label="马斯克 & 中日" name="Japan_Musk"></el-tab-pane>
          <el-tab-pane label="AI & 中菲" name="PH_AI"></el-tab-pane>
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
      <div v-if="hasData && currentAgentData">
        <el-row :gutter="24">
          
          <el-col :span="14">
            <el-card class="modern-card list-card" style="margin-bottom: 20px;" :body-style="{ padding: '0' }">
              <template #header>
                <div class="card-header">
                  <span class="title-text">📌 {{ currentAgentData.domain1_name }} 焦点话题</span>
                </div>
              </template>
              <el-scrollbar height="260px">
                <div class="topic-list">
                  <div 
                    v-for="(item, index) in currentAgentData.domain1_topics" 
                    :key="'d1-'+index" 
                    class="topic-item"
                    :class="{ active: selectedGroup === 'domain1' && selectedTopicIndex === index }"
                    @click="selectTopic('domain1', index)"
                  >
                    <div class="topic-rank" :class="{'top-3': index < 3}">{{ item.rank || (index + 1) }}</div>
                    <div class="topic-content">
                      <div class="topic-title">{{ item.topic }}</div>
                      <div class="topic-summary">{{ item.summary }}</div>
                    </div>
                  </div>
                  <el-empty v-if="!currentAgentData.domain1_topics?.length" description="暂无话题" :image-size="60"/>
                </div>
              </el-scrollbar>
            </el-card>

            <el-card class="modern-card list-card" :body-style="{ padding: '0' }">
              <template #header>
                <div class="card-header">
                  <span class="title-text">{{ currentAgentData.domain2_name }} 焦点话题</span>
                </div>
              </template>
              <el-scrollbar height="260px">
                <div class="topic-list">
                  <div 
                    v-for="(item, index) in currentAgentData.domain2_topics" 
                    :key="'d2-'+index" 
                    class="topic-item"
                    :class="{ active: selectedGroup === 'domain2' && selectedTopicIndex === index }"
                    @click="selectTopic('domain2', index)"
                  >
                    <div class="topic-rank" :class="{'top-3': index < 3}">{{ item.rank || (index + 1) }}</div>
                    <div class="topic-content">
                      <div class="topic-title">{{ item.topic }}</div>
                      <div class="topic-summary">{{ item.summary }}</div>
                    </div>
                  </div>
                  <el-empty v-if="!currentAgentData.domain2_topics?.length" description="暂无话题" :image-size="60"/>
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
                <p class="loading-text">智能体正在针对选定领域构思推文...</p>
              </div>

              <div v-else-if="dynamicTweet" class="draft-content">
                <div class="draft-zh-only">
                  <p>{{ dynamicTweet.tweet }}</p>
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
                <el-empty description="请从左侧选取任意领域的单一话题，生成专递推文" :image-size="100">
                  <el-button type="primary" size="large" icon="MagicStick" @click="triggerTweetGeneration" round>
                    ✨ 为选中话题拟写推文
                  </el-button>
                </el-empty>
              </div>
            </el-card>
          </el-col>

        </el-row>
      </div>
      <el-empty v-else description="该日期暂无数据 (请确保运行了当天的分析任务)" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import axios from 'axios';
import { Promotion, DocumentCopy, MagicStick, Refresh } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

const activeTab = ref('US_NBA');

// ================= 日期逻辑 (改为默认今天) =================
const disabledDate = (time: Date) => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return time.getTime() > today.getTime(); // 修改点：允许选择今天
};

const getTodayDate = () => {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const selectedDate = ref<string>(getTodayDate());

// ================= 状态变量 =================
const loading = ref(false);
const hasData = ref(false);
const agentDataStore = ref<Record<string, any>>({});

// 记录选中的是上方列表(domain1)还是下方列表(domain2)
const selectedGroup = ref<'domain1' | 'domain2'>('domain1');
const selectedTopicIndex = ref<number>(0); 

const generatingTweet = ref(false);
const dynamicTweet = ref<{tweet: string} | null>(null);

// ================= 计算属性 =================
const currentAgentData = computed(() => {
  return agentDataStore.value[activeTab.value] || null;
});

// ================= 监听与事件 =================
const handleTabChange = () => {
  dynamicTweet.value = null; 
  selectedGroup.value = 'domain1';
  selectedTopicIndex.value = 0; 
};

watch(selectedDate, () => {
  dynamicTweet.value = null; 
  selectedGroup.value = 'domain1';
  selectedTopicIndex.value = 0;
  // 切换日期后自动请求数据
});

const selectTopic = (group: 'domain1' | 'domain2', index: number) => {
  selectedGroup.value = group;
  selectedTopicIndex.value = index;
  dynamicTweet.value = null; // 切换话题后清空右侧推文
};

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
      selectedGroup.value = 'domain1';
      selectedTopicIndex.value = 0; 
    }
  } catch (error) {
    console.warn('Load failed:', error);
    hasData.value = false;
  } finally {
    loading.value = false;
  }
};

const triggerTweetGeneration = async () => {
  if (!currentAgentData.value) return;
  
  // 判断当前选中的是哪个领域的话题
  const topicList = selectedGroup.value === 'domain1' 
                    ? currentAgentData.value.domain1_topics 
                    : currentAgentData.value.domain2_topics;
  const targetDomainName = selectedGroup.value === 'domain1' 
                           ? currentAgentData.value.domain1_name 
                           : currentAgentData.value.domain2_name;

  const targetTopic = topicList[selectedTopicIndex.value];
  if (!targetTopic) {
    ElMessage.warning('请先选择一个有效话题');
    return;
  }
  
  generatingTweet.value = true;
  dynamicTweet.value = null;

  try {
    // 调用后端接口，只传入当前确切的一个领域名称（如 "US" 或 "NBA"）
    const res = await axios.post('/api/generate_agent_tweet', {
      domains: targetDomainName,
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

const copyTweet = () => {
  if (dynamicTweet.value?.tweet) {
    navigator.clipboard.writeText(dynamicTweet.value.tweet);
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
.card-header { font-weight: 700; color: #374151; display: flex; justify-content: space-between; align-items: center; padding: 12px 20px;}

/* 话题列表 (交互升级) */
.topic-item {
  display: flex; padding: 15px 20px; border-bottom: 1px solid #f3f4f6; transition: all 0.2s; cursor: pointer;
  
  &:hover { background-color: #f9fafb; }
  /* 选中状态的高亮效果 */
  &.active { 
    background-color: #eff6ff; 
    border-left: 4px solid #3b82f6; 
    .topic-title { color: #1d4ed8; }
  }
}
.topic-rank { 
  width: 28px; height: 28px; background: #e5e7eb; border-radius: 6px; 
  display: flex; align-items: center; justify-content: center; 
  font-size: 14px; font-weight: bold; margin-right: 15px; color: #4b5563; flex-shrink: 0;
  &.top-3 { background: #3b82f6; color: white; }
}
.topic-content { flex: 1; }
.topic-title { font-weight: 700; font-size: 15px; color: #1f2937; margin-bottom: 4px; transition: color 0.2s; }
.topic-summary { font-size: 13px; color: #6b7280; line-height: 1.5; }

/* 动态推文卡片 */
.draft-card { background: linear-gradient(to bottom right, #ffffff, #f8fafc); border: 1px solid #e2e8f0; height: 100%; min-height: 620px;}
.empty-state { padding: 60px 0; text-align: center; }
.draft-content { padding: 10px 20px; }

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