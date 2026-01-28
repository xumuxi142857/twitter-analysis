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
         <span class="label">日期:</span>
         <el-date-picker v-model="selectedDate" type="date" value-format="YYYY-MM-DD" :clearable="false" @change="fetchData" />
      </div>
    </div>

    <div v-loading="loading" style="min-height: 500px;">
      <div v-if="hasData">
        
        <el-row :gutter="24">
          <el-col :span="8">
            <el-card class="modern-card" style="margin-bottom: 20px;">
              <template #header>
                <div class="card-header">
                  <span>📊 舆情立场分布</span>
                </div>
              </template>
              <div ref="pieChartRef" style="height: 220px; width: 100%;"></div>
            </el-card>

            <el-card class="modern-card list-card" :body-style="{ padding: '0' }">
              <template #header>
                <div class="card-header">
                  <span class="title-text">🔥 核心话题聚类</span>
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
                    <!--div class="topic-meta">{{ item.tweets ? item.tweets.length : 0 }} 条相关推文</div-->
                  </div>
                  <div class="arrow-icon"><el-icon><ArrowRight /></el-icon></div>
                </div>
              </div>
            </el-card>
            
             <el-card class="modern-card" style="margin-top: 20px;">
               <template #header><span>☁️ 关键词云</span></template>
               <WordCloud :data="currentData.hot_words" style="height: 200px;" />
            </el-card>
          </el-col>

          <el-col :span="16">
            <el-card class="modern-card detail-card">
              <template #header>
                <div class="card-header">
                  <span class="title-text">
                    <el-icon><ChatLineSquare /></el-icon> 
                    话题溯源与详细研判
                  </span>
                  <el-tag v-if="selectedTopic" effect="dark" type="primary">
                    {{ selectedTopic.topic }}
                  </el-tag>
                </div>
              </template>

              <div v-if="selectedTopic" class="tweets-container">
                <el-scrollbar height="850px">
                  <div v-for="(tweet, tIndex) in selectedTopic.tweets" :key="tIndex" class="tweet-card">
                    
                    <div class="tweet-header">
                      <div class="tweet-user-info">
                        <span class="username">@{{ tweet.username }}</span>
                        <!--span class="time">{{ formatDate(tweet.created_at) }}</span-->
                      </div>
                      <el-tag :type="getStanceColor(tweet.stance)" effect="light" size="small" class="stance-tag">
                        {{ getStanceLabel(tweet.stance) }}
                      </el-tag>
                    </div>

                    <div class="tweet-body">
                      <div class="tweet-trans" v-if="tweet.translation">
                        <span class="trans-badge">译</span>
                        {{ tweet.translation }}
                      </div>
                      <div class="tweet-original">{{ tweet.text }}</div>
                    </div>

                    <div class="tweet-meta-row">
                      <div class="metrics-group">
                        <span class="metric"><el-icon><ChatDotRound /></el-icon> {{ tweet.metrics?.reply || 0 }}</span>
                        <span class="metric"><el-icon><Share /></el-icon> {{ tweet.metrics?.retweet || 0 }}</span>
                        <span class="metric"><el-icon><Star /></el-icon> {{ tweet.metrics?.like || 0 }}</span>
                      </div>
                    </div>

                  </div>
                </el-scrollbar>
              </div>

              <div v-else class="empty-state">
                <el-empty description="请从左侧选择一个话题以查看推文列表" />
              </div>
            </el-card>
          </el-col>
        </el-row>

      </div>
      <el-empty v-else description="暂无数据" />
    </div>
  </div>
</template>

<script setup lang="ts">


import { ref, computed, onMounted, watch, nextTick } from 'vue';
import axios from 'axios';
import * as echarts from 'echarts'; // 引入 ECharts
import dayjs from 'dayjs';
import { ArrowRight, ChatLineSquare, ChatDotRound, Share, Star } from '@element-plus/icons-vue';
import WordCloud from './components/WordCloud.vue';

const activeTab = ref('US');
const selectedDate = ref<string>('2026-01-26');
const loading = ref(false);
const hasData = ref(false);
const regionDataStore = ref<Record<string, any>>({});
const selectedTopicIndex = ref<number>(-1);
const pieChartRef = ref<HTMLElement | null>(null);
let pieChartInstance: echarts.ECharts | null = null;

const currentData = computed(() => {
  return regionDataStore.value[activeTab.value] || { top_topics: [], hot_words: [], stance_stats: [] };
});

const selectedTopic = computed(() => {
  if (selectedTopicIndex.value === -1) return null;
  return currentData.value.top_topics[selectedTopicIndex.value] || null;
});

const handleTabChange = () => {
  selectedTopicIndex.value = -1;
  if (currentData.value.top_topics?.length > 0) selectedTopicIndex.value = 0;
  nextTick(() => renderPieChart()); // 切换 Tab 后重绘图表
};

const handleSelectTopic = (index: number) => {
  selectedTopicIndex.value = index;
};

