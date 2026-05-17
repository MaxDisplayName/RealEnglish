<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, reactive } from "vue";
import { useRouter } from "vue-router";
import { ArrowLeft, Plus, Delete, ChatDotRound } from "@element-plus/icons-vue";
import MarkdownIt from "markdown-it";
import hljs from "highlight.js";
import "highlight.js/styles/github.css";
import { ElMessage, ElMessageBox } from "element-plus";
import { listThreads, createThread, deleteThread, getThreadMessages } from "@/api/assistant/api";

const router = useRouter();
const threads = ref([]);
const currentThreadId = ref(null);
const sidebarOpen = ref(true);
const messages = ref([]);
const inputText = ref("");
const loading = ref(false);
const chatContainer = ref(null);
const abortController = ref(null);
const threadTitle = ref("新对话");
const timelineOpen = reactive({});
const suggestions = ref([]);
const suggestionsLoading = ref(false);

const md = new MarkdownIt({
  html: false, breaks: true, linkify: true, typographer: true,
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) return `<pre class="hljs"><code>${hljs.highlight(str, { language: lang }).value}</code></pre>`;
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`;
  },
});

const renderedMessages = computed(() =>
  messages.value.map((m) => ({ ...m, html: m.role === "assistant" ? md.render(m.content || "") : "", streaming: m._streaming || false })),
);

onMounted(async () => { await loadThreads(); const s = sessionStorage.getItem("teacher_thread_id"); if (s && threads.value.find(t => t.id === s)) selectThread(s); fetchSuggestions(); });
onBeforeUnmount(() => stopStreaming());

async function loadThreads() { try { const r = await listThreads("teacher"); threads.value = r.data.threads || []; } catch { /* */ } }
async function handleNewThread() { try { const r = await createThread("teacher"); threads.value.unshift({ id: r.data.id, title: r.data.title || "新对话" }); await selectThread(r.data.id); } catch { ElMessage.error("创建失败"); } }
async function handleDeleteThread(id) {
  try { await ElMessageBox.confirm("确定删除？", "删除确认", { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" }); await deleteThread(id); threads.value = threads.value.filter(t => t.id !== id); if (currentThreadId.value === id) { messages.value = []; currentThreadId.value = null; threadTitle.value = "新对话"; sessionStorage.removeItem("teacher_thread_id"); if (threads.value.length > 0) await selectThread(threads.value[0].id); } } catch { /* */ }
}
async function selectThread(id) {
  currentThreadId.value = id; sessionStorage.setItem("teacher_thread_id", id);
  threadTitle.value = threads.value.find(t => t.id === id)?.title || "新对话";
  messages.value = [];
  try {
    const res = await getThreadMessages(id);
    messages.value = (res.data.messages || []).map(m => ({ ...m, timestamp: new Date(), toolCalls: [] }));
    scrollToBottom();
  } catch { /* */ }
}

async function handleSendText() {
  const text = inputText.value.trim();
  if (!text || loading.value) return;
  inputText.value = "";
  if (!currentThreadId.value) await handleNewThread();

  messages.value.push({ role: "user", content: text, timestamp: new Date() });
  const aiMsg = { role: "assistant", content: "", timestamp: new Date(), toolCalls: [], _streaming: true };
  messages.value.push(aiMsg);
  const aiIdx = messages.value.length - 1;
  timelineOpen[aiIdx] = true;
  loading.value = true;
  abortController.value = new AbortController();
  scrollToBottom();

  try {
    const t = localStorage.getItem("access_token");
    const h = { "Content-Type": "application/json" };
    if (t) h.Authorization = `Bearer ${t}`;
    const resp = await fetch("/api/v1/assistants/teacher/chat/stream", {
      method: "POST", headers: h,
      body: JSON.stringify({ message: text, thread_id: currentThreadId.value }),
      signal: abortController.value.signal,
    });
    if (!resp.ok) throw new Error("连接失败");
    if (!resp.body) throw new Error("无响应流");

    const reader = resp.body.getReader();
    const dec = new TextDecoder("utf-8");
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() || "";
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const evt = JSON.parse(line);
          if (evt.type === "content") messages.value[aiIdx].content += evt.content;
          else if (evt.type === "tool_start") messages.value[aiIdx].toolCalls.push({ name: evt.tool, status: "running", startTime: Date.now() });
          else if (evt.type === "tool_end") {
            const tc = messages.value[aiIdx].toolCalls;
            for (let i = tc.length - 1; i >= 0; i--) { if (tc[i].name === evt.tool && tc[i].status === "running") { tc[i].status = "done"; tc[i].endTime = Date.now(); tc[i].output = evt.output; break; } }
          }
          else if (evt.type === "thread_id") { if (!currentThreadId.value) { currentThreadId.value = evt.thread_id; sessionStorage.setItem("teacher_thread_id", evt.thread_id); } }
          else if (evt.type === "error") messages.value[aiIdx].content += evt.message || "";
        } catch { /* */ }
      }
      messages.value[aiIdx]._streaming = messages.value[aiIdx].content === "" && messages.value[aiIdx].toolCalls.length === 0;
      scrollToBottom();
    }
  } catch (e) {
    if (e.name !== "AbortError") { ElMessage.error("AI 服务暂时不可用"); messages.value[aiIdx].content = messages.value[aiIdx].content || "抱歉，连接出现问题。"; }
  } finally {
    loading.value = false; messages.value[aiIdx]._streaming = false; abortController.value = null; await loadThreads();
  }
}

function stopStreaming() { if (abortController.value) { abortController.value.abort(); abortController.value = null; loading.value = false; } }
function scrollToBottom() { nextTick(() => { if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight; }); }
async function fetchSuggestions() {
  const cacheKey = "assistant_suggestions_teacher";
  const cached = sessionStorage.getItem(cacheKey);
  if (cached) {
    try { suggestions.value = JSON.parse(cached); } catch { /* */ }
    return;
  }
  suggestionsLoading.value = true;
  try {
    const token = localStorage.getItem("access_token");
    const resp = await fetch("/api/v1/assistants/teacher/suggestions", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: "{}",
    });
    if (resp.ok) {
      const json = await resp.json();
      suggestions.value = json.data?.suggestions || [];
      if (suggestions.value.length > 0) {
        sessionStorage.setItem(cacheKey, JSON.stringify(suggestions.value));
      }
    }
  } catch { /* silent */ }
  finally { suggestionsLoading.value = false; }
}
function useSuggestion(text) {
  inputText.value = text;
  handleSendText();
}
function refreshSuggestions() {
  sessionStorage.removeItem("assistant_suggestions_teacher");
  suggestions.value = [];
  fetchSuggestions();
}
function handleKeydown(e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSendText(); } }
function toggleSidebar() { sidebarOpen.value = !sidebarOpen.value; }
function copyContent(msg) { navigator.clipboard.writeText(msg.content).then(() => ElMessage.success("已复制")); }

const editingIdx = ref(-1), editText = ref("");
function startEdit(idx) { editingIdx.value = idx; editText.value = messages.value[idx].content; }
function cancelEdit() { editingIdx.value = -1; editText.value = ""; }
async function submitEdit() { if (!editText.value.trim()) return; messages.value.splice(editingIdx.value); const text = editText.value; cancelEdit(); inputText.value = text; await handleSendText(); }
async function regenerateMsg(aiIdx) { let u = -1; for (let i = aiIdx - 1; i >= 0; i--) { if (messages.value[i].role === "user") { u = i; break; } } if (u < 0) return; const t = messages.value[u].content; messages.value.splice(u); inputText.value = t; await nextTick(); await handleSendText(); }
function formatMs(s, e) { return e && s ? ((e - s) / 1000).toFixed(1) + "s" : ""; }

const CopyIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;
const EditIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`;
const RefreshIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><polyline points="23 20 23 14 17 14"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/></svg>`;
</script>

<template>
  <div class="assistant-page">
    <aside class="sidebar" :class="{ collapsed: !sidebarOpen }">
      <div class="sidebar-hd"><el-button :icon="Plus" size="small" type="primary" @click="handleNewThread">新建对话</el-button></div>
      <div class="thread-list">
        <div v-for="t in threads" :key="t.id" class="thread-item" :class="{ active: t.id === currentThreadId }" @click="selectThread(t.id)">
          <span class="t-icon"><ChatDotRound /></span>
          <span class="t-title">{{ t.title }}</span>
          <el-button class="t-del" :icon="Delete" size="small" text @click.stop="handleDeleteThread(t.id)" />
        </div>
        <div v-if="threads.length === 0" class="t-empty">暂无对话</div>
      </div>
    </aside>

    <main class="chat-main">
      <div class="chat-hd">
        <div class="hd-left">
          <button class="hd-toggle" @click="toggleSidebar">{{ sidebarOpen ? '◀' : '▶' }}</button>
          <el-button size="small" :icon="ArrowLeft" text @click="router.push('/teacher')">返回</el-button>
        </div>
        <div class="hd-title">{{ threadTitle }}</div>
      </div>

      <div ref="chatContainer" class="chat-body">
        <div v-if="messages.length === 0 && !loading" class="chat-empty">
          <div class="empty-icon"><ChatDotRound style="font-size:32px;color:#E6A23C" /></div>
          <h3>教师管理助手</h3>
          <p>帮你查看学生列表、等级分布、生成学习报告</p>

          <div v-if="suggestionsLoading" class="suggestion-loading">
            <div class="s-skel" /><div class="s-skel" /><div class="s-skel" /><div class="s-skel" />
          </div>

          <div v-else-if="suggestions.length > 0" class="suggestions">
            <div class="suggestions-header">
              <span class="suggestions-label">试试这些</span>
              <button class="suggestions-refresh" title="换一批" @click="refreshSuggestions">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                <span>换一批</span>
              </button>
            </div>
            <div class="suggestion-list">
              <div
                v-for="(s, i) in suggestions"
                :key="i"
                class="suggestion-chip"
                :style="{ animationDelay: `${i * 0.06}s` }"
                @click="useSuggestion(s)"
              >{{ s }}</div>
            </div>
          </div>
        </div>

        <div v-for="(msg, idx) in renderedMessages" :key="idx" class="msg-wrapper" :class="'role-' + msg.role">
          <div class="msg-row" :class="'role-' + msg.role">
            <div class="msg-avatar">{{ msg.role === "user" ? "我" : "AI" }}</div>
            <div class="msg-bubble">
              <div v-if="msg.streaming && !msg.content && (!msg.toolCalls || msg.toolCalls.length === 0)" class="streaming-indicator">
                <span class="dot-pulse"><span /><span /><span /></span>
              </div>
              <div v-if="msg.role === 'assistant' && msg.toolCalls && msg.toolCalls.length > 0" class="tool-timeline">
                <div class="tl-header" @click="timelineOpen[idx] = !timelineOpen[idx]">
                  <span class="tl-caret">{{ timelineOpen[idx] !== false ? '▾' : '▸' }}</span>
                  <span class="tl-title">工具调用</span>
                  <span class="tl-count">{{ msg.toolCalls.filter(t => t.status === 'done').length }}/{{ msg.toolCalls.length }}</span>
                </div>
                <div v-show="timelineOpen[idx] !== false" class="tl-body">
                  <div v-for="(tc, i) in msg.toolCalls" :key="i" class="tl-item" :class="{ done: tc.status === 'done' }">
                    <div class="tl-dot"><span v-if="tc.status === 'running'" class="spin" /><span v-else>✓</span></div>
                    <div class="tl-info">
                      <div class="tl-name">{{ tc.name }}</div>
                      <div v-if="tc.output" class="tl-out">{{ tc.output.substring(0, 80) }}{{ tc.output.length > 80 ? '...' : '' }}</div>
                    </div>
                    <div class="tl-time">{{ tc.status === 'running' ? '运行中' : formatMs(tc.startTime, tc.endTime) }}</div>
                  </div>
                </div>
              </div>
              <div v-if="msg.role === 'assistant' && msg.content" class="bubble-content markdown-body" v-html="msg.html" />
              <div v-else-if="editingIdx === idx" class="edit-area">
                <el-input v-model="editText" type="textarea" :rows="2" @keydown.ctrl.enter="submitEdit" @keydown.escape="cancelEdit" />
                <div class="edit-btns"><el-button size="small" text @click="cancelEdit">取消</el-button><el-button size="small" type="primary" @click="submitEdit">保存并重发</el-button></div>
              </div>
              <div v-else-if="msg.role === 'user'" class="bubble-content">{{ msg.content }}</div>
            </div>
          </div>
          <div v-if="msg.content && editingIdx !== idx" class="msg-actions">
            <button class="act-btn" v-html="CopyIcon + ' 复制'" @click="copyContent(msg)" />
            <button v-if="msg.role === 'user'" class="act-btn" v-html="EditIcon + ' 编辑'" @click="startEdit(idx)" />
            <button v-if="msg.role === 'assistant'" class="act-btn" v-html="RefreshIcon + ' 重新生成'" @click="regenerateMsg(idx)" />
          </div>
        </div>

      </div>

      <div class="chat-input">
        <el-input v-model="inputText" type="textarea" :rows="2" placeholder="输入你的问题..." :disabled="loading" resize="none" @keydown="handleKeydown" />
        <el-button type="primary" :loading="loading" :disabled="!inputText.trim()" @click="handleSendText">发送</el-button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.assistant-page { display: flex; height: calc(100vh - 56px - 40px); overflow: hidden; }
.sidebar { width: 260px; min-width: 260px; display: flex; flex-direction: column; background: linear-gradient(180deg, #FEF9F2, #FDF4E8); border-right: 1px solid rgba(230,162,60,.12); transition: all .3s cubic-bezier(.4,0,.2,1); overflow: hidden; }
.sidebar.collapsed { width: 0; min-width: 0; border-right: none; }
.sidebar-hd { padding: 16px 14px 12px; }
.sidebar-hd .el-button { width: 100%; }
.thread-list { flex: 1; overflow-y: auto; padding: 6px 8px; }
.thread-item { display: flex; align-items: center; gap: 10px; padding: 11px 14px; border-radius: 10px; cursor: pointer; margin-bottom: 2px; transition: all .2s; position: relative; }
.thread-item::before { content: ''; position: absolute; left: 0; top: 50%; transform: translateY(-50%); width: 3px; height: 0; background: #E6A23C; border-radius: 0 3px 3px 0; transition: height .2s; }
.thread-item:hover { background: rgba(255,255,255,.6); }
.thread-item.active { background: #fff; box-shadow: 0 1px 4px rgba(230,162,60,.12); }
.thread-item.active::before { height: 60%; }
.t-icon { color: rgba(75,75,75,.3); font-size: 15px; flex-shrink: 0; transition: color .2s; }
.thread-item.active .t-icon { color: #E6A23C; }
.t-title { flex: 1; font-size: 13px; color: #5A5A5A; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
.thread-item.active .t-title { color: #3A3A3A; font-weight: 600; }
.t-del { opacity: 0; transition: opacity .2s; }
.thread-item:hover .t-del { opacity: .7; }
.t-empty { padding: 32px 20px; text-align: center; font-size: 13px; color: rgba(75,75,75,.25); }

.chat-main { flex: 1; display: flex; flex-direction: column; min-width: 0; background: #fff; }
.chat-hd { display: flex; align-items: center; gap: 12px; padding: 12px 20px; border-bottom: 1px solid rgba(0,0,0,.06); flex-shrink: 0; }
.hd-left { display: flex; align-items: center; gap: 6px; }
.hd-toggle { background: none; border: none; cursor: pointer; font-size: 10px; color: rgba(75,75,75,.4); padding: 6px 8px; border-radius: 6px; transition: all .2s; }
.hd-toggle:hover { color: #E6A23C; background: rgba(230,162,60,.05); }
.hd-title { font-size: 14px; font-weight: 600; color: #333; }

.chat-body { flex: 1; overflow-y: auto; padding: 20px 24px; background: radial-gradient(ellipse at 50% 0%, rgba(230,162,60,.015), transparent 60%), #fff; }
.chat-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; }
.chat-empty .empty-icon { width: 80px; height: 80px; border-radius: 20px; background: linear-gradient(135deg, rgba(230,162,60,.1), rgba(230,162,60,.03)); display: flex; align-items: center; justify-content: center; margin-bottom: 20px; animation: float 3s ease-in-out infinite; }
@keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }
.chat-empty h3 { font-size: 20px; font-weight: 700; color: #3A3A3A; margin: 0 0 8px; }
.chat-empty p { font-size: 14px; color: rgba(75,75,75,.45); max-width: 320px; line-height: 1.8; }

.msg-wrapper { margin-bottom: 20px; animation: msgIn .35s cubic-bezier(.16,1,.3,1); }
.msg-wrapper.role-user { display: flex; flex-direction: column; align-items: flex-end; }
@keyframes msgIn { from{opacity:0;transform:translateY(12px) scale(.98)} to{opacity:1;transform:translateY(0) scale(1)} }

.msg-row { display: flex; gap: 12px; }
.msg-row.role-user { flex-direction: row-reverse; }
.msg-avatar { width: 36px; height: 36px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; flex-shrink: 0; box-shadow: 0 2px 6px rgba(0,0,0,.08); }
.role-ai .msg-avatar { background: linear-gradient(135deg, #E6A23C, #D4942E); color: #fff; }
.role-user .msg-avatar { background: linear-gradient(135deg, #4F46E5, #3D35D0); color: #fff; }
.msg-bubble { max-width: 100%; padding: 12px 16px; border-radius: 16px; font-size: 14.5px; line-height: 1.75; letter-spacing: .01em; }
.role-ai .msg-bubble { background: #FDF8F0; color: #3A3A3A; border-bottom-left-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
.role-user .msg-bubble { background: linear-gradient(135deg, #4F46E5, #3D35D0); color: #fff; border-bottom-right-radius: 6px; box-shadow: 0 2px 8px rgba(79,70,229,.3); }

.streaming-indicator { padding: 4px 0; }
.dot-pulse { display: inline-flex; gap: 5px; align-items: center; padding: 6px 2px; }
.dot-pulse span { width: 7px; height: 7px; border-radius: 50%; background: rgba(75,75,75,.25); animation: dotBounce 1.4s infinite ease-in-out; }
.dot-pulse span:nth-child(2) { animation-delay: .16s; }
.dot-pulse span:nth-child(3) { animation-delay: .32s; }
@keyframes dotBounce { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-7px)} }

.msg-actions { display: flex; gap: 6px; margin-top: 6px; padding: 0 4px; }
.role-user.msg-wrapper .msg-actions { justify-content: flex-end; }
.act-btn { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border: none; border-radius: 8px; background: transparent; color: rgba(75,75,75,.35); font-size: 12px; font-weight: 500; cursor: pointer; transition: all .15s; font-family: inherit; }
.act-btn:hover { color: #E6A23C; background: rgba(230,162,60,.06); }

.edit-area { display: flex; flex-direction: column; gap: 6px; }
.edit-area :deep(.el-textarea__inner) { font-size: 14px; }
.edit-btns { display: flex; gap: 4px; justify-content: flex-end; }

.chat-input { display: flex; gap: 10px; padding: 14px 20px; border-top: 1px solid rgba(0,0,0,.06); flex-shrink: 0; background: rgba(255,255,255,.98); }
.chat-input :deep(.el-textarea__inner) { border-radius: 12px !important; background: #F5F5F7 !important; border: 2px solid transparent !important; font-size: 14px; padding: 10px 14px; transition: all .2s; }
.chat-input :deep(.el-textarea__inner:focus) { border-color: #E6A23C !important; background: #fff !important; box-shadow: 0 0 0 3px rgba(230,162,60,.08) !important; }
.chat-input .el-button { width: 80px; flex-shrink: 0; min-height: 44px; border-radius: 12px; }

.bubble-content { word-break: break-word; }
.markdown-body :deep(p) { margin: 0 0 10px; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(pre) { overflow-x: auto; padding: 14px; border-radius: 10px; margin: 10px 0; font-size: 13px; background: #F0F0F3; }
.markdown-body :deep(code) { font-family: 'JetBrains Mono', Consolas, Monaco, monospace; font-size: .88em; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { padding-left: 20px; margin: 8px 0; }
.markdown-body :deep(a) { color: #2f76ff; }
.markdown-body :deep(blockquote) { margin: 10px 0; padding: 6px 14px; border-left: 3px solid #E6A23C; background: rgba(230,162,60,.06); border-radius: 0 6px 6px 0; color: #6B6B6B; }
.markdown-body :deep(table) { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 13.5px; border-radius: 8px; overflow: hidden; }
.markdown-body :deep(th) { background: #FDF8F0; border: 1px solid #EDE0CC; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; }
.markdown-body :deep(td) { border: 1px solid #EDE0CC; padding: 10px 14px; }
.markdown-body :deep(tr:nth-child(even) td) { background: rgba(230,162,60,.02); }

.tool-timeline { margin-bottom: 14px; border: 1px solid rgba(230,162,60,.15); border-radius: 10px; overflow: hidden; font-size: 12.5px; background: rgba(230,162,60,.02); }
.tl-header { display: flex; align-items: center; gap: 8px; padding: 9px 14px; background: rgba(230,162,60,.05); cursor: pointer; user-select: none; transition: background .15s; }
.tl-header:hover { background: rgba(230,162,60,.1); }
.tl-caret { font-size: 10px; color: rgba(75,75,75,.35); width: 14px; }
.tl-title { font-weight: 600; color: #8B6914; font-size: 12px; letter-spacing: .03em; text-transform: uppercase; }
.tl-count { font-size: 11px; color: rgba(75,75,75,.4); margin-left: auto; font-variant-numeric: tabular-nums; }
.tl-body { border-top: 1px solid rgba(230,162,60,.08); }
.tl-item { display: flex; align-items: flex-start; gap: 12px; padding: 10px 14px; border-bottom: 1px solid rgba(0,0,0,.03); }
.tl-item:last-child { border-bottom: none; }
.tl-dot { width: 20px; height: 20px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 1px; transition: all .3s; }
.tl-item.done .tl-dot { background: linear-gradient(135deg, #FEF0D6, #FCE4B8); color: #D4942E; font-size: 11px; font-weight: 700; box-shadow: 0 1px 3px rgba(230,162,60,.2); }
.tl-item:not(.done) .tl-dot { background: linear-gradient(135deg, #FEF9F2, #FDF4E8); box-shadow: 0 1px 4px rgba(230,162,60,.15); }
.tl-info { flex: 1; min-width: 0; }
.tl-name { font-weight: 600; color: #4A4A4A; font-family: 'JetBrains Mono', Consolas, Monaco, monospace; font-size: 11.5px; }
.tl-out { font-size: 11.5px; color: rgba(75,75,75,.5); margin-top: 2px; line-height: 1.5; word-break: break-all; }
.tl-time { font-size: 10.5px; color: rgba(75,75,75,.3); flex-shrink: 0; margin-top: 2px; font-variant-numeric: tabular-nums; }
.tl-dot .spin { display: inline-block; width: 11px; height: 11px; border: 2px solid rgba(230,162,60,.2); border-top-color: #E6A23C; border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to{transform:rotate(360deg)} }

/* ════ Suggestions ════ */
.suggestion-loading { margin-top: 28px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; max-width: 440px; width: 100%; }
.s-skel { height: 44px; border-radius: 14px; background: linear-gradient(90deg, #f5f0e8 25%, #efe8dc 50%, #f5f0e8 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

.suggestions { margin-top: 32px; width: 100%; max-width: 440px; }
.suggestions-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.suggestions-label { font-size: 11.5px; color: rgba(75,75,75,.30); letter-spacing: .06em; font-weight: 500; }
.suggestions-refresh {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px; border: none; border-radius: 8px;
  background: transparent; color: rgba(75,75,75,.25);
  font-size: 11px; cursor: pointer; transition: all .2s;
  font-family: inherit; letter-spacing: .03em;
}
.suggestions-refresh:hover { color: #E6A23C; background: rgba(230,162,60,.06); }
.suggestions-refresh:active { transform: scale(.95); }
.suggestions-refresh svg { transition: transform .35s cubic-bezier(.4,0,.2,1); }
.suggestions-refresh:hover svg { transform: rotate(180deg); }

.suggestion-list { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.suggestion-chip {
  padding: 12px 16px;
  border-radius: 14px;
  background: rgba(230,162,60,.05);
  border: 1px solid rgba(230,162,60,.12);
  color: #8B6914;
  font-size: 13px;
  cursor: pointer;
  transition: all .22s cubic-bezier(.4,0,.2,1);
  text-align: center;
  line-height: 1.45;
  box-shadow: 0 1px 2px rgba(0,0,0,.02);
  animation: chipIn .4s cubic-bezier(.16,1,.3,1) both;
  word-break: break-word;
}
@keyframes chipIn { from { opacity: 0; transform: translateY(8px) scale(.96); } to { opacity: 1; transform: translateY(0) scale(1); } }
.suggestion-chip:hover {
  background: rgba(230,162,60,.12);
  border-color: rgba(230,162,60,.32);
  box-shadow: 0 4px 14px rgba(230,162,60,.14);
  transform: translateY(-1px);
}
.suggestion-chip:active { transform: scale(.97); }

@media (max-width:768px) { .sidebar{width:0;min-width:0} .sidebar.collapsed{width:260px;min-width:260px} .msg-bubble{max-width:95%} }
</style>
