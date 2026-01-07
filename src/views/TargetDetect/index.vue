<template>
  <div class="detect-page">
    <div class="header-section">
      <h1 class="page-title">重点目标监测与画像</h1>
      <p class="page-subtitle">High-Value Target Monitoring & Analysis</p>
    </div>

    <div class="control-panel">
      <el-tabs v-model="activeTab" class="custom-tabs" @tab-change="selectedTarget = null">
        <el-tab-pane label="🇺🇸 中美关系 (US)" name="US"></el-tab-pane>
        <el-tab-pane label="🇯🇵 中日关系 (Japan)" name="Japan"></el-tab-pane>
        <el-tab-pane label="🇵🇭 中菲关系 (Philippines)" name="Philippines"></el-tab-pane>
        <el-tab-pane label="🇹🇼 两岸关系 (Taiwan)" name="Taiwan"></el-tab-pane>
        <el-tab-pane label="🇨🇳 中国官方 (China)" name="China"></el-tab-pane>
      </el-tabs>
      
      <div class="right-controls">
        <el-radio-group v-model="filterType" size="large">
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="politician">政要</el-radio-button>
          <el-radio-button label="media">媒体</el-radio-button>
        </el-radio-group>
        <el-button circle :icon="Refresh" @click="fetchList" style="margin-left: 12px;" :loading="listLoading" />
      </div>
    </div>

    <div v-loading="listLoading" style="min-height: 400px;">
      
      <div v-if="filteredTargets.length > 0">
        <div class="target-grid">
          <div 
            v-for="target in filteredTargets" 
            :key="target.id"
            class="target-card"
            :class="{ active: selectedTarget?.id === target.id }"
            @click="handleSelect(target)"
          >
            <el-avatar :size="60" class="target-avatar" :style="getAvatarStyle(target.category)">
              {{ target.name.substring(0,1).toUpperCase() }}
            </el-avatar>
            <div class="target-info">
              <div class="name">{{ target.name }}</div>
              <div class="handle">@{{ target.username }}</div>
              <el-tag size="small" :type="target.category === 'politician' ? 'danger' : 'success'">
                {{ target.category === 'politician' ? '政要' : '媒体' }}
              </el-tag>
            </div>
            <div class="indicator" v-if="selectedTarget?.id === target.id">
              <el-icon><CaretBottom /></el-icon>
            </div>
          </div>
        </div>

        <transition name="el-zoom-in-top">
          <div v-if="selectedTarget" class="analysis-dashboard" v-loading="detailLoading">
            <div class="dashboard-header">
              <div class="dh-left">
                <h3><el-icon><DataLine /></el-icon> 监测指标分析: {{ selectedTarget.name }}</h3>
              </div>
              <div class="dh-right">
                <span class="filter-label">言论回溯日期:</span>
                <el-date-picker
                  v-model="tweetDateFilter"
                  type="date"
                  placeholder="选择日期筛选推文"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  :shortcuts="dateShortcuts"
                />
                <el-button circle icon="Close" @click="selectedTarget = null" style="margin-left: 10px;" />
              </div>
            </div>

            <div v-if="!selectedTarget.tweets" style="padding: 40px; text-align: center; color: #909399;">
              正在调取深度分析档案...
            </div>

            <div v-else>
              <el-row :gutter="20" style="margin-bottom: 24px;">
                <el-col :span="8">
                  <el-card class="metric-card" shadow="never">
                    <template #header><span>👤 基础档案 (Profile)</span></template>
                    <div class="bio-box">{{ selectedTarget.metrics.bio }}</div>
                    <div class="stats-grid">
                      <div class="stat-item">
                        <div class="label">日均发稿</div>
                        <div class="value">{{ selectedTarget.metrics.daily_count }}</div>
                      </div>
                    </div>
                    <div class="keywords-box">
                      <div class="label">核心关键词:</div>
                      <div class="tags">
                        <el-tag v-for="kw in selectedTarget.metrics.keywords" :key="kw" effect="light" round size="small">
                          {{ kw }}
                        </el-tag>
                      </div>
                    </div>
                  </el-card>
                </el-col>
                <el-col :span="8">
                  <el-card class="metric-card" shadow="never">
                    <template #header><span>🧩 对中立场矩阵 (Stance)</span></template>
                    <StanceMatrix :data="selectedTarget.stance_matrix" />
                  </el-card>
                </el-col>
                <el-col :span="8">
                  <el-card class="metric-card" shadow="never">
                    <template #header><span>📡 影响类型分布 (Influence)</span></template>
                    <InfluencePie :data="selectedTarget.influence_type" />
                  </el-card>
                </el-col>
              </el-row>

              <div class="tweets-section">
                <div class="section-title">
                  <el-icon><ChatLineSquare /></el-icon>
                  <span>言论回溯与立场研判 ({{ tweetDateFilter || '全部日期' }})</span>
                  <el-tag type="info" size="small" round style="margin-left: 10px">
                    共找到 {{ filteredTweets.length }} 条相关记录
                  </el-tag>
                </div>

                <el-scrollbar max-height="500px">
                  <div v-if="filteredTweets.length > 0" class="tweet-grid">
                    <div v-for="(tweet, idx) in filteredTweets" :key="idx" class="tweet-card">
                      <div class="t-header">
                        <span class="t-time">{{ formatDate(tweet.created_at) }}</span>
                        <el-tag :type="getStanceColor(tweet.stance)" size="small" effect="dark">
                          {{ tweet.stance }}
                        </el-tag>
                      </div>
                      <div class="t-body">{{ tweet.text }}</div>
                      <div class="t-footer">
                        <span><el-icon><ChatDotRound /></el-icon> {{ tweet.metrics?.reply }}</span>
                        <span><el-icon><Share /></el-icon> {{ tweet.metrics?.retweet }}</span>
                        <span><el-icon><Star /></el-icon> {{ tweet.metrics?.like }}</span>
                      </div>
                    </div>
                  </div>
                  <el-empty v-else description="该日期下暂无收录的高热度推文 (尝试清除日期或选择其他日期)" />
                </el-scrollbar>
              </div>
            </div>

          </div>
        </transition>
      </div>
      
      <el-empty v-else-if="!listLoading" description="该板块下暂无监测目标配置" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
