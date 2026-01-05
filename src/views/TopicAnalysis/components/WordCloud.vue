<template>
  <div ref="chartRef" style="width: 100%; height: 300px;"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import * as echarts from 'echarts';
import 'echarts-wordcloud';
import type { WordCloudItem } from '@/types'; // 使用我们定义的类型

// 接收父组件传来的数据
const props = defineProps<{ data: WordCloudItem[] }>();
const chartRef = ref(null);
let myChart: any = null;

const renderChart = () => {
  if (!chartRef.value) return;
  if (!myChart) myChart = echarts.init(chartRef.value);

  myChart.setOption({
    series: [{
      type: 'wordCloud',
      gridSize: 10,
      sizeRange: [12, 120],
      rotationRange: [-45, 90],
      shape: 'circle',
      textStyle: {
        fontFamily: 'sans-serif',
        fontWeight: 'bold',
        color: () => `rgb(${Math.round(Math.random() * 160)}, ${Math.round(Math.random() * 160)}, ${Math.round(Math.random() * 160)})`
      },
      data: props.data
    }]
  });
};

watch(() => props.data, renderChart); // 数据变了就重画
onMounted(renderChart); // 挂载时画
</script>