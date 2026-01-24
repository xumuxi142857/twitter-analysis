<template>
  <div class="detect-page">
    <div class="header-section">
      <h1 class="page-title">目标监测</h1>
    </div>

    <div class="control-panel">
      <el-tabs v-model="activeTab" class="custom-tabs" @tab-change="selectedTarget = null">
        <el-tab-pane label="🇺🇸 美国" name="US"></el-tab-pane>
        <el-tab-pane label="🇯🇵 日本" name="Japan"></el-tab-pane>
        <el-tab-pane label="🇵🇭 菲律宾" name="Philippines"></el-tab-pane>
        <el-tab-pane label="🇹🇼 中国台湾" name="Taiwan"></el-tab-pane>
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
                <h2><el-icon><Document /></el-icon> 深度用户报告: {{ selectedTarget.name }}</h2>
                
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
                        <el-icon><Compass /></el-icon> 对华立场态势 
                      </div>
                      <el-tooltip 
                        effect="dark" 
                        placement="top"
                        :show-after="200"
                      >
                        <template #content>
                          <div class="tooltip-content">
                            <p><b>X轴 (立场):</b> 0=反华/负面, 1=中立, 2=亲华/正面</p>
                            <p><b>Y轴 (领域):</b> 0=政治, 1=军事, 2=经济, 3=文化</p>
                            <p><b>气泡大小:</b> 代表活跃度与强度 (0-10)</p>
                          </div>
                        </template>
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
                      <el-tooltip 
                        effect="dark" 
                        placement="top"
                        :show-after="200"
                      >
                        <template #content>
                          <div class="tooltip-content">
                            <p><b>权威:</b> 基于专业/官方地位的影响力</p>
                            <p><b>同伴:</b> 基于群体认同的横向影响力</p>
                            <p><b>亲情:</b> 基于情感/纽带的感性影响力</p>
                          </div>
                        </template>
                        <el-icon class="help-icon"><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </div>
                    <InfluencePie :data="selectedTarget.influence_type" style="height: 220px;" />
                  </div>
                </el-col>
              </el-row>
            </div>

            <div class="report-section" v-if="selectedTarget.analysis_report && selectedTarget.analysis_report.length > 0">
              <div class="section-label">Ⅰ. 综合研判结论</div>
              
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
                      <div 
                        v-for="(line, lIdx) in formatDetailText(item.detail)" 
                        :key="lIdx" 
                        class="detail-line"
                      >
                        <span class="detail-label" v-if="line.label">{{ line.label }}</span>
                        <span class="detail-content">{{ line.content }}</span>
                      </div>
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
                <el-scrollbar height="800px">
                  <div v-if="filteredTweets.length > 0" class="tweets-wrapper">
                    <div v-for="(tweet, idx) in filteredTweets" :key="idx" class="tweet-card-enhanced">
                      
                      <div class="te-header">
                        <div class="te-date">{{ formatDate(tweet.created_at) }}</div>
                        <div class="te-stance" :class="getStanceClass(tweet.stance)">
                          {{ tweet.stance || '未研判' }}
                        </div>
                      </div>

                      <div class="te-body">
                        <div class="te-trans" v-if="tweet.translation">
                          <span class="trans-label">译文：</span>{{ tweet.translation }}
                        </div>
                        <div class="te-original">
                          {{ tweet.text }}
                        </div>
                      </div>

                      <div class="te-footer" v-if="tweet.metrics">
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
import dayjs from 'dayjs';
import { 
  Refresh, Close, ChatDotRound, Share, Star, 
  CaretBottom, Document, Compass, PieChart, QuestionFilled
} from '@element-plus/icons-vue';
import StanceMatrix from '@/views/AccountRec/components/StanceMatrix.vue';
import InfluencePie from '@/views/AccountRec/components/InfluencePie.vue';

interface SubItem { term: string; analysis: string; }
interface AnalysisItem { dimension?: string; title?: string; summary: string; detail?: string; sub_items?: SubItem[]; }
// 【更新】TweetRaw 增加 translation 和 stance
interface TweetRaw { 
  created_at: string; 
  text: string; 
  translation?: string; 
  stance?: string;
  metrics?: { reply: number; retweet: number; like: number }; 
}
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

const filteredTargets = computed(() => currentList.value);
const filteredTweets = computed(() => selectedTarget.value?.all_tweets || []);

// 格式化详情文本
// 修复后的格式化函数
const formatDetailText = (text: string) => {
  if (!text) return [];
  
  // 1. 预处理：给所有的“标签：”前面加上一个特殊分隔符（例如 |||）
  // 正则含义：匹配 2到10个非标点字符 + 冒号
  // 这样可以避免把长句子里的冒号误判为标题，只抓取短标题
  const taggedText = text.replace(/([^\n。；;：:]{2,12}[：:])/g, '|||$1');

  // 2. 基于分隔符拆分
  const parts = taggedText.split('|||').filter(p => p.trim());

  // 3. 映射为对象
  return parts.map(part => {
    // 尝试提取 "标签：" 和 "内容"
    // 匹配开头的 "xxx："
    const match = part.match(/^([^：:]+[：:])(.*)$/s);
    if (match) {
      return {
        label: match[1], // 例如 "开放性高："
        content: match[2] // 后面的内容
      };
    }
    // 如果没有冒号（比如第一段话），就只有内容
    return { label: '', content: part };
  });
};