import dayjs from 'dayjs';
import { CaretBottom, DataLine, Refresh, Close, ChatLineSquare, ChatDotRound, Share, Star } from '@element-plus/icons-vue';
import StanceMatrix from '@/views/AccountRec/components/StanceMatrix.vue';
import InfluencePie from '@/views/AccountRec/components/InfluencePie.vue';
import type { DetectData, TargetProfile } from '@/types';

const activeTab = ref('US');
const filterType = ref('all');
const listLoading = ref(false);
const detailLoading = ref(false); // 新增详情加载状态
const selectedTarget = ref<TargetProfile | null>(null);
const dbData = ref<Record<string, DetectData>>({});
const tweetDateFilter = ref<string | null>(null);

const currentData = computed(() => dbData.value[activeTab.value] || { targets: [] });

const filteredTargets = computed(() => {
  const all = currentData.value.targets || [];
  if (filterType.value === 'all') return all;
  return all.filter(t => t.category === filterType.value);
});

const filteredTweets = computed(() => {
  if (!selectedTarget.value || !selectedTarget.value.tweets) return [];
  let tweets = selectedTarget.value.tweets;
  if (tweetDateFilter.value) {
    const targetDate = dayjs(tweetDateFilter.value).format('YYYY-MM-DD');
    tweets = tweets.filter(t => dayjs(t.created_at).format('YYYY-MM-DD') === targetDate);
  }
  return tweets;
});

const dateShortcuts = [
  { text: '今天', value: new Date() },
  { text: '昨天', value: () => { const date = new Date(); date.setTime(date.getTime() - 3600 * 1000 * 24); return date; } },
];

// 1. 获取轻量级列表
const fetchList = async () => {
  listLoading.value = true;
  selectedTarget.value = null;
  try {
    const res = await axios.get('/db/detect/list.json?t=' + new Date().getTime());
    if (res.data) dbData.value = res.data;
  } catch (error) {
    console.error("List Fetch Error", error);
  } finally {
    listLoading.value = false;
  }
};

// 2. 按需获取详情
const handleSelect = async (summaryTarget: TargetProfile) => {
  // 先把 summary 信息展示出来，占位
  selectedTarget.value = summaryTarget; 
  tweetDateFilter.value = null;
  
  // 滚动
  setTimeout(() => window.scrollTo({ top: 350, behavior: 'smooth' }), 100);

  // 开始加载详情
  detailLoading.value = true;
  try {
    // 根据 ID (即文件名) 去 details 文件夹找数据
    const res = await axios.get(`/db/detect/details/${summaryTarget.id}?t=` + new Date().getTime());
    if (res.data) {
      // 合并数据：把详情里的 tweets, stance_matrix 等合并到当前对象
      selectedTarget.value = { ...summaryTarget, ...res.data };
    }
  } catch (error) {
    console.error("Detail Fetch Error", error);
  } finally {
    detailLoading.value = false;
  }
};

