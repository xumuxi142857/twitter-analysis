<template>
  <el-table 
    :data="data" 
    style="width: 100%" 
    :row-style="{ height: '65px' }" 
    :header-cell-style="headerStyle"
  >
    <el-table-column type="index" label="Rank" width="80" align="center">
      <template #default="scope">
        <div class="rank-badge" :class="getRankClass(scope.$index)">{{ scope.$index + 1 }}</div>
      </template>
    </el-table-column>
    
    <el-table-column prop="topic" label="话题摘要 / Topic Summary" min-width="400">
      <template #default="scope">
        <span class="topic-text">{{ scope.row.topic }}</span>
      </template>
    </el-table-column>

    <el-table-column prop="stance" label="立场研判 / Stance" width="180" align="center">
      <template #default="scope">
        <div class="stance-pill" :class="scope.row.stance">
          <span class="dot"></span>
          {{ getStanceLabel(scope.row.stance) }}
        </div>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { TopicStance } from '@/types';

defineProps<{ data: TopicStance[] }>();

// 表头样式配置
const headerStyle = {
  background: '#f9fafb',
  color: '#4b5563',
  fontSize: '15px',
  fontWeight: '600',
  height: '50px'
};

const getRankClass = (index: number) => {
  if (index === 0) return 'top-1';
  if (index === 1) return 'top-2';
  if (index === 2) return 'top-3';
  return 'normal';
};

const getStanceLabel = (stance: string) => {
  const map: Record<string, string> = {
    'positive': '正面 Positive',
    'neutral': '中性 Neutral',
    'negative': '负面 Negative'
  };
  return map[stance] || stance;
};
</script>

<style scoped lang="scss">
.topic-text {
  font-size: 16px; /* 增大字体 */
  font-weight: 500;
  color: #1f2937; /* 深灰色，高对比度 */
  line-height: 1.5;
}

/* 排名徽章 */
.rank-badge {
  width: 28px;
  height: 28px;
  line-height: 28px;
  border-radius: 50%;
  background: #f3f4f6;
  color: #6b7280;
  margin: 0 auto;
  font-weight: bold;
  font-size: 14px;

  &.top-1 { background: #fee2e2; color: #dc2626; } /* 红色 */
  &.top-2 { background: #ffedd5; color: #ea580c; } /* 橙色 */
  &.top-3 { background: #fef9c3; color: #ca8a04; } /* 黄色 */
}

/* 自定义立场胶囊 (比 el-tag 更漂亮) */
.stance-pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 16px;
  border-radius: 9999px; /* 全圆角 */
  font-size: 14px;
  font-weight: 600;
  
  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    margin-right: 8px;
  }

  &.positive {
    background: #dcfce7;
    color: #166534;
    .dot { background: #166534; }
  }

  &.negative {
    background: #fee2e2;
    color: #991b1b;
    .dot { background: #991b1b; }
  }

  &.neutral {
    background: #f3f4f6;
    color: #4b5563;
    .dot { background: #9ca3af; }
  }
}
</style>