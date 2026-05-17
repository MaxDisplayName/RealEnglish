<script setup>
import { computed, onMounted, ref } from "vue";
import { ArrowLeft } from "@element-plus/icons-vue";
import {
  assignStudentGroup,
  createTeacherGroup,
  updateTeacherGroup,
  getStudentList,
  getTeacherGroups,
  getGroupDetail,
  deleteGroup,
  batchAssignGroups,
  getGroupsComparison,
} from "@/modules/teacher/api";
import { ElMessage, ElMessageBox } from "element-plus";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

use([BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

// ── 数据 ──
const groups = ref([]);
const students = ref([]);
const loading = ref(false);
const creating = ref(false);

// 创建弹窗
const dialogVisible = ref(false);
const form = ref({ name: "", description: "" });

// 编辑弹窗
const editDialogVisible = ref(false);
const editForm = ref({ name: "", description: "" });

// 选中分组
const selectedGroupId = ref(null);
const groupDetail = ref(null);
const detailLoading = ref(false);

// 批量分配
const selectedStudents = ref([]);
const batchGroupId = ref(null);
const batchAssigning = ref(false);

// 分组对比
const comparisonData = ref([]);
const comparisonActive = ref(false);

// 计算
const selectedGroup = computed(() =>
  groups.value.find((g) => g.id === selectedGroupId.value),
);

const detailStats = computed(() => groupDetail.value?.stats || {});
const detailMembers = computed(() => groupDetail.value?.members || []);

// ── 分组对比图表 ──
const comparisonChartOption = computed(() => {
  const names = comparisonData.value.map((d) => d.group_name);
  const accuracy = comparisonData.value.map((d) => d.avg_accuracy);
  const speaking = comparisonData.value.map((d) => d.avg_speaking_score);
  return {
    tooltip: { trigger: "axis" },
    legend: { data: ["正确率(%)", "口语均分"], top: 4, textStyle: { fontSize: 11 } },
    grid: { top: 36, right: 16, bottom: 24, left: 50 },
    xAxis: { type: "value", axisLabel: { fontSize: 10 } },
    yAxis: { type: "category", data: names, axisLabel: { fontSize: 10 } },
    series: [
      { name: "正确率(%)", type: "bar", data: accuracy, barMaxWidth: 18, itemStyle: { color: "#58CC02", borderRadius: [0, 4, 4, 0] } },
      { name: "口语均分", type: "bar", data: speaking, barMaxWidth: 18, itemStyle: { color: "#E6A23C", borderRadius: [0, 4, 4, 0] } },
    ],
  };
});

// ── 方法 ──
async function loadData() {
  loading.value = true;
  try {
    const [groupsRes, studentsRes] = await Promise.all([
      getTeacherGroups(),
      getStudentList({ limit: 100 }),
    ]);
    groups.value = groupsRes.data || [];
    students.value = studentsRes.data.items || [];
  } finally {
    loading.value = false;
  }
}

async function loadGroupDetail(groupId) {
  detailLoading.value = true;
  groupDetail.value = null;
  try {
    const res = await getGroupDetail(groupId);
    groupDetail.value = res.data;
  } catch {
    ElMessage.error("加载分组详情失败");
  } finally {
    detailLoading.value = false;
  }
}

function selectGroup(groupId) {
  selectedGroupId.value = groupId;
  loadGroupDetail(groupId);
}

async function handleCreate() {
  if (!form.value.name.trim()) return;
  creating.value = true;
  try {
    await createTeacherGroup(form.value);
    form.value = { name: "", description: "" };
    dialogVisible.value = false;
    ElMessage.success("分组已创建");
    await loadData();
    if (comparisonActive.value.length > 0) loadComparison();
  } finally {
    creating.value = false;
  }
}

function openEdit() {
  if (!selectedGroup.value) return;
  editForm.value = {
    name: selectedGroup.value.name,
    description: selectedGroup.value.description || "",
  };
  editDialogVisible.value = true;
}

async function handleEditSave() {
  if (!editForm.value.name.trim()) return;
  try {
    await updateTeacherGroup(selectedGroupId.value, editForm.value);
    editDialogVisible.value = false;
    ElMessage.success("分组已更新");
    await loadData();
    loadGroupDetail(selectedGroupId.value);
  } catch {
    ElMessage.error("更新失败");
  }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm(
      '解散分组后，组内学生将变为"未分组"状态。确定要解散吗？',
      "解散分组",
      { confirmButtonText: "确定解散", cancelButtonText: "取消", type: "warning" },
    );
    await deleteGroup(selectedGroupId.value);
    selectedGroupId.value = null;
    groupDetail.value = null;
    ElMessage.success("分组已解散");
    await loadData();
    loadComparison();
  } catch { /* 取消 */ }
}

async function handleStudentAssign(studentId, groupId) {
  await assignStudentGroup(studentId, groupId || null);
  ElMessage.success("学生分组已更新");
  await loadData();
  if (selectedGroupId.value) loadGroupDetail(selectedGroupId.value);
  if (comparisonActive.value.length > 0) loadComparison();
}

async function handleBatchAssign() {
  if (selectedStudents.value.length === 0) {
    ElMessage.warning("请先选择学生");
    return;
  }
  batchAssigning.value = true;
  try {
    const res = await batchAssignGroups(
      selectedStudents.value.map((s) => s.id),
      batchGroupId.value || null,
    );
    ElMessage.success(`已分配 ${res.data.changed} 名学生`);
    selectedStudents.value = [];
    batchGroupId.value = null;
    await loadData();
    if (comparisonActive.value.length > 0) loadComparison();
    if (selectedGroupId.value) loadGroupDetail(selectedGroupId.value);
  } catch {
    ElMessage.error("批量分配失败");
  } finally {
    batchAssigning.value = false;
  }
}

async function loadComparison() {
  try {
    const res = await getGroupsComparison();
    comparisonData.value = res.data || [];
  } catch { /* */ }
}

async function handleComparisonToggle(activeNames) {
  if (activeNames.includes("comparison")) {
    await loadComparison();
  }
}

function handleSelectionChange(selection) {
  selectedStudents.value = selection;
}

// ── 生命周期 ──
onMounted(loadData);
</script>

<template>
  <div class="groups-page">
    <!-- 标题 -->
    <div class="page-hd">
      <div>
        <el-button size="small" :icon="ArrowLeft" text @click="$router.back()">返回</el-button>
        <h1 class="page-title">分组管理</h1>
        <p class="page-desc">创建分组、查看成员、分配学生，支持分组间数据对比</p>
      </div>
    </div>

    <!-- 双栏 -->
    <div class="groups-layout">
      <!-- 左栏：分组列表 -->
      <div class="left-col">
        <div class="left-hd">
          <span class="left-title">我的分组</span>
          <el-button size="small" type="primary" @click="dialogVisible = true">创建分组</el-button>
        </div>

        <div v-if="loading" class="left-loading">
          <el-skeleton :rows="4" animated />
        </div>
        <div v-else-if="groups.length === 0" class="left-empty">
          <p>尚未创建分组</p>
        </div>
        <div v-else class="group-cards">
          <div
            v-for="g in groups"
            :key="g.id"
            class="group-card"
            :class="{ active: g.id === selectedGroupId }"
            @click="selectGroup(g.id)"
          >
            <div class="gc-top">
              <span class="gc-name">{{ g.name }}</span>
              <el-tag size="small" effect="plain">{{ g.student_count }}人</el-tag>
            </div>
            <div class="gc-desc">{{ g.description || "暂无说明" }}</div>
          </div>
        </div>
      </div>

      <!-- 右栏：详情 -->
      <div class="right-col">
        <template v-if="!selectedGroupId">
          <div class="right-empty">
            <div class="re-icon">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#C0C4CC" stroke-width="1.5">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>
            </div>
            <p>选择左侧分组查看详情</p>
          </div>
        </template>
        <template v-else>
          <div v-if="detailLoading" class="right-loading">
            <el-skeleton :rows="6" animated />
          </div>
          <template v-else-if="groupDetail">
            <!-- 分组头部 -->
            <div class="detail-hd">
              <div>
                <h2 class="detail-name">{{ groupDetail.name }}</h2>
                <span class="detail-desc">{{ groupDetail.description || "暂无说明" }}</span>
              </div>
              <div class="detail-actions">
                <el-button size="small" text @click="openEdit">编辑</el-button>
                <el-button size="small" text type="danger" @click="handleDelete">解散分组</el-button>
              </div>
            </div>

            <!-- 统计卡片 -->
            <div class="detail-stats" v-if="detailStats.total_students > 0">
              <div class="dstat-card">
                <div class="dstat-value">{{ detailStats.total_students }}</div>
                <div class="dstat-label">组员数</div>
              </div>
              <div class="dstat-card">
                <div class="dstat-value">{{ detailStats.avg_accuracy }}%</div>
                <div class="dstat-label">平均正确率</div>
              </div>
              <div class="dstat-card">
                <div class="dstat-value">{{ detailStats.avg_speaking_score || '—' }}</div>
                <div class="dstat-label">口语均分</div>
              </div>
              <div class="dstat-card">
                <div class="dstat-value">{{ detailStats.active_14d }}</div>
                <div class="dstat-label">近14天活跃</div>
              </div>
            </div>

            <!-- 成员表格 -->
            <div class="detail-members">
              <h3 class="section-title">组成员</h3>
              <el-table :data="detailMembers" size="small" v-if="detailMembers.length > 0">
                <el-table-column prop="username" label="用户名" min-width="100" />
                <el-table-column prop="level" label="等级" width="70">
                  <template #default="{ row }">
                    <el-tag v-if="row.level" size="small" :type="row.level === 'A' ? 'warning' : row.level === 'B' ? '' : 'success'">
                      {{ row.level }}
                    </el-tag>
                    <span v-else style="color:#C0C4CC;font-size:12px">未定级</span>
                  </template>
                </el-table-column>
                <el-table-column prop="total_practices" label="练习" width="60" align="center" />
                <el-table-column label="正确率" width="70" align="center">
                  <template #default="{ row }">{{ row.accuracy }}%</template>
                </el-table-column>
                <el-table-column prop="speaking_count" label="口语" width="60" align="center" />
              </el-table>
              <div v-else class="members-empty">该分组暂无学生</div>
            </div>
          </template>
        </template>
      </div>
    </div>

    <!-- 批量分配区 -->
    <div class="batch-section">
      <h3 class="section-title">批量分配</h3>
      <div class="batch-body">
        <el-table
          :data="students"
          size="small"
          @selection-change="handleSelectionChange"
          style="flex:1"
          max-height="280"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column prop="username" label="学生" min-width="100" />
          <el-table-column prop="group_name" label="当前分组" min-width="100">
            <template #default="{ row }">{{ row.group_name || "未分组" }}</template>
          </el-table-column>
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-select
                :model-value="row.group_id"
                clearable
                placeholder="分配分组"
                size="small"
                @change="(v) => handleStudentAssign(row.id, v)"
              >
                <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
              </el-select>
            </template>
          </el-table-column>
        </el-table>
        <div class="batch-actions">
          <p v-if="selectedStudents.length > 0">已选 {{ selectedStudents.length }} 名学生</p>
          <p v-else style="color:#C0C4CC">勾选学生后批量分配</p>
          <el-select v-model="batchGroupId" clearable placeholder="目标分组" size="small" style="width:160px">
            <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
          <el-button type="primary" size="small" :loading="batchAssigning" :disabled="selectedStudents.length === 0" @click="handleBatchAssign">
            一键分配
          </el-button>
        </div>
      </div>
    </div>

    <!-- 分组对比 -->
    <el-collapse v-model="comparisonActive" @change="handleComparisonToggle" class="comparison-section">
      <el-collapse-item title="分组数据对比" name="comparison">
        <div v-if="comparisonData.length > 0">
          <el-table :data="comparisonData" size="small" style="margin-bottom:16px">
            <el-table-column prop="group_name" label="分组" min-width="100" />
            <el-table-column prop="student_count" label="人数" width="60" align="center" />
            <el-table-column label="正确率" width="80" align="center">
              <template #default="{ row }">{{ row.avg_accuracy }}%</template>
            </el-table-column>
            <el-table-column prop="avg_speaking_score" label="口语均分" width="80" align="center" />
            <el-table-column label="活跃率" width="80" align="center">
              <template #default="{ row }">{{ row.active_rate }}%</template>
            </el-table-column>
          </el-table>
          <VChart :option="comparisonChartOption" autoresize style="height:180px" />
        </div>
        <div v-else style="text-align:center;color:#C0C4CC;padding:20px">暂无分组数据</div>
      </el-collapse-item>
    </el-collapse>

    <!-- 创建弹窗 -->
    <el-dialog v-model="dialogVisible" title="创建分组" width="420px" :close-on-click-modal="false">
      <el-input v-model="form.name" placeholder="分组名称" maxlength="20" show-word-limit />
      <el-input v-model="form.description" type="textarea" :rows="3" placeholder="分组说明（可选）" class="mt-12" maxlength="100" show-word-limit />
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate" :disabled="!form.name.trim()">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑分组" width="420px">
      <el-input v-model="editForm.name" placeholder="分组名称" maxlength="20" show-word-limit />
      <el-input v-model="editForm.description" type="textarea" :rows="3" placeholder="分组说明（可选）" class="mt-12" maxlength="100" show-word-limit />
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEditSave" :disabled="!editForm.name.trim()">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.groups-page { max-width: 1100px; margin: 0 auto; }

/* ── 标题 ── */
.page-hd { margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 800; color: #303133; margin: 6px 0 4px; }
.page-desc { color: #909399; font-size: 13px; margin: 0; }

/* ── 双栏布局 ── */
.groups-layout { display: flex; gap: 18px; margin-bottom: 24px; }
.left-col { width: 300px; flex-shrink: 0; }
.right-col { flex: 1; min-height: 320px; background: #fff; border-radius: 12px; border: 1px solid #EBEDF0; padding: 20px 24px; box-shadow: 0 1px 3px rgba(0,0,0,.02); }

.left-hd { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.left-title { font-size: 13px; font-weight: 700; color: #606266; text-transform: uppercase; letter-spacing: .05em; }
.left-loading, .left-empty { padding: 20px 0; text-align: center; color: #C0C4CC; font-size: 13px; }

.group-cards { display: flex; flex-direction: column; gap: 8px; }
.group-card {
  background: #fff; border: 1px solid #EBEDF0; border-radius: 10px;
  padding: 14px 16px; cursor: pointer; transition: all .2s;
  border-left: 3px solid transparent;
}
.group-card:hover { border-color: #E6A23C; box-shadow: 0 2px 8px rgba(230,162,60,.08); }
.group-card.active {
  border-left-color: #E6A23C;
  background: rgba(230,162,60,.04);
  border-color: rgba(230,162,60,.2);
  box-shadow: 0 2px 12px rgba(230,162,60,.08);
}
.gc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.gc-name { font-weight: 700; font-size: 14px; color: #303133; }
.gc-desc { font-size: 12px; color: #909399; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ── 右侧空态 ── */
.right-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; min-height: 300px; color: #C0C4CC; }
.re-icon { margin-bottom: 12px; opacity: .6; }
.right-empty p { font-size: 13px; margin: 0; }
.right-loading { padding: 10px 0; }

/* ── 详情头部 ── */
.detail-hd { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 18px; }
.detail-name { font-size: 18px; font-weight: 700; margin: 0 0 4px; color: #303133; }
.detail-desc { font-size: 13px; color: #909399; }
.detail-actions { display: flex; gap: 4px; flex-shrink: 0; }

/* ── 统计小卡 ── */
.detail-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
.dstat-card { background: #FAFBFC; border-radius: 10px; padding: 14px 10px; text-align: center; border: 1px solid #F0F0F0; }
.dstat-value { font-size: 22px; font-weight: 800; color: #E6A23C; line-height: 1.2; }
.dstat-label { font-size: 11px; color: #909399; margin-top: 2px; font-weight: 600; letter-spacing: .04em; }

/* ── 成员 ── */
.detail-members { margin-top: 4px; }
.section-title { font-size: 13px; font-weight: 700; color: #606266; margin: 0 0 10px; text-transform: uppercase; letter-spacing: .05em; }
.members-empty { text-align: center; padding: 30px 0; color: #C0C4CC; font-size: 13px; }

/* ── 批量分配 ── */
.batch-section { background: #fff; border-radius: 12px; border: 1px solid #EBEDF0; padding: 18px 20px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,.02); }
.batch-body { display: flex; gap: 16px; align-items: flex-start; }
.batch-actions { width: 180px; flex-shrink: 0; display: flex; flex-direction: column; gap: 10px; padding-top: 4px; }
.batch-actions p { font-size: 12px; color: #606266; margin: 0; font-weight: 500; }

/* ── 对比 ── */
.comparison-section { background: #fff; border-radius: 12px; border: 1px solid #EBEDF0; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.02); }
.comparison-section :deep(.el-collapse-item__header) { padding: 14px 20px; font-size: 13px; font-weight: 700; color: #606266; letter-spacing: .05em; }
.comparison-section :deep(.el-collapse-item__wrap) { padding: 0 20px 16px; }

.mt-12 { margin-top: 12px; }

@media (max-width: 860px) {
  .groups-layout { flex-direction: column; }
  .left-col { width: 100%; }
  .detail-stats { grid-template-columns: repeat(2, 1fr); }
  .batch-body { flex-direction: column; }
  .batch-actions { width: 100%; flex-direction: row; align-items: center; }
}
</style>
