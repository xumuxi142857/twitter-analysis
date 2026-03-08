<template>
  <div class="guide-page">
    <div class="header-section">
      <div class="header-content">
        <h1 class="page-title">推文引导</h1>
      </div>
      <div class="header-actions">
        <span class="label">日期:</span>
        <el-date-picker
          v-model="selectedDate"
          type="date"
          placeholder="选择日期"
          value-format="YYYY-MM-DD"
          :clearable="false"
          :disabled-date="disabledDate"
          @change="fetchData"
          size="default"
        />
      </div>
    </div>

    <div class="nav-bar">
      <el-tabs v-model="activeTab" class="custom-tabs" @tab-change="resetSelection">
        <el-tab-pane label="🇺🇸 美国" name="US"></el-tab-pane>
        <el-tab-pane label="🇯🇵 日本" name="Japan"></el-tab-pane>
        <el-tab-pane label="🇵🇭 菲律宾" name="Philippines"></el-tab-pane>
        <el-tab-pane label="🇹🇼 中国台湾" name="Taiwan"></el-tab-pane>
      </el-tabs>
    </div>

    <div v-loading="loading" class="main-content">
      <div v-if="hasData">
        <el-card class="topic-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span class="header-title">📋 待引导舆情话题</span>
              
            </div>
          </template>

          <el-table 
            :data="currentData.topics" 
            style="width: 100%" 
            highlight-current-row
            @current-change="handleTopicChange"
            :row-class-name="tableRowClassName"
          >
            <el-table-column type="index" label="No." width="60" align="center" />
            
            <el-table-column prop="topic" label="话题焦点 " min-width="400">
               <template #default="{ row }">
                 <span style="font-weight: 600;">{{ row.topic }}</span>
               </template>
            </el-table-column>
            
            <el-table-column label="状态" width="150" align="center">
              <template #default="{ row }">
                <el-button
                  v-if="activeTopic !== row"
                  type="primary"
                  link
                  @click.stop="handleTopicChange(row)"
                >
                  点击展开分析
                </el-button>
                <el-tag v-else type="primary" effect="light">正在分析</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <transition name="el-zoom-in-top">
          <div v-if="activeTopic" class="workspace-section">
            <el-row :gutter="24">
              
              <el-col :span="9">
                <div class="panel-header">
                  <div class="ph-left">
                    <el-icon><Postcard /></el-icon>
                    <span>精选推文流</span>
                  </div>
                  <!--span class="ph-sub">共 {{ activeTopic.tweets?.length || 0 }} 条</span-->
                </div>

                <div class="tweet-list-container">
                  <el-scrollbar height="650px">
                    <div v-if="activeTopic.tweets && activeTopic.tweets.length > 0" class="tweet-stack">
                      <div 
                        v-for="(tweet, idx) in activeTopic.tweets" 
                        :key="idx" 
                        :class="['tweet-card', { 'is-active': selectedTweetForDraft === tweet }]"
                        @click="handleGenerateForTweet(tweet)"
                      >
                        <div class="t-header">
                          <span class="t-author">@{{ tweet.username || 'user_unknown' }}</span>
                          <el-tag v-if="tweet.stance" size="small" :type="getStanceType(tweet.stance)" effect="light">
  {{ getStanceLabel(tweet.stance) }}
</el-tag>
                        </div>
                        
                        <div class="t-body">
                          <div class="t-trans" v-if="tweet.translation">
                            <span class="trans-badge">译</span>{{ tweet.translation }}
                          </div>
                          <div class="t-original">{{ tweet.text }}</div>
                        </div>

                        <div class="t-footer">
                          <div class="t-metrics">
                            <span><el-icon><Star /></el-icon> {{ tweet.metrics?.like || 0 }}</span>
                            <span><el-icon><Share /></el-icon> {{ tweet.metrics?.retweet || 0 }}</span>
                          </div>
                          <el-button 
                            size="small" 
                            :type="selectedTweetForDraft === tweet ? 'success' : 'primary'" 
                            :plain="selectedTweetForDraft !== tweet"
                            round
                          >
                            {{ selectedTweetForDraft === tweet ? '分析中' : '生成策略' }}
                            <el-icon class="el-icon--right"><MagicStick /></el-icon>
                          </el-button>
                        </div>
                      </div>
                    </div>
                    <el-empty v-else description="该话题下暂无推文" image-size="100" />
                  </el-scrollbar>
                </div>
              </el-col>

              <el-col :span="15">
                <div class="strategy-panel">
                  <div class="panel-header">
                    <div class="ph-left">
                      <el-icon><EditPen /></el-icon>
                      <span>智能应对策略</span>
                    </div>
                  </div>

                  <div class="strategy-content">
                    <div v-if="!selectedTweetForDraft" class="empty-state-wrapper">
                      <el-empty description="请从左侧点击一条推文，AI 将为您生成针对性回复策略" />
                    </div>

                    <div v-else class="strategy-result">
                      <div class="context-box">
                        <div class="context-label">针对目标推文：</div>
                        <div class="context-text">
                          {{ selectedTweetForDraft.translation || selectedTweetForDraft.text }}
                        </div>
                      </div>

                      <div class="draft-grid">
                        <div v-for="(val, key) in draftTypes" :key="key" :class="['draft-box', key]">
                          <div class="box-header">
                            <el-icon :size="20"><component :is="val.icon" /></el-icon>
                            <span class="box-title">{{ val.label }}</span>
                            <el-tag size="small" :type="val.tagType" effect="plain">{{ val.desc }}</el-tag>
                          </div>
                          
                          <div class="box-body">
                            <div class="ai-text">
                              {{ (activeTopic && activeTopic.drafts && activeTopic.drafts[key]) ? activeTopic.drafts[key] : 'AI 思考中...' }}
                            </div>
                          </div>

                          <div class="box-footer">
                             <el-button size="small" :type="val.btnType" plain @click="copyText(activeTopic.drafts[key])">复制文案</el-button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </el-col>
            </el-row>
          </div>
        </transition>
      </div>
      <el-empty v-else description="该日期暂无监测数据" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
