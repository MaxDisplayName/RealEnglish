<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { ArrowLeft, Promotion, ArrowRight, Microphone, Delete } from "@element-plus/icons-vue";
import { useRecorder } from "@/composables/useRecorder";
import { useSpeech } from "@/composables/useSpeech";
import {
  startFreeTalk,
  respondFreeTalk,
  respondFreeTalkWithVoice,
  endFreeTalk,
  getFreeTalkHistory,
} from "@/modules/student/api";

const router = useRouter();
const { isRecording, startRecording, stopRecording } = useRecorder();
const { speakText, stopSpeaking } = useSpeech();

// 状态: idle / active / ended
const state = ref("idle");
const conversation = ref(null);
const messages = ref([]);
const inputText = ref("");
const loading = ref(false);
const submitting = ref(false);
const evaluation = ref(null);
const chatContainer = ref(null);

const inputMode = ref("text"); // text / voice
const recordingPending = ref(false);

const isActive = computed(() => state.value === "active");
const isEnded = computed(() => state.value === "ended");

onMounted(() => {
  // 从 storage 尝试恢复对话
  const savedId = sessionStorage.getItem("free_talk_id");
  if (savedId) {
    restoreConversation(savedId);
  }
});

onUnmounted(() => {
  stopSpeaking();
});

async function restoreConversation(id) {
  try {
    const res = await getFreeTalkHistory(id);
    conversation.value = res.data.conversation;
    messages.value = res.data.messages || [];
    if (conversation.value.status === "active") {
      state.value = "active";
    } else if (conversation.value.status === "completed") {
      state.value = "ended";
      evaluation.value = conversation.value.evaluation_json;
    }
    scrollToBottom();
  } catch {
    sessionStorage.removeItem("free_talk_id");
  }
}

async function handleStart() {
  loading.value = true;
  try {
    const res = await startFreeTalk();
    conversation.value = res.data;
    messages.value = [
      { role: "ai", content: res.data.first_message },
    ];
    sessionStorage.setItem("free_talk_id", res.data.conversation_id);
    state.value = "active";
    await nextTick();
    scrollToBottom();
    // 自动朗读第一条消息
    autoSpeak(res.data.first_message);
  } catch {
    ElMessage.error("生成话题失败，请稍后重试");
  } finally {
    loading.value = false;
  }
}

async function handleSendText() {
  const text = inputText.value.trim();
  if (!text || loading.value) return;
  inputText.value = "";

  const userMsg = { role: "user", content: text };
  messages.value.push(userMsg);
  loading.value = true;
  await nextTick();
  scrollToBottom();

  try {
    const res = await respondFreeTalk(conversation.value.conversation_id, text);
    messages.value.push({ role: "ai", content: res.data.reply });
    await nextTick();
    scrollToBottom();
    autoSpeak(res.data.reply);
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "发送失败");
  } finally {
    loading.value = false;
  }
}

async function handleVoiceToggle() {
  if (isRecording.value) {
    // 停止录音
    recordingPending.value = false;
    try {
      const blob = await stopRecording();
      if (blob.size < 100) {
        ElMessage.warning("录音太短，请重试");
        return;
      }
      await submitVoice(blob);
    } catch (e) {
      if (e.message) ElMessage.error(e.message);
    }
  } else {
    // 开始录音
    try {
      await startRecording();
      recordingPending.value = true;
    } catch (e) {
      ElMessage.error(e.message || "无法访问麦克风");
    }
  }
}

async function submitVoice(audioBlob) {
  loading.value = true;
  try {
    const res = await respondFreeTalkWithVoice(
      conversation.value.conversation_id,
      audioBlob,
    );
    const transcript = res.data.transcript || "";
    messages.value.push({ role: "user", content: transcript, voice: true });
    await nextTick();
    scrollToBottom();

    messages.value.push({ role: "ai", content: res.data.reply });
    await nextTick();
    scrollToBottom();
    autoSpeak(res.data.reply);
  } catch (e) {
    if (e.response?.data?.code === 400) {
      ElMessage.warning("未识别到有效语音，请重试");
    } else {
      ElMessage.error(e.response?.data?.detail || "发送失败");
    }
  } finally {
    loading.value = false;
  }
}

