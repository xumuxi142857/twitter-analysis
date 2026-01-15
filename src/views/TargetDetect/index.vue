<template>
  <div class="detect-page">
    <div class="header-section">
      <h1 class="page-title">目标监测系统</h1>
     
    </div>

    <div class="control-panel">
      <el-tabs v-model="activeTab" class="custom-tabs" @tab-change="selectedTarget = null">
        <el-tab-pane label="🇺🇸 中美关系" name="US"></el-tab-pane>
        <el-tab-pane label="🇯🇵 中日关系" name="Japan"></el-tab-pane>
        <el-tab-pane label="🇵🇭 中菲关系" name="Philippines"></el-tab-pane>
        <el-tab-pane label="🇹🇼 两岸关系" name="Taiwan"></el-tab-pane>
        <el-tab-pane label="🇨🇳 中国官方" name="China"></el-tab-pane>
      </el-tabs>
      
      <div class="right-controls">
        <el-button circle :icon="Refresh" @click="fetchList" :loading="listLoading" />
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
            <el-avatar :size="56" class="target-avatar" :style="getUnifiedAvatarStyle()">
              {{ target.name ? target.name.substring(0,1).toUpperCase() : '?' }}
            </el-avatar>
            
            <div class="target-info">
              <div class="name">{{ target.name }}</div>
              <div class="handle">@{{ target.username }}</div>
              
              <div class="preview-text" v-if="target.preview">
                {{ target.preview.length > 25 ? target.preview.substring(0, 25) + '...' : target.preview }}
              </div>
            </div>
            
            <div class="indicator" v-if="selectedTarget?.id === target.id">
              <el-icon><CaretBottom /></el-icon>
            </div>
          </div>
        </div>

        <transition name="el-zoom-in-top">
          <div v-if="selectedTarget" class="dossier-container" v-loading="detailLoading">
            
            <div class="dossier-header">
              <div class="dh-left">
                <h2><el-icon><Document /></el-icon> 深度研判档案: {{ selectedTarget.name }}</h2>
                <span class="stats-tag">日均发稿: {{ selectedTarget.daily_count || 0 }}</span>
              </div>
              <div class="dh-right">
                <el-button circle :icon="Close" @click="handleClose" />
              </div>
            </div>

            <div class="charts-section" v-if="selectedTarget.stance_matrix && selectedTarget.influence_type">
              <el-row :gutter="20">
                <el-col :span="14">
                  <div class="chart-card">
                    <div class="chart-title-row">
                      <div class="title-left">
                        <el-icon><Compass /></el-icon> 对中立场分析
                      </div>
                      <el-tooltip 
                        effect="dark" 
                        content="矩阵热力图释义：横轴与纵轴代表不同的立场倾向维度，方块中的数值及颜色深浅代表该维度下的言论强度。颜色越深，表示该立场下的活跃度/强度越高。" 
                        placement="top"
                        :show-after="200"
                      >
                        <el-icon class="help-icon"><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </div>
                    <StanceMatrix :data="selectedTarget.stance_matrix" style="height: 220px;" />
                  </div>
                </el-col>
                <el-col :span="10">
                  <div class="chart-card">
                    <div class="chart-title-row">
                      <div class="title-left">
                         <el-icon><PieChart /></el-icon> 影响力类型构成
                      </div>
                    </div>
                    <InfluencePie :data="selectedTarget.influence_type" style="height: 220px;" />
                  </div>
                </el-col>
              </el-row>
            </div>

            <div class="report-section" v-if="selectedTarget.analysis_report && selectedTarget.analysis_report.length > 0">
              <div class="section-label">Ⅰ. 综合研判结论 </div>
              
              <el-collapse v-model="activeCollapseNames" class="simple-collapse">
                <el-collapse-item 
                  v-for="(item, index) in selectedTarget.analysis_report" 
                  :key="index" 
                  :name="index"
                >
                  <template #title>
                    <div class="report-item-title">
                      <span class="title-main">
                        {{ (item.dimension || item.title || '维度').replace(/^\d+\.\s*/, '') }}
                      </span>
                      <span class="title-summary">{{ item.summary }}</span>
                    </div>
                  </template>
                  
                  <div class="report-content-wrapper">
                    <div v-if="item.sub_items && item.sub_items.length > 0" class="sub-items-list">
                      <div v-for="(sub, sIdx) in item.sub_items" :key="sIdx" class="sub-item-row">
                        <div class="sub-term">{{ sub.term }}</div>
                        <div class="sub-analysis">{{ sub.analysis }}</div>
                      </div>
                    </div>
                    <div v-else-if="item.detail" class="report-detail-text">
                      {{ item.detail }}
                    </div>
                  </div>

                </el-collapse-item>
              </el-collapse>
            </div>

            <div class="timeline-section" v-if="selectedTarget.all_tweets">
              <div class="timeline-header">
                <div class="section-label">Ⅱ. 最新言论监测</div>
              </div>

              <div class="tweet-list-container">
                <el-scrollbar height="600px">
                  <div v-if="filteredTweets.length > 0" class="tweets-wrapper">
                    <div v-for="(tweet, idx) in filteredTweets" :key="idx" class="tweet-card-simple">
                      <div class="tc-content">
                        {{ tweet.text }}
                      </div>
                      <div class="tc-footer" v-if="tweet.metrics">
                        <span title="回复"><el-icon><ChatDotRound /></el-icon> {{ tweet.metrics.reply || 0 }}</span>
                        <span title="转发"><el-icon><Share /></el-icon> {{ tweet.metrics.retweet || 0 }}</span>
                        <span title="点赞"><el-icon><Star /></el-icon> {{ tweet.metrics.like || 0 }}</span>
                      </div>
                    </div>
                  </div>
                  <el-empty v-else description="暂无推文记录" />
                </el-scrollbar>
              </div>
            </div>

          </div>
        </transition>
      </div>
      
      <el-empty v-else-if="!listLoading" description="该板块下暂无监测目标" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
