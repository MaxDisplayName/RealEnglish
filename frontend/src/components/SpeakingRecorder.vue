<script setup>
import { ref, computed, onMounted } from "vue";
import { Microphone, Promotion } from "@element-plus/icons-vue";
import { useRecorder } from "@/composables/useRecorder";
import { useSpeech } from "@/composables/useSpeech";
import { evaluateSpeaking, generateSpeakingQuestion } from "@/modules/student/api";
import { extractPlainText } from "@/utils/dialogueParser";
import { ElMessage } from "element-plus";

const props = defineProps({
  /** 跟读模式参考文本（原台词） — 用于传统单块模式 */
  referenceText: { type: String, default: "" },
  /** 自由应答模式使用的剧情摘要 */
  summary: { type: String, default: "" },
  /** 模式：repeat（跟读）/ free（自由应答） */
  mode: { type: String, default: "repeat" },
  /** 关联片段 ID */
  clipId: { type: String, default: null },
  /** 逐句模式：传入单行对话对象 { speaker, text, gender } */
  line: { type: Object, default: null },
  /** 逐句模式中的行序号（用于进度展示） */
  lineIndex: { type: Number, default: 0 },
});

const emit = defineEmits(["practice-complete"]);

const { isRecording, startRecording, stopRecording } = useRecorder();
const { speakText, stopSpeaking } = useSpeech();

const recordingComplete = ref(false);
const submitting = ref(false);
const result = ref(null);
const question = ref("");
const generatingQuestion = ref(false);
const error = ref(null);

const hasStarted = ref(false);

// 动画相关
const animatedScores = ref({});
const scoreVisible = ref({});
const resultVisible = ref(false);

/** 逐句模式下的实际参考文本 */
const referenceLine = computed(() => props.line?.text || "");

const SCORE_LABELS = {
  total_score: "总分",
  accuracy: "准确度",
  fluency: "流畅度",
  integrity: "完整度",
};

const freeScoreItems = [
  { key: "content_score", label: "内容相关性" },
  { key: "grammar_score", label: "语法准确性" },
  { key: "fluency_score", label: "表达流畅度" },
  { key: "vocabulary_score", label: "词汇丰富度" },
];

const MAX_SCORE = 5;

function scorePercent(val) {
  return Math.round((val / MAX_SCORE) * 100);
}

/** 数字跳动动画：从 0 计数到目标值 */
function animateScore(key, targetVal) {
  const duration = 600;
  const startTime = performance.now();
  function tick(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // ease-out
    const eased = 1 - Math.pow(1 - progress, 3);
    animatedScores.value[key] = Math.round(targetVal * eased * 10) / 10;
    if (progress < 1) {
      requestAnimationFrame(tick);
    } else {
      animatedScores.value[key] = targetVal;
    }
  }
  requestAnimationFrame(tick);
}

/** 触发评分结果交错动画 */
function triggerResultAnimation() {
  resultVisible.value = true;
  const dimKeys = props.mode === "free"
    ? freeScoreItems.map(i => i.key)
    : ["accuracy", "fluency", "integrity"];

  // 总分数先动
  setTimeout(() => {
    if (result.value?.score?.total_score) {
      animateScore("total", result.value.score.total_score);
    }
  }, 100);

  // 各维度依次交错出现
  dimKeys.forEach((key, i) => {
    setTimeout(() => {
      scoreVisible.value[key] = true;
      if (result.value?.score?.[key] != null) {
        animateScore(key, result.value.score[key]);
      }
    }, 250 + i * 120);
  });
}

function genderLabel(gender) {
  return gender === "male" ? "男声" : "女声";
}

function genderTagType(gender) {
  return gender === "male" ? "info" : "success";
}

onMounted(async () => {
  // 跟读模式自动准备；自由模式需用户点击"生成题目"
});

