<script setup>
import { ref, computed, onMounted, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getClipDetail } from "@/modules/student/api";
import SpeakingRecorder from "@/components/SpeakingRecorder.vue";
import { parseDialogue } from "@/utils/dialogueParser";
import { ArrowLeft, CircleCheck } from "@element-plus/icons-vue";
import request from "@/api/shared/request";

const route = useRoute();
const router = useRouter();

const clip = ref(null);
const loading = ref(true);
const error = ref(null);
const activeTab = ref("repeat"); // repeat / free

/** 已完成评测的行索引集合 */
const completedLines = ref(new Set());

/** 解析后的对话行 */
const dialogueLines = computed(() => {
  if (!clip.value?.dialogue_text) return [];
  return parseDialogue(clip.value.dialogue_text, clip.value.character_genders);
});

/** 进度文本 */
const progressText = computed(() => {
  const total = dialogueLines.value.length;
  const done = completedLines.value.size;
  return total > 0 ? `已完成 ${done}/${total} 句` : "";
});

// 趋势图
const trendVisible = ref(false);
const trendData = ref([]);
const trendChart = ref(null);

async function loadTrend() {
  try {
    const res = await request.get("/speaking/history");
    trendData.value = res.data || [];
  } catch { trendData.value = []; }
}

async function toggleTrend() {
  trendVisible.value = !trendVisible.value;
  if (trendVisible.value) {
    await loadTrend();
    await nextTick();
    renderTrendChart();
  }
}

function renderTrendChart() {
  if (!trendChart.value || trendData.value.length < 2) return;
  import("echarts").then((echarts) => {
    const chart = echarts.init(trendChart.value);
    const dates = trendData.value.map(r => r.created_at?.slice(0, 10) || "");
    const scores = trendData.value.map(r => r.total_score);
    const accuracy = trendData.value.map(r => r.accuracy);
    const fluency = trendData.value.map(r => r.fluency);
    chart.setOption({
      tooltip: { trigger: "axis" },
      legend: { data: ["总分", "准确度", "流畅度"], bottom: 0 },
      grid: { left: 40, right: 20, top: 20, bottom: 40 },
      xAxis: { type: "category", data: dates, axisLabel: { rotate: 30, fontSize: 10 } },
      yAxis: { type: "value", min: 0, max: 5, interval: 1 },
      series: [
        { name: "总分", type: "line", data: scores, smooth: true, lineStyle: { color: "#58CC02", width: 2 }, itemStyle: { color: "#58CC02" } },
        { name: "准确度", type: "line", data: accuracy, smooth: true, lineStyle: { color: "#1CB0F6", width: 1.5 }, itemStyle: { color: "#1CB0F6" } },
        { name: "流畅度", type: "line", data: fluency, smooth: true, lineStyle: { color: "#9B4DE0", width: 1.5 }, itemStyle: { color: "#9B4DE0" } },
      ],
    });
    window.addEventListener("resize", () => chart.resize(), { once: true });
  }).catch(() => {});
}

onMounted(async () => {
  try {
    const res = await getClipDetail(route.params.id);
    clip.value = res.data;
  } catch (e) {
    error.value = e.response?.data?.detail || "加载失败";
  } finally {
    loading.value = false;
  }
});

function onLineComplete(result) {
  if (result.lineIndex !== undefined) {
    completedLines.value = new Set([...completedLines.value, result.lineIndex]);
  }
}
</script>

<template>
  <div class="speaking-practice">
    <div class="page-header">
      <h2>口语练习</h2>
      <el-button size="small" :icon="ArrowLeft" text @click="router.push(`/clips/${route.params.id}`)">返回片段</el-button>
    </div>

    <div v-if="loading">
      <el-skeleton :rows="6" animated />
    </div>

    <div v-else-if="error" class="state-wrap">
      <el-result icon="error" :title="error">
        <template #extra>
          <el-button @click="router.back()">返回</el-button>
        </template>
      </el-result>
    </div>

    <div v-else class="practice-content">
      <!-- 模式选择 -->
      <el-card class="mode-card" shadow="never">
        <el-radio-group v-model="activeTab" class="mode-tabs">
          <el-radio-button value="repeat">跟读模式</el-radio-button>
          <el-radio-button value="free">自由应答</el-radio-button>
        </el-radio-group>
        <p class="mode-desc">
          {{
            activeTab === "repeat"
              ? "逐句跟读台词，AI 将评测你的发音准确度和流畅度"
              : "AI 会根据剧情生成一个开放性问题，你用英语口述回答"
          }}
        </p>
      </el-card>

      <!-- 跟读模式：逐句显示 + 录音 -->
      <template v-if="activeTab === 'repeat'">
        <div v-if="dialogueLines.length === 0" class="empty-dialogue">
          <el-empty description="暂无对话文本" />
        </div>

        <div v-else class="dialogue-practice-list">
          <div class="progress-bar">
            <el-tag type="success" v-if="progressText">
              <el-icon style="margin-right: 4px"><CircleCheck /></el-icon>
              {{ progressText }}
            </el-tag>
          </div>

          <SpeakingRecorder
            v-for="(line, idx) in dialogueLines"
            :key="idx"
            :line="line"
            :line-index="idx"
            :mode="activeTab"
            :clip-id="route.params.id"
            @practice-complete="onLineComplete"
          />
        </div>
      </template>

      <!-- 自由应答模式：保持原有界面 -->
      <template v-else>
        <SpeakingRecorder
          :summary="clip?.summary || ''"
          :mode="activeTab"
          :clip-id="route.params.id"
        />
      </template>

      <!-- 历史趋势图 -->
      <div class="trend-section">
        <el-button size="small" text @click="toggleTrend">
          {{ trendVisible ? '收起趋势' : '查看历史趋势' }}
        </el-button>
        <div v-if="trendVisible" class="trend-chart-wrap">
          <div v-if="trendData.length < 2" class="trend-empty">需要至少 2 次练习数据才能展示趋势</div>
          <div ref="trendChart" v-else style="width:100%;height:260px" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.speaking-practice {
  max-width: 640px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 22px;
  color: #303133;
}

.state-wrap {
  margin-top: 60px;
}

.practice-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.mode-card {
  margin-bottom: 20px;
  border-radius: var(--radius-base);
}

.mode-tabs {
  display: flex;
  margin-bottom: 12px;
}

.mode-desc {
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
}

.empty-dialogue {
  margin-top: 40px;
}

.dialogue-practice-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.progress-bar {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.trend-section { margin-top: 24px; text-align: center; }
.trend-chart-wrap { margin-top: 12px; }
.trend-empty { padding: 30px; color: #C0C4CC; font-size: 13px; }
</style>
