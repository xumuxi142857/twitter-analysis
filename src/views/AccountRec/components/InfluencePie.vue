<template>
  <div ref="chartRef" style="width: 100%; height: 300px;"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import * as echarts from 'echarts';
import type { InfluenceType } from '@/types';

const props = defineProps<{ data: InfluenceType[] }>();
const chartRef = ref(null);
let myChart: any = null;

const initChart = () => {
  if (!chartRef.value) return;
  myChart = echarts.init(chartRef.value);
  updateChart();
};

const updateChart = () => {
  if (!myChart || !props.data) return;

  const option = {
    tooltip: { trigger: 'item' },
    legend: { bottom: '0%', left: 'center' },
    color: ['#f87171', '#fbbf24', '#60a5fa'], // 红(亲情), 黄(同伴), 蓝(权威)
    series: [
      {
        name: '影响类型',
        type: 'pie',
        radius: ['40%', '70%'], // 环形图更现代
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: { show: false, position: 'center' },
        emphasis: {
          label: { show: true, fontSize: 20, fontWeight: 'bold' }
        },
        labelLine: { show: false },
        data: props.data
      }
    ]
  };
  myChart.setOption(option);
};

watch(() => props.data, updateChart, { deep: true });
onMounted(initChart);
</script>