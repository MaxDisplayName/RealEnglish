<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ArrowLeft } from "@element-plus/icons-vue";
import { useQuizStore } from "@/stores/quiz";
import { useUserStore } from "@/stores/user";
import QuestionCard from "@/components/QuestionCard.vue";
import VideoPlayer from "@/components/VideoPlayer.vue";

const router = useRouter();
const quizStore = useQuizStore();
const userStore = useUserStore();

const currentIndex = ref(0);
const submitting = ref(false);

const currentQuestion = computed(() => quizStore.currentQuestions[currentIndex.value] || null);

onMounted(async () => {
  try {
    await quizStore.fetchPlacementQuestions();
  } catch (e) {
    console.error("加载失败:", e);
  }
});

function handleSelect(optionIndex) {
  if (!currentQuestion.value) return;
  quizStore.selectAnswer(currentQuestion.value.id, optionIndex);
}

function handleNext() {
  if (currentIndex.value < quizStore.currentQuestions.length - 1) {
    currentIndex.value++;
  }
}

function handlePrev() {
  if (currentIndex.value > 0) {
    currentIndex.value--;
  }
}

async function handleSubmit() {
  if (quizStore.currentAnswers.length < 10) {
    return;
  }
  submitting.value = true;
  try {
    const result = await quizStore.submitPlacementAnswers();
    userStore.setLevel(result.level);
    router.push("/student/placement-result");
  } catch (e) {
    console.error("提交失败:", e);
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="placement-test">
    <!-- Loading State -->
    <div v-if="quizStore.loading && quizStore.currentQuestions.length === 0" class="loading-wrap">
      <el-skeleton :rows="6" animated />
    </div>

    <!-- Error State -->
    <div v-else-if="quizStore.error && quizStore.currentQuestions.length === 0" class="error-wrap">
      <el-result icon="error" title="加载失败" :sub-title="quizStore.error">
        <template #extra>
          <el-button type="primary" @click="quizStore.fetchPlacementQuestions()">重试</el-button>
        </template>
      </el-result>
    </div>

    <!-- Active State -->
    <div v-else-if="currentQuestion" class="test-content">
      <div class="page-top">
        <el-button size="small" :icon="ArrowLeft" text @click="router.push('/student')">返回看板</el-button>
      </div>
      <div class="progress-bar">
        <div class="progress-text">第 {{ currentIndex + 1 }} / 10 题</div>
        <el-progress :percentage="(currentIndex + 1) * 10" :show-text="false" />
      </div>

      <!-- 题目关联的视频片段 -->
      <div v-if="currentQuestion.video" class="placement-video">
        <VideoPlayer
          :key="currentIndex"
          :bvid="currentQuestion.video.bvid"
          :page="currentQuestion.video.page || 1"
          :start-sec="currentQuestion.video.start_sec"
          :end-sec="currentQuestion.video.end_sec"
        />
      </div>

      <QuestionCard
        :question="currentQuestion"
        :question-index="currentIndex"
        :selected-option="quizStore.getSelectedOption(currentQuestion.id)"
        @select="handleSelect"
      />

      <div class="nav-buttons">
        <el-button v-if="currentIndex > 0" @click="handlePrev">上一题</el-button>
        <el-button
          v-if="currentIndex < 9"
          type="primary"
          :disabled="quizStore.getSelectedOption(currentQuestion.id) === null"
          @click="handleNext"
        >
          下一题
        </el-button>
        <el-button
          v-if="currentIndex === 9"
          type="success"
          :disabled="quizStore.currentAnswers.length < 10"
          :loading="submitting"
          @click="handleSubmit"
        >
          提交全部答案
        </el-button>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-wrap">
      <el-empty description="暂无题目" />
    </div>
  </div>
</template>

<style scoped>
.placement-test {
  max-width: 680px;
  margin: 0 auto;
}

.loading-wrap,
.error-wrap,
.empty-wrap {
  margin-top: 60px;
}

.progress-bar {
  margin-bottom: 20px;
}

.progress-text {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
}

.test-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.placement-video {
  margin-bottom: 16px;
}

.nav-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}
</style>