// 获取立场颜色样式
const getStanceClass = (stance?: string) => {
  if (!stance) return 'stance-neutral';
  if (stance.includes('正面') || stance.includes('Positive')) return 'stance-positive';
  if (stance.includes('负面') || stance.includes('Negative')) return 'stance-negative';
  return 'stance-neutral';
};

const formatDate = (str: string) => dayjs(str).isValid() ? dayjs(str).format('YYYY-MM-DD HH:mm') : str;

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
    if (res.data) selectedTarget.value = { ...summary, ...res.data };
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
/* 基础样式 (保留原有的 Layout, Grid, Header 等) */
.detect-page { padding: 30px 60px; background-color: #f0f4f8; min-height: 100vh; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; color: #333; }
.header-section { margin-bottom: 30px; text-align: center; }
.page-title { font-size: 28px; font-weight: 700; color: #1f2937; margin: 0; }
.page-subtitle { font-size: 14px; color: #6b7280; margin-top: 8px; text-transform: uppercase; letter-spacing: 1px; }
.control-panel { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; background: #ffffff; padding: 10px 20px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
.target-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }
.target-card { background: white; border-radius: 12px; padding: 20px; display: flex; align-items: center; gap: 16px; cursor: pointer; border: 2px solid transparent; transition: all 0.2s ease; position: relative; box-shadow: 0 2px 4px rgba(0,0,0,0.02); &:hover { transform: translateY(-3px); box-shadow: 0 10px 15px rgba(0,0,0,0.08); } &.active { border-color: #2563eb; background: #eff6ff; .indicator { opacity: 1; transform: translateY(0); } } .target-avatar { font-size: 24px; font-weight: bold; color: white; flex-shrink: 0; } .target-info { flex: 1; overflow: hidden; .name { font-weight: 700; color: #1f2937; font-size: 16px; margin-bottom: 4px; } .handle { font-size: 13px; color: #6b7280; margin-bottom: 6px; } .preview-text { font-size: 12px; color: #9ca3af; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; } } .indicator { position: absolute; bottom: -22px; left: 50%; margin-left: -10px; color: #2563eb; font-size: 24px; opacity: 0; transform: translateY(-5px); transition: all 0.3s; } }
.dossier-container { background: #fff; border-radius: 16px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); border: 1px solid #e5e7eb; margin-bottom: 40px; overflow: hidden; }
.dossier-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f3f4f6; padding: 20px 30px; background-color: #f9fafb; .dh-left { display: flex; align-items: center; gap: 15px; h2 { margin: 0; color: #1f2937; display: flex; align-items: center; gap: 10px; font-size: 20px; } .stats-tag { font-size: 13px; color: #6b7280; background: #e5e7eb; padding: 2px 8px; border-radius: 4px; } } }
.charts-section { padding: 30px 30px 0 30px; background-color: #fff; }
.chart-card { background: #f9fafb; border-radius: 12px; padding: 20px; border: 1px solid #e5e7eb; .chart-title-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; .title-left { font-size: 15px; font-weight: 700; color: #374151; display: flex; align-items: center; gap: 8px; } .help-icon { font-size: 16px; color: #9ca3af; cursor: pointer; transition: color 0.2s; &:hover { color: #2563eb; } } } }
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
.report-detail-text { padding: 16px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb; margin-top: 5px; color: #374151; }
.detail-line { display: flex; align-items: baseline; margin-bottom: 8px; line-height: 1.6; font-size: 14px; &:last-child { margin-bottom: 0; } }
.detail-label { font-weight: 700; color: #1f293b; margin-right: 4px; white-space: nowrap; flex-shrink: 0; }
.detail-content { color: #4b5563; word-break: break-all; }

/* --- 【新样式】增强版推文卡片 --- */
.timeline-section { border-top: 1px solid #e5e7eb; background: #fafafa; padding: 30px; }
.timeline-header { margin-bottom: 20px; }
.tweets-wrapper { display: flex; flex-direction: column; gap: 16px; }

.tweet-card-enhanced {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px; 
  transition: transform 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
  
  &:hover { box-shadow: 0 8px 12px rgba(0,0,0,0.08); border-color: #d1d5db; transform: translateY(-2px); }
  
  /* 头部: 时间 + 标签 */
  .te-header {
    display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
    .te-date { font-size: 13px; color: #9ca3af; font-weight: 500; }
    .te-stance { 
      font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 4px;
      &.stance-positive { background: #ecfdf5; color: #059669; }
      &.stance-negative { background: #fef2f2; color: #dc2626; }
      &.stance-neutral { background: #f3f4f6; color: #4b5563; }
    }
  }
  
  /* 内容区 */
  .te-body { margin-bottom: 16px; }
  .te-trans { 
    font-size: 15px; color: #1f293b; font-weight: 600; line-height: 1.6; margin-bottom: 8px; 
    .trans-label { color: #3b82f6; font-size: 13px; font-weight: 400; margin-right: 4px; }
  }
  .te-original { font-size: 13px; color: #6b7280; line-height: 1.5; font-family: sans-serif; }
  
  /* 底部 */
  .te-footer { 
    display: flex; justify-content: flex-end; gap: 20px; font-size: 12px; color: #9ca3af; 
    border-top: 1px dashed #f3f4f6; padding-top: 10px;
    span { display: flex; align-items: center; gap: 4px; }
  }
}
</style>