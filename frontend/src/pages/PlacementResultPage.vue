<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import { ArrowLeft } from "@element-plus/icons-vue";
import { useQuizStore } from "@/stores/quiz";
import LevelBadge from "@/components/LevelBadge.vue";

const router = useRouter();
const quizStore = useQuizStore();

const result = computed(() => quizStore.placementResult);

function goLearn() {
  router.push("/clips");
}
</script>

<template>
  <div class="placement-result">
    <div v-if="!result" class="empty-wrap">
      <el-result icon="warning" title="无测试结果" sub-title="请先完成定级测试">
        <template #extra>
          <el-button type="primary" @click="router.push('/placement-test')">去测试</el-button>
        </template>
      </el-result>
    </div>

    <div v-else class="result-content">
      <div class="page-top">
        <el-button size="small" :icon="ArrowLeft" text @click="router.push('/student')">返回看板</el-button>
      </div>
      <div class="result-hero">
        <h1>测试完成</h1>
        <div class="score-display">
          <span class="score-num">{{ result.score }}</span>
          <span class="score-divider">/</span>
          <span class="score-total">{{ result.total }}</span>
        </div>
        <LevelBadge :level="result.level" class="big-badge" />
      </div>

      <div class="level-desc">
        <template v-if="result.level === 'A'">
          <p>听力能力出色，适合挑战高难度片段和复杂对话场景。</p>
        </template>
        <template v-else-if="result.level === 'B'">
          <p>有一定基础，可以挑战中等难度片段，重点提升听力理解。</p>
        </template>
        <template v-else>
          <p>基础扎实，建议从简单片段开始，逐步积累听力词汇。</p>
        </template>
      </div>

      <el-button type="primary" size="large" class="start-btn" @click="goLearn">
        开始学习
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.placement-result {
  max-width: 480px;
  margin: 0 auto;
  text-align: center;
}

.page-top {
  text-align: left;
  margin-bottom: 12px;
}

.result-hero {
  margin: 48px 0 24px;
}

.result-hero h1 {
  font-size: 24px;
  color: #303133;
  margin-bottom: 20px;
}

.score-display {
  margin-bottom: 20px;
}

.score-num {
  font-size: 56px;
  font-weight: 800;
  color: var(--color-primary);
}

.score-divider {
  font-size: 36px;
  color: #c0c4cc;
  margin: 0 8px;
}

.score-total {
  font-size: 36px;
  color: #909399;
}

.big-badge {
  font-size: 18px;
  padding: 8px 28px;
}

.level-desc {
  margin: 20px 0 32px;
  color: #606266;
  line-height: 1.8;
}

.start-btn {
  width: 200px;
}
</style>