const formatDate = (str: string) => dayjs(str).isValid() ? dayjs(str).format('YYYY-MM-DD HH:mm') : str;
const getStanceColor = (s: string) => {
  if (s === 'positive') return 'success';
  if (s === 'negative') return 'danger';
  return 'info';
};
const getAvatarStyle = (cat: string) => ({ backgroundColor: cat === 'politician' ? '#e11d48' : '#059669' });

onMounted(() => fetchList());
</script>

<style scoped lang="scss">
.detect-page { padding: 30px 60px; background-color: #f0f4f8; min-height: 100vh; }
.header-section { margin-bottom: 30px; text-align: center; }
.page-title { font-size: 28px; font-weight: 700; color: #1f2937; margin: 0; }
.page-subtitle { font-size: 14px; color: #6b7280; margin-top: 8px; }
.control-panel { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; background: #fff; padding: 10px 20px; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }

/* Grid */
.target-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }
.target-card {
  background: white; border-radius: 16px; padding: 20px; display: flex; align-items: center; gap: 16px; cursor: pointer; border: 2px solid transparent; transition: all 0.3s ease; position: relative;
  &:hover { transform: translateY(-3px); box-shadow: 0 10px 15px rgba(0,0,0,0.08); }
  &.active { border-color: #2563eb; background: #eff6ff; .indicator { opacity: 1; transform: translateY(0); } }
  .target-avatar { font-size: 24px; font-weight: bold; color: white; }
  .target-info { flex: 1; .name { font-weight: 700; color: #1f2937; } .handle { font-size: 13px; color: #6b7280; } }
  .indicator { position: absolute; bottom: -22px; left: 50%; margin-left: -10px; color: #2563eb; font-size: 24px; opacity: 0; transform: translateY(-5px); transition: all 0.3s; }
}

/* Dashboard */
.analysis-dashboard { background: #fff; border-radius: 16px; padding: 24px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); border: 1px solid #e5e7eb; }
.dashboard-header {
  display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f3f4f6; margin-bottom: 20px; padding-bottom: 10px;
  h3 { margin: 0; display: flex; align-items: center; gap: 10px; color: #1f2937; }
  .dh-right { display: flex; align-items: center; gap: 10px; }
  .filter-label { font-size: 14px; color: #6b7280; font-weight: 600; }
}

.metric-card { height: 100%; border: none; background: #f9fafb; border-radius: 12px; :deep(.el-card__header) { border-bottom: none; font-weight: 600; color: #4b5563; } }
.bio-box { font-size: 14px; color: #4b5563; line-height: 1.6; margin-bottom: 20px; background: #fff; padding: 12px; border-radius: 8px; border: 1px solid #e5e7eb; }
.stats-grid { display: flex; gap: 15px; margin-bottom: 20px; .stat-item { flex: 1; background: #fff; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #e5e7eb; .label { font-size: 12px; color: #9ca3af; } .value { font-size: 20px; font-weight: 700; color: #2563eb; } } }
.keywords-box { .label { font-size: 12px; color: #9ca3af; margin-bottom: 8px; } .tags { display: flex; flex-wrap: wrap; gap: 8px; } }

.tweets-section { margin-top: 20px; border-top: 1px dashed #e5e7eb; padding-top: 20px; }
.section-title { font-size: 16px; font-weight: 700; color: #374151; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.tweet-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.tweet-card {
  background: #f9fafb; border-radius: 12px; padding: 16px; border: 1px solid #f3f4f6; display: flex; flex-direction: column; gap: 10px; transition: transform 0.2s;
  &:hover { background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.05); transform: translateY(-2px); border-color: #e5e7eb; }
  .t-header { display: flex; justify-content: space-between; align-items: center; .t-time { font-size: 12px; color: #9ca3af; } }
  .t-body { font-size: 14px; color: #374151; line-height: 1.5; flex: 1; }
  .t-footer { display: flex; gap: 16px; font-size: 12px; color: #9ca3af; span { display: flex; align-items: center; gap: 4px; } }
}
</style>