async function handleGenerateQuestion() {
  if (!props.summary) return;
  generatingQuestion.value = true;
  try {
    const res = await generateSpeakingQuestion(props.summary);
    question.value = res.data?.question || "";
  } catch (e) {
    question.value = "What do you think about this scene?";
  } finally {
    generatingQuestion.value = false;
  }
}

async function handleStart() {
  error.value = null;
  hasStarted.value = true;
  recordingComplete.value = false;
  result.value = null;

  try {
    await startRecording();
  } catch (e) {
    error.value = e.message || "无法访问麦克风";
    ElMessage.error(error.value);
  }
}

async function handleStop() {
  try {
    submitting.value = true;
    const { blob, duration } = await stopRecording();
    recordingComplete.value = true;

    const refText = props.line
      ? referenceLine.value
      : props.mode === "repeat"
        ? props.referenceText
        : question.value;

    if (!refText && !props.line && props.mode === "repeat") {
      error.value = "没有参考文本";
      return;
    }

    const res = await evaluateSpeaking(blob, refText || "", props.mode, props.clipId, duration);
    result.value = res.data;
    // 重置动画状态，延迟触发交错入场
    animatedScores.value = {};
    scoreVisible.value = {};
    resultVisible.value = false;
    setTimeout(triggerResultAnimation, 50);
    emit("practice-complete", {
      ...res.data,
      lineIndex: props.lineIndex,
      line: props.line,
    });
  } catch (e) {
    error.value = "提交评测失败";
    ElMessage.error(error.value);
  } finally {
    submitting.value = false;
  }
}

function handleReset() {
  hasStarted.value = false;
  recordingComplete.value = false;
  result.value = null;
  error.value = null;
  animatedScores.value = {};
  scoreVisible.value = {};
  resultVisible.value = false;
  stopSpeaking();
}

function handlePlayOriginal() {
  if (props.line) {
    speakText(props.line.text, props.line.gender || "female", "en-US");
  } else if (props.referenceText) {
    speakText(extractPlainText(props.referenceText), "female", "en-US");
  }
}
</script>