async function handleEndConversation() {
  if (messages.value.filter((m) => m.role === "user").length === 0) {
    ElMessage.warning("请至少发言一次再结束对话");
    return;
  }
  submitting.value = true;
  try {
    const res = await endFreeTalk(conversation.value.conversation_id);
    evaluation.value = res.data.evaluation;
    state.value = "ended";
    sessionStorage.removeItem("free_talk_id");
    await nextTick();
    scrollToBottom();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "评测失败，请稍后重试");
  } finally {
    submitting.value = false;
  }
}

function handleNewRound() {
  stopSpeaking();
  conversation.value = null;
  messages.value = [];
  evaluation.value = null;
  inputText.value = "";
  state.value = "idle";
  sessionStorage.removeItem("free_talk_id");
}

function handleSpeak(text) {
  stopSpeaking();
  speakText(text, "female", "en-US", 0.85);
}

function autoSpeak(text) {
  // 仅在新消息时自动朗读
  if (text && text.length < 500) {
    handleSpeak(text);
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
    }
  });
}

function handleKeydown(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    handleSendText();
  }
}

function scorePercent(val) {
  return Math.round((val / 10) * 100);
}

const scoreLabels = {
  participation: "参与完成度",
  grammar: "语法准确性",
  vocabulary: "词汇丰富度",
  fluency: "表达流畅度",
};
</script>

