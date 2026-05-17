<script setup>
import { ref, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { ArrowLeft } from "@element-plus/icons-vue";
import {
  getTeacherTasks, createTask, updateTask, deleteTask, toggleTaskStatus,
  getTaskDetail, getTeacherGroups,
  getAnnouncements, createAnnouncement, updateAnnouncement, deleteAnnouncement, pinAnnouncement,
} from "@/modules/teacher/api";

const activeTab = ref("tasks");

// ── 任务 ──
const tasks = ref([]);
const loading = ref(false);
const groups = ref([]);
const filterGroup = ref(null);
const filterStatus = ref(null);

// ── 公告 ──
const announcements = ref([]);
const annLoading = ref(false);
const annForm = ref({ title: "", content: "", target_type: "all", target_group_id: null });
const annSaving = ref(false);
const editingAnn = ref(null);
const editForm = ref({ title: "", content: "" });

async function loadAnnouncements() {
  annLoading.value = true;
  try {
    const res = await getAnnouncements();
    announcements.value = res.data.items || [];
  } finally { annLoading.value = false; }
}

async function handleCreateAnn() {
  if (!annForm.value.title.trim() || !annForm.value.content.trim()) return;
  annSaving.value = true;
  try {
    await createAnnouncement(annForm.value);
    annForm.value = { title: "", content: "", target_type: "all", target_group_id: null };
    ElMessage.success("公告已发布");
    loadAnnouncements();
  } finally { annSaving.value = false; }
}

function openEditAnn(ann) { editingAnn.value = ann.id; editForm.value = { title: ann.title, content: ann.content }; }
async function handleEditSave() {
  try {
    await updateAnnouncement(editingAnn.value, { ...editForm.value, target_type: "all", target_group_id: null });
    editingAnn.value = null;
    loadAnnouncements();
  } catch { ElMessage.error("更新失败"); }
}
async function handleDeleteAnn(id) { await deleteAnnouncement(id); loadAnnouncements(); }
async function handlePin(id) { await pinAnnouncement(id); loadAnnouncements(); }

// 创建任务弹窗
const dialogVisible = ref(false);
const editingId = ref(null);
const taskForm = ref({
  title: "", description: "", target_type: "all", target_group_id: null,
  practice_goal: 10, speaking_goal: 5, free_talk_goal: 2, clip_goal: 3,
  accuracy_goal: null, deadline: "",
});
const saving = ref(false);

// 详情抽屉
const drawerVisible = ref(false);
const taskDetail = ref(null);
const detailLoading = ref(false);

const goals = computed(() => [
  { key: "practice_goal", label: "练习次数", icon: "📝" },
  { key: "speaking_goal", label: "口语次数", icon: "🎤" },
  { key: "free_talk_goal", label: "情景对话", icon: "💬" },
  { key: "clip_goal", label: "学习片段", icon: "🎬" },
]);

async function loadTasks() {
  loading.value = true;
  try {
    const params = {};
    if (filterGroup.value) params.group_id = filterGroup.value;
    if (filterStatus.value) params.status = filterStatus.value;
    const res = await getTeacherTasks(params);
    tasks.value = res.data.items || [];
  } finally { loading.value = false; }
}

async function loadGroups() {
  try {
    const res = await getTeacherGroups();
    groups.value = res.data || [];
  } catch { /* */ }
}

function openCreate() {
  editingId.value = null;
  taskForm.value = { title: "", description: "", target_type: "all", target_group_id: null, practice_goal: 10, speaking_goal: 5, free_talk_goal: 2, clip_goal: 3, accuracy_goal: null, deadline: "" };
  dialogVisible.value = true;
}

function openEdit(task) {
  editingId.value = task.id;
  taskForm.value = {
    title: task.title, description: task.description || "",
    target_type: task.target_type, target_group_id: task.target_group_id,
    practice_goal: task.practice_goal, speaking_goal: task.speaking_goal,
    free_talk_goal: task.free_talk_goal, clip_goal: task.clip_goal,
    accuracy_goal: task.accuracy_goal, deadline: task.deadline || "",
  };
  dialogVisible.value = true;
}

async function handleSave() {
  if (!taskForm.value.title.trim()) return;
  saving.value = true;
  try {
    if (editingId.value) {
      await updateTask(editingId.value, taskForm.value);
      ElMessage.success("任务已更新");
    } else {
      await createTask(taskForm.value);
      ElMessage.success("任务已创建");
    }
    dialogVisible.value = false;
    loadTasks();
  } catch { ElMessage.error("操作失败"); }
  finally { saving.value = false; }
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm("确定删除该任务？", "删除确认", { type: "warning" });
    await deleteTask(id);
    ElMessage.success("已删除");
    loadTasks();
  } catch { /* */ }
}

