<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import MarkdownIt from "markdown-it";
import hljs from "highlight.js";
import "highlight.js/styles/github.css";
import { ArrowLeft, ArrowRight, Delete, Promotion, VideoPause } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

import { useSpeech } from "@/composables/useSpeech";

const { speakText, stopSpeaking } = useSpeech();
const router = useRouter();

const messages = ref([]);
const inputText = ref("");
const loading = ref(false);
const chatContainer = ref(null);
const streamController = ref(null);

const quickQuestions = [
  "Can you help me practice English?",
  "What does 'break a leg' mean?",
  "How can I improve my pronunciation?",
  "Please correct my grammar: 'I goes to school'",
];

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
  typographer: true,
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return `<pre class="hljs"><code>${hljs.highlight(str, { language: lang }).value}</code></pre>`;
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`;
  },
});

const renderedMessages = computed(() =>
  messages.value.map((message) => ({
    ...message,
    html:
      message.role === "assistant" && message.renderAsMarkdown
        ? md.render(message.content || "")
        : "",
  })),
);

onUnmounted(() => {
  stopSpeaking();
  stopStreaming();
});

onMounted(() => {
  messages.value.push({
    role: "assistant",
    content:
      "你好！我是你的 RealEnglish 英语教练。\n\n" +
      "我支持：\n" +
      "- 英语对话练习\n" +
      "- Markdown 格式回复\n" +
      "- 语法纠正与表达润色\n" +
      "- 对影视台词和地道表达的讲解\n\n" +
      "今天想从什么开始？",
    renderAsMarkdown: true,
    timestamp: new Date(),
  });
});

async function sendMessage() {
  const text = inputText.value.trim();
  if (!text || loading.value) return;

  inputText.value = "";
  messages.value.push({
    role: "user",
    content: text,
    timestamp: new Date(),
  });

  const assistantMessage = {
    role: "assistant",
    content: "",
    renderAsMarkdown: true,
    timestamp: new Date(),
  };
  messages.value.push(assistantMessage);

  loading.value = true;
  const assistantIndex = messages.value.length - 1;
  const history = messages.value
    .slice(0, -2)
    .map((message) => ({ role: message.role, content: message.content }));

  streamController.value = new AbortController();

  try {
    const token = localStorage.getItem("access_token");
    const headers = { "Content-Type": "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;

    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || "/api/v1"}/chat/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify({ message: text, history }),
      signal: streamController.value.signal,
    });

    if (!response.ok) throw new Error("连接流式服务失败");
    if (!response.body) throw new Error("浏览器未返回可读取的流式响应");

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      messages.value[assistantIndex].content += decoder.decode(value, { stream: true });
      scrollToBottom();
    }
  } catch (error) {
    if (error.name !== "AbortError") {
      ElMessage.error("AI 服务暂时不可用，请稍后重试");
      messages.value[assistantIndex].content =
        messages.value[assistantIndex].content || "抱歉，我现在连接有些问题，请稍后再试。";
    }
  } finally {
    loading.value = false;
    streamController.value = null;
    scrollToBottom();
  }
}

function stopStreaming() {
  if (streamController.value) {
    streamController.value.abort();
    streamController.value = null;
    loading.value = false;
  }
}

function handleQuickQuestion(question) {
  inputText.value = question;
  sendMessage();
}

function handleSpeak(text) {
  stopSpeaking();
  speakText(text, "female", "en-US", 0.85);
}

function clearChat() {
  stopStreaming();
  messages.value = [
    {
      role: "assistant",
      content: "你好！我是你的 RealEnglish 英语教练。今天你想练习什么？",
      renderAsMarkdown: true,
      timestamp: new Date(),
    },
  ];
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
    sendMessage();
  }
}
</script>

<template>
  <div class="ai-chat-page">
    <div class="chat-container">
      <div class="chat-header">
        <div class="header-info">
          <el-button size="small" :icon="ArrowLeft" text @click="router.back()" style="margin-right:4px">返回</el-button>
          <img src="/assets/ai-chat.svg" alt="" class="header-illustration" />
          <div>
            <h2>AI 英语教练</h2>
            <span class="header-status">
              <span class="status-dot" />
              {{ loading ? "生成中..." : "在线" }}
            </span>
          </div>
        </div>
        <div class="header-actions">
          <el-button v-if="loading" size="small" :icon="VideoPause" text @click="stopStreaming">
            停止生成
          </el-button>
          <el-button size="small" :icon="Delete" text @click="clearChat">
            清空对话
          </el-button>
        </div>
      </div>

      <div ref="chatContainer" class="chat-messages">
        <div v-for="(msg, idx) in renderedMessages" :key="idx" class="message-row" :class="'role-' + msg.role">
          <div class="avatar">
            {{ msg.role === "user" ? "我" : "AI" }}
          </div>
          <div class="message-bubble">
            <div v-if="msg.role === 'assistant' && msg.renderAsMarkdown" class="bubble-content markdown-body"
              v-html="msg.html" />
            <div v-else class="bubble-content streaming-text">
              {{ msg.content }}
            </div>
            <div class="bubble-actions">
              <span class="msg-time">{{ msg.timestamp ? msg.timestamp.toLocaleTimeString() : "" }}</span>
              <el-button v-if="msg.role === 'assistant' && msg.content" size="small" text :icon="Promotion"
                @click="handleSpeak(msg.content)">
                朗读
              </el-button>
            </div>
          </div>
        </div>

        <div v-if="messages.length <= 2 && !loading" class="quick-questions">
          <p class="quick-title">快速开始：</p>
          <div class="quick-grid">
            <el-button v-for="(q, idx) in quickQuestions" :key="idx" class="quick-btn" @click="handleQuickQuestion(q)">
              {{ q }}
            </el-button>
          </div>
        </div>
      </div>

      <div class="chat-input">
        <el-input v-model="inputText" type="textarea" :rows="2" placeholder="输入你想练习的英语内容，支持让 AI 输出 Markdown..."
          :disabled="loading" @keydown="handleKeydown" resize="none" />
        <el-button type="primary" :icon="ArrowRight" :loading="loading" :disabled="!inputText.trim()"
          @click="sendMessage" class="send-btn">
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-chat-page {
  max-width: 840px;
  margin: 0 auto;
  height: calc(100vh - 56px - 48px);
  display: flex;
  flex-direction: column;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid #f0f2f5;
  flex-shrink: 0;
}

.header-info { display: flex; align-items: center; gap: 10px; }
.header-illustration { width: 40px; height: auto; }

.header-actions {
  display: flex;
  gap: 8px;
}

.header-info h2 {
  font-size: 16px;
  color: var(--text-main);
}

.header-status {
  font-size: 12px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-blue);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.message-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  animation: msgIn 0.3s ease;
}

@keyframes msgIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-row.role-user {
  flex-direction: row-reverse;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}

.role-assistant .avatar {
  background: var(--color-primary);
  color: #fff;
}

.role-user .avatar {
  background: var(--color-blue);
  color: #fff;
}

.message-bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
}

.role-assistant .message-bubble {
  background: var(--bg-surface);
  color: var(--text-main);
  border-bottom-left-radius: 4px;
}

.role-user .message-bubble {
  background: var(--color-primary);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.bubble-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.msg-time {
  font-size: 11px;
  color: var(--text-light);
}

.quick-questions {
  margin-top: 16px;
  text-align: center;
}

.quick-title {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.quick-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.quick-btn {
  font-size: 12px;
}

.chat-input {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #f0f2f5;
  align-items: flex-end;
}

.chat-input :deep(.el-textarea__inner) {
  border-radius: 8px;
  font-size: 14px;
}

.send-btn {
  height: 56px;
  width: 80px;
  flex-shrink: 0;
}

.streaming-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.markdown-body :deep(p) {
  margin: 0 0 10px;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(pre) {
  overflow-x: auto;
  padding: 12px;
  border-radius: 8px;
  margin: 10px 0;
}

.markdown-body :deep(code) {
  font-family: Consolas, Monaco, monospace;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.markdown-body :deep(a) {
  color: #2f76ff;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
  font-size: 14px;
}
.markdown-body :deep(th) {
  background: var(--bg-surface, #F7F7F7);
  border: 1px solid var(--border-color, #E5E5E5);
  padding: 8px 12px;
  text-align: left;
  font-weight: 700;
}
.markdown-body :deep(td) {
  border: 1px solid var(--border-color, #E5E5E5);
  padding: 8px 12px;
}
.markdown-body :deep(tr:nth-child(even) td) {
  background: rgba(0,0,0,0.02);
}

@media (max-width: 640px) {
  .message-bubble {
    max-width: 88%;
  }
}
</style>