import { ElMessage } from 'element-plus';
import { MagicStick, EditPen, Stamp, ChatDotRound, Coffee, Share, Star, Postcard } from '@element-plus/icons-vue';

// --- 数据定义 ---
const activeTab = ref('US');
const getYesterdayDate = () => {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  
  const year = yesterday.getFullYear();
  const month = String(yesterday.getMonth() + 1).padStart(2, '0');
  const day = String(yesterday.getDate()).padStart(2, '0');
  
  return `${year}-${month}-${day}`;
};

const getTodayDate = () => {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const disabledDate = (time: Date) => {
  const today = new Date();
  today.setHours(0, 0, 0, 0); // 把今天的时间重置到零点
  return time.getTime() > today.getTime();
};
const selectedDate = ref<string>(getTodayDate());
const loading = ref(false);
const hasData = ref(true);

const activeTopic = ref<any>(null); 
const selectedTweetForDraft = ref<any>(null); 
const regionDataStore = ref<Record<string, any>>({});
const currentData = computed(() => regionDataStore.value[activeTab.value] || { topics: [] });

// 配置项
const draftTypes = {
  authority: { label: '权威引导', icon: Stamp, desc: '引用法规/官方', btnType: 'primary', tagType: '' },
  peer: { label: '同伴引导', icon: ChatDotRound, desc: '平视/网络语', btnType: 'warning', tagType: 'warning' },
  kinship: { label: '亲情引导', icon: Coffee, desc: '共情/感性', btnType: 'danger', tagType: 'danger' }
};

// --- 方法 ---

const resetSelection = () => {
  activeTopic.value = null;
  selectedTweetForDraft.value = null;
};

const handleTopicChange = (row: any) => {
  if (activeTopic.value === row) return; 
  activeTopic.value = row;
  selectedTweetForDraft.value = null;
};

const tableRowClassName = ({ row }: { row: any }) => {
  return row === activeTopic.value ? 'highlight-row' : '';
};

const getStanceType = (stance: string) => {
  if (stance === 'positive') return 'success';
  if (stance === 'negative') return 'danger';
  return 'info';
};

const getStanceLabel = (stance: string) => {
  const map: Record<string, string> = {
    'positive': '亲华',
    'negative': '反华',
    'neutral': '中立'
  };
  // 如果遇到未知的状态，默认显示原文，防止报错
  return map[stance] || stance;
};

const fetchData = async () => {
  if (!selectedDate.value) return;
  loading.value = true;
  activeTopic.value = null;
  selectedTweetForDraft.value = null;

  const tempStore: any = { 
    US: { topics: [] }, 
    Japan: { topics: [] }, 
    Philippines: { topics: [] }, 
    Taiwan: { topics: [] } 
  };
  
  try {
    const res = await axios.get(`/db/topic/${selectedDate.value}.json`); // 确保读取的是包含翻译的topic json
    const dayData = res.data;

    if (dayData) {
      hasData.value = true;
      Object.keys(dayData).forEach(reg => {
        if (tempStore[reg] && dayData[reg]) {
          const rawTopics = dayData[reg].top_topics || [];
          const processedTopics = rawTopics.map((t: any) => ({
            ...t,
            stance: t.tweets && t.tweets.length > 0 ? t.tweets[0].stance : 'neutral'
          }));
          tempStore[reg].topics = processedTopics;
        }
      });
      regionDataStore.value = tempStore;
    } else {
      hasData.value = false;
    }
  } catch (error) {
    console.error("Fetch data error:", error);
    hasData.value = false;
  } finally {
    loading.value = false;
  }
};

const handleGenerateForTweet = async (tweet: any) => {
  if(selectedTweetForDraft.value === tweet && activeTopic.value.drafts?.authority) return;

  selectedTweetForDraft.value = tweet;

  if (!activeTopic.value.drafts) {
    activeTopic.value.drafts = { authority: '', peer: '', kinship: '' };
  }
  
  activeTopic.value.drafts = { 
    authority: "AI 正在思考策略...", 
    peer: "AI 正在组织语言...", 
    kinship: "AI 正在分析情感..." 
  };

  try {
    //const response = await axios.post('http://127.0.0.1:5000/api/generate_guide', {
    const response = await axios.post('/api/generate_guide', {
      text: tweet.translation || tweet.text, // 优先使用译文生成策略，效果更好
      topic: activeTopic.value.topic,
      region: activeTab.value
    });
    activeTopic.value.drafts = { ...response.data };
  } catch (error) {
    console.error(error);
    activeTopic.value.drafts.authority = "请求失败，请稍后重试";
  }
};

const copyText = (text: string) => {
  if(!text) return;
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('文案已复制');
  });
}

