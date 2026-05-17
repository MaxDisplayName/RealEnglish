<script setup>
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { LineChart, BarChart, PieChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

use([LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

const props = defineProps({
  trend: { type: Array, default: () => [] },
  levelDistribution: { type: Object, default: () => ({ A: 0, B: 0, C: 0, unset: 0 }) },
});

const commonGrid = { top: 38, right: 16, bottom: 24, left: 40 };
const axisLabelStyle = { fontSize: 10, color: "#909399" };

const trendOption = computed(() => {
  const dates = props.trend.map((d) => d.date.slice(5));
  const practice = props.trend.map((d) => d.practice_count);
  const speaking = props.trend.map((d) => d.speaking_count);
  return {
    grid: commonGrid,
    tooltip: { trigger: "axis" },
    legend: { data: ["练习", "口语"], top: 6, textStyle: { fontSize: 11, color: "#606266" } },
    xAxis: { type: "category", data: dates, axisLabel: axisLabelStyle, axisLine: { lineStyle: { color: "#E4E7ED" } } },
    yAxis: { type: "value", minInterval: 1, axisLabel: axisLabelStyle, splitLine: { lineStyle: { color: "#F2F3F5" } } },
    series: [
      { name: "练习", type: "line", data: practice, smooth: true, symbol: "circle", symbolSize: 4, lineStyle: { width: 2, color: "#58CC02" }, itemStyle: { color: "#58CC02" } },
      { name: "口语", type: "line", data: speaking, smooth: true, symbol: "circle", symbolSize: 4, lineStyle: { width: 2, color: "#E6A23C" }, itemStyle: { color: "#E6A23C" } },
    ],
  };
});

const accuracyOption = computed(() => {
  const dates = props.trend.map((d) => d.date.slice(5));
  const data = props.trend.map((d) => (d.practice_count > 0 ? d.correct_rate : null));
  return {
    grid: commonGrid,
    tooltip: { trigger: "axis", formatter: (p) => `${p[0].axisValue}<br/>正确率: ${p[0].value ?? "-"}%` },
    legend: { data: ["正确率"], top: 6, textStyle: { fontSize: 11, color: "#606266" } },
    xAxis: { type: "category", data: dates, axisLabel: axisLabelStyle, axisLine: { lineStyle: { color: "#E4E7ED" } } },
    yAxis: { type: "value", min: 0, max: 100, axisLabel: { fontSize: 10, color: "#909399", formatter: "{value}%" }, splitLine: { lineStyle: { color: "#F2F3F5" } } },
    series: [{
      name: "正确率", type: "bar", data,
      itemStyle: {
        color: (p) => (p.value != null && p.value >= 70 ? "#67C23A" : p.value != null ? "#E6A23C" : "#DCDFE6"),
        borderRadius: [4, 4, 0, 0],
      },
      barMaxWidth: 20,
    }],
  };
});

const speakingScoreOption = computed(() => {
  const dates = props.trend.map((d) => d.date.slice(5));
  const data = props.trend.map((d) => (d.speaking_count > 0 ? d.avg_speaking_score : null));
  return {
    grid: commonGrid,
    tooltip: { trigger: "axis", formatter: (p) => `${p[0].axisValue}<br/>口语均分: ${p[0].value ?? "-"}` },
    legend: { data: ["口语均分"], top: 6, textStyle: { fontSize: 11, color: "#606266" } },
    xAxis: { type: "category", data: dates, axisLabel: axisLabelStyle, axisLine: { lineStyle: { color: "#E4E7ED" } } },
    yAxis: { type: "value", min: 0, max: 5, axisLabel: { fontSize: 10, color: "#909399" }, splitLine: { lineStyle: { color: "#F2F3F5" } } },
    series: [{
      name: "口语均分", type: "line", data, smooth: true,
      symbol: "circle", symbolSize: 5,
      lineStyle: { width: 2, color: "#E6A23C" },
      itemStyle: { color: "#E6A23C" },
      areaStyle: { color: "rgba(230,162,60,0.08)" },
    }],
  };
});

const levelPieOption = computed(() => {
  const { A, B, C, unset } = props.levelDistribution || {};
  const total = A + B + C + unset || 1;
  const data = [
    { value: A, name: "A级", itemStyle: { color: "#67C23A" } },
    { value: B, name: "B级", itemStyle: { color: "#1CB0F6" } },
    { value: C, name: "C级", itemStyle: { color: "#9B4DE0" } },
    { value: unset, name: "未定级", itemStyle: { color: "#C0C4CC" } },
  ].filter((d) => d.value > 0);
  return {
    tooltip: { trigger: "item", formatter: "{b}: {c}人 ({d}%)" },
    legend: { orient: "vertical", right: 8, top: "center", textStyle: { fontSize: 10, color: "#606266" }, itemWidth: 10, itemHeight: 10 },
    series: [{
      type: "pie", radius: ["48%", "72%"], center: ["38%", "50%"],
      data, label: { show: false }, emphasis: { scale: false, label: { show: true, fontSize: 13, fontWeight: "bold" } },
      itemStyle: { borderRadius: 4, borderColor: "#fff", borderWidth: 2 },
    }],
  };
});
</script>

<template>
  <div class="t-charts">
    <div class="t-chart-card">
      <h4 class="t-chart-title">练习 / 口语趋势</h4>
      <VChart v-if="trend.length" :option="trendOption" autoresize style="height:196px" />
      <div v-else class="t-chart-empty">暂无趋势数据</div>
    </div>
    <div class="t-chart-card">
      <h4 class="t-chart-title">日均正确率</h4>
      <VChart v-if="trend.length" :option="accuracyOption" autoresize style="height:196px" />
      <div v-else class="t-chart-empty">暂无正确率数据</div>
    </div>
    <div class="t-chart-card">
      <h4 class="t-chart-title">口语均分走势</h4>
      <VChart v-if="trend.some(d => d.speaking_count > 0)" :option="speakingScoreOption" autoresize style="height:196px" />
      <div v-else class="t-chart-empty">暂无口语评分数据</div>
    </div>
    <div class="t-chart-card">
      <h4 class="t-chart-title">等级分布</h4>
      <VChart v-if="Object.values(levelDistribution).some(v => v > 0)" :option="levelPieOption" autoresize style="height:196px" />
      <div v-else class="t-chart-empty">暂无等级数据</div>
    </div>
  </div>
</template>

<style scoped>
.t-charts {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}
.t-chart-card {
  background: #fff;
  border-radius: 12px;
  padding: 14px 14px 6px;
  border: 1px solid #EBEDF0;
  box-shadow: 0 1px 3px rgba(0,0,0,.03);
  transition: box-shadow .25s;
}
.t-chart-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.06); }
.t-chart-title {
  font-size: 12.5px;
  font-weight: 600;
  color: #606266;
  margin: 0 0 2px 6px;
  letter-spacing: .03em;
}
.t-chart-empty {
  height: 196px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #C0C4CC;
  font-size: 13px;
}
@media (max-width: 900px) {
  .t-charts { grid-template-columns: 1fr; }
}
</style>
