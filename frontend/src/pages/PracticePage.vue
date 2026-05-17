<script setup>
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQuizStore } from "@/stores/quiz";
import { ArrowLeft } from "@element-plus/icons-vue";
import QuestionCard from "@/components/QuestionCard.vue";
import VideoPlayer from "@/components/VideoPlayer.vue";
import { getClipDetail } from "@/api/student/api";

const route = useRoute();
const router = useRouter();
const quizStore = useQuizStore();

const questions = ref([]);
const currentIndex = ref(0);
const loading = ref(true);
const results = ref({});
const clip = ref(null);
const clipLoading = ref(true);

const currentQuestion = () => questions.value[currentIndex.value] || null;

onMounted(async () => {
  // 加载片段信息（用于视频播放）
  if (route.params.clipId) {
    try {
      const res = await getClipDetail(route.params.clipId);
      clip.value = res.data;
    } catch { /* */ }
    clipLoading.value = false;
  }

  if (quizStore.aiQuestions.length > 0) {
    questions.value = quizStore.aiQuestions;
  }
  // 如果直接访问此页面（刷新后），尝试重新生成
  else if (route.params.clipId) {
    // 没有缓存的题目，跳转回去
    router.replace(`/clips/${route.params.clipId}`);
    return;
  }
  loading.value = false;
});

async function handleSelect(optionIndex) {
  if (!currentQuestion()) return;
  try {
    const result = await quizStore.submitSingleAnswer(currentQuestion().id, optionIndex);
    results.value[currentQuestion().id] = {
      selectedOption: optionIndex,
      ...result,
    };
  } catch (e) {
    console.error("提交失败:", e);
  }
}

function handleNext() {
  if (currentIndex.value < questions.value.length - 1) {
    currentIndex.value++;
  }
}

function handlePrev() {
  if (currentIndex.value > 0) {
    currentIndex.value--;
  }
}

function goBack() {
  router.push(`/clips/${route.params.clipId}`);
}
</script>

<template>
  <div class="practice-page">
    <!-- Loading -->
    <div v-if="loading" class="state-wrap">
      <el-skeleton :rows="6" animated />
    </div>

    <!-- Empty -->
    <div v-else-if="questions.length === 0" class="state-wrap">
      <el-empty description="暂无题目，请先从片段页面生成题目">
        <template #extra>
          <el-button size="small" :icon="ArrowLeft" text @click="goBack">返回片段</el-button>
        </template>
      </el-empty>
    </div>

    <!-- Active -->
    <div v-else class="practice-content">
      <!-- 视频播放区 -->
      <div v-if="clip && clip.bvid" class="video-section">
        <VideoPlayer
          :bvid="clip.bvid"
          :page="clip.page || 1"
          :start-sec="clip.start_sec"
          :end-sec="clip.end_sec"
          :title="clip.title"
        />
      </div>

      <div class="practice-header">
        <div class="header-top">
          <el-button size="small" :icon="ArrowLeft" text @click="goBack">返回片段</el-button>
        </div>
        <div class="header-main">
          <h2>答题练习</h2>
          <div class="progress-text">第 {{ currentIndex + 1 }} / {{ questions.length }} 题</div>
        </div>
      </div>

      <el-progress
        :percentage="((currentIndex + 1) / questions.length) * 100"
        :show-text="false"
        class="progress-bar"
      />

      <QuestionCard
        v-if="currentQuestion()"
        :key="currentQuestion().id"
        :question="currentQuestion()"
        :question-index="currentIndex"
        :show-result="!!results[currentQuestion().id]"
        :selected-option="results[currentQuestion().id]?.selectedOption ?? null"
        :correct-answer="results[currentQuestion().id]?.correct_answer ?? null"
        :explanation="results[currentQuestion().id]?.explanation ?? ''"
        @select="handleSelect"
      />

      <div class="nav-buttons">
        <el-button :disabled="currentIndex === 0" @click="handlePrev">上一题</el-button>
        <el-button
          v-if="currentIndex < questions.length - 1"
          :disabled="!results[currentQuestion()?.id]"
          type="primary"
          @click="handleNext"
        >
          下一题
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.practice-page {
  max-width: 780px;
  margin: 0 auto;
}

.video-section {
  margin-bottom: 20px;
}

.state-wrap {
  margin-top: 60px;
}

.practice-header {
  margin-bottom: 12px;
}

.header-top {
  margin-bottom: 6px;
}

.header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-main h2 {
  font-size: 20px;
  color: #303133;
}

.progress-text {
  font-size: 14px;
  color: #909399;
}

.progress-bar {
  margin-bottom: 20px;
}

.practice-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.nav-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}
</style>
