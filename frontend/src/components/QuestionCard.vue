<script setup>
import { computed } from "vue";

const props = defineProps({
  question: { type: Object, required: true },
  showResult: { type: Boolean, default: false },
  selectedOption: { type: Number, default: null },
  correctAnswer: { type: Number, default: null },
  explanation: { type: String, default: "" },
  questionIndex: { type: Number, default: 0 },
});

const emit = defineEmits(["select"]);

const optionLabels = ["A", "B", "C"];

const optionClass = (idx) => {
  if (!props.showResult) return "";
  if (idx === props.correctAnswer) return "option-correct";
  if (idx === props.selectedOption && idx !== props.correctAnswer) return "option-wrong";
  return "";
};

function handleSelect(idx) {
  if (!props.showResult) {
    emit("select", idx);
  }
}
</script>

<template>
  <div class="question-card">
    <div class="question-header">
      <span class="question-num">Q{{ questionIndex + 1 }}</span>
      <span class="question-type">{{ question.difficulty }}级</span>
    </div>
    <p class="question-text">{{ question.content?.question || question.question }}</p>
    <div class="options">
      <div
        v-for="(opt, idx) in (question.content?.options || question.options || [])"
        :key="idx"
        class="option-item"
        :class="[
          optionClass(idx),
          { 'option-selected': selectedOption === idx && !showResult },
        ]"
        @click="handleSelect(idx)"
      >
        <span class="option-label">{{ optionLabels[idx] }}</span>
        <span class="option-text">{{ opt }}</span>
        <el-icon v-if="showResult && idx === correctAnswer" class="result-icon correct-icon">
          <span>&#10003;</span>
        </el-icon>
        <el-icon v-if="showResult && idx === selectedOption && idx !== correctAnswer" class="result-icon wrong-icon">
          <span>&#10007;</span>
        </el-icon>
      </div>
    </div>
    <div v-if="showResult && explanation" class="explanation">
      {{ explanation }}
    </div>
  </div>
</template>

<style scoped>
.question-card {
  background: #fff;
  border-radius: var(--radius-base);
  padding: 24px;
  box-shadow: var(--shadow-card);
}

.question-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.question-num {
  font-weight: 700;
  font-size: 16px;
  color: var(--color-primary);
}

.question-type {
  font-size: 12px;
  padding: 1px 8px;
  border-radius: 8px;
  background: #ecf5ff;
  color: var(--color-primary);
}

.question-text {
  font-size: 16px;
  line-height: 1.6;
  margin-bottom: 18px;
  color: #303133;
}

.options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.option-item {
  display: flex;
  align-items: center;
  padding: 12px 14px;
  border: 1.5px solid #e4e7ed;
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: all 0.2s;
}

.option-item:hover:not(.option-correct):not(.option-wrong) {
  border-color: var(--color-primary);
  background: #ecf5ff;
}

.option-selected {
  border-color: var(--color-primary);
  background: #ecf5ff;
}

.option-correct {
  border-color: var(--color-success);
  background: #f0f9eb;
}

.option-wrong {
  border-color: var(--color-danger);
  background: #fef0f0;
}

.option-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #f0f2f5;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-right: 12px;
  flex-shrink: 0;
}

.option-correct .option-label {
  background: var(--color-success);
  color: #fff;
}

.option-wrong .option-label {
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
.wrong-icon { color: var(--color-danger); }

.explanation {
  margin-top: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: var(--radius-base);
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}
</style>
