<script setup>
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { LineChart, BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

use([LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

const props = defineProps({
  weeklyActivity: { type: Array, default: () => [] },
});

const practiceOption = computed(() => {
  const dates = props.weeklyActivity.map((d) => d.date.slice(5));
  const practice = props.weeklyActivity.map((d) => d.practice_count);
  const speaking = props.weeklyActivity.map((d) => d.speaking_count);
  return {
    grid: { top: 40, right: 16, bottom: 24, left: 36 },
    tooltip: { trigger: "axis" },
    legend: { data: ["练习", "口语"], top: 8, textStyle: { fontSize: 11 } },
    xAxis: { type: "category", data: dates, axisLabel: { fontSize: 10 } },
    yAxis: { type: "value", minInterval: 1, axisLabel: { fontSize: 10 } },
    series: [
      { name: "练习", type: "line", data: practice, smooth: true, symbol: "circle", symbolSize: 4, lineStyle: { width: 2 } },
      { name: "口语", type: "line", data: speaking, smooth: true, symbol: "circle", symbolSize: 4, lineStyle: { width: 2 } },
    ],
  };
});

const accuracyOption = computed(() => {
  const dates = props.weeklyActivity.map((d) => d.date.slice(5));
  const accuracy = props.weeklyActivity.map((d) =>
    d.practice_count > 0 ? Math.round((d.correct_count / d.practice_count) * 100) : null
  );
  return {
    grid: { top: 40, right: 16, bottom: 24, left: 36 },
    tooltip: { trigger: "axis", formatter: (p) => `${p[0].axisValue}<br/>正确率: ${p[0].value ?? "-"}%` },
    legend: { data: ["正确率"], top: 8, textStyle: { fontSize: 11 } },
    xAxis: { type: "category", data: dates, axisLabel: { fontSize: 10 } },
    yAxis: { type: "value", min: 0, max: 100, axisLabel: { fontSize: 10, formatter: "{value}%" } },
    series: [
      {
        name: "正确率", type: "bar", data: accuracy,
        itemStyle: {
          color: (p) => (p.value != null && p.value >= 70 ? "#67C23A" : p.value != null ? "#E6A23C" : "#E5E6EB"),
          borderRadius: [4, 4, 0, 0],
        },
        barMaxWidth: 20,
      },
    ],
  };
});

const speakingScoreOption = computed(() => {
  const dates = props.weeklyActivity.map((d) => d.date.slice(5));
  const scores = props.weeklyActivity.map((d) => (d.speaking_count > 0 ? d.avg_speaking_score : null));
  return {
    grid: { top: 40, right: 16, bottom: 24, left: 36 },
    tooltip: { trigger: "axis", formatter: (p) => `${p[0].axisValue}<br/>口语均分: ${p[0].value ?? "-"}` },
    legend: { data: ["口语均分"], top: 8, textStyle: { fontSize: 11 } },
    xAxis: { type: "category", data: dates, axisLabel: { fontSize: 10 } },
    yAxis: { type: "value", min: 0, max: 5, axisLabel: { fontSize: 10 } },
    series: [
      {
        name: "口语均分", type: "line", data: scores, smooth: true,
        symbol: "circle", symbolSize: 5,
        lineStyle: { width: 2, color: "#E6A23C" },
        itemStyle: { color: "#E6A23C" },
        areaStyle: { color: "rgba(230,162,60,0.1)" },
      },
    ],
  };
});
</script>

<template>
  <div class="charts-grid">
    <div class="chart-card">
      <h4 class="chart-title">每日练习/口语次数</h4>
      <VChart :option="practiceOption" autoresize style="height:180px" />
    </div>
    <div class="chart-card">
      <h4 class="chart-title">每日正确率</h4>
      <VChart :option="accuracyOption" autoresize style="height:180px" />
    </div>
    <div class="chart-card">
      <h4 class="chart-title">口语平均评分</h4>
      <VChart v-if="weeklyActivity.some(d => d.speaking_count > 0)" :option="speakingScoreOption" autoresize style="height:180px" />
      <div v-else class="chart-empty">暂无口语数据</div>
    </div>
  </div>
</template>

<style scoped>
.charts-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.chart-card {
  background: #fff;
  border-radius: 8px;
  padding: 12px 8px 4px;
  border: 1px solid #ebeef5;
}
.chart-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin: 0 0 4px 8px;
}
.chart-empty {
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
  font-size: 13px;
}
@media (max-width: 900px) {
  .charts-grid { grid-template-columns: 1fr; }
}
</style>