<template>
  <div class="speaking-recorder" :class="{ 'line-mode': !!line }">
    <!-- 逐句模式：显示说话人和性别标签 -->
    <div v-if="line" class="line-header">
      <span class="speaker-name">{{ line.speaker }}</span>
      <el-tag :type="genderTagType(line.gender)" size="small" class="gender-tag">
        {{ genderLabel(line.gender) }}
      </el-tag>
    </div>

    <!-- 自由模式：未生成题目时显示生成按钮 -->
    <div v-if="mode === 'free' && !hasStarted && !question" class="generate-area">
      <p class="hint-text" style="margin-bottom:12px">AI 将根据剧情摘要为你生成一个开放性问题</p>
      <el-button type="primary" size="large" :loading="generatingQuestion" @click="handleGenerateQuestion">
        {{ generatingQuestion ? '生成中...' : '生成口语题目' }}
      </el-button>
    </div>

    <!-- 自由应答模式的问题 -->
    <div v-if="mode === 'free' && question" class="question-display">
      <h4>口语问题</h4>
      <el-alert :title="question" type="info" :closable="false" show-icon />
    </div>

    <!-- 录音控制 -->
    <div class="recorder-controls">
      <div v-if="!hasStarted && (mode === 'repeat' || (mode === 'free' && question))" class="start-area">
        <el-button type="primary" size="large" @click="handleStart" :icon="Microphone"
          >开始录音</el-button
        >
        <p class="hint-text">
          {{ line ? "点击按钮，朗读这句台词：" : mode === "repeat" ? "请朗读以下台词：" : "请回答上述问题：" }}
        </p>
      </div>

      <div v-else class="recording-area">
        <div class="recording-status" :class="{ active: isRecording }">
          <span class="status-dot" />
          <span>{{ isRecording ? "录音中..." : "录音完成" }}</span>
        </div>

        <div class="action-buttons">
          <el-button v-if="isRecording" type="danger" :loading="submitting" @click="handleStop">
            停止录音
          </el-button>
          <el-button v-else :disabled="submitting" @click="handleReset">
            重新录制
          </el-button>
        </div>
      </div>

      <!-- 参考文本显示 -->
      <div v-if="mode === 'repeat'" class="reference-text">
        <p>{{ line ? line.text : referenceText }}</p>
        <el-button size="small" text @click="handlePlayOriginal">
          <el-icon style="margin-right: 4px"><Promotion /></el-icon>
          播放原声
        </el-button>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-display">
      <el-alert :title="error" type="error" :closable="false" show-icon />
    </div>

    <!-- 评测中动画 -->
    <div v-if="submitting && !result" class="evaluating-overlay">
      <div class="eval-spinner">
        <div class="spinner-ring" />
        <span class="spinner-label">AI 正在评测...</span>
      </div>
      <div class="eval-waves">
        <span v-for="i in 5" :key="i" class="wave-bar" :style="{ animationDelay: `${i * 0.1}s` }" />
      </div>
    </div>

    <!-- 评测结果 -->
    <Transition name="result-reveal">
      <div v-if="result" class="eval-result">
        <el-card shadow="hover">
          <template #header>
            <div class="result-header">
              <span>{{ mode === 'free' ? '自由应答评分' : '评测结果' }}</span>
              <span class="total-score" :class="{ 'score-pop': animatedScores.total }">
                {{ animatedScores.total != null ? animatedScores.total : result.score.total_score }}
                <small>/ {{ MAX_SCORE }}</small>
              </span>
            </div>
          </template>

          <!-- 自由模式：四维度评分 + 转录 -->
          <template v-if="mode === 'free'">
            <div v-if="result.transcript" class="transcript-section">
              <h4>识别文本</h4>
              <p class="transcript-text">{{ result.transcript }}</p>
            </div>
            <div class="score-details">
              <div
                v-for="item in freeScoreItems"
                :key="item.key"
                class="score-item"
                :class="{ 'score-enter': scoreVisible[item.key] }"
              >
                <span class="score-label">{{ item.label }}</span>
                <div class="score-bar-row">
                  <el-progress
                    :percentage="scoreVisible[item.key] ? scorePercent(result.score[item.key]) : 0"
                    :stroke-width="10"
                    :status="result.score[item.key] >= 4 ? 'success' : 'warning'"
                    class="animated-progress"
                  />
                  <span class="score-value" :class="{ 'score-pop': scoreVisible[item.key] }">
                    {{ animatedScores[item.key] != null ? animatedScores[item.key] : result.score[item.key] }}
                    <small>/ {{ MAX_SCORE }}</small>
                  </span>
                </div>
              </div>
            </div>
          </template>

          <!-- 跟读模式：准确度/流畅度/完整度 -->
          <template v-else>
            <div class="score-details">
              <div
                v-for="key in ['accuracy', 'fluency', 'integrity']"
                :key="key"
                class="score-item"
                :class="{ 'score-enter': scoreVisible[key] }"
              >
                <span class="score-label">{{ SCORE_LABELS[key] }}</span>
                <div class="score-bar-row">
                  <el-progress
                    :percentage="scoreVisible[key] ? scorePercent(result.score[key]) : 0"
                    :stroke-width="10"
                    :status="result.score[key] >= 4 ? 'success' : 'warning'"
                    class="animated-progress"
                  />
                  <span class="score-value" :class="{ 'score-pop': scoreVisible[key] }">
                    {{ animatedScores[key] != null ? animatedScores[key] : result.score[key] }}
                    <small>/ {{ MAX_SCORE }}</small>
                  </span>
                </div>
              </div>
            </div>
          </template>

          <div class="feedback-section">
            <h4>AI 教练反馈</h4>
            <p class="feedback-text">{{ result.feedback }}</p>
          </div>
        </el-card>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.speaking-recorder {
  max-width: 640px;
  margin: 0 auto;
}

.question-display {
  margin-bottom: 16px;
}

.line-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.speaker-name {
  font-weight: 700;
  font-size: 14px;
  color: var(--color-primary);
}

