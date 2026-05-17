<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { ArrowLeft } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  getStudentList, getStudentDetail, generateReport,
  getTeacherGroups, createTeacherGroup, updateTeacherGroup,
  deleteGroup, assignStudentGroup, getGroupDetail,
  getAllStudents, batchUpdateLevel,
} from "@/modules/teacher/api";

const activeTab = ref("students");

// ── 学生列表 ──
const students = ref([]);
const total = ref(0);
const loading = ref(false);
const keyword = ref("");
const page = ref(1);
const pageSize = ref(10);
const drawerVisible = ref(false);
const detailLoading = ref(false);
const selectedStudent = ref(null);
const reportLoading = ref(false);
const reportContent = ref("");

async function loadStudents() {
  loading.value = true;
  try {
    const res = await getStudentList({ skip: (page.value - 1) * pageSize.value, limit: pageSize.value, keyword: keyword.value || undefined });
    students.value = res.data.items;
    total.value = res.data.total;
  } finally { loading.value = false; }
}
function handleSearch() { page.value = 1; loadStudents(); }
function handlePageChange(p) { page.value = p; loadStudents(); }
async function openDetail(row) {
  drawerVisible.value = true; detailLoading.value = true; reportContent.value = ""; selectedStudent.value = null;
  try { const res = await getStudentDetail(row.id); selectedStudent.value = res.data; } catch { drawerVisible.value = false; }
  finally { detailLoading.value = false; }
}
async function handleGenerateReport() {
  if (!selectedStudent.value) return;
  reportLoading.value = true; reportContent.value = "";
  try { const res = await generateReport(selectedStudent.value.id); reportContent.value = res.data.report; }
  catch { ElMessage.error("生成失败"); } finally { reportLoading.value = false; }
}
function formatAccuracy(a) { return a != null ? `${a}%` : "—"; }
function fmtTime(t) { return t ? new Date(t).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—"; }

// ── 分组管理 ──
const groups = ref([]);
const groupLoading = ref(false);
const createForm = ref({ name: "", description: "" });
const creating = ref(false);
const selectedGroupId = ref(null);
const groupDetail = ref(null);
const detailLoading2 = ref(false);

async function loadGroups() {
  groupLoading.value = true;
  try { const res = await getTeacherGroups(); groups.value = res.data || []; } finally { groupLoading.value = false; }
}
async function handleCreateGroup() {
  if (!createForm.value.name.trim()) return;
  creating.value = true;
  try { await createTeacherGroup(createForm.value); createForm.value = { name: "", description: "" }; ElMessage.success("已创建"); loadGroups(); }
  finally { creating.value = false; }
}
async function handleDeleteGroup(gid) {
  try { await ElMessageBox.confirm("确定解散？组员将变为未分组。", "解散确认", { type: "warning" }); await deleteGroup(gid); selectedGroupId.value = null; groupDetail.value = null; ElMessage.success("已解散"); loadGroups(); }
  catch { /* */ }
}
async function selectGroup(gid) {
  selectedGroupId.value = gid; detailLoading2.value = true; groupDetail.value = null;
  try { const res = await getGroupDetail(gid); groupDetail.value = res.data; } catch { ElMessage.error("加载失败"); }
  finally { detailLoading2.value = false; }
}
async function handleStudentAssign(studentId, groupId) {
  await assignStudentGroup(studentId, groupId || null);
  ElMessage.success("已更新");
  if (selectedGroupId.value) selectGroup(selectedGroupId.value);
  loadStudents();
}

// ── 添加学生弹窗 ──
const addStudentVisible = ref(false);
const availableStudents = ref([]);

async function openAddStudent() {
  addStudentVisible.value = true;
  // 加载不在当前分组的学生
  try {
    const res = await getStudentList({ limit: 100 });
    const all = res.data.items || [];
    const memberIds = new Set((groupDetail.value?.members || []).map(m => m.id));
    availableStudents.value = all.filter(s => !memberIds.has(s.id));
  } catch { availableStudents.value = []; }
}

async function addToGroup(studentId) {
  await assignStudentGroup(studentId, selectedGroupId.value);
  ElMessage.success("已添加");
  selectGroup(selectedGroupId.value);
  loadStudents();
  // 更新可用列表
  availableStudents.value = availableStudents.value.filter(s => s.id !== studentId);
}

// ── 分级管理 ──
const levelStudents = ref([]);
const levelLoading = ref(false);
const levelSelected = ref([]);
const batchLevel = ref("");

const levelDist = computed(() => {
  const d = { A: 0, B: 0, C: 0, unset: 0 };
  for (const s of levelStudents.value) {
    const k = s.level && d[s.level] !== undefined ? s.level : "unset";
    d[k]++;
  }
  return d;
});

async function loadLevelStudents() {
  levelLoading.value = true;
  try {
    const res = await getAllStudents();
    levelStudents.value = res.data || [];
  } finally { levelLoading.value = false; }
}

async function updateLevel(studentId, level) {
  try {
    await batchUpdateLevel([studentId], level);
    const s = levelStudents.value.find(x => x.id === studentId);
    if (s) s.level = level;
    ElMessage.success("等级已更新");
  } catch { ElMessage.error("更新失败"); }
}

async function handleBatchLevel() {
  if (levelSelected.value.length === 0 || !batchLevel.value) return;
  try {
    await batchUpdateLevel(levelSelected.value.map(s => s.id), batchLevel.value);
    for (const s of levelStudents.value) {
      if (levelSelected.value.find(x => x.id === s.id)) s.level = batchLevel.value;
    }
    levelSelected.value = [];
    batchLevel.value = "";
    ElMessage.success("批量更新完成");
  } catch { ElMessage.error("批量更新失败"); }
}

function handleLevelSelect(s) { levelSelected.value = s; }

onMounted(() => { loadStudents(); loadGroups(); });
watch(activeTab, (v) => { if (v === "levels" && levelStudents.value.length === 0) loadLevelStudents(); });
</script>

<template>
  <div class="sl-page">
    <div class="page-hd">
      <el-button size="small" :icon="ArrowLeft" text @click="$router.back()">返回</el-button>
      <h1>学生管理</h1>
    </div>

    <el-tabs v-model="activeTab">
      <!-- ════ 学生列表 ════ -->
      <el-tab-pane label="学生列表" name="students">
        <div class="search-bar">
          <el-input v-model="keyword" placeholder="搜索用户名或邮箱..." clearable style="width:280px" @keyup.enter="handleSearch" />
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </div>
        <div v-if="loading && students.length === 0" class="state-wrap"><el-skeleton :rows="6" animated /></div>
        <div v-else-if="students.length === 0" class="state-wrap"><el-empty description="暂无学生" /></div>
        <template v-else>
          <el-table :data="students" stripe @row-click="openDetail" class="student-table">
            <el-table-column prop="username" label="用户名" min-width="90" />
            <el-table-column prop="email" label="邮箱" min-width="150" />
            <el-table-column label="最近活跃" min-width="130">
              <template #default="{ row }">{{ fmtTime(row.last_active) }}</template>
            </el-table-column>
            <el-table-column prop="level" label="等级" width="65">
              <template #default="{ row }"><el-tag v-if="row.level" size="small">{{ row.level }}</el-tag><span v-else class="muted">未定级</span></template>
            </el-table-column>
            <el-table-column label="当前分组" min-width="90">
              <template #default="{ row }">{{ row.group_name || "未分组" }}</template>
            </el-table-column>
            <el-table-column prop="total_practices" label="练习" width="60" align="center" />
            <el-table-column label="正确率" width="70" align="center">
              <template #default="{ row }">{{ formatAccuracy(row.accuracy) }}</template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrap" v-if="total > pageSize">
            <el-pagination background layout="prev,pager,next" :total="total" :page-size="pageSize" :current-page="page" @current-change="handlePageChange" />
          </div>
        </template>

        <el-drawer v-model="drawerVisible" title="学生详情" size="500px">
          <div v-if="detailLoading" v-loading="true" style="min-height:200px" />
          <template v-else-if="selectedStudent">
            <el-descriptions title="基本信息" :column="1" border size="small">
              <el-descriptions-item label="用户名">{{ selectedStudent.username || "匿名" }}</el-descriptions-item>
              <el-descriptions-item label="邮箱">{{ selectedStudent.email || "—" }}</el-descriptions-item>
              <el-descriptions-item label="等级"><el-tag v-if="selectedStudent.level" size="small">{{ selectedStudent.level }}</el-tag></el-descriptions-item>
              <el-descriptions-item label="总练习">{{ selectedStudent.total_practices }}</el-descriptions-item>
              <el-descriptions-item label="正确率">{{ formatAccuracy(selectedStudent.accuracy) }}</el-descriptions-item>
              <el-descriptions-item label="口语">{{ selectedStudent.speaking_stats?.total || 0 }}次</el-descriptions-item>
            </el-descriptions>
            <el-card class="ds" shadow="never"><template #header>各难度正确率</template>
              <div v-if="selectedStudent.difficulty_stats" class="diff-stats">
                <div v-for="(s,k) in selectedStudent.difficulty_stats" :key="k" class="diff-item">
                  <div class="diff-hd"><el-tag size="small">{{ {A:"高级",B:"中级",C:"初级"}[k]||k }}</el-tag><span>{{ s.correct }}/{{ s.total }}</span></div>
                  <el-progress :percentage="s.accuracy" :stroke-width="10" :status="s.accuracy>=75?'success':s.accuracy>=50?'warning':'exception'" />
                </div>
              </div>
            </el-card>
            <el-card class="ds" shadow="never"><template #header>14天活跃</template>
              <div v-if="selectedStudent.recent_activity?.length" class="act-chart">
                <div v-for="d in selectedStudent.recent_activity" :key="d.date" class="act-bar-wrap">
                  <div class="act-stack"><div class="act speaking" :style="{height:Math.min(d.speaking_count/5*40,40)+'px'}"/><div class="act practice" :style="{height:Math.min(d.practice_count/5*40,40)+'px'}"/></div>
                  <div class="act-label">{{ d.date.slice(5) }}</div>
                </div>
              </div>
            </el-card>
            <el-card class="ds" shadow="never"><template #header>高频错题</template>
              <div v-if="selectedStudent.wrong_notes_summary?.length"><div v-for="(w,i) in selectedStudent.wrong_notes_summary" :key="w.question_id" class="wn">{{ i+1 }}. {{ w.question }} <el-tag size="small" type="danger">错{{ w.wrong_times }}次</el-tag></div></div>
            </el-card>
            <el-card v-if="selectedStudent.speaking_samples?.length" class="ds" shadow="never">
              <template #header>口语录音回顾</template>
              <div v-for="s in selectedStudent.speaking_samples" :key="s.id" class="sp-sample">
                <div class="sp-meta">
                  <el-tag size="small">{{ s.mode === 'repeat' ? '跟读' : '自由应答' }}</el-tag>
                  <span v-if="s.total_score" class="sp-score">{{ s.total_score }}分</span>
                  <span class="sp-date">{{ s.created_at?.slice(0,10) }}</span>
                </div>
                <div v-if="s.reference_text" class="sp-ref">"{{ s.reference_text.slice(0,80) }}{{ s.reference_text.length>80?'...':'' }}"</div>
                <audio v-if="s.audio_url" :src="s.audio_url" controls controlslist="nodownload" style="width:100%;height:32px;margin-top:6px" />
                <div v-if="s.feedback" class="sp-fb">{{ s.feedback }}</div>
              </div>
            </el-card>
            <el-card class="ds" shadow="never"><template #header><div class="sh"><span>AI报告</span><el-button type="primary" size="small" :loading="reportLoading" @click="handleGenerateReport">{{ reportLoading?'生成中...':'生成报告' }}</el-button></div></template>
              <div v-if="reportContent" class="report">{{ reportContent }}</div></el-card>
          </template>
        </el-drawer>
      </el-tab-pane>

      <!-- ════ 分组管理 ════ -->
      <el-tab-pane label="分组管理" name="groups">
        <div class="groups-layout">
          <div class="gl-left">
            <div class="group-create-card">
              <h3>创建分组</h3>
              <el-input v-model="createForm.name" placeholder="分组名称" maxlength="20" class="mb-8" />
              <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="说明（可选）" class="mb-8" />
              <el-button type="primary" size="small" :loading="creating" :disabled="!createForm.name.trim()" @click="handleCreateGroup">创建</el-button>
            </div>
            <div class="group-cards">
              <h3>已有分组</h3>
              <div v-if="groups.length === 0" class="muted" style="text-align:center;padding:20px">暂无分组</div>
              <div v-for="g in groups" :key="g.id" class="g-card" :class="{ active: g.id === selectedGroupId }" @click="selectGroup(g.id)">
                <div class="gc-top"><span class="gc-name">{{ g.name }}</span><el-tag size="small">{{ g.student_count }}人</el-tag></div>
                <div class="gc-desc" v-if="g.description">{{ g.description }}</div>
                <el-button size="small" text type="danger" class="gc-del" @click.stop="handleDeleteGroup(g.id)">解散</el-button>
              </div>
            </div>
          </div>
          <div class="gl-right">
            <template v-if="!selectedGroupId">
              <div class="gr-empty">选择左侧分组查看详情</div>
            </template>
            <div v-else-if="detailLoading2" v-loading="true" style="min-height:200px" />
            <template v-else-if="groupDetail">
              <div class="gr-hd"><h2>{{ groupDetail.name }}</h2></div>
              <div class="gr-stats">
                <div class="grs"><b>{{ groupDetail.stats?.total_students || 0 }}</b><span>组员</span></div>
                <div class="grs"><b>{{ groupDetail.stats?.avg_accuracy || 0 }}%</b><span>均正确率</span></div>
                <div class="grs"><b>{{ groupDetail.stats?.avg_speaking_score || '—' }}</b><span>口语均分</span></div>
                <div class="grs"><b>{{ groupDetail.stats?.active_14d || 0 }}</b><span>14天活跃</span></div>
              </div>
              <div class="sec-hd">
                <h3 class="sec-title">组成员</h3>
                <el-button size="small" type="primary" @click="openAddStudent">添加学生</el-button>
              </div>
              <el-table :data="groupDetail.members || []" size="small" v-if="(groupDetail.members || []).length > 0">
                <el-table-column prop="username" label="用户名" min-width="90" />
                <el-table-column prop="level" label="等级" width="60" />
                <el-table-column prop="total_practices" label="练习" width="55" align="center" />
                <el-table-column label="正确率" width="70" align="center">
                  <template #default="{ row }">{{ row.accuracy }}%</template>
                </el-table-column>
                <el-table-column label="操作" width="80">
                  <template #default="{ row }">
                    <el-button size="small" text type="danger" @click="handleStudentAssign(row.id, null)">移出</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div v-else class="muted" style="text-align:center;padding:20px">该分组暂无学生</div>
            </template>
          </div>
        </div>
      </el-tab-pane>

      <!-- ════ 分级管理 ════ -->
      <el-tab-pane label="分级管理" name="levels">
        <!-- 统计卡片 -->
        <div class="level-stats">
          <div class="ls-card a"><b>{{ levelDist.A }}</b><span>A 级 · 高级</span></div>
          <div class="ls-card b"><b>{{ levelDist.B }}</b><span>B 级 · 中级</span></div>
          <div class="ls-card c"><b>{{ levelDist.C }}</b><span>C 级 · 初级</span></div>
          <div class="ls-card u"><b>{{ levelDist.unset }}</b><span>未定级</span></div>
        </div>
        <!-- 批量操作栏 -->
        <div v-if="levelSelected.length > 0" class="batch-bar">
          <span>已选 {{ levelSelected.length }} 名学生</span>
          <el-select v-model="batchLevel" placeholder="目标等级" size="small" style="width:120px">
            <el-option label="A 级 · 高级" value="A" /><el-option label="B 级 · 中级" value="B" /><el-option label="C 级 · 初级" value="C" />
          </el-select>
          <el-button type="primary" size="small" :disabled="!batchLevel" @click="handleBatchLevel">一键应用</el-button>
        </div>
        <!-- 表格 -->
        <div v-if="levelLoading" class="state-wrap"><el-skeleton :rows="6" animated /></div>
        <el-table v-else :data="levelStudents" size="small" @selection-change="handleLevelSelect" class="level-table">
          <el-table-column type="selection" width="40" />
          <el-table-column prop="username" label="用户名" min-width="100" />
          <el-table-column label="当前等级" width="90">
            <template #default="{ row }">
              <span class="level-tag" :class="'lv-' + (row.level || 'unset').toLowerCase()">{{ row.level || '未定级' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="所在分组" min-width="110">
            <template #default="{ row }">{{ row.group_name || '未分组' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" align="center">
            <template #default="{ row }">
              <div class="level-btns">
                <button class="lb-btn lb-a" :class="{ active: row.level === 'A' }" @click="updateLevel(row.id, 'A')">A</button>
                <button class="lb-btn lb-b" :class="{ active: row.level === 'B' }" @click="updateLevel(row.id, 'B')">B</button>
                <button class="lb-btn lb-c" :class="{ active: row.level === 'C' }" @click="updateLevel(row.id, 'C')">C</button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加学生弹窗 -->
    <el-dialog v-model="addStudentVisible" title="添加学生到分组" width="500px">
      <el-table :data="availableStudents" size="small" max-height="400">
        <el-table-column prop="username" label="用户名" min-width="100" />
        <el-table-column prop="level" label="等级" width="60">
          <template #default="{ row }"><el-tag v-if="row.level" size="small">{{ row.level }}</el-tag></template>
        </el-table-column>
        <el-table-column label="当前分组" min-width="90">
          <template #default="{ row }">{{ row.group_name || "未分组" }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="addToGroup(row.id)">添加</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="availableStudents.length === 0" class="muted" style="text-align:center;padding:30px">没有可添加的学生</div>
    </el-dialog>
  </div>
</template>

<style scoped>
.sl-page { max-width: 1060px; margin: 0 auto; }
.page-hd { margin-bottom: 6px; }
.page-hd h1 { font-size: 22px; font-weight: 800; margin: 6px 0 0; }
.search-bar { display: flex; gap: 10px; margin-bottom: 14px; }
.student-table { cursor: pointer; }
.muted { color: #C0C4CC; font-size: 12px; }
.pagination-wrap { display: flex; justify-content: center; margin-top: 16px; }
.state-wrap { margin-top: 40px; }

.ds { margin-top: 14px; border-radius: 12px; }
.diff-stats { display: flex; flex-direction: column; gap: 10px; }
.diff-hd { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; font-size: 12px; color: #909399; }
.act-chart { display: flex; align-items: flex-end; gap: 3px; height: 70px; overflow-x: auto; }
.act-bar-wrap { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.act-stack { display: flex; flex-direction: column-reverse; height: 55px; justify-content: flex-end; gap: 1px; }
.act { width: 12px; border-radius: 100px 100px 0 0; }
.act.practice { background: #58CC02; }
.act.speaking { background: #9B4DE0; }

/* speaking samples */
.sp-sample { padding: 10px 0; border-bottom: 1px solid #F2F3F5; }
.sp-sample:last-child { border-bottom: none; }
.sp-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.sp-score { font-weight: 700; color: #58CC02; font-size: 13px; }
.sp-date { font-size: 11px; color: #C0C4CC; }
.sp-ref { font-size: 12px; color: #909399; font-style: italic; }
.sp-fb { font-size: 12px; color: #606266; margin-top: 4px; line-height: 1.5; }
.act-label { font-size: 9px; color: #909399; }
.wn { padding: 6px 0; border-bottom: 1px solid #F5F5F5; font-size: 12px; display: flex; align-items: baseline; gap: 6px; }
.sh { display: flex; justify-content: space-between; align-items: center; }
.report { font-size: 13px; line-height: 1.8; color: #303133; white-space: pre-wrap; }

/* ── 分组 ── */
.groups-layout { display: flex; gap: 18px; }
.gl-left { width: 300px; flex-shrink: 0; }
.gl-right { flex: 1; background: #fff; border-radius: 12px; border: 1px solid #EBEDF0; padding: 20px 24px; min-height: 300px; }
.group-create-card { background: #fff; border-radius: 12px; padding: 16px 18px; border: 1px solid #EBEDF0; margin-bottom: 14px; }
.group-create-card h3 { font-size: 13px; font-weight: 700; margin: 0 0 10px; }
.mb-8 { margin-bottom: 8px; }
.group-cards { background: #fff; border-radius: 12px; padding: 14px 16px; border: 1px solid #EBEDF0; }
.group-cards h3 { font-size: 13px; font-weight: 700; margin: 0 0 8px; }
.g-card { padding: 12px 14px; border-radius: 10px; cursor: pointer; border: 1px solid transparent; margin-bottom: 6px; transition: all .15s; position: relative; }
.g-card:hover { background: #FAFBFC; }
.g-card.active { border-color: rgba(230,162,60,.25); background: rgba(230,162,60,.04); }
.gc-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.gc-name { font-weight: 700; font-size: 13px; }
.gc-desc { font-size: 12px; color: #909399; }
.gc-del { position: absolute; right: 8px; bottom: 6px; font-size: 11px; }

.gr-empty { display: flex; align-items: center; justify-content: center; height: 100%; min-height: 300px; color: #C0C4CC; font-size: 13px; }
.gr-hd h2 { font-size: 17px; font-weight: 700; margin: 0 0 16px; }
.gr-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
.grs { background: #FAFBFC; border-radius: 10px; padding: 12px 8px; text-align: center; border: 1px solid #F0F0F0; }
.grs b { display: block; font-size: 20px; color: #E6A23C; }
.grs span { font-size: 11px; color: #909399; margin-top: 2px; }
.sec-hd { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.sec-title { font-size: 13px; font-weight: 700; color: #606266; margin: 0; }

/* ── 分级管理 ── */
.level-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 16px; }
.ls-card { background: #fff; border-radius: 10px; padding: 14px 12px; text-align: center; border: 1.5px solid #EBEDF0; }
.ls-card.a { border-color: rgba(88,204,2,.25); background: rgba(88,204,2,.03); }
.ls-card.b { border-color: rgba(28,176,246,.25); background: rgba(28,176,246,.03); }
.ls-card.c { border-color: rgba(155,77,224,.25); background: rgba(155,77,224,.03); }
.ls-card.u { border-color: #E4E7ED; }
.ls-card b { display: block; font-size: 24px; font-weight: 800; line-height: 1.2; }
.ls-card.a b { color: #58CC02; }
.ls-card.b b { color: #1CB0F6; }
.ls-card.c b { color: #9B4DE0; }
.ls-card.u b { color: #C0C4CC; }
.ls-card span { font-size: 11px; color: #909399; font-weight: 600; }
.batch-bar { display: flex; align-items: center; gap: 10px; padding: 10px 16px; margin-bottom: 12px; background: rgba(230,162,60,.05); border-radius: 10px; border: 1px solid rgba(230,162,60,.15); font-size: 13px; font-weight: 500; }
.level-table { border-radius: 10px; overflow: hidden; }
.level-tag { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 700; }
.level-tag.lv-a { background: rgba(88,204,2,.12); color: #4A7A30; }
.level-tag.lv-b { background: rgba(28,176,246,.10); color: #1493D3; }
.level-tag.lv-c { background: rgba(155,77,224,.10); color: #9B4DE0; }
.level-tag.lv-unset { background: #F5F5F7; color: #C0C4CC; }
.level-btns { display: flex; gap: 6px; justify-content: center; }
.lb-btn {
  width: 32px; height: 28px; border-radius: 8px; border: 1.5px solid #E4E7ED;
  background: #fff; font-size: 12px; font-weight: 700; cursor: pointer;
  transition: all .15s; font-family: inherit; color: #909399;
}
.lb-btn:hover { transform: translateY(-1px); }
.lb-btn.active { color: #fff; }
.lb-btn.lb-a:hover, .lb-btn.lb-a.active { background: #58CC02; border-color: #58CC02; color: #fff; }
.lb-btn.lb-b:hover, .lb-btn.lb-b.active { background: #1CB0F6; border-color: #1CB0F6; color: #fff; }
.lb-btn.lb-c:hover, .lb-btn.lb-c.active { background: #9B4DE0; border-color: #9B4DE0; color: #fff; }

@media (max-width: 760px) { .groups-layout { flex-direction: column; } .gl-left { width: 100%; } }
</style>
