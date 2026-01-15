<template>
  <div class="account-page">
    <div class="header-section">
      <h1 class="page-title">账号推荐</h1>
    </div>

    <div class="control-panel">
      <div class="left-controls">
        <el-tabs v-model="activeTab" class="custom-tabs" @tab-change="selectedUser = null">
          <el-tab-pane label="🇺🇸 中美关系" name="US"></el-tab-pane>
          <el-tab-pane label="🇯🇵 中日关系" name="Japan"></el-tab-pane>
          <el-tab-pane label="🇵🇭 中菲关系" name="Philippines"></el-tab-pane>
          <el-tab-pane label="🇹🇼 两岸关系" name="Taiwan"></el-tab-pane>
        </el-tabs>
      </div>

      <div class="right-controls">
        <span class="label">日期:</span>
        <el-date-picker
          v-model="selectedDate"
          type="date"
          placeholder="选择日期"
          value-format="YYYY-MM-DD"
          :disabled-date="disabledDate"
          :clearable="false"
          @change="fetchData"
        />
      </div>
    </div>

    <div v-loading="loading" style="min-height: 400px;">
      
      <div v-if="hasData">
        <el-card class="modern-card">
          <template #header>
            <div class="card-header">
              <span>👥 用户简述</span>
            </div>
          </template>
          
          <el-table 
            :data="currentData.top_users" 
            style="width: 100%"
            @row-click="handleRowClick"
            highlight-current-row
          >
            <el-table-column type="index" label="#" width="50" align="center" />
            
            <el-table-column label="用户账号" width="220">
              <template #default="{ row }">
                <div class="user-cell">
                  <el-avatar :size="32" class="avatar-bg">{{ row.username.substring(0,1).toUpperCase() }}</el-avatar>
                  <div class="user-info-col">
                    <span class="username">@{{ row.username }}</span>
                    <span class="tweet-count">热门推文: {{ row.tweets ? row.tweets.length : 0 }}</span>
                  </div>
                </div>
              </template>
            </el-table-column>

            <el-table-column prop="info" label="情报简述 " min-width="300">
              <template #default="{ row }">
                <span class="info-text">{{ row.info }}</span>
              </template>
            </el-table-column>
            
            <el-table-column label="操作" width="120" align="center">
              <template #default="{ row }">
                <el-button 
                  type="primary" 
                  size="small" 
                  plain 
                  round
                  @click.stop="handleRowClick(row)"
                >
                  查看画像
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <transition name="el-zoom-in-top">
          <div v-if="selectedUser" class="profile-section">
            <div class="profile-header">
              <h3>
                <el-icon><UserFilled /></el-icon> 
                深度画像分析: @{{ selectedUser.username }}
              </h3>
              <el-button circle icon="Close" @click="selectedUser = null" />
            </div>

            <el-row :gutter="24" style="margin-bottom: 24px;">
              <el-col :span="14">
                <el-card shadow="never" class="chart-card">
                  <template #header><span>🧩 对中立场矩阵 </span></template>
                  <StanceMatrix :data="selectedUser.stance_matrix" />
                </el-card>
              </el-col>
              
              <el-col :span="10">
                <el-card shadow="never" class="chart-card">
                  <template #header><span>❤️ 影响类型情感判断</span></template>
                  <InfluencePie :data="selectedUser.influence_type" />
                </el-card>
              </el-col>
            </el-row>

            <div class="tweets-section">
              <div class="section-subtitle">
                <el-icon><ChatLineSquare /></el-icon> 最新言论立场研判 
              </div>
              
              <el-scrollbar max-height="500px">
                <div v-if="selectedUser.tweets && selectedUser.tweets.length > 0" class="tweet-grid">
                  <div v-for="(tweet, idx) in selectedUser.tweets" :key="idx" class="tweet-item-card">
                    <div class="t-header">
                      <el-tag :type="getStanceColor(tweet.stance)" size="small" effect="dark">
                        {{ getStanceLabel(tweet.stance) }}
                      </el-tag>
                    </div>
                    <div class="t-content">{{ tweet.text }}</div>
                    <div class="t-footer">
                      <span><el-icon><ChatDotRound /></el-icon> {{ tweet.metrics?.reply }}</span>
                      <span><el-icon><Share /></el-icon> {{ tweet.metrics?.retweet }}</span>
                      <span><el-icon><Star /></el-icon> {{ tweet.metrics?.like }}</span>
                    </div>
                  </div>
                </div>
                <el-empty v-else description="暂无高热度推文记录" :image-size="80" />
              </el-scrollbar>
            </div>

          </div>
        </transition>
      </div>

      <el-empty v-else description="该日期暂无账号数据" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
import { UserFilled, Close, ChatLineSquare, ChatDotRound, Share, Star } from '@element-plus/icons-vue';
import StanceMatrix from './components/StanceMatrix.vue';
import InfluencePie from './components/InfluencePie.vue';
import type { AccountAnalysisData, UserProfile } from '@/types';