const formatDate = (str: string) => dayjs(str).isValid() ? dayjs(str).format('MM-DD HH:mm') : str;

const getStanceColor = (stance: string) => {
  if (!stance) return 'info';
  const s = stance.toLowerCase();
  if (s.includes('positive') || s.includes('亲华')) return 'success';
  if (s.includes('negative') || s.includes('反华')) return 'danger';
  return 'warning'; // Neutral
};

const getStanceLabel = (stance: string) => {
    // 简单的映射显示
    if (!stance) return '未知';
    if (stance.includes('positive')) return '亲华';
    if (stance.includes('negative')) return '反华';
    return '中立';
}

// 渲染饼图的核心函数
const renderPieChart = () => {
  if (!pieChartRef.value || !currentData.value.stance_stats) return;
  
  if (pieChartInstance) pieChartInstance.dispose();
  pieChartInstance = echarts.init(pieChartRef.value);

  //const data = currentData.value.stance_stats; // 格式: [{name: 'xx', value: 10}, ...]
  const rawData = currentData.value.stance_stats; // 格式: [{name: 'xx', value: 10}, ...]

  const cleanedData = rawData.map(item => ({
    ...item,
    // 使用正则去掉括号及其内容，例如 "亲华(positive)" 变为 "亲华"
    name: item.name.replace(/\s*\(.*?\)\s*/g, '') 
  }));

  const option = {
    tooltip: { trigger: 'item' , formatter: '{b}: {d}%'},
    legend: { bottom: '0%', left: 'center' },
    series: [
      {
        name: '立场分布',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 5, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: false, fontSize: 16, fontWeight: 'bold' ,formatter: '{d}%'} },
        data: cleanedData,
        color: ['#10b981', '#f59e0b', '#ef4444'] // 绿(亲华)，黄(中立)，红(反华)
      }
    ]
  };
  pieChartInstance.setOption(option);
};

const fetchData = async () => {
  if (!selectedDate.value) return;
  loading.value = true;
  hasData.value = false;
  selectedTopicIndex.value = -1;
  const tempStore: any = {};

  try {
    const res = await axios.get(`/db/topic/${selectedDate.value}.json?t=${Date.now()}`);
    const data = res.data;
    if (data) {
      // 简单处理数据
      Object.keys(data).forEach(k => {
          if(k !== '_meta') tempStore[k] = data[k];
      });
      regionDataStore.value = tempStore;
      hasData.value = true;
      if (currentData.value.top_topics?.length > 0) selectedTopicIndex.value = 0;
      
      // 数据加载完后，渲染图表
      nextTick(() => renderPieChart());
    }
  } catch (error) {
    console.warn('Load failed:', error);
    hasData.value = false;
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchData();
  window.addEventListener('resize', () => pieChartInstance?.resize());
});
</script>

<style scoped lang="scss">
/* 复用之前的样式，稍作微调 */
.dashboard-container { padding: 30px 40px; background-color: #f0f4f8; min-height: 100vh; }
.header-section { margin-bottom: 20px; }
.page-title { font-size: 26px; font-weight: 700; color: #1f2937; margin: 0; }
.control-panel { display: flex; justify-content: space-between; margin-bottom: 20px; background: #fff; padding: 10px 20px; border-radius: 12px; }

.modern-card { border: none; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
.card-header { font-weight: 700; color: #374151; display: flex; justify-content: space-between; align-items: center; }

/* 话题列表 */
.topic-list { max-height: 400px; overflow-y: auto; }
.topic-item {
  display: flex; align-items: center; padding: 14px 16px; border-bottom: 1px solid #f3f4f6; cursor: pointer;
  &:hover { background-color: #f9fafb; }
  &.active { background-color: #eff6ff; border-left: 3px solid #2563eb; }
}
.topic-rank { width: 24px; height: 24px; background: #e5e7eb; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; margin-right: 10px; color: #666; }
.topic-content { flex: 1; }
.topic-title { font-weight: 600; font-size: 18px; color: #1f2937; margin-bottom: 2px; }
.topic-meta { font-size: 12px; color: #9ca3af; }

/* 推文卡片 */
.tweet-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 15px; margin-bottom: 15px; }
.tweet-header { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 12px; color: #6b7280; }
.tweet-user-info .username { font-weight: 700; color: #374151; margin-right: 8px; }

.tweet-trans { font-size: 18px; font-weight: 500; color: #111827; margin-bottom: 6px; line-height: 1.5; }
.trans-badge { background: #e0e7ff; color: #4f46e5; font-size: 14px; padding: 1px 4px; border-radius: 4px; margin-right: 4px; }
.tweet-original { font-size: 14px; color: #9ca3af; line-height: 1.4; border-top: 1px dashed #f3f4f6; padding-top: 6px; }

.tweet-meta-row { display: flex; justify-content: flex-end; margin-top: 8px; font-size: 12px; color: #9ca3af; }
.metrics-group { display: flex; gap: 15px; .metric { display: flex; align-items: center; gap: 4px; } }
</style>