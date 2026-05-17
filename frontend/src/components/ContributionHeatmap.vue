<script setup>
import { computed } from "vue";

const props = defineProps({
  heatmapData: { type: Array, default: () => [] },
});

const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];

/** 本地日期 → "2026-04-01" 格式（不涉及时区转换） */
function localKey(year, month, day) {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

const heatmapGrid = computed(() => {
  const map = {};
  for (const d of props.heatmapData) {
    map[d.date] = d.count;
  }

  const today = new Date();
  const thisYear = today.getFullYear();
  const thisMonth = today.getMonth();   // 0-index
  const thisDay = today.getDate();

  // 上月（跨年自动处理）
  const prevY = thisMonth === 0 ? thisYear - 1 : thisYear;
  const prevM = thisMonth === 0 ? 12 : thisMonth; // 1-index
  // 本月
  const curY = thisYear;
  const curM = thisMonth + 1;                      // 1-index

  // 上月第一天 + 本月最后一天
  const firstOfPrev = new Date(prevY, prevM - 1, 1);
  const firstY = firstOfPrev.getFullYear();
  const firstM = firstOfPrev.getMonth() + 1;
  const lastOfCur = new Date(thisYear, thisMonth + 1, 0);

  // 网格起点 = 上月第一天对齐到周日
  const startDow = firstOfPrev.getDay();
  const gridStartDay = firstOfPrev.getDate() - startDow;
  const gridStart = new Date(firstY, firstM - 1, gridStartDay);

  // 网格结束 = 本月最后一天对齐到周六
  const lastDow = lastOfCur.getDay();
  const gridEndDay = lastOfCur.getDate() + (lastDow < 6 ? 6 - lastDow : 0);
  const gridEnd = new Date(thisYear, thisMonth, gridEndDay);

  // 总天数和周数
  const totalDays = Math.round((gridEnd - gridStart) / 86400000) + 1;
  const weeks = Math.ceil(totalDays / 7);

  const cells = [];
  for (let w = 0; w < weeks; w++) {
    const col = [];
    for (let d = 0; d < 7; d++) {
      const cd = new Date(gridStart);
      cd.setDate(gridStart.getDate() + w * 7 + d);
      const cy = cd.getFullYear();
      const cm = cd.getMonth() + 1;
      const cday = cd.getDate();
      const key = localKey(cy, cm, cday);
      const count = map[key] || 0;

      // 是否在 [4月, 5月] 范围内（完整两个月）
      const inRange = (cm === firstM && cy === firstY) || (cm === curM && cy === curY);
      // 是否在今天之后（未来）
      const future = cy > thisYear
        || (cy === thisYear && cm > thisMonth + 1)
        || (cy === thisYear && cm === thisMonth + 1 && cday > thisDay);

      col.push({ date: key, count, future, inRange });
    }
    cells.push(col);
  }

  return { cells, weeks, firstM, curM, firstY, curY };
});

function colorClass(count, inRange, future) {
  if (!inRange) return "level-out";
  if (future) return "level-future";
  if (count === 0) return "level-0";
  if (count <= 2) return "level-1";
  if (count <= 5) return "level-2";
  if (count <= 9) return "level-3";
  return "level-4";
}

const monthLabels = computed(() => {
  const { cells, firstM, curM } = heatmapGrid.value;
  const labels = [];
  let foundFirst = false;
  let foundLast = false;
  for (let w = 0; w < cells.length; w++) {
    const thu = cells[w][4]; // 周四比较稳定
    if (!thu || thu.future) continue;
    const m = parseInt(thu.date.slice(5, 7), 10);
    if (!foundFirst && m === firstM) { labels.push({ week: w, label: `${m}月` }); foundFirst = true; }
    else if (!foundLast && m === curM) { labels.push({ week: w, label: `${m}月` }); foundLast = true; }
  }
  return labels;
});

const totalWeeks = computed(() => heatmapGrid.value.weeks);

const dayLabels = computed(() => {
  const firstCol = heatmapGrid.value.cells[0];
  if (!firstCol) return [];
  return firstCol.map((d) => {
    const parts = d.date.split("-");
    const dt = new Date(+parts[0], +parts[1] - 1, +parts[2]);
    return WEEKDAYS[dt.getDay()];
  });
});

const monthRowColumns = computed(() => `repeat(${totalWeeks.value}, 15px)`);
</script>

<template>
  <div class="heatmap-wrap">
    <h4 class="heatmap-title">学习活跃度</h4>
    <div class="heatmap-scroll">
      <div class="heatmap-grid">
        <div class="day-labels">
          <span v-for="(lb, i) in dayLabels" :key="i">{{ lb }}</span>
        </div>
        <div class="grid-body">
          <div class="month-row" :style="{ gridTemplateColumns: monthRowColumns }">
            <span v-for="ml in monthLabels" :key="ml.week"
              :style="{ gridColumn: `${ml.week + 1}` }">{{ ml.label }}</span>
          </div>
          <div class="weeks-grid"
            :style="{
              gridTemplateColumns: `repeat(${totalWeeks}, 15px)`,
              gridTemplateRows: `repeat(7, 15px)`,
            }">
            <template v-for="(col, wi) in heatmapGrid.cells" :key="wi">
              <span v-for="(day, di) in col" :key="di"
                class="heat-cell"
                :class="colorClass(day.count, day.inRange, day.future)"
                :title="`${day.date}: ${day.count} 次活动`" />
            </template>
          </div>
        </div>
      </div>
    </div>
    <div class="heat-legend">
      <span>少</span>
      <span class="legend-cell level-0" /><span class="legend-cell level-1" />
      <span class="legend-cell level-2" /><span class="legend-cell level-3" />
      <span class="legend-cell level-4" />
      <span>多</span>
    </div>
  </div>
</template>

<style scoped>
.heatmap-wrap {
  background: #fff; border-radius: 8px; padding: 14px 16px 10px;
  border: 1px solid #ebeef5;
}
.heatmap-title { font-size: 13px; font-weight: 600; color: #606266; margin: 0 0 8px 0; }
.heatmap-scroll { overflow-x: auto; padding-bottom: 4px; }
.heatmap-grid { display: flex; gap: 4px; min-width: fit-content; }

.day-labels {
  display: flex; flex-direction: column; gap: 4px; padding-top: 16px;
  margin-right: 4px; flex-shrink: 0;
}
.day-labels span { width: 20px; height: 15px; font-size: 10px; color: #909399; line-height: 15px; text-align: right; }

.grid-body { display: flex; flex-direction: column; }

.month-row { display: grid; gap: 4px; margin-bottom: 4px; height: 15px; }
.month-row span { font-size: 10px; color: #606266; font-weight: 600; white-space: nowrap; }

.weeks-grid { display: grid; grid-auto-flow: column; gap: 4px; }
.heat-cell { width: 15px; height: 15px; border-radius: 3px; }

.level-out { background: transparent; }
.level-future { background: #f0f0f0; border: 1px dashed #d9d9d9; }
.level-0  { background: #ebedf0; }
.level-1  { background: #9be9a8; }
.level-2  { background: #40c463; }
.level-3  { background: #30a14e; }
.level-4  { background: #216e39; }

.heat-legend {
  display: flex; align-items: center; gap: 4px; margin-top: 10px;
  font-size: 10px; color: #c0c4cc; justify-content: flex-end;
}
.legend-cell { width: 12px; height: 12px; border-radius: 2px; }
</style>