.gender-tag {
  font-size: 10px;
}

.recorder-controls {
  margin-bottom: 16px;
}

.start-area {
  text-align: center;
  padding: 32px 0;
}

.hint-text {
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 14px;
}

.recording-area {
  text-align: center;
  padding: 24px 0;
}

.recording-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 16px;
  color: #606266;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #c0c4cc;
}

.recording-status.active .status-dot {
  background: var(--color-danger);
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.reference-text {
  margin-top: 16px;
  padding: 12px;
  background: var(--bg-surface);
  border-radius: var(--radius-base);
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.reference-text p {
  flex: 1;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.error-display {
  margin-bottom: 16px;
}

.eval-result {
  margin-top: 16px;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.total-score {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-primary);
}

.score-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.score-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.score-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.score-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.score-bar-row .el-progress {
  flex: 1;
}

.score-value {
  font-size: 14px;
  font-weight: 600;
  color: #606266;
  min-width: 36px;
  text-align: right;
}

.feedback-section {
  padding: 12px;
  background: #f0f9eb;
  border-radius: var(--radius-base);
}

.feedback-section h4 {
  font-size: 14px;
  color: var(--color-success);
  margin-bottom: 8px;
}

.feedback-text {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.transcript-section {
  margin-bottom: 14px;
  padding: 12px 14px;
  background: var(--bg-surface, #F7F7F7);
  border-radius: 8px;
}
.transcript-section h4 {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-secondary, #AFAFAF);
  margin-bottom: 6px;
}
.transcript-text {
  font-size: 15px;
  color: var(--text-main, #4B4B4B);
  line-height: 1.6;
  font-style: italic;
}

/* 逐句模式：紧凑布局，固定宽度 */
.line-mode {
  width: 100%;
  padding: 14px 18px;
  background: #fff;
  border: 2px solid var(--border-color);
  border-radius: var(--radius-base);
  margin-bottom: 12px;
  box-shadow: none;
}

.line-mode .start-area {
  padding: 12px 0;
}

.line-mode .recording-area {
  padding: 12px 0;
}

.line-mode .reference-text {
  margin-top: 8px;
}

/* ---------- 评测动画 ---------- */

/* 评测中加载动画 */
.evaluating-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding: 40px 0;
}

.eval-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.spinner-ring {
  width: 40px;
  height: 40px;
  border: 3px solid #e5e6eb;
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.spinner-label {
  font-size: 14px;
  color: var(--text-secondary);
}

/* 声波动画 */
.eval-waves {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 30px;
}

.wave-bar {
  width: 4px;
  background: var(--color-primary);
  border-radius: 2px;
  opacity: 0.4;
  animation: wave 0.8s ease-in-out infinite alternate;
}

@keyframes wave {
  0% { height: 6px; opacity: 0.3; }
  100% { height: 28px; opacity: 1; }
}

/* 结果卡片入场 */
.result-reveal-enter-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}
.result-reveal-enter-from {
  opacity: 0;
  transform: translateY(16px) scale(0.97);
}

/* 分数逐项交错入场 */
.score-item {
  opacity: 0;
  transform: translateX(-12px);
  transition: opacity 0.4s ease, transform 0.4s ease;
}
.score-item.score-enter {
  opacity: 1;
  transform: translateX(0);
}

/* 分数数字跳动 */
.score-value.score-pop {
  animation: scoreBounce 0.5s ease;
}

@keyframes scoreBounce {
  0% { transform: scale(1); }
  30% { transform: scale(1.25); color: var(--color-primary); }
  100% { transform: scale(1); }
}

.total-score.score-pop {
  animation: scoreBounce 0.5s ease;
}

/* 进度条平滑过渡 */
.animated-progress :deep(.el-progress-bar__inner) {
  transition: width 0.6s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.total-score small,
.score-value small {
  font-size: 12px;
  font-weight: 400;
  color: #c0c4cc;
}
</style>
