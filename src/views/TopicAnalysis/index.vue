<template>
  <div class="dashboard-container">
    <div class="header-section">
      <h1 class="page-title">话题分析</h1>
    </div>
    
    <div class="control-panel">
      <div class="left-controls">
        <el-tabs v-model="activeTab" class="custom-tabs" @tab-change="handleTabChange">
          <el-tab-pane label="🇺🇸 美国" name="US"></el-tab-pane>
          <el-tab-pane label="🇯🇵 日本" name="Japan"></el-tab-pane>
          <el-tab-pane label="🇵🇭 菲律宾" name="Philippines"></el-tab-pane>
          <el-tab-pane label="🇹🇼 中国台湾" name="Taiwan"></el-tab-pane>
        </el-tabs>
      </div>

      <div class="right-controls">
        <span class="label">数据日期:</span>
        <el-date-picker
          v-model="selectedDate"
          type="date"
          placeholder="选择日期"
          :disabled-date="disabledDate"
          value-format="YYYY-MM-DD"
          @change="fetchData"
          :clearable="false"
        />
      </div>
    </div>

    <div v-loading="loading" style="min-height: 500px;">
      <div v-if="hasData">
        
        <el-row :gutter="24">
          <el-col :span="10">
            <el-card class="modern-card list-card" :body-style="{ padding: '0' }">
              <template #header>
                <div class="card-header">
                  <span class="title-text">🔥 热门话题 </span>
                  <el-tag type="info" size="small">点击话题查看详情</el-tag>
                </div>
              </template>
              
              <div class="topic-list">
                <div 
                  v-for="(item, index) in currentData.top_topics" 
                  :key="index"
                  class="topic-item"
                  :class="{ active: selectedTopicIndex === index }"
                  @click="handleSelectTopic(index)"
                >
                  <div class="topic-rank">{{ index + 1 }}</div>
                  <div class="topic-content">
                    <div class="topic-title">{{ item.topic }}</div>
                  </div>
                  <div class="arrow-icon">
                    <el-icon><ArrowRight /></el-icon>
                  </div>
                </div>
              </div>
            </el-card>

            <el-card class="modern-card" style="margin-top: 20px;">
               <template #header><span>☁️ 词云展示</span></template>
               <WordCloud :data="currentData.hot_words" style="height: 250px;" />
            </el-card>
          </el-col>

          <el-col :span="14">
            <el-card class="modern-card detail-card">
              <template #header>
                <div class="card-header">
                  <span class="title-text">
                    <el-icon><ChatLineSquare /></el-icon> 
                    舆情溯源与立场研判
                  </span>
                </div>
              </template>

              <div v-if="selectedTopic" class="tweets-container">
                <div class="selected-topic-banner">
                  当前话题：{{ selectedTopic.topic }}
                </div>

                <el-scrollbar height="920px">
                  <div v-for="(tweet, tIndex) in selectedTopic.tweets" :key="tIndex" class="tweet-card">
                    
                    <div class="tweet-header">
                      <div class="tweet-user-info">
                        <span class="username">@{{ tweet.username }}</span>
                      </div>
                      <el-tag :type="getStanceColor(tweet.stance)" effect="dark" size="small" class="stance-tag">
                        {{ getStanceLabel(tweet.stance) }}
                      </el-tag>
                    </div>

                    <div class="tweet-body">
                      <div class="tweet-trans" v-if="tweet.translation">
                        <span class="trans-badge">译</span>
                        {{ tweet.translation }}
                      </div>
                      
                      <div class="tweet-original">
                        {{ tweet.text }}
                      </div>
                    </div>

                    <div class="tweet-meta-row">
                      <div class="metrics-group">
                        <span class="metric" title="Replies">
                          <el-icon><ChatDotRound /></el-icon> {{ tweet.metrics?.reply || 0 }}
                        </span>
                        <span class="metric" title="Retweets">
                          <el-icon><Share /></el-icon> {{ tweet.metrics?.retweet || 0 }}
                        </span>
                        <span class="metric" title="Likes">
                          <el-icon><Star /></el-icon> {{ tweet.metrics?.like || 0 }}
                        </span>
                      </div>
                    </div>

                  </div>
                </el-scrollbar>
              </div>

              <div v-else class="empty-state">
                <el-empty description="请从左侧选择一个话题以查看分析详情" />
              </div>
            </el-card>
          </el-col>
        </el-row>

      </div>
      <el-empty v-else description="暂无数据，请切换日期或运行分析脚本" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
import dayjs from 'dayjs';
import { ArrowRight, ChatLineSquare, Clock, ChatDotRound, Share, Star } from '@element-plus/icons-vue';
import WordCloud from './components/WordCloud.vue';
import type { RegionAnalysisData, TopicCluster } from '@/types';

const activeTab = ref('US');
const selectedDate = ref<string>('2026-01-26');
const loading = ref(false);
const hasData = ref(false);
const regionDataStore = ref<Record<string, RegionAnalysisData>>({});
const selectedTopicIndex = ref<number>(-1);

const currentData = computed(() => {
  return regionDataStore.value[activeTab.value] || { top_topics: [], hot_words: [] };
});

const selectedTopic = computed<TopicCluster | null>(() => {
  if (selectedTopicIndex.value === -1) return null;
  return currentData.value.top_topics[selectedTopicIndex.value] || null;
});

