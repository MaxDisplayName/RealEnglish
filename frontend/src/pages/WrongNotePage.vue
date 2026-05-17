<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ArrowLeft } from "@element-plus/icons-vue";
import request from "@/modules/shared/request";

const router = useRouter();

const wrongNotes = ref([]);
const total = ref(0);
const loading = ref(true);
const error = ref(null);
const pagination = ref({ current: 1, pageSize: 20 });

async function loadNotes() {
  loading.value = true;
  error.value = null;
  try {
    const skip = (pagination.value.current - 1) * pagination.value.pageSize;
    const res = await request.get("/answers/wrong-notes", {
      params: { skip, limit: pagination.value.pageSize },
    });
    wrongNotes.value = res.data.items || [];
    total.value = res.data.total || 0;
  } catch (e) {
    error.value = e.response?.data?.detail || "加载错题失败";
  } finally {
    loading.value = false;
  }
}

function handleCurrentChange(page) {
  pagination.value.current = page;
  loadNotes();
}

function goClip(clipId) {
  if (clipId) router.push(`/clips/${clipId}`);
}

onMounted(loadNotes);
</script>

<template>
  <div class="wrong-note-page">
    <div class="page-top">
      <el-button size="small" :icon="ArrowLeft" text @click="router.back()">返回</el-button>
    </div>
    <div class="page-header">
      <h2>错题本</h2>
      <span class="total-badge">共 {{ total }} 道错题</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="state-wrap">
      <el-skeleton :rows="6" animated />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="state-wrap">
      <el-result icon="error" title="加载失败" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="loadNotes">重试</el-button>
        </template>
      </el-result>
    </div>

    <!-- Empty -->
    <div v-else-if="wrongNotes.length === 0" class="state-wrap">
      <el-empty description="暂无错题，继续保持！">
        <template #extra>
          <el-button type="primary" @click="router.push('/clips')">去学习</el-button>
        </template>
      </el-empty>
    </div>

    <!-- Wrong Notes List -->
    <div v-else class="notes-list">
      <el-card
        v-for="note in wrongNotes"
        :key="note.id"
        class="note-card"
        shadow="hover"
      >
        <div class="note-header">
          <span class="diff-badge" :class="'diff-' + note.difficulty.toLowerCase()">{{ note.difficulty }}级</span>
          <el-tag type="danger" size="small" effect="plain">错题</el-tag>
          <span class="note-time">{{ note.answered_at ? new Date(note.answered_at).toLocaleString() : "" }}</span>
        </div>

        <p class="note-question">{{ note.content?.question }}</p>

        <div class="note-options">
          <div
            v-for="(opt, idx) in note.content?.options || []"
            :key="idx"
            class="option-item"
            :class="{
              'correct-option': idx === note.content?.answer,
              'wrong-option': idx === note.selected_option && idx !== note.content?.answer,
            }"
          >
            <span class="option-label">{{ String.fromCharCode(65 + idx) }}</span>
            <span class="option-text">{{ opt }}</span>
            <el-icon v-if="idx === note.content?.answer" class="result-icon correct-icon">
              <span>&#10003;</span>
            </el-icon>
          </div>
        </div>

        <div class="note-explanation">
          <el-alert
            :title="note.content?.explanation || '无解析'"
            type="info"
            :closable="false"
            show-icon
          />
        </div>
      </el-card>

      <!-- Pagination -->
      <div v-if="total > pagination.pageSize" class="pagination-wrap">
        <el-pagination
          v-model:current="pagination.current"
          :page-size="pagination.pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.wrong-note-page {
  max-width: 720px;
  margin: 0 auto;
}

.page-top {
  margin-bottom: 12px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 22px;
  color: #303133;
}

.total-badge {
  font-size: 13px;
  color: #909399;
}

.state-wrap {
  margin-top: 60px;
}

.notes-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.note-card {
  border-radius: var(--radius-base);
}

.note-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.note-time {
  margin-left: auto;
  font-size: 12px;
  color: #c0c4cc;
}

.note-question {
  font-size: 15px;
  color: #303133;
  line-height: 1.6;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: var(--radius-base);
}

.note-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.option-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid #e4e7ed;
  border-radius: var(--radius-base);
}

.correct-option {
  border-color: var(--color-success);
  background: #f0f9eb;
}

.wrong-option {
  border-color: var(--color-danger);
  background: #fef0f0;
}

.option-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #f0f2f5;
  font-size: 12px;
  font-weight: 600;
  color: #606266;
  margin-right: 10px;
  flex-shrink: 0;
}

.correct-option .option-label {
  background: var(--color-success);
  color: #fff;
}

.wrong-option .option-label {
  background: var(--color-danger);
  color: #fff;
}

.option-text {
  flex: 1;
  font-size: 14px;
}

.result-icon {
  margin-left: 8px;
  font-weight: 700;
}

.correct-icon { color: var(--color-success); }

.note-explanation {
  font-size: 13px;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
