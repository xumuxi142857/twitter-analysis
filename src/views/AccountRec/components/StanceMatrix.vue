<template>
  <div ref="chartRef" style="width: 100%; height: 300px;"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import * as echarts from 'echarts';
// import type { StanceMatrixItem } from '@/types'; 

interface StanceMatrixItem {
    [key: string]: any; 
}

const props = defineProps<{ data: any[] }>();
const chartRef = ref<HTMLElement | null>(null);
let myChart: echarts.ECharts | null = null;

const hours = ['政治', '军事', '经济 ', '文化']; // Y轴
const days = ['负面/反华', '中立', '正面/亲华']; // X轴

const initChart = () => {
  if (!chartRef.value) return;
  myChart = echarts.init(chartRef.value);
  updateChart();
  window.addEventListener('resize', () => myChart?.resize());
};

const updateChart = () => {
  if (!myChart || !props.data) return;

  const maxVal = props.data.length > 0 
    ? Math.max(...props.data.map((item: any) => item[2])) 
    : 10;
  const visualMax = maxVal < 5 ? 5 : maxVal;

  const option = {
    tooltip: {
      position: 'top',
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderColor: '#e2e8f0',
      textStyle: { color: '#334155' },
      extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);', // 添加柔和阴影
      formatter: (params: any) => {
        return `
          <div style="font-size:12px; color:#64748b; margin-bottom:4px;">${hours[params.data[1]]} · ${days[params.data[0]]}</div>
          <div style="font-size:14px; color:#0ea5e9; font-weight:800;">强度: ${params.data[2]}</div>
        `;
      }
    },
    grid: {
      height: '68%', // 稍微减小绘图区高度，给底部留空间
      top: '10%',
      bottom: '22%', // 【关键修改】加大底部留白，防止X轴文字被 slider 遮挡
      left: '12%',
      right: '5%'
    },
    xAxis: {
      type: 'category',
      data: days,
      splitArea: { show: true, areaStyle: { color: ['rgba(248,250,252,0.5)', 'rgba(255,255,255,1)'] } },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { 
        color: '#64748b', 
        fontWeight: '600',
        fontSize: 12,
        margin: 10 // 文字距离轴线的距离
      }
    },
    yAxis: {
      type: 'category',
      data: hours,
      splitArea: { show: false },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { 
        color: '#64748b', 
        fontWeight: '600',
        fontSize: 12 
      }
    },
    visualMap: {
      min: 0,
      max: visualMax,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0, // 紧贴底部
      itemWidth: 16,
      itemHeight: 240, // 稍微加宽拖动条
      text: ['高', '低'],
      textGap: 10,
      textStyle: { color: '#94a3b8', fontSize: 11 },
      // 【关键修改】更柔和、清爽的“晴空蓝”渐变，不刺眼
      // 0: #f1f5f9 (灰白) -> 极低值几乎隐形
      // 0.4: #bae6fd (浅天蓝)
      // 0.8: #38bdf8 (天蓝)
      // 1.0: #0284c7 (海蓝) -> 最高值清晰但不炸眼
      inRange: {
        color: ['#f1f5f9', '#bae6fd', '#38bdf8', '#0284c7']
      }
    },
    series: [{
      name: '立场强度',
      type: 'heatmap',
      data: props.data,
      label: {
        //矩阵的数字显示
        show: true,
        color: 'inherit', // 自动适配颜色
        fontSize: 14,
        fontWeight: 'bold'
      },
      itemStyle: {
        borderRadius: 6, // 圆角稍微调小一点，显得更稳重
        borderColor: '#ffffff',
        borderWidth: 2
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 5,
          shadowColor: 'rgba(0, 0, 0, 0.1)',
          borderColor: '#0ea5e9',
          borderWidth: 2
        }
      }
    }]
  };
  myChart.setOption(option);
};

watch(() => props.data, updateChart, { deep: true });
onMounted(initChart);
</script>