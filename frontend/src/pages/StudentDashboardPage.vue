<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "@/stores/user";
import { getDashboard } from "@/api/student/api";
import LevelBadge from "@/components/LevelBadge.vue";
import DashboardCharts from "@/components/DashboardCharts.vue";
import ContributionHeatmap from "@/components/ContributionHeatmap.vue";
import BindTeacherDialog from "@/components/BindTeacherDialog.vue";
import { VideoPlay, Microphone, Document, MagicStick } from "@element-plus/icons-vue";

const router = useRouter();
const userStore = useUserStore();

const dashboard = ref(null);
const loading = ref(true);

const showBindDialog = ref(false);

const stats = computed(() => dashboard.value || {});
const clips = computed(() => dashboard.value?.recommended_clips || []);
const weeklyActivity = computed(() => dashboard.value?.weekly_activity || []);
const heatmapData = computed(() => dashboard.value?.heatmap_data || []);

const accuracyText = computed(() => {
  const d = dashboard.value;
  if (!d || !d.today_practice_count) return "暂无练习记录";
  // 从后端获取总统计
  return "";
});

onMounted(async () => {
  try {
    const res = await getDashboard();
    dashboard.value = res.data || {};
  } catch (e) {
    dashboard.value = {};
  } finally {
    loading.value = false;
  }

  if (
    userStore.isStudent &&
    !userStore.userInfo?.teacher_id &&
    !localStorage.getItem("bind_skipped")
  ) {
    showBindDialog.value = true;
  }
});
</script>

<template>
  <div class="student-dashboard">
    <BindTeacherDialog v-model="showBindDialog" />

    <!-- Welcome -->
    <div class="welcome-card">
      <div class="welcome-info">
        <h2>你好，{{ userStore.userInfo?.username || "同学" }}</h2>
        <p>继续你的英语学习之旅</p>
      </div>
      <LevelBadge v-if="userStore.level" :level="userStore.level" />
    </div>

    <!-- Stats: 3 cards -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value">{{ stats.today_practice_count || 0 }}</div>
        <div class="stat-label">今日练习次数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.today_clip_count || 0 }}</div>
        <div class="stat-label">今日学习片段</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.today_speaking_count || 0 }}</div>
        <div class="stat-label">今日口语练习</div>
      </div>
    </div>

    <!-- Data Dashboard -->
    <div v-if="weeklyActivity.length > 0" class="dashboard-section">
      <h3 class="section-title">数据看板</h3>
      <div class="dashboard-layout">
        <div class="dashboard-charts">
          <DashboardCharts :weeklyActivity="weeklyActivity" />
        </div>
        <div class="dashboard-heatmap">
          <ContributionHeatmap :heatmapData="heatmapData" />
        </div>
      </div>
    </div>
    <div v-else-if="!loading" class="dashboard-section">
      <h3 class="section-title">数据看板</h3>
      <div class="dashboard-empty">
        <p>还没有学习数据，快去开始练习吧！</p>
      </div>
    </div>

    <!-- Quick actions -->
    <div class="quick-actions">
      <h3 class="section-title">快速入口</h3>
      <div class="action-grid">
        <div class="action-card" @click="router.push('/student/clips')">
          <el-icon class="action-icon" :size="24"><VideoPlay /></el-icon>
          <span>影视片段</span>
        </div>
        <div class="action-card" @click="router.push('/student/free-talk')">
          <el-icon class="action-icon" :size="24"><Microphone /></el-icon>
          <span>情景对话</span>
        </div>
        <div class="action-card" @click="router.push('/student/accumulate')">
          <el-icon class="action-icon" :size="24"><Document /></el-icon>
          <span>我的积累</span>
        </div>
        <div class="action-card" @click="router.push('/student/assistant')">
          <el-icon class="action-icon" :size="24"><MagicStick /></el-icon>
          <span>学习助手</span>
        </div>
      </div>
    </div>

    <!-- Recommended clips -->
    <div class="clip-section" v-if="clips.length > 0">
      <h3 class="section-title">推荐片段</h3>
      <div class="clip-grid">
        <div
          v-for="clip in clips"
          :key="clip.id"
          class="clip-card"
          @click="router.push(`/student/clips/${clip.id}`)"
        >
          <div class="clip-difficulty" :class="'level-' + clip.difficulty">
            {{ clip.difficulty }}
          </div>
          <div class="clip-title">{{ clip.title || "未命名片段" }}</div>
          <div class="clip-category">{{ clip.category || "" }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.student-dashboard { max-width: 960px; margin: 0 auto; }

/* welcome */
.welcome-card {
  display: flex; justify-content: space-between; align-items: center;
  background: var(--color-primary); color: #fff; border-radius: var(--radius-md);
  padding: 32px; margin-bottom: 24px;
  box-shadow: 0 4px 0 #45A502;
}
.welcome-info h2 { margin: 0 0 6px; font-size: 24px; font-weight: 800; }
.welcome-info p { margin: 0; opacity: .8; font-size: 14px; }

/* stats */
.stats-row {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 28px;
}
.stat-card {
  background: #fff; border-radius: var(--radius-base); padding: 22px 18px;
  text-align: center; border: 2px solid var(--border-color);
  transition: all .2s ease; cursor: default;
}
.stat-card:hover { transform: translateY(-3px); border-color: #D1D1D1; box-shadow: var(--shadow-md); }
.stat-value { font-size: 30px; font-weight: 800; color: var(--color-primary); margin-bottom: 4px; }
.stat-label { font-size: 13px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: .04em; }

/* section title */
.section-title { margin: 0 0 14px; font-size: 18px; font-weight: 800; }

/* dashboard */
.dashboard-section { margin-bottom: 28px; }
.dashboard-layout {
  display: grid; grid-template-columns: 1fr 300px; gap: 16px;
  align-items: start;
}
@media (max-width: 900px) {
  .dashboard-layout { grid-template-columns: 1fr; }
}
.dashboard-empty {
  background: #fff; border: 2px solid #ebeef5; border-radius: var(--radius-base);
  padding: 40px; text-align: center; color: #c0c4cc; font-size: 14px;
}

/* quick actions */
.quick-actions { margin-bottom: 28px; }
.action-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.action-card {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  background: #fff; border: 2px solid var(--border-color); border-radius: var(--radius-base);
  padding: 22px 12px; cursor: pointer; transition: all .2s ease;
}
.action-card:hover { transform: translateY(-3px); border-color: var(--color-primary); box-shadow: 0 4px 0 #45A502; }
.action-icon { font-size: 30px; transition: transform .2s ease; }
.action-card:hover .action-icon { transform: scale(1.15); }

/* recommended clips */
.clip-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.clip-card {
  background: #fff; border: 2px solid var(--border-color); border-radius: var(--radius-base);
  padding: 16px; cursor: pointer; position: relative; transition: all .2s ease;
}
.clip-card:hover { transform: translateY(-2px); border-color: var(--color-blue); box-shadow: var(--shadow-md); }
.clip-difficulty {
  position: absolute; top: 10px; right: 10px;
  font-size: 11px; font-weight: 800; padding: 2px 8px; border-radius: 20px;
}
.level-A { background: var(--color-primary-light); color: var(--color-primary-dark); }
.level-B { background: var(--color-blue-light); color: #1493D3; }
.level-C { background: var(--color-purple-light); color: #9B4DE0; }
.clip-title { font-weight: 700; margin-bottom: 4px; padding-right: 34px; font-size: 14px; }
.clip-category { font-size: 12px; color: var(--text-secondary); font-weight: 500; }
</style>