async function handleToggleStatus(id) {
  await toggleTaskStatus(id);
  loadTasks();
}

async function openDetail(id) {
  drawerVisible.value = true;
  detailLoading.value = true;
  taskDetail.value = null;
  try {
    const res = await getTaskDetail(id);
    taskDetail.value = res.data;
  } finally { detailLoading.value = false; }
}

function progressPct(task) {
  if (!task.total_count) return 0;
  return Math.round(task.completed_count / task.total_count * 100);
}

function studentProgressPct(p) {
  const goals = taskDetail.value;
  if (!goals) return 0;
  const totalGoal = (goals.practice_goal || 0) + (goals.speaking_goal || 0) + (goals.free_talk_goal || 0) + (goals.clip_goal || 0);
  const totalDone = (p.practice_done || 0) + (p.speaking_done || 0) + (p.free_talk_done || 0) + (p.clips_done || 0);
  if (totalGoal === 0) return 0;
  return Math.round(totalDone / totalGoal * 100);
}

onMounted(() => { loadTasks(); loadGroups(); loadAnnouncements(); });
</script>

<template>
  <div class="tasks-page">
    <div class="page-hd">
      <el-button size="small" :icon="ArrowLeft" text @click="$router.back()">返回</el-button>
      <h1>任务公告</h1>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="学习任务" name="tasks">
        <div class="hd-filters">
          <el-select v-model="filterGroup" clearable placeholder="分组" size="small" style="width:140px" @change="loadTasks">
            <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
          <el-select v-model="filterStatus" clearable placeholder="状态" size="small" style="width:100px" @change="loadTasks">
            <el-option label="进行中" value="active" />
            <el-option label="已完成" value="completed" />
          </el-select>
          <el-button type="primary" size="small" @click="openCreate">创建任务</el-button>
        </div>

    <div class="task-grid" v-loading="loading">
      <div v-for="t in tasks" :key="t.id" class="task-card" @click="openDetail(t.id)">
        <div class="tc-top">
          <h3 class="tc-title">{{ t.title }}</h3>
          <el-tag :type="t.status === 'active' ? 'warning' : 'success'" size="small">{{ t.status === 'active' ? '进行中' : '已完成' }}</el-tag>
        </div>
        <p class="tc-desc" v-if="t.description">{{ t.description }}</p>
        <div class="tc-goals">
          <span v-if="t.practice_goal">练习 {{ t.practice_goal }}次</span>
          <span v-if="t.speaking_goal">口语 {{ t.speaking_goal }}次</span>
          <span v-if="t.free_talk_goal">对话 {{ t.free_talk_goal }}次</span>
          <span v-if="t.clip_goal">片段 {{ t.clip_goal }}个</span>
        </div>
        <div class="tc-progress-bar">
          <div class="bar-fill" :style="{ width: progressPct(t) + '%' }" />
        </div>
        <div class="tc-foot">
          <span class="tc-progress-text">{{ t.completed_count }}/{{ t.total_count }} 人完成</span>
          <span class="tc-deadline" v-if="t.deadline">截止 {{ t.deadline }}</span>
        </div>
        <div class="tc-actions" @click.stop>
          <el-button size="small" text @click="openEdit(t)">编辑</el-button>
          <el-button size="small" text @click="handleToggleStatus(t.id)">{{ t.status === 'active' ? '完成' : '重启' }}</el-button>
          <el-button size="small" text type="danger" @click="handleDelete(t.id)">删除</el-button>
        </div>
      </div>
      <div v-if="tasks.length === 0 && !loading" class="empty-hint">暂无任务，点击"创建任务"开始</div>
    </div>

    <!-- 创建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑任务' : '创建任务'" width="500px" :close-on-click-modal="false">
      <el-input v-model="taskForm.title" placeholder="任务标题" maxlength="100" class="mb-10" />
      <el-input v-model="taskForm.description" type="textarea" :rows="2" placeholder="任务描述（可选）" class="mb-10" />
      <div class="form-goals">
        <div v-for="g in goals" :key="g.key" class="goal-row">
          <label>{{ g.label }}</label>
          <el-input-number v-model="taskForm[g.key]" :min="0" :max="99" size="small" controls-position="right" />
        </div>
        <div class="goal-row">
          <label>目标正确率(%)</label>
          <el-input-number v-model="taskForm.accuracy_goal" :min="0" :max="100" size="small" controls-position="right" />
        </div>
      </div>
      <div class="form-row">
        <el-select v-model="taskForm.target_type" size="small" style="width:120px">
          <el-option label="全部学生" value="all" />
          <el-option label="指定分组" value="group" />
        </el-select>
        <el-select v-if="taskForm.target_type === 'group'" v-model="taskForm.target_group_id" size="small" placeholder="选择分组" style="width:160px">
          <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
        </el-select>
        <el-input v-model="taskForm.deadline" placeholder="截止日期 (YYYY-MM-DD)" size="small" style="width:180px" class="ml-auto" />
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave" :disabled="!taskForm.title.trim()">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawerVisible" title="任务详情" size="520px">
      <div v-if="detailLoading" v-loading="true" style="min-height:200px" />
      <template v-else-if="taskDetail">
        <h3>{{ taskDetail.title }}</h3>
        <p v-if="taskDetail.description" class="detail-desc">{{ taskDetail.description }}</p>
        <div class="detail-goals">
          <div class="dgoal"><span class="dgoal-num">{{ taskDetail.practice_goal }}</span>练习</div>
          <div class="dgoal"><span class="dgoal-num">{{ taskDetail.speaking_goal }}</span>口语</div>
          <div class="dgoal"><span class="dgoal-num">{{ taskDetail.free_talk_goal }}</span>对话</div>
          <div class="dgoal"><span class="dgoal-num">{{ taskDetail.clip_goal }}</span>片段</div>
        </div>
        <div class="detail-meta">
          <span>完成 {{ taskDetail.completed_count }}/{{ taskDetail.total_count }} 人</span>
          <span v-if="taskDetail.deadline">截止 {{ taskDetail.deadline }}</span>
        </div>

        <h4 class="section-title">学生进度</h4>
        <div v-if="taskDetail.progress && taskDetail.progress.length > 0">
          <div v-for="p in taskDetail.progress" :key="p.student_id" class="progress-item">
            <div class="pi-top">
              <strong>{{ p.student_name || "学生" }}</strong>
              <el-tag v-if="p.is_completed" type="success" size="small">已完成</el-tag>
              <el-tag v-else size="small" type="info">进行中</el-tag>
            </div>
            <div class="pi-goals">
              <span>练习 {{ p.practice_done }}/{{ taskDetail.practice_goal }}</span>
              <span>口语 {{ p.speaking_done }}/{{ taskDetail.speaking_goal }}</span>
              <span>对话 {{ p.free_talk_done }}/{{ taskDetail.free_talk_goal }}</span>
              <span>片段 {{ p.clips_done }}/{{ taskDetail.clip_goal }}</span>
            </div>
            <div class="pi-bar"><div class="pi-fill" :style="{ width: studentProgressPct(p) + '%' }" /></div>
          </div>
        </div>
        <div v-else class="empty-hint">暂无学生进度数据</div>
      </template>
    </el-drawer>
      </el-tab-pane>

      <!-- ════ 公告管理 ════ -->
      <el-tab-pane label="公告管理" name="announcements">
        <div class="ann-publish">
          <h3>发布公告</h3>
          <el-input v-model="annForm.title" placeholder="公告标题" class="mb-10" />
          <el-input v-model="annForm.content" type="textarea" :rows="3" placeholder="公告内容" maxlength="500" show-word-limit class="mb-10" />
          <div class="ann-actions">
            <el-select v-model="annForm.target_type" size="small" style="width:120px">
              <el-option label="全部可见" value="all" /><el-option label="指定分组" value="group" />
            </el-select>
            <el-select v-if="annForm.target_type === 'group'" v-model="annForm.target_group_id" size="small" placeholder="分组" style="width:140px">
              <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
            </el-select>
            <el-button type="primary" size="small" :loading="annSaving" :disabled="!annForm.title.trim()" @click="handleCreateAnn">发布</el-button>
          </div>
        </div>
        <div class="ann-list" v-loading="annLoading">
          <div v-for="a in announcements" :key="a.id" class="ann-item" :class="{ pinned: a.is_pinned }">
            <div class="ann-top">
              <span class="ann-title"><el-tag v-if="a.is_pinned" type="warning" size="small" effect="dark" class="mr-4">置顶</el-tag>{{ a.title }}</span>
              <div class="ann-item-actions">
                <el-button size="small" text @click="handlePin(a.id)">{{ a.is_pinned ? '取消' : '置顶' }}</el-button>
                <el-button size="small" text @click="openEditAnn(a)">编辑</el-button>
                <el-button size="small" text type="danger" @click="handleDeleteAnn(a.id)">删除</el-button>
              </div>
            </div>
            <p class="ann-content">{{ a.content }}</p>
            <span class="ann-time">{{ a.created_at }}</span>
          </div>
          <div v-if="announcements.length === 0 && !annLoading" class="empty-hint">暂无公告</div>
        </div>

        <el-dialog :model-value="editingAnn !== null" @close="editingAnn = null" title="编辑公告" width="420px" v-if="editingAnn !== null">
          <el-input v-model="editForm.title" placeholder="标题" class="mb-10" />
          <el-input v-model="editForm.content" type="textarea" :rows="3" placeholder="内容" />
          <template #footer><el-button @click="editingAnn = null">取消</el-button><el-button type="primary" @click="handleEditSave">保存</el-button></template>
        </el-dialog>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.tasks-page { max-width: 1000px; margin: 0 auto; }
