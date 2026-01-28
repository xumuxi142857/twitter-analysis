<template>
  <div class="account-page">
    <div class="header-section">
      <h1 class="page-title">账号推荐</h1>
    </div>

    <div class="control-panel">
      <div class="left-controls">
        <el-tabs v-model="activeTab" class="custom-tabs" @tab-change="selectedUser = null">
          <el-tab-pane label="🇺🇸 美国" name="US"></el-tab-pane>
          <el-tab-pane label="🇯🇵 日本" name="Japan"></el-tab-pane>
          <el-tab-pane label="🇵🇭 菲律宾" name="Philippines"></el-tab-pane>
          <el-tab-pane label="🇹🇼 中国台湾" name="Taiwan"></el-tab-pane>
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
              <span>👥 重点账号挖掘</span>
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
                    
                  </div>
                </div>
              </template>
            </el-table-column>

            <el-table-column prop="info" label="情报简述" min-width="300">
              <template #default="{ row }">
                <el-tooltip :content="row.info" placement="top" :show-after="500">
                  <span class="info-text">{{ row.info }}</span>
                </el-tooltip>
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
                  <template #header>
                    <div class="header-with-tip">
                      <span>🧩 对中立场矩阵</span>
                      <el-popover placement="top" :width="320" trigger="hover">
                        <template #reference>
                          <el-icon class="help-icon"><QuestionFilled /></el-icon>
                        </template>
                        <div class="matrix-guide">
                          <h4 style="margin:0 0 10px 0; color:#1f2937;">📊 如何解读热力图？</h4>
                          <p style="margin:5px 0; font-size:15px; color:#4b5563;">
                            <b>X轴 (横向):</b> 代表立场倾向 <br/>(反华 ↔ 亲华)
                          </p>
                          <p style="margin:5px 0; font-size:15px; color:#4b5563;">
                            <b>Y轴 (纵向):</b> 代表用户关注的话题领域 <br/>(政治 / 军事 / 经济 / 文化)
                          </p>
                          <p style="margin:5px 0; font-size:15px; color:#4b5563;">
                            <b>颜色浓度 (0-10):</b> 代表表达强度。<br/>
                            <span style="color:#0284c7; font-weight:bold;">深蓝色</span> 表示该用户在该领域的观点输出非常密集且强烈。
                          </p>
                        </div>
                      </el-popover>
                    </div>
                  </template>
                  <StanceMatrix :data="selectedUser.stance_matrix" style="height: 220px;" />
                </el-card>
              </el-col>
              
              <el-col :span="10">
                <el-card shadow="never" class="chart-card">
                  <template #header><span>❤️ 影响类型情感判断</span></template>
                  <InfluencePie :data="selectedUser.influence_type" style="height: 220px;" />
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
                      <el-tag :type="getStanceColor(tweet.stance)" size="small" effect="dark" class="stance-badge">
                        {{ getStanceLabel(tweet.stance) }}
                      </el-tag>
                    </div>
                    
                    <div class="t-body">
                      <div class="t-trans" v-if="tweet.translation">
                        <span class="trans-tag">译</span> {{ tweet.translation }}
                      </div>
                      <div class="t-original">{{ tweet.text }}</div>
                    </div>

                    <div class="t-footer">
                      <span><el-icon><ChatDotRound /></el-icon> {{ tweet.metrics?.reply || 0 }}</span>
                      <span><el-icon><Share /></el-icon> {{ tweet.metrics?.retweet || 0 }}</span>
                      <span><el-icon><Star /></el-icon> {{ tweet.metrics?.like || 0 }}</span>
                    </div>
                  </div>
                </div>
                <el-empty v-else description="暂无高热度推文记录" :image-size="80" />
              </el-scrollbar>
            </div>

          </div>
        </transition>
      </div>

      <el-empty v-else description="该日期暂无账号数据 (请运行脚本生成)" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
// 修改：引入 QuestionFilled 图标
import { UserFilled, Close, ChatLineSquare, ChatDotRound, Share, Star, QuestionFilled } from '@element-plus/icons-vue';
import StanceMatrix from './components/StanceMatrix.vue';
import InfluencePie from './components/InfluencePie.vue';

// 接口定义
interface Tweet { 
  text: string; 
  translation?: string; 
  stance: string; 
  metrics?: any; 
}
interface UserProfile { 
  username: string; 
  tweet_count: number; 
  info: string; 
  stance_matrix: any[]; 
  influence_type: any[]; 
  tweets: Tweet[]; 
}
interface AccountAnalysisData { region: string; top_users: UserProfile[]; }