onMounted(() => fetchData());
</script>

<style scoped lang="scss">
/* 全局布局变量 */
$bg-color: #f3f6f9;
$card-radius: 12px;
$primary-color: #409eff;

.guide-page {
  padding: 20px 40px;
  background-color: $bg-color;
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* 头部样式 */
.header-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 20px;
  
  .page-title { margin: 0; font-size: 26px; color: #1f2937; }
  
  .header-actions {
    display: flex; align-items: center; gap: 10px;
    background: #fff; padding: 8px 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    .label { font-size: 13px; font-weight: 500; color: #4b5563; }
  }
}

.nav-bar { margin-bottom: 20px; }
.custom-tabs :deep(.el-tabs__nav-wrap::after) { height: 1px; background-color: #e5e7eb; }

/* 话题卡片样式 */
.topic-card {
  border: none; border-radius: $card-radius; margin-bottom: 24px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  
  .card-header { display: flex; justify-content: space-between; align-items: center; }
  .header-title { font-weight: 600; font-size: 16px; color: #374151; }
}

/* 核心工作台样式 */
.workspace-section {
  margin-top: 20px;
}

.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px; padding: 0 4px;
  
  .ph-left { display: flex; align-items: center; gap: 8px; font-weight: 600; color: #374151; font-size: 16px; }
  .ph-sub { font-size: 14px; color: #9ca3af; }
}

/* 左侧：推文列表 */
.tweet-list-container {
  padding-right: 5px; 
}

.tweet-stack {
  display: flex; flex-direction: column; gap: 12px;
}

.tweet-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    border-color: $primary-color;
  }

  &.is-active {
    border: 2px solid $primary-color;
    background: #f0f9ff;
    .t-author { color: #0369a1; }
  }

  .t-header { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 12px; color: #6b7280; }
  .t-author { font-weight: 700; color: #4b5563; }
  
  /* --- 内容样式优化 --- */
  .t-body {
    margin-bottom: 12px;
  }
  
  .t-trans {
    font-size: 16px;
    line-height: 1.5;
    color: #1f2937;
    margin-bottom: 6px;
    font-weight: 500;
    
    .trans-badge {
      display: inline-block;
      background: #e0e7ff;
      color: #3b82f6;
      font-size: 11px;
      padding: 1px 5px;
      border-radius: 4px;
      margin-right: 6px;
      vertical-align: text-bottom;
      font-weight: normal;
    }
  }
  
  .t-original {
    font-size: 13px;
    color: #9ca3af;
    line-height: 1.4;
    font-family: sans-serif;
  }
  /* ------------------ */
  
  .t-footer {
    display: flex; justify-content: space-between; align-items: center;
    .t-metrics { display: flex; gap: 12px; font-size: 14px; color: #9ca3af; .el-icon { vertical-align: -1px; } }
  }
}

/* 右侧：策略面板 */
.strategy-panel {
  background: #fff;
  border-radius: $card-radius;
  padding: 20px;
  height: 650px; 
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 12px rgba(0,0,0,0.04);
}

.strategy-content {
  flex-grow: 1;
  overflow-y: auto;
  padding-right: 5px;
}

.empty-state-wrapper {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.context-box {
  background: #f8fafc;
  border-left: 4px solid #64748b;
  padding: 12px 16px;
  margin-bottom: 20px;
  border-radius: 0 8px 8px 0;
  
  .context-label { font-size: 12px; font-weight: bold; color: #64748b; margin-bottom: 4px; }
  .context-text { font-size: 16px; color: #334155; font-style: italic; line-height: 1.4; }
}

.draft-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.draft-box {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  transition: box-shadow 0.2s;

  &:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.05); }

  .box-header {
    padding: 10px 15px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 18px;
    font-weight: 600;
    
    .box-title { flex-grow: 1; }
  }

  .box-body {
    padding: 15px;
    background: #fff;
    font-size: 18px;
    line-height: 1.6;
    color: #374151;
    min-height: 80px;
  }

  .box-footer {
    padding: 8px 15px;
    background: #f9fafb;
    border-top: 1px solid #f3f4f6;
    text-align: right;
  }
  
  &.authority {
    border-color: #bfdbfe;
    .box-header { background: #eff6ff; color: #1e40af; }
  }
  &.peer {
    border-color: #fde68a;
    .box-header { background: #fffbeb; color: #92400e; }
  }
  &.kinship {
    border-color: #fecdd3;
    .box-header { background: #fff1f2; color: #9f1239; }
  }
}

:deep(.highlight-row) {
  background-color: #ecf5ff !important;
}
</style>