<template>
  <div class="free-talk-page">
    <!-- Header -->
    <div class="ft-header">
      <div class="header-left">
        <el-button size="small" :icon="ArrowLeft" text @click="router.push('/student')">返回</el-button>
        <h2 v-if="state === 'idle'">情景式自由对话</h2>
        <h2 v-else-if="conversation">{{ conversation.topic }}</h2>
      </div>
      <div class="header-right">
        <el-button
          v-if="isActive"
          type="warning"
          size="small"
          :loading="submitting"
          @click="handleEndConversation"
        >
          结束对话并评测
        </el-button>
      </div>
    </div>

    <!-- 对话内容区 -->
    <div class="ft-body">
      <!-- Idle 状态: 开始面板 -->
      <div v-if="state === 'idle'" class="start-panel">
        <div class="start-card">
          <div class="start-icon">
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
              <rect width="64" height="64" rx="16" fill="#58CC02" opacity="0.12" />
              <path d="M24 20v24l20-12L24 20z" fill="#58CC02" />
            </svg>
          </div>
          <h3>情景式自由对话</h3>
          <p class="start-desc">
            AI 将为你生成一个真实的生活场景，并扮演一个角色与你进行英语对话。
            你可以使用文字或语音进行回复，对话结束后 AI 会给出综合评测。
          </p>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleStart"
            class="start-btn"
          >
            <el-icon style="margin-right: 6px"><Promotion /></el-icon>
            开始对话
          </el-button>
        </div>
      </div>

      <!-- Active / Ended 状态: 聊天区域 -->
      <div
        v-else
        ref="chatContainer"
        class="chat-area"
      >
        <!-- 场景提示 -->
        <div v-if="conversation?.scenario" class="scenario-banner">
          <el-alert
            :title="'场景：' + conversation.scenario"
            type="info"
            :closable="false"
            show-icon
          >
            <template #default>
              <p class="scenario-text">
                你扮演 {{ conversation.user_role_name || '你自己' }}，AI 扮演 {{ conversation.ai_role_name || 'AI' }}
              </p>
            </template>
          </el-alert>
        </div>

        <!-- 消息列表 -->
        <div v-for="(msg, idx) in messages" :key="idx" class="msg-row" :class="'msg-' + msg.role">
          <div class="msg-avatar">
            {{ msg.role === "ai" ? "AI" : "我" }}
          </div>
          <div class="msg-bubble">
            <div class="msg-content">{{ msg.content }}</div>
            <div class="msg-footer">
              <span v-if="msg.voice" class="voice-tag">
                <el-icon :size="12"><Microphone /></el-icon>
                语音
              </span>
              <el-button
                v-if="msg.role === 'ai' && msg.content"
                size="small"
                text
                :icon="Promotion"
                @click="handleSpeak(msg.content)"
              >
                朗读
              </el-button>
            </div>
          </div>
        </div>

        <!-- 加载指示器 -->
        <div v-if="loading" class="msg-row msg-ai">
          <div class="msg-avatar">AI</div>
          <div class="msg-bubble">
            <span class="typing-dots">
              <span /><span /><span />
            </span>
          </div>
        </div>

        <!-- 评测结果面板 -->
        <div v-if="evaluation" class="eval-panel">
          <el-card shadow="hover">
            <template #header>
              <div class="eval-header">
                <span>对话评测</span>
                <span class="eval-overall">{{ evaluation.overall }} / 10</span>
              </div>
            </template>

            <div class="eval-scores">
              <div v-for="(label, key) in scoreLabels" :key="key" class="eval-item">
                <div class="eval-item-header">
                  <span class="eval-label">{{ label }}</span>
                  <span class="eval-val">{{ evaluation[key] }} / 10</span>
                </div>
                <el-progress
                  :percentage="scorePercent(evaluation[key])"
                  :stroke-width="8"
                  :status="evaluation[key] >= 7 ? 'success' : 'warning'"
                />
              </div>
            </div>

            <div class="eval-summary">
              <h4>AI 总结</h4>
              <p>{{ evaluation.summary }}</p>
            </div>

            <div v-if="evaluation.suggestions?.length" class="eval-suggestions">
              <h4>改进建议</h4>
              <ul>
                <li v-for="(s, i) in evaluation.suggestions" :key="i">{{ s }}</li>
              </ul>
            </div>
          </el-card>

          <div class="eval-actions">
            <el-button type="primary" size="large" @click="handleNewRound">
              再练一次
            </el-button>
            <el-button size="large" @click="router.push('/student')">
              返回看板
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Active 状态: 输入区 -->
    <div v-if="isActive" class="ft-footer">
      <div class="input-area">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="2"
          placeholder="输入你的英语回复..."
          :disabled="loading"
          resize="none"
          @keydown="handleKeydown"
          class="text-input"
        />
        <div class="input-actions">
          <el-button
            :type="isRecording ? 'danger' : 'default'"
            :icon="Microphone"
            circle
            :class="{ recording: isRecording }"
            @click="handleVoiceToggle"
          />
          <el-button
            type="primary"
            :icon="ArrowRight"
            :loading="loading"
            :disabled="!inputText.trim()"
            @click="handleSendText"
          >
            发送
          </el-button>
        </div>
        <div v-if="isRecording" class="recording-hint">
          <span class="rec-dot" /> 录音中，再次点击麦克风停止并发送...
        </div>
      </div>
    </div>

    <!-- Ended 状态底部提示 -->
    <div v-if="isEnded" class="ft-footer ended-footer">
      <span class="ended-tip">对话已结束，查看上方评测结果</span>
    </div>
  </div>
</template>

<style scoped>
.free-talk-page {
  max-width: 780px;
  margin: 0 auto;
  height: calc(100vh - 56px - 48px);
  display: flex;
  flex-direction: column;
}

.ft-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0 16px;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-left h2 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main, #4B4B4B);
  margin: 0;
}

.header-right {
  display: flex;
  gap: 8px;
}