const disabledDate = (time: Date) => time.getTime() > Date.now();

const handleTabChange = () => {
  selectedTopicIndex.value = -1;
  if (currentData.value.top_topics.length > 0) {
    selectedTopicIndex.value = 0;
  }
};

const handleSelectTopic = (index: number) => {
  selectedTopicIndex.value = index;
};

const fetchData = async () => {
  if (!selectedDate.value) return;
  loading.value = true;
  hasData.value = false;
  selectedTopicIndex.value = -1;

  // 初始化结构
  const tempStore: Record<string, RegionAnalysisData> = {
    US: { region: 'US', time_range: [selectedDate.value, selectedDate.value], top_topics: [], hot_words: [] },
    Japan: { region: 'Japan', time_range: [selectedDate.value, selectedDate.value], top_topics: [], hot_words: [] },
    Philippines: { region: 'Philippines', time_range: [selectedDate.value, selectedDate.value], top_topics: [], hot_words: [] },
    Taiwan: { region: 'Taiwan', time_range: [selectedDate.value, selectedDate.value], top_topics: [], hot_words: [] }
  };

  try {
    // 请求单日数据
    const res = await axios.get(`/db/topic/${selectedDate.value}.json?t=${Date.now()}`);
    const data = res.data;

    if (data) {
      Object.keys(data).forEach(region => {
        if (tempStore[region] && region !== '_meta') {
          tempStore[region].top_topics = data[region].top_topics || [];
          tempStore[region].hot_words = data[region].hot_words || [];
        }
      });
      
      regionDataStore.value = tempStore;
      hasData.value = true;
      
      if (currentData.value.top_topics.length > 0) {
        selectedTopicIndex.value = 0;
      }
    }
  } catch (error) {
    console.error('Data load failed:', error);
    hasData.value = false;
  } finally {
    loading.value = false;
  }
};

const getStanceColor = (stance: string) => {
  if (stance === 'positive') return 'success';
  if (stance === 'negative') return 'danger';
  return 'info';
};

const getStanceLabel = (stance: string) => {
  const map: Record<string, string> = { 'positive': '正面', 'neutral': '中性', 'negative': '负面' };
  return map[stance] || stance;
};

onMounted(() => fetchData());
</script>

<style scoped lang="scss">
.dashboard-container { padding: 30px 60px; background-color: #f0f4f8; min-height: 100vh; }
.header-section { margin-bottom: 20px; text-align: center; }
.page-title { font-size: 28px; font-weight: 700; color: #1f2937; margin: 0; }

.control-panel {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;
  background: #ffffff; padding: 10px 20px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
  .right-controls { display: flex; align-items: center; gap: 10px; font-weight: bold; color: #6b7280; }
}

.modern-card { border: none; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }

/* 左侧样式 */
.topic-list { max-height: 650px; overflow-y: auto; }
.topic-item {
  display: flex; align-items: center; padding: 16px 20px; border-bottom: 1px solid #f3f4f6; cursor: pointer; transition: all 0.2s;
  &:hover { background-color: #f9fafb; }
  &.active { background-color: #eff6ff; border-left: 4px solid #2563eb; 
    .topic-rank { background: #2563eb; color: white; }
    .topic-title { color: #2563eb; }
  }
}
.topic-rank {
  width: 24px; height: 24px; border-radius: 50%; background: #e5e7eb; color: #6b7280;
  display: flex; justify-content: center; align-items: center; font-size: 12px; font-weight: bold; margin-right: 12px;
}
.topic-content { flex: 1; }
.topic-title { font-weight: 600; color: #374151; font-size: 15px; margin-bottom: 4px; line-height: 1.4; }
.arrow-icon { color: #d1d5db; }

/* 右侧推文详情样式 */
.selected-topic-banner {
  background: #f0f9ff; border: 1px solid #b9e6fe; color: #0369a1;
  padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-weight: 600;
}
.tweet-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; margin-bottom: 16px;
  transition: transform 0.2s; display: flex; flex-direction: column; gap: 12px;
  &:hover { box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05); transform: translateY(-2px); }
}

.tweet-header {
  display: flex; justify-content: space-between; align-items: center;
  .username { font-weight: 800; color: #111827; font-size: 14px; }
  .stance-tag { font-weight: bold; }
}

.tweet-body {
  display: flex; flex-direction: column; gap: 8px;
}

/* 翻译部分样式 */
.tweet-trans {
  font-size: 15px; font-weight: 600; color: #1f2937; line-height: 1.6;
  .trans-badge {
    display: inline-block; background: #e0e7ff; color: #3b82f6; font-size: 11px; padding: 1px 5px; 
    border-radius: 4px; margin-right: 6px; vertical-align: text-bottom;
  }
}

/* 原文部分样式 */
.tweet-original {
  font-size: 13px; color: #6b7280; line-height: 1.5; font-family: sans-serif;
  padding-top: 6px; border-top: 1px dashed #f3f4f6;
}

.tweet-meta-row {
  display: flex; justify-content: flex-end; align-items: center;
  padding-top: 8px; font-size: 12px; color: #9ca3af;
  .metrics-group {
    display: flex; gap: 16px;
    .metric { display: flex; align-items: center; gap: 4px; }
  }
}

.empty-state { display: flex; justify-content: center; align-items: center; height: 400px; color: #9ca3af; }
</style>