.page-hd { margin-bottom: 18px; }
.page-hd h1 { font-size: 22px; font-weight: 800; margin: 6px 0 0; }
.hd-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
.hd-filters { display: flex; gap: 8px; align-items: center; }
.mb-10 { margin-bottom: 10px; }
.ml-auto { margin-left: auto; }

.task-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
.task-card {
  background: #fff; border-radius: 12px; padding: 18px 20px;
  border: 1px solid #EBEDF0; cursor: pointer;
  transition: all .2s; box-shadow: 0 1px 3px rgba(0,0,0,.02);
}
.task-card:hover { border-color: #E6A23C; box-shadow: 0 4px 16px rgba(230,162,60,.08); }
.tc-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px; }
.tc-title { font-size: 15px; font-weight: 700; margin: 0; }
.tc-desc { font-size: 12px; color: #909399; margin: 4px 0 8px; }
.tc-goals { display: flex; gap: 10px; font-size: 12px; color: #606266; margin-bottom: 10px; flex-wrap: wrap; }
.tc-goals span { background: #F5F5F7; padding: 2px 8px; border-radius: 6px; }
.tc-progress-bar { height: 6px; background: #F0F0F0; border-radius: 3px; margin-bottom: 8px; overflow: hidden; }
.bar-fill { height: 100%; background: linear-gradient(90deg, #E6A23C, #F5C85A); border-radius: 3px; transition: width .4s; }
.tc-foot { display: flex; justify-content: space-between; font-size: 11px; color: #C0C4CC; }
.tc-progress-text { color: #606266; font-weight: 500; }
.tc-actions { display: flex; gap: 2px; margin-top: 8px; padding-top: 8px; border-top: 1px solid #F5F5F5; }

.form-goals { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
.goal-row { display: flex; align-items: center; justify-content: space-between; }
.goal-row label { font-size: 12px; color: #606266; font-weight: 500; }
.form-row { display: flex; gap: 8px; align-items: center; }

.detail-desc { color: #606266; font-size: 13px; margin: 4px 0 12px; }
.detail-goals { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 12px; }
.dgoal { background: #FDF8F0; border-radius: 10px; padding: 10px; text-align: center; font-size: 12px; color: #8B6914; }
.dgoal-num { display: block; font-size: 22px; font-weight: 800; color: #E6A23C; }
.detail-meta { display: flex; gap: 16px; font-size: 12px; color: #909399; margin-bottom: 18px; }

.section-title { font-size: 13px; font-weight: 700; color: #606266; margin: 0 0 10px; }
.progress-item { padding: 12px 0; border-bottom: 1px solid #F5F5F5; }
.pi-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 13px; }
.pi-goals { display: flex; gap: 10px; font-size: 11px; color: #909399; margin-bottom: 6px; flex-wrap: wrap; }
.pi-bar { height: 4px; background: #F0F0F0; border-radius: 2px; overflow: hidden; }
.pi-fill { height: 100%; background: #58CC02; border-radius: 2px; transition: width .4s; }
.empty-hint { text-align: center; color: #C0C4CC; padding: 40px; font-size: 13px; grid-column: 1/-1; }

/* ── 公告 ── */
.ann-publish { background: #fff; border-radius: 12px; padding: 18px 20px; border: 1px solid #EBEDF0; margin-bottom: 18px; }
.ann-publish h3 { font-size: 14px; font-weight: 700; margin: 0 0 12px; }
.ann-actions { display: flex; gap: 10px; align-items: center; }
.ann-list { background: #fff; border-radius: 12px; border: 1px solid #EBEDF0; overflow: hidden; }
.ann-item { padding: 14px 20px; border-bottom: 1px solid #F5F5F5; }
.ann-item.pinned { background: rgba(230,162,60,.03); border-left: 3px solid #E6A23C; padding-left: 17px; }
.ann-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.ann-title { font-weight: 700; font-size: 14px; }
.ann-content { color: #606266; font-size: 13px; margin: 0; }
.ann-time { font-size: 11px; color: #C0C4CC; }
.ann-item-actions { display: flex; gap: 2px; flex-shrink: 0; }
.mr-4 { margin-right: 4px; }
</style>
