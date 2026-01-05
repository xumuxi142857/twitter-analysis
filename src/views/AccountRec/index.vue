<template>
  <div class="account-page">
    <div class="header-section">
      <h1 class="page-title">重点账号画像推荐</h1>
      <p class="page-subtitle">Key Opinion Leader (KOL) Profiling & Recommendation</p>
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
        <span class="label">分析时间:</span>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始"
          end-placeholder="结束"
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
              <span>👥 活跃账号列表 ({{ dateRange ? `${dateRange[0]} ~ ${dateRange[1]}` : '' }})</span>
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
                    <span class="tweet-count">活跃度: {{ row.tweet_count }} posts</span>
                  </div>
                </div>
              </template>
            </el-table-column>

            <el-table-column prop="info" label="情报简述 (Profile Summary)" min-width="300">
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

            <el-row :gutter="24">
              <el-col :span="14">
                <el-card shadow="never" class="chart-card">
                  <template #header><span>🧩 对中立场矩阵 (Stance Matrix)</span></template>
                  <StanceMatrix :data="selectedUser.stance_matrix" />
                </el-card>
              </el-col>
              
              <el-col :span="10">
                <el-card shadow="never" class="chart-card">
                  <template #header><span>❤️ 影响类型情感判断 (Influence Type)</span></template>
                  <InfluencePie :data="selectedUser.influence_type" />
                </el-card>
              </el-col>
            </el-row>
          </div>
        </transition>
      </div>

      <el-empty v-else description="该时间段内暂无账号数据" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
import dayjs from 'dayjs';
import { Calendar, UserFilled, Close } from '@element-plus/icons-vue';
import StanceMatrix from './components/StanceMatrix.vue';
import InfluencePie from './components/InfluencePie.vue';
import type { AccountAnalysisData, UserProfile } from '@/types';

const activeTab = ref('Philippines');
// 默认日期
const dateRange = ref<[string, string]>(['2025-12-25', '2025-12-25']);
const loading = ref(false);
const hasData = ref(true);
const selectedUser = ref<UserProfile | null>(null);

// 存储器
const regionDataStore = ref<Record<string, AccountAnalysisData>>({});

const currentData = computed(() => {
  return regionDataStore.value[activeTab.value] || { 
    region: 'Unknown', 
    time_range: ['-', '-'], 
    top_users: [] 
  };
});

const disabledDate = (time: Date) => time.getTime() > Date.now();

// 核心：加载并聚合数据
const fetchData = async () => {
  if (!dateRange.value) return;
  
  loading.value = true;
  hasData.value = false;
  selectedUser.value = null; // 切换日期时关闭详情
  
  const [start, end] = dateRange.value;
  const startDate = dayjs(start);
  const endDate = dayjs(end);
  const diffDays = endDate.diff(startDate, 'day');

  const promises = [];
  for (let i = 0; i <= diffDays; i++) {
    const dateStr = startDate.add(i, 'day').format('YYYY-MM-DD');
    promises.push(
      axios.get(`/db/account/${dateStr}.json`)
        .then(res => res.data)
        .catch(() => null)
    );
  }

  const results = await Promise.all(promises);

  // 初始化临时存储
  const tempStore: Record<string, AccountAnalysisData> = {
    US: { region: 'US', time_range: dateRange.value, top_users: [] },
    Japan: { region: 'Japan', time_range: dateRange.value, top_users: [] },
    Philippines: { region: 'Philippines', time_range: dateRange.value, top_users: [] },
    Taiwan: { region: 'Taiwan', time_range: dateRange.value, top_users: [] }
  };

  let foundAnyData = false;

  // 聚合逻辑：按 username 去重
  results.forEach(dayData => {
    if (dayData) {
      foundAnyData = true;
      Object.keys(dayData).forEach(region => {
        if (tempStore[region]) {
          const newUsers = dayData[region].top_users || [];
          const existingUsers = tempStore[region].top_users;
          
          // 使用 Map 去重，保留 tweet_count 较高的那个记录（或者你也可以逻辑相加）
          const userMap = new Map();
          existingUsers.forEach((u: UserProfile) => userMap.set(u.username, u));
          
          newUsers.forEach((u: UserProfile) => {
            if (userMap.has(u.username)) {
              // 如果已存在，对比谁的 tweet_count 高就留谁
              const existing = userMap.get(u.username);
              if (u.tweet_count > existing.tweet_count) {
                userMap.set(u.username, u);
              }
            } else {
              userMap.set(u.username, u);
            }
          });
          
          tempStore[region].top_users = Array.from(userMap.values());
        }
      });
    }
  });

  if (foundAnyData) {
    // 排序：按活跃度降序
    Object.keys(tempStore).forEach(r => {
      tempStore[r].top_users.sort((a, b) => b.tweet_count - a.tweet_count);
    });
    regionDataStore.value = tempStore;
    hasData.value = true;
  } else {
    hasData.value = false;
  }
  
  loading.value = false;
};

const handleRowClick = (row: UserProfile) => {
  selectedUser.value = row;
  setTimeout(() => {
    window.scrollTo({ top: 400, behavior: 'smooth' });
  }, 100);
};

onMounted(() => {
  fetchData();
});
</script>

<style scoped lang="scss">
.account-page {
  padding: 30px 60px;
  background-color: #f0f4f8;
  min-height: 100vh;
}

.header-section { margin-bottom: 30px; text-align: center; }
.page-title { font-size: 28px; font-weight: 700; color: #1f2937; margin: 0; }
.page-subtitle { font-size: 14px; color: #6b7280; margin-top: 8px; text-transform: uppercase; letter-spacing: 1px; }

.control-panel {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  background: #ffffff;
  padding: 10px 20px;
  border-radius: 16px;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
  
  .right-controls {
    display: flex;
    align-items: center;
    gap: 10px;
    .label { font-size: 14px; font-weight: bold; color: #6b7280; }
  }
}

.modern-card {
  border: none;
  border-radius: 16px;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
}

.card-header { font-weight: bold; color: #374151; font-size: 16px; }

.user-cell {
  display: flex;
  align-items: center;
  gap: 12px;
  
  .avatar-bg { background: #3b82f6; font-weight: 700; color: white; }
  
  .user-info-col {
    display: flex;
    flex-direction: column;
    .username { font-weight: 600; color: #1f2937; font-size: 14px; }
    .tweet-count { font-size: 12px; color: #9ca3af; }
  }
}

.info-text { color: #4b5563; line-height: 1.4; font-size: 14px; }

/* 详情动画区域 */
.profile-section {
  margin-top: 30px;
  background: #fff;
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  border: 1px solid #e5e7eb;

  .profile-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 1px solid #f3f4f6;
    h3 { margin: 0; color: #1f2937; display: flex; align-items: center; gap: 10px; }
  }
}

.chart-card {
  border: none; 
  background: #f9fafb;
  border-radius: 12px;
  :deep(.el-card__header) { border-bottom: none; font-weight: 600; color: #4b5563; }
}
</style>