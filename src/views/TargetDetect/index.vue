<template>
  <div class="detect-page">
    <div class="header-section">
      <h1 class="page-title">重点目标监测与画像</h1>
      <p class="page-subtitle">High-Value Target Monitoring & Analysis</p>
    </div>

    <div class="control-panel">
      <el-tabs v-model="activeTab" class="custom-tabs" @tab-change="selectedTarget = null">
        <el-tab-pane label="🇺🇸 美国 (US)" name="US"></el-tab-pane>
        <el-tab-pane label="🇯🇵 日本 (Japan)" name="Japan"></el-tab-pane>
        <el-tab-pane label="🇵🇭 菲律宾 (Philippines)" name="Philippines"></el-tab-pane>
        <el-tab-pane label="🇹🇼 台湾地区 (Taiwan)" name="Taiwan"></el-tab-pane>
        
      </el-tabs>
      
      <div class="right-controls">
        <el-radio-group v-model="filterType" size="large">
          <el-radio-button label="all">全部 All</el-radio-button>
          <el-radio-button label="politician">政要 Politicians</el-radio-button>
          <el-radio-button label="media">媒体 Media</el-radio-button>
        </el-radio-group>
        
        <el-button circle :icon="Refresh" @click="fetchData" style="margin-left: 12px;" :loading="loading" />
      </div>
    </div>

    <div v-loading="loading" style="min-height: 400px;">
      
      <div v-if="hasData && filteredTargets.length > 0">
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
          <div v-if="selectedTarget" class="analysis-dashboard">
            <div class="dashboard-header">
              <h3>
                <el-icon><DataLine /></el-icon> 
                监测指标分析: {{ selectedTarget.name }}
              </h3>
              <el-button circle icon="Close" @click="selectedTarget = null" />
            </div>

            <el-row :gutter="20">
              <el-col :span="8">
                <el-card class="metric-card" shadow="never">
                  <template #header><span>👤 基础档案 (Profile)</span></template>
                  
                  <div class="bio-box">
                    {{ selectedTarget.metrics.bio }}
                  </div>

                  <div class="stats-grid">
                    <div class="stat-item">
                      <div class="label">日均发稿</div>
                      <div class="value">{{ selectedTarget.metrics.daily_count }}</div>
                    </div>
                    <div class="stat-item">
                      <div class="label">活跃时段</div>
                      <div class="value text-sm">{{ selectedTarget.metrics.active_hours }}</div>
                    </div>
                  </div>

                  <div class="keywords-box">
                    <div class="label">核心关键词 (Keywords):</div>
                    <div class="tags">
                      <el-tag 
                        v-for="kw in selectedTarget.metrics.keywords" 
                        :key="kw" 
                        effect="light"
                        round
                        size="small"
                      >
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
          </div>
        </transition>
      </div>
      
      <el-empty v-else description="该板块下暂无监测目标配置" />
      
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
import { CaretBottom, DataLine, Refresh, Close } from '@element-plus/icons-vue';
// 复用图表组件
import StanceMatrix from '@/views/AccountRec/components/StanceMatrix.vue';
import InfluencePie from '@/views/AccountRec/components/InfluencePie.vue';
import type { DetectData, TargetProfile } from '@/types';

const activeTab = ref('US');
const filterType = ref('all');
const loading = ref(false);
const hasData = ref(false);
const selectedTarget = ref<TargetProfile | null>(null);

// 数据源
const dbData = ref<Record<string, DetectData>>({});

const currentData = computed(() => {
  return dbData.value[activeTab.value] || { targets: [] };
});

// 过滤器逻辑
const filteredTargets = computed(() => {
  const all = currentData.value.targets || [];
  if (filterType.value === 'all') return all;
  return all.filter(t => t.category === filterType.value);
});

// 核心：从后端 JSON 读取数据
const fetchData = async () => {
  loading.value = true;
  selectedTarget.value = null;
  try {
    // 请求 public/db/detect/targets.json
    const res = await axios.get('/db/detect/targets.json?t=' + new Date().getTime()); // 加时间戳防缓存
    if (res.data) {
      dbData.value = res.data;
      hasData.value = true;
    }
  } catch (error) {
    console.error("Failed to load targets:", error);
    hasData.value = false;
  } finally {
    loading.value = false;
  }
};

const handleSelect = (target: TargetProfile) => {
  selectedTarget.value = target;
  setTimeout(() => {
    window.scrollTo({ top: 350, behavior: 'smooth' });
  }, 100);
};

// 头像颜色生成
const getAvatarStyle = (category: string) => {
  return category === 'politician' 
    ? { backgroundColor: '#e11d48' } // 红色
    : { backgroundColor: '#059669' }; // 绿色
};

onMounted(() => {
  fetchData();
});
</script>

<style scoped lang="scss">
.detect-page {
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
  margin-bottom: 30px;
  background: #ffffff;
  padding: 10px 20px;
  border-radius: 16px;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
}

/* --- Grid 布局 --- */
.target-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.target-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.3s ease;
  position: relative;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);

  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 15px rgba(0,0,0,0.08);
  }

  &.active {
    border-color: #2563eb;
    background: #eff6ff;
    .indicator { opacity: 1; transform: translateY(0); }
  }

  .target-avatar { font-size: 24px; font-weight: bold; color: white; }
  
  .target-info {
    flex: 1;
    .name { font-weight: 700; color: #1f2937; font-size: 16px; margin-bottom: 4px; }
    .handle { font-size: 13px; color: #6b7280; margin-bottom: 6px; }
  }

  .indicator {
    position: absolute;
    bottom: -22px;
    left: 50%;
    margin-left: -10px;
    color: #2563eb;
    font-size: 24px;
    opacity: 0;
    transform: translateY(-5px);
    transition: all 0.3s;
  }
}

/* --- Dashboard --- */
.analysis-dashboard {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  border: 1px solid #e5e7eb;

  .dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #f3f4f6;
    margin-bottom: 20px;
    padding-bottom: 10px;
    h3 { margin: 0; color: #1f2937; display: flex; align-items: center; gap: 10px; }
  }
}

.metric-card {
  height: 100%;
  border-radius: 12px;
  border: none;
  background: #f9fafb;
  :deep(.el-card__header) { border-bottom: none; font-weight: 600; color: #4b5563; }
}

.bio-box {
  font-size: 14px; color: #4b5563; line-height: 1.6; margin-bottom: 20px;
  background: #fff; padding: 12px; border-radius: 8px; border: 1px solid #e5e7eb;
}

.stats-grid {
  display: flex; gap: 15px; margin-bottom: 20px;
  .stat-item {
    flex: 1; background: #fff; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #e5e7eb;
    .label { font-size: 12px; color: #9ca3af; margin-bottom: 4px; }
    .value { font-size: 20px; font-weight: 700; color: #2563eb; }
    .text-sm { font-size: 14px; color: #1f2937; }
  }
}

.keywords-box {
  .label { font-size: 12px; color: #9ca3af; margin-bottom: 8px; }
  .tags { display: flex; flex-wrap: wrap; gap: 8px; }
}
</style>