const activeTab = ref('US');
const selectedDate = ref<string>('2026-01-26');
const loading = ref(false);
const hasData = ref(true);
const selectedUser = ref<UserProfile | null>(null);
const regionDataStore = ref<Record<string, AccountAnalysisData>>({});

const currentData = computed(() => {
  return regionDataStore.value[activeTab.value] || { region: 'Unknown', top_users: [] };
});

const disabledDate = (time: Date) => time.getTime() > Date.now();

const getStanceColor = (s: string) => {
  if (s === 'positive') return 'success';
  if (s === 'negative') return 'danger';
  return 'info';
};

const getStanceLabel = (s: string) => {
  const map: Record<string, string> = { 'positive': '亲华', 'negative': '反华', 'neutral': '中立' };
  return map[s] || s;
};

const fetchData = async () => {
  if (!selectedDate.value) return;
  loading.value = true;
  hasData.value = false;
  selectedUser.value = null; 

  const tempStore: Record<string, AccountAnalysisData> = {
    US: { region: 'US', top_users: [] },
    Japan: { region: 'Japan', top_users: [] },
    Philippines: { region: 'Philippines', top_users: [] },
    Taiwan: { region: 'Taiwan', top_users: [] }
  };

  try {
    const res = await axios.get(`/db/account/${selectedDate.value}.json?t=${Date.now()}`);
    const data = res.data;

    if (data) {
      Object.keys(data).forEach(region => {
        if (tempStore[region] && region !== '_meta') {
          tempStore[region].top_users = data[region].top_users || [];
        }
      });
      regionDataStore.value = tempStore;
      hasData.value = true;
    } else {
      hasData.value = false;
    }
  } catch (error) {
    console.warn('Fetch error:', error);
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
.card-header { font-weight: 600; } /* 补充样式 */
.user-cell { display: flex; align-items: center; gap: 12px; }
.avatar-bg { background: #3b82f6; color: white; font-weight: 700; }
.user-info-col { display: flex; flex-direction: column; }
.username { font-weight: 600; color: #1f2937; font-size: 14px; }
.tweet-count { font-size: 12px; color: #9ca3af; }

.info-text { 
  color: #4b5563; font-size: 16px; 
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; 
}

.profile-section { margin-top: 30px; background: #fff; padding: 24px; border-radius: 16px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); border: 1px solid #e5e7eb; }
.profile-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #f3f4f6; h3 { margin: 0; display: flex; align-items: center; gap: 10px; color: #1f2937; } }
.chart-card { border: none; background: #f9fafb; border-radius: 12px; :deep(.el-card__header) { border-bottom: none; font-weight: 600; color: #4b5563; } }

/* 修改：带提示的头部样式 */
.header-with-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .help-icon {
    color: #9ca3af;
    cursor: pointer;
    font-size: 16px;
    transition: color 0.2s;
    &:hover { color: #3b82f6; }
  }
}

.tweets-section { margin-top: 10px; border-top: 1px dashed #e5e7eb; padding-top: 20px; }
.section-subtitle { font-size: 16px; font-weight: 700; color: #374151; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }

.tweet-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }

.tweet-item-card {
  background: #fff; border-radius: 12px; padding: 16px; border: 1px solid #e5e7eb;
  display: flex; flex-direction: column; gap: 10px;
  transition: transform 0.2s, box-shadow 0.2s;
  
  &:hover { box-shadow: 0 8px 15px -3px rgba(0,0,0,0.08); transform: translateY(-2px); border-color: #d1d5db; }
}

.t-header { display: flex; justify-content: flex-end; }
.stance-badge { font-weight: 600; }

.t-body { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.t-trans { 
  font-size: 17px; font-weight: 600; color: #1f2937; line-height: 1.5; 
  .trans-tag { background: #e0e7ff; color: #3b82f6; font-size: 11px; padding: 1px 4px; border-radius: 4px; margin-right: 4px; }
}
.t-original { font-size: 13px; color: #9ca3af; line-height: 1.4; border-top: 1px dashed #f3f4f6; padding-top: 6px; }

.t-footer { display: flex; gap: 16px; font-size: 12px; color: #9ca3af; span { display: flex; align-items: center; gap: 4px; } }
</style>