const activeTab = ref('US');
// 修改：改为单个日期字符串
const selectedDate = ref<string>('2025-12-25');
const loading = ref(false);
const hasData = ref(true);
const selectedUser = ref<UserProfile | null>(null);
const regionDataStore = ref<Record<string, AccountAnalysisData>>({});

const currentData = computed(() => {
  return regionDataStore.value[activeTab.value] || { region: 'Unknown', time_range: ['-', '-'], top_users: [] };
});

const disabledDate = (time: Date) => time.getTime() > Date.now();

const getStanceColor = (s: string) => {
  if (s === 'positive') return 'success';
  if (s === 'negative') return 'danger';
  return 'info';
};

// 新增：立场中文转换
const getStanceLabel = (s: string) => {
  const map: Record<string, string> = {
    'positive': '正面',
    'negative': '负面',
    'neutral': '中立'
  };
  return map[s] || s;
};

const fetchData = async () => {
  if (!selectedDate.value) return;
  loading.value = true;
  hasData.value = false;
  selectedUser.value = null; 

  const tempStore: Record<string, AccountAnalysisData> = {
    US: { region: 'US', time_range: [selectedDate.value, selectedDate.value], top_users: [] },
    Japan: { region: 'Japan', time_range: [selectedDate.value, selectedDate.value], top_users: [] },
    Philippines: { region: 'Philippines', time_range: [selectedDate.value, selectedDate.value], top_users: [] },
    Taiwan: { region: 'Taiwan', time_range: [selectedDate.value, selectedDate.value], top_users: [] }
  };

  try {
    // 修改：直接请求单日数据，不再循环和合并
    const res = await axios.get(`/db/account/${selectedDate.value}.json`);
    const data = res.data;

    if (data) {
      Object.keys(data).forEach(region => {
        if (tempStore[region] && region !== '_meta') {
          // 直接赋值当日用户数据
          tempStore[region].top_users = data[region].top_users || [];
        }
      });
      
      // 按推文数量简单排序
      Object.keys(tempStore).forEach(r => {
        tempStore[r].top_users.sort((a, b) => (b.tweets?.length || 0) - (a.tweets?.length || 0));
      });

      regionDataStore.value = tempStore;
      hasData.value = true;
    } else {
      hasData.value = false;
    }
  } catch (error) {
    console.error('Fetch error:', error);
    hasData.value = false;
  } finally {
    loading.value = false;
  }
};

const handleRowClick = (row: UserProfile) => {
  selectedUser.value = row;
  setTimeout(() => { window.scrollTo({ top: 500, behavior: 'smooth' }); }, 100);
};

onMounted(() => fetchData());
</script>

<style scoped lang="scss">
.account-page { padding: 30px 60px; background-color: #f0f4f8; min-height: 100vh; }
.header-section { margin-bottom: 20px; text-align: center; }
.page-title { font-size: 28px; font-weight: 700; color: #1f2937; margin: 0; }
.control-panel { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; background: #fff; padding: 10px 20px; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }

.modern-card { border: none; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.user-cell { display: flex; align-items: center; gap: 12px; }
.avatar-bg { background: #3b82f6; color: white; font-weight: 700; }
.user-info-col { display: flex; flex-direction: column; }
.username { font-weight: 600; color: #1f2937; font-size: 14px; }
.tweet-count { font-size: 12px; color: #9ca3af; }
.info-text { color: #4b5563; font-size: 14px; }

/* 详情区 */
.profile-section {
  margin-top: 30px; background: #fff; padding: 24px; border-radius: 16px; 
  box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); border: 1px solid #e5e7eb;
}
.profile-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #f3f4f6;
  h3 { margin: 0; display: flex; align-items: center; gap: 10px; color: #1f2937; }
}
.chart-card { border: none; background: #f9fafb; border-radius: 12px; :deep(.el-card__header) { border-bottom: none; font-weight: 600; color: #4b5563; } }

/* 推文列表区 */
.tweets-section { margin-top: 10px; border-top: 1px dashed #e5e7eb; padding-top: 20px; }
.section-subtitle { font-size: 16px; font-weight: 700; color: #374151; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }

.tweet-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;
}
.tweet-item-card {
  background: #f9fafb; border-radius: 12px; padding: 16px; border: 1px solid #f3f4f6;
  display: flex; flex-direction: column; gap: 10px;
  transition: transform 0.2s;
  &:hover { background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.05); transform: translateY(-2px); border-color: #e5e7eb; }
}
.t-header { display: flex; justify-content: flex-end; align-items: center; } /* 修改为靠右对齐，因为删除了左侧的时间 */
.t-content { font-size: 14px; color: #374151; line-height: 1.5; flex: 1; }
.t-footer { 
  display: flex; gap: 16px; font-size: 12px; color: #9ca3af; 
  span { display: flex; align-items: center; gap: 4px; }
}
</style>