.ft-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ── Start Panel ── */
.start-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.start-card {
  text-align: center;
  padding: 48px 32px;
  background: #fff;
  border: 2px solid var(--border-color, #E5E5E5);
  border-radius: var(--radius-md, 16px);
  box-shadow: var(--shadow-card, 0 4px 12px rgba(0,0,0,0.06));
  max-width: 440px;
  width: 100%;
}

.start-icon {
  margin-bottom: 20px;
}

.start-card h3 {
  font-size: 20px;
  font-weight: 800;
  color: var(--text-main, #4B4B4B);
  margin: 0 0 12px;
}

.start-desc {
  font-size: 14px;
  color: var(--text-secondary, #AFAFAF);
  line-height: 1.7;
  margin: 0 0 28px;
}

.start-btn {
  font-size: 16px;
  padding: 14px 40px;
}

/* ── Chat Area ── */
.chat-area {
  flex: 1;
  overflow-y: auto;
  padding: 0 4px 20px;
}

.scenario-banner {
  margin-bottom: 16px;
}

.scenario-text {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--text-secondary, #AFAFAF);
  line-height: 1.5;
}

.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  animation: msgIn 0.3s ease;
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.msg-row.msg-user {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}

.msg-ai .msg-avatar {
  background: var(--color-primary, #58CC02);
  color: #fff;
}

.msg-user .msg-avatar {
  background: var(--color-blue, #1CB0F6);
  color: #fff;
}

.msg-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.7;
}

.msg-ai .msg-bubble {
  background: #F7F7F7;
  color: var(--text-main, #4B4B4B);
  border-bottom-left-radius: 4px;
}

.msg-user .msg-bubble {
  background: var(--color-primary, #58CC02);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.msg-content {
  white-space: pre-wrap;
  word-break: break-word;
}

.msg-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 6px;
}

.voice-tag {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  color: var(--text-light, #C2C2C2);
  background: rgba(255,255,255,0.2);
  padding: 1px 6px;
  border-radius: 10px;
}

.msg-ai .voice-tag {
  color: var(--text-secondary, #AFAFAF);
  background: rgba(0,0,0,0.05);
}

/* 打字动画 */
.typing-dots {
  display: inline-flex;
  gap: 4px;
  align-items: center;
  padding: 4px 0;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-light, #C2C2C2);
  animation: dotBounce 1.2s infinite ease-in-out;
}

.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes dotBounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-6px); }
}

/* ── Input Area ── */
.ft-footer {
  flex-shrink: 0;
  padding: 12px 0 8px;
  border-top: 1px solid #F0F2F5;
  background: #fff;
}

.input-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.text-input :deep(.el-textarea__inner) {
  border-radius: 10px;
  font-size: 14px;
  padding: 10px 14px;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
}

.recording.recording {
  animation: pulseRing 1.5s infinite;
  box-shadow: 0 0 0 0 rgba(255, 75, 75, 0.4);
}

@keyframes pulseRing {
  0% { box-shadow: 0 0 0 0 rgba(255, 75, 75, 0.4); }
  70% { box-shadow: 0 0 0 8px rgba(255, 75, 75, 0); }
  100% { box-shadow: 0 0 0 0 rgba(255, 75, 75, 0); }
}

.recording-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-danger, #FF4B4B);
}

.rec-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-danger, #FF4B4B);
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* ── Ended Footer ── */
.ended-footer {
  border: none;
  text-align: center;
}

.ended-tip {
  font-size: 13px;
  color: var(--text-light, #C2C2C2);
}

/* ── Evaluation Panel ── */
.eval-panel {
  margin-top: 24px;
  animation: slideUp 0.4s ease;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.eval-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 700;
}

.eval-overall {
  font-size: 22px;
  font-weight: 800;
  color: var(--color-primary, #58CC02);
}

.eval-scores {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 20px;
}

.eval-item-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.eval-label {
  font-size: 13px;
  color: var(--text-secondary, #AFAFAF);
}

.eval-val {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main, #4B4B4B);
}

.eval-summary {
  padding: 14px;
  background: #F0F9EB;
  border-radius: var(--radius-base, 8px);
  margin-bottom: 14px;
}

.eval-summary h4 {
  font-size: 14px;
  color: var(--color-primary, #58CC02);
  margin: 0 0 8px;
}

.eval-summary p {
  font-size: 14px;
  color: var(--text-main, #4B4B4B);
  line-height: 1.7;
  margin: 0;
}

.eval-suggestions {
  padding: 14px;
  background: #F7F7F7;
  border-radius: var(--radius-base, 8px);
}

.eval-suggestions h4 {
  font-size: 14px;
  color: var(--text-main, #4B4B4B);
  margin: 0 0 8px;
}

.eval-suggestions ul {
  margin: 0;
  padding-left: 18px;
}

.eval-suggestions li {
  font-size: 14px;
  color: var(--text-main, #4B4B4B);
  line-height: 1.8;
}

.eval-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 20px;
}

/* ── Responsive ── */
@media (max-width: 640px) {
  .msg-bubble {
    max-width: 82%;
  }
  .start-card {
    padding: 32px 20px;
  }
}
</style>
