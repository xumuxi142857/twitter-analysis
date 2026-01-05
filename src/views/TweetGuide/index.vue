<template>
  <div class="guide-page">
    <div class="header-section">
      <h1 class="page-title">智能推文引导与应对</h1>
      <p class="page-subtitle">AI-Powered Response Generation & Public Opinion Guidance</p>
    </div>

    <div class="control-panel">
      <div class="left-controls">
        <el-tabs v-model="activeTab" class="custom-tabs" @tab-change="resetSelection">
          <el-tab-pane label="🇺🇸 中美关系" name="US"></el-tab-pane>
          <el-tab-pane label="🇯🇵 中日关系" name="Japan"></el-tab-pane>
          <el-tab-pane label="🇵🇭 中菲关系" name="Philippines"></el-tab-pane>
          <el-tab-pane label="🇹🇼 两岸关系" name="Taiwan"></el-tab-pane>
        </el-tabs>
      </div>

      <div class="right-controls">
        <span class="label">事件时间:</span>
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
              <span>📋 待引导舆情事件 ({{ dateRange ? `${dateRange[0]} ~ ${dateRange[1]}` : '' }})</span>
            </div>
          </template>
          
          <el-table :data="currentData.topics" style="width: 100%" row-key="topic">
            <el-table-column type="index" label="No." width="60" align="center" />
            
            <el-table-column prop="topic" label="舆情话题 (Topic Focus)" min-width="400">
              <template #default="{ row }">
                <span class="topic-text">{{ row.topic }}</span>
              </template>
            </el-table-column>

            <el-table-column prop="stance" label="当前立场" width="150" align="center">
              <template #default="{ row }">
                <el-tag :type="getStanceColor(row.stance)" effect="light" round>
                  {{ row.stance }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column label="操作 (Action)" width="180" align="center">
              <template #default="{ row }">
                <el-button 
                  type="primary" 
                  :icon="MagicStick" 
                  round 
                  plain
                  :loading="generatingId === row.topic"
                  @click="handleGenerate(row)"
                >
                  {{ activeTopic === row ? '收起策略' : '生成引导文案' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <transition name="el-fade-in-linear">
          <div v-if="activeTopic" class="draft-section">
            <div class="section-title">
              <el-icon><EditPen /></el-icon>
              <span>针对话题: “{{ activeTopic.topic }}” 的应对策略草稿</span>
            </div>

            <el-row :gutter="20">
              <el-col :span="8">
                <div class="draft-card authority">
                  <div class="card-icon">
                    <el-icon><Stamp /></el-icon>
                  </div>
                  <h3 class="card-title">权威引导 (Authority)</h3>
                  <p class="card-desc">官方口吻 / 引用法规 / 严正声明</p>
                  <div class="draft-content">
                    "{{ activeTopic.drafts.authority }}"
                  </div>
                  <div class="card-footer">
                    <el-button link type="primary">复制草稿</el-button>
                  </div>
                </div>
              </el-col>

              <el-col :span="8">
                <div class="draft-card peer">
                  <div class="card-icon">
                    <el-icon><ChatDotRound /></el-icon>
                  </div>
                  <h3 class="card-title">同伴引导 (Peer)</h3>
                  <p class="card-desc">平视视角 / 网络语言 / 幽默反讽</p>
                  <div class="draft-content">
                    "{{ activeTopic.drafts.peer }}"
                  </div>
                  <div class="card-footer">
                    <el-button link type="warning">复制草稿</el-button>
                  </div>
                </div>
              </el-col>

              <el-col :span="8">
                <div class="draft-card kinship">
                  <div class="card-icon">
                    <el-icon><Coffee /></el-icon>
                  </div>
                  <h3 class="card-title">亲情引导 (Kinship)</h3>
                  <p class="card-desc">感性共情 / 呼唤和平 / 情感连接</p>
                  <div class="draft-content">
                    "{{ activeTopic.drafts.kinship }}"
                  </div>
                  <div class="card-footer">
                    <el-button link type="danger">复制草稿</el-button>
                  </div>
                </div>
              </el-col>
            </el-row>
          </div>
        </transition>
      </div>

      <el-empty v-else description="该时间段内暂无需要引导的舆情事件" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
import dayjs from 'dayjs';
import { MagicStick, EditPen, Stamp, ChatDotRound, Coffee } from '@element-plus/icons-vue';
import type { GuideData, GuideTopicItem } from '@/types';

const activeTab = ref('US');
// 默认日期
const dateRange = ref<[string, string]>(['2025-12-25', '2025-12-25']);
const loading = ref(false);
const hasData = ref(true);

const activeTopic = ref<GuideTopicItem | null>(null);
const generatingId = ref<string>('');

// 数据存储
const regionDataStore = ref<Record<string, GuideData>>({});

const currentData = computed(() => {
  return regionDataStore.value[activeTab.value] || { topics: [] };
});

const disabledDate = (time: Date) => time.getTime() > Date.now();

const resetSelection = () => {
  activeTopic.value = null;
};

// 核心：数据获取与聚合
const fetchData = async () => {
  if (!dateRange.value) return;
  
  loading.value = true;
  hasData.value = false;
  activeTopic.value = null; // 清空当前选中的
  
  const [start, end] = dateRange.value;
  const startDate = dayjs(start);
  const endDate = dayjs(end);
  const diffDays = endDate.diff(startDate, 'day');

  const promises = [];
  for (let i = 0; i <= diffDays; i++) {
    const dateStr = startDate.add(i, 'day').format('YYYY-MM-DD');
    promises.push(
      axios.get(`/db/guide/${dateStr}.json`)
        .then(res => res.data)
        .catch(() => null)
    );
  }

  const results = await Promise.all(promises);

  const tempStore: Record<string, GuideData> = {
    US: { region: 'US', time_range: dateRange.value, topics: [] },
    Japan: { region: 'Japan', time_range: dateRange.value, topics: [] },
    Philippines: { region: 'Philippines', time_range: dateRange.value, topics: [] },
    Taiwan: { region: 'Taiwan', time_range: dateRange.value, topics: [] }
  };

  let foundAnyData = false;

  results.forEach(dayData => {
    if (dayData) {
      foundAnyData = true;
      Object.keys(dayData).forEach(region => {
        if (tempStore[region]) {
          // 直接拼接所有话题，让用户看到所有日期的事件
          const newTopics = dayData[region].topics || [];
          tempStore[region].topics.push(...newTopics);
        }
      });
    }
  });

  if (foundAnyData) {
    regionDataStore.value = tempStore;
    hasData.value = true;
  } else {
    hasData.value = false;
  }
  
  loading.value = false;
};

const getStanceColor = (stance: string) => {
  if (stance === 'positive') return 'success';
  if (stance === 'negative') return 'danger';
  return 'info';
};

const handleGenerate = (row: GuideTopicItem) => {
  if (activeTopic.value === row) {
    activeTopic.value = null;
    return;
  }
  
  generatingId.value = row.topic;
  setTimeout(() => {
    activeTopic.value = row;
    generatingId.value = '';
    setTimeout(() => {
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    }, 100);
  }, 500);
};

onMounted(() => {
  fetchData();
});
</script>

<style scoped lang="scss">
.guide-page {
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

.topic-text { font-weight: 500; color: #374151; font-size: 16px; }

/* 引导草稿区域 */
.draft-section {
  margin-top: 30px;
  animation: slideUp 0.4s ease-out;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 20px;
  padding-left: 10px;
}

.draft-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  border: 1px solid rgba(0,0,0,0.02);
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;

  &:hover {
    transform: translateY(-5px);
    box-shadow: 0 15px 30px rgba(0,0,0,0.08);
  }

  .card-icon {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
    font-size: 28px;
    margin-bottom: 16px;
  }

  .card-title { font-size: 18px; font-weight: 700; margin: 0 0 8px 0; color: #1f2937; }
  .card-desc { font-size: 12px; color: #9ca3af; margin: 0 0 20px 0; }
  
  .draft-content {
    background: #f9fafb;
    padding: 16px;
    border-radius: 12px;
    font-size: 15px;
    line-height: 1.6;
    color: #4b5563;
    font-style: italic;
    margin-bottom: 16px;
    flex-grow: 1;
    width: 100%;
    text-align: left;
    position: relative;
    &::before { content: '“'; font-size: 40px; position: absolute; top: -10px; left: 5px; color: #e5e7eb; font-family: serif; }
  }
}

.draft-card.authority {
  border-top: 4px solid #2563eb;
  .card-icon { background: #eff6ff; color: #2563eb; }
}

.draft-card.peer {
  border-top: 4px solid #f59e0b;
  .card-icon { background: #fffbeb; color: #f59e0b; }
}

.draft-card.kinship {
  border-top: 4px solid #e11d48;
  .card-icon { background: #fff1f2; color: #e11d48; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>