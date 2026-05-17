<script setup>
import { ref, computed, onMounted } from "vue";
import {
  getTeacherDashboard,
  getLevelDistribution,
  getTeacherGroups,
  getTeacherAlerts,
} from "@/modules/teacher/api";
import TeacherDashboardCharts from "@/components/TeacherDashboardCharts.vue";

// ── 看板聚合数据 ──
const dashboard = ref(null);
const dashboardLoading = ref(false);
const filterGroupId = ref(null);
const groups = ref([]);

const levelDist = ref(null);
const alerts = ref([]);

async function loadAlerts() {
  try {
    const res = await getTeacherAlerts();
    alerts.value = res.data?.alerts || [];
  } catch { alerts.value = []; }
}

// ── 计算属性 ──
const trend = computed(() => dashboard.value?.trend || []);
const levelDistribution = computed(() => dashboard.value?.level_distribution || { A: 0, B: 0, C: 0, unset: 0 });
const stats = computed(() => dashboard.value || {});

// ── 方法 ──
async function loadDashboard() {
  dashboardLoading.value = true;
  try {
    const params = {};
    if (filterGroupId.value) params.group_id = filterGroupId.value;
    const res = await getTeacherDashboard(params);
    dashboard.value = res.data;
  } catch {
    dashboard.value = null;
  } finally {
    dashboardLoading.value = false;
  }
}

async function loadGroups() {
  try {
    const res = await getTeacherGroups();
    groups.value = res.data || [];
  } catch { /* */ }
}

async function onGroupChange() {
  await loadDashboard();
  await loadLevelDistribution();
}

async function loadLevelDistribution() {
  try {
    const params = {};
    if (filterGroupId.value) params.group_id = filterGroupId.value;
    const res = await getLevelDistribution(params);
    levelDist.value = res.data;
  } catch { /* */ }
}

// ── 生命周期 ──
onMounted(() => {
  loadDashboard();
  loadGroups();
  loadLevelDistribution();
  loadAlerts();
});
</script>

<template>
  <div class="teacher-dashboard">
    <!-- 标题行 -->
    <div class="page-hd">
      <h1 class="page-title">教学看板</h1>
      <el-select
        v-model="filterGroupId"
        placeholder="全部分组"
        clearable
        size="default"
        style="width: 180px"
        @change="onGroupChange"
      >
        <el-option label="全部分组" value="" />
        <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
      </el-select>
    </div>

    <!-- 学习预警 -->
    <div v-if="alerts.length > 0" class="alerts-section">
      <div
        v-for="alert in alerts"
        :key="alert.student_id"
        class="alert-item"
        :class="'alert-' + alert.type"
        @click="$router.push(`/teacher/students?highlight=${alert.student_id}`)"
      >
        <span class="alert-dot" />
        <span class="alert-student">{{ alert.username }}</span>
        <span class="alert-desc">{{ alert.description }}</span>
      </div>
    </div>

    <!-- 4 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_students ?? '—' }}</div>
        <div class="stat-label">总学生数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value accent-gold">{{ stats.today_active_students ?? '—' }}</div>
        <div class="stat-label">今日活跃</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_practices_today ?? '—' }}</div>
        <div class="stat-label">今日练习</div>
      </div>
      <div class="stat-card">
        <div class="stat-value accent-gold">{{ stats.total_speaking_today ?? '—' }}</div>
        <div class="stat-label">今日口语</div>
      </div>
    </div>

    <!-- ECharts 图表区 -->
    <div class="charts-section">
      <TeacherDashboardCharts :trend="trend" :levelDistribution="levelDistribution" />
    </div>

    <!-- 快速入口 -->
    <div class="quick-section">
      <h3 class="section-title">快速入口</h3>
      <div class="quick-grid">
        <div class="quick-card" @click="$router.push('/teacher/students')">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#58CC02" stroke-width="1.8"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          <span>学生管理</span>
        </div>
        <div class="quick-card" @click="$router.push('/teacher/communication')">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#1CB0F6" stroke-width="1.8"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <span>学生消息</span>
        </div>
        <div class="quick-card" @click="$router.push('/teacher/tasks')">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#E6A23C" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          <span>任务公告</span>
        </div>
        <div class="quick-card" @click="$router.push('/teacher/assistant')">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#9B4DE0" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          <span>AI助手</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.teacher-dashboard { max-width: 1060px; margin: 0 auto; }

/* ── 标题行 ── */
.page-hd { display: flex; align-items: center; justify-content: space-between; margin-bottom: 22px; }

/* ── 预警 ── */
.alerts-section {
  display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px;
}
.alert-item {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all .15s; user-select: none;
}
.alert-item:hover { transform: translateY(-1px); }
.alert-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.alert-student { white-space: nowrap; }
.alert-desc { opacity: .75; }

.alert-unset_level { background: #F5F5F5; color: #909399; }
.alert-unset_level .alert-dot { background: #C0C4CC; }
.alert-unset_level:hover { background: #EBEBEB; }

.alert-inactive { background: #FFF8EC; color: #B87A14; }
.alert-inactive .alert-dot { background: #E6A23C; }
.alert-inactive:hover { background: #FFF2D8; }

.alert-accuracy_drop { background: #FEF0F0; color: #C45656; }
.alert-accuracy_drop .alert-dot { background: #F56C6C; }
.alert-accuracy_drop:hover { background: #FDE2E2; }
.page-title { font-size: 22px; font-weight: 800; color: #303133; margin: 0; letter-spacing: .02em; }

/* ── 统计卡片 ── */
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 22px; }
.stat-card {
  background: #fff; border-radius: 12px; padding: 22px 20px;
  text-align: center; border: 1px solid #EBEDF0;
  box-shadow: 0 1px 3px rgba(0,0,0,.03);
  transition: all .22s cubic-bezier(.4,0,.2,1);
  animation: cardUp .45s cubic-bezier(.16,1,.3,1) both;
  cursor: default;
}
.stat-card:nth-child(2) { animation-delay: .06s; }
.stat-card:nth-child(3) { animation-delay: .12s; }
.stat-card:nth-child(4) { animation-delay: .18s; }
@keyframes cardUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
.stat-card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,.07); border-color: #D4D4D4; }
.stat-value { font-size: 32px; font-weight: 800; color: #58CC02; line-height: 1.2; }
.stat-value.accent-gold { color: #E6A23C; }
.stat-label { font-size: 11.5px; color: #909399; margin-top: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; }

/* ── 图表区 ── */
.charts-section { margin-bottom: 26px; }

/* ── 快速入口 ── */
.quick-section { margin-bottom: 20px; }
.section-title { font-size: 15px; font-weight: 700; color: #303133; margin: 0 0 14px; }
.quick-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.quick-card {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  background: #fff; border: 1.5px solid #EBEDF0; border-radius: 12px;
  padding: 22px 12px; cursor: pointer; transition: all .2s;
  box-shadow: 0 1px 3px rgba(0,0,0,.02);
}
.quick-card:hover { transform: translateY(-3px); border-color: #E6A23C; box-shadow: 0 4px 14px rgba(230,162,60,.10); }
.quick-card span { font-size: 13px; font-weight: 600; color: #606266; }

@media (max-width: 768px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
}
</style>
