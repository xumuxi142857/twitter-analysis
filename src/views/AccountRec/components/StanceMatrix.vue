<template>
  <div ref="chartRef" style="width: 100%; height: 300px;"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import * as echarts from 'echarts';
import type { StanceMatrixItem } from '@/types';

const props = defineProps<{ data: StanceMatrixItem[] }>();
const chartRef = ref(null);
let myChart: any = null;

// 定义坐标轴含义
const hours = ['政治', '军事', '经济 ', '文化']; // Y轴
const days = ['负面/反华', '中立', '正面/亲华']; // X轴

const initChart = () => {
  if (!chartRef.value) return;
  myChart = echarts.init(chartRef.value);
  updateChart();
};

const updateChart = () => {
  if (!myChart || !props.data) return;

  // 将数据映射到 heatmap 所需格式
  // data item: [x, y, value]
  const option = {
    tooltip: { position: 'top' },
    grid: { height: '70%', top: '10%' },
    xAxis: {
      type: 'category',
      data: days,
      splitArea: { show: true }
    },
    yAxis: {
      type: 'category',
      data: hours,
      splitArea: { show: true }
    },
    visualMap: {
      min: 0,
      max: 10,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#f0f9ff', '#bae6fd', '#0284c7'] // 浅蓝到深蓝
      }
    },
    series: [{
      name: '立场强度',
      type: 'heatmap',
      data: props.data,
      label: { show: true },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  };
  myChart.setOption(option);
};

watch(() => props.data, updateChart, { deep: true });
onMounted(initChart);
</script>