import { 
  Refresh, Close, ChatDotRound, Share, Star, 
  CaretBottom, Document, Compass, PieChart,
  QuestionFilled // 新增引入
} from '@element-plus/icons-vue';
import StanceMatrix from '@/views/AccountRec/components/StanceMatrix.vue';
import InfluencePie from '@/views/AccountRec/components/InfluencePie.vue';

interface SubItem { term: string; analysis: string; }
interface AnalysisItem { dimension?: string; title?: string; summary: string; detail?: string; sub_items?: SubItem[]; }
interface TweetRaw { created_at: string; text: string; metrics?: { reply: number; retweet: number; like: number }; }
interface TargetSummary { id: string; name: string; username: string; category: string; daily_count?: number; preview?: string; }
interface TargetDetail extends TargetSummary { 
  analysis_report?: AnalysisItem[]; 
  all_tweets?: TweetRaw[]; 
  stance_matrix?: Array<any>;
  influence_type?: Array<any>;
}

const activeTab = ref('US');
const listLoading = ref(false);
const detailLoading = ref(false);
const selectedTarget = ref<TargetDetail | null>(null);
const dbList = ref<Record<string, { targets: TargetSummary[] }>>({});
const activeCollapseNames = ref([0, 8]); 

const currentList = computed(() => {
  if (!dbList.value || !dbList.value[activeTab.value]) return [];
  return dbList.value[activeTab.value].targets || [];
});

const filteredTargets = computed(() => {
  return currentList.value;
});

const filteredTweets = computed(() => selectedTarget.value?.all_tweets || []);

const fetchList = async () => {
  listLoading.value = true;
  selectedTarget.value = null;
  try {
    const res = await axios.get('/db/detect/list.json?t=' + Date.now());
    if (res.data) dbList.value = res.data;
  } catch (e) { console.error(e); } 
  finally { listLoading.value = false; }
};

const handleSelect = async (summary: TargetSummary) => {
  // @ts-ignore
  selectedTarget.value = summary; 
  activeCollapseNames.value = [0, 8]; 
  
  setTimeout(() => {
    const el = document.querySelector('.dossier-container');
    if(el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 100);

  detailLoading.value = true;
  try {
    const res = await axios.get(`/db/detect/details/${summary.id}?t=` + Date.now());
    if (res.data) {
      selectedTarget.value = { ...summary, ...res.data };
    }
  } catch (e) { console.error(e); }
  finally { detailLoading.value = false; }
};

const handleClose = () => {
  selectedTarget.value = null;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

const getUnifiedAvatarStyle = () => ({ 
  background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
  boxShadow: '0 4px 6px rgba(37, 99, 235, 0.3)'
});

onMounted(() => fetchList());
</script>

<style scoped lang="scss">
/* 布局 */
.detect-page { padding: 30px 60px; background-color: #f0f4f8; min-height: 100vh; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; color: #333; }
.header-section { margin-bottom: 30px; text-align: center; }
.page-title { font-size: 28px; font-weight: 700; color: #1f2937; margin: 0; }
.page-subtitle { font-size: 14px; color: #6b7280; margin-top: 8px; text-transform: uppercase; letter-spacing: 1px; }

/* 控制栏 */
.control-panel { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; background: #ffffff; padding: 10px 20px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }

/* Grid */
.target-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }
.target-card { 
  background: white; border-radius: 12px; padding: 20px; display: flex; align-items: center; gap: 16px; 
  cursor: pointer; border: 2px solid transparent; transition: all 0.2s ease; position: relative; box-shadow: 0 2px 4px rgba(0,0,0,0.02); 
  &:hover { transform: translateY(-3px); box-shadow: 0 10px 15px rgba(0,0,0,0.08); } 
  &.active { border-color: #2563eb; background: #eff6ff; .indicator { opacity: 1; transform: translateY(0); } } 
  .target-avatar { font-size: 24px; font-weight: bold; color: white; flex-shrink: 0; } 
  .target-info { flex: 1; overflow: hidden; .name { font-weight: 700; color: #1f2937; font-size: 16px; margin-bottom: 4px; } .handle { font-size: 13px; color: #6b7280; margin-bottom: 6px; } .preview-text { font-size: 12px; color: #9ca3af; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; } } 
  .indicator { position: absolute; bottom: -22px; left: 50%; margin-left: -10px; color: #2563eb; font-size: 24px; opacity: 0; transform: translateY(-5px); transition: all 0.3s; } 
}

/* 详情档案 */
.dossier-container { background: #fff; border-radius: 16px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); border: 1px solid #e5e7eb; margin-bottom: 40px; overflow: hidden; }
.dossier-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f3f4f6; padding: 20px 30px; background-color: #f9fafb; .dh-left { display: flex; align-items: center; gap: 15px; h2 { margin: 0; color: #1f2937; display: flex; align-items: center; gap: 10px; font-size: 20px; } .stats-tag { font-size: 13px; color: #6b7280; background: #e5e7eb; padding: 2px 8px; border-radius: 4px; } } }

/* 图表区域 */
.charts-section { padding: 30px 30px 0 30px; background-color: #fff; }
.chart-card { background: #f9fafb; border-radius: 12px; padding: 20px; border: 1px solid #e5e7eb; }

/* 修改：标题行样式，支持左右对齐 */
.chart-title-row {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;
  .title-left { font-size: 15px; font-weight: 700; color: #374151; display: flex; align-items: center; gap: 8px; }
  .help-icon { font-size: 16px; color: #9ca3af; cursor: pointer; transition: color 0.2s; &:hover { color: #2563eb; } }
}

/* 报告部分 */
.report-section { padding: 30px; background: #fff; }
.section-label { font-size: 18px; font-weight: 700; color: #1f293b; margin-bottom: 20px; border-left: 5px solid #2563eb; padding-left: 12px; }

.simple-collapse { border: none; }
:deep(.el-collapse-item__header) { font-size: 15px; font-weight: 500; color: #374151; background-color: #fff; border-bottom: 1px solid #f3f4f6; height: auto; padding: 12px 0; }
:deep(.el-collapse-item__content) { padding-bottom: 20px; color: #4b5563; }

.report-item-title { display: flex; align-items: center; gap: 15px; width: 100%; .title-main { font-weight: 700; color: #111827; min-width: 150px; } .title-summary { font-weight: 400; color: #6b7280; font-size: 13px; font-style: italic; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 60%; } }
.report-content-wrapper { padding: 10px 0; }
.sub-items-list { display: flex; flex-direction: column; gap: 12px; }
.sub-item-row { background: #f8fafc; padding: 15px; border-radius: 8px; border-left: 3px solid #cbd5e1; }
.sub-term { font-weight: 700; color: #334155; font-size: 14px; margin-bottom: 4px; }
.sub-analysis { color: #475569; font-size: 14px; line-height: 1.6; }
.report-detail-text { padding: 16px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb; line-height: 1.6; font-size: 14px; margin-top: 5px; color: #374151; }

/* 列表部分 */
.timeline-section { border-top: 1px solid #e5e7eb; background: #fafafa; padding: 30px; }
.timeline-header { margin-bottom: 20px; }
.tweets-wrapper { display: flex; flex-direction: column; gap: 12px; }
.tweet-card-simple { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; transition: transform 0.2s; box-shadow: 0 1px 2px rgba(0,0,0,0.05); &:hover { box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-color: #d1d5db; } .tc-content { font-size: 14px; line-height: 1.6; color: #374151; margin-bottom: 10px; } .tc-footer { display: flex; justify-content: flex-end; gap: 20px; font-size: 12px; color: #9ca3af; border-top: 1px solid #f9fafb; padding-top: 8px; span { display: flex; align-items: center; gap: 4px; } } }
</style>