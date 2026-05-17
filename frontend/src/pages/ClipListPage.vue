<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { getClips } from "@/modules/student/api";

const router = useRouter();

const clips = ref([]);
const totalCount = ref(0);
const loading = ref(true);
const error = ref(null);
const filters = ref({ difficulty: null, category: null });

const categories = ref([]);

async function loadClips() {
  loading.value = true;
  error.value = null;
  try {
    const params = { limit: 100 };
    if (filters.value.difficulty) params.difficulty = filters.value.difficulty;
    if (filters.value.category) params.category = filters.value.category;
    const res = await getClips(params);
    clips.value = res.data;
    totalCount.value = clips.value.length;
    // 提取类别列表
    const cats = new Set(clips.value.map((c) => c.category).filter(Boolean));
    categories.value = [...cats];
  } catch (e) {
    error.value = e.response?.data?.detail || "加载失败";
  } finally {
    loading.value = false;
  }
}

function onFilterChange() {
  loadClips();
}

function goClip(id) {
  router.push(`/clips/${id}`);
}

onMounted(loadClips);
</script>

<template>
  <div class="clip-list-page">
    <div class="page-header">
      <h2>影视片段库 <span v-if="totalCount" class="clip-count">({{ totalCount }})</span></h2>
      <div class="filters">
        <el-select v-model="filters.difficulty" placeholder="难度筛选" clearable @change="onFilterChange" size="small">
          <el-option label="A级 (高级)" value="A" />
          <el-option label="B级 (中级)" value="B" />
          <el-option label="C级 (初级)" value="C" />
        </el-select>
        <el-select v-model="filters.category" placeholder="类别筛选" clearable @change="onFilterChange" size="small">
          <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
        </el-select>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="clips-grid">
      <el-card v-for="i in 6" :key="i" class="clip-card">
        <el-skeleton :rows="3" animated />
      </el-card>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="state-wrap">
      <el-result icon="error" title="加载失败" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="loadClips">重试</el-button>
        </template>
      </el-result>
    </div>

    <!-- Empty -->
    <div v-else-if="clips.length === 0" class="state-wrap">
      <el-empty description="暂无匹配片段" />
    </div>

    <!-- Data -->
    <div v-else class="clips-grid">
      <el-card
        v-for="clip in clips"
        :key="clip.id"
        class="clip-card"
        :body-style="{ padding: '16px', cursor: 'pointer' }"
        shadow="hover"
        @click="goClip(clip.id)"
      >
        <div class="card-top">
          <span class="diff-badge" :class="'diff-' + clip.difficulty.toLowerCase()">{{ clip.difficulty }}级</span>
          <span class="card-category">{{ clip.category }}</span>
        </div>
        <h3 class="card-title">{{ clip.title }}</h3>
        <p class="card-summary">{{ clip.summary }}</p>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.clip-list-page {
  max-width: 960px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 12px;
}

.page-header h2 {
  font-size: 22px;
  color: #303133;
}

.clip-count {
  font-size: 16px;
  font-weight: 400;
  color: #909399;
}

.filters {
  display: flex;
  gap: 8px;
}

.clips-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.clip-card {
  transition: transform 0.2s;
}

.clip-card:hover {
  transform: translateY(-2px);
}

.card-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.card-category {
  font-size: 12px;
  color: #909399;
}

.card-title {
  font-size: 16px;
  color: #303133;
  margin-bottom: 8px;
  line-height: 1.4;
}

.card-summary {
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.state-wrap {
  margin-top: 60px;
}
</style>
