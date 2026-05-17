<script setup>
import { ref, nextTick, onMounted, onUnmounted } from "vue";
import markdownit from "markdown-it";

const md = markdownit({ html: false, linkify: true, breaks: true });

const props = defineProps({
  clipId: { type: String, required: true },
  clipTitle: { type: String, default: "" },
});

// ── 持久化 ──
const STORE = "float_asst";
function load() { try { const r = sessionStorage.getItem(STORE); return r ? JSON.parse(r) : {}; } catch { return {}; } }
function save(s) { sessionStorage.setItem(STORE, JSON.stringify(s)); }
const sv = load();

// ── 状态 ──
const bubbleX = ref(sv.bx ?? window.innerWidth - 62);
const bubbleY = ref(sv.by ?? window.innerHeight - 180);
const cardX  = ref(sv.cx ?? Math.max(20, window.innerWidth - 410));
const cardY  = ref(sv.cy ?? Math.max(60, window.innerHeight - 530));
const isOpen = ref(sv.open ?? false);
const messages = ref([]);
const inputText = ref("");
const sending = ref(false);
const chatBody = ref(null);
const suggestions = ref([]);
const suggestionsLoading = ref(false);
let abortCtrl = null;

function persist() {
  save({ bx: bubbleX.value, by: bubbleY.value, cx: cardX.value, cy: cardY.value, open: isOpen.value });
}

// ── 拖动（闭包捕获 ref，避免模板中 ref 解包问题） ──
function makeDraggable(rx, ry) {
  let dragging = false, sx, sy, px, py;
  return {
    onDown(e) {
      if (e.target.tagName === "INPUT" || e.target.tagName === "BUTTON" || e.target.tagName === "TEXTAREA") return;
      dragging = true; sx = e.clientX; sy = e.clientY; px = rx.value; py = ry.value;
      e.preventDefault();
    },
    onMove(e) {
      if (!dragging) return;
      rx.value = Math.max(0, Math.min(window.innerWidth - 40, px + e.clientX - sx));
      ry.value = Math.max(0, Math.min(window.innerHeight - 40, py + e.clientY - sy));
    },
    onUp() {
      if (!dragging) return;
      dragging = false; persist();
    },
  };
}

const bubbleDrag = makeDraggable(bubbleX, bubbleY);
const cardDrag = makeDraggable(cardX, cardY);

onMounted(() => {
  window.addEventListener("pointermove", bubbleDrag.onMove);
  window.addEventListener("pointerup", bubbleDrag.onUp);
  window.addEventListener("pointermove", cardDrag.onMove);
  window.addEventListener("pointerup", cardDrag.onUp);
  fetchClipSuggestions();
});
onUnmounted(() => {
  window.removeEventListener("pointermove", bubbleDrag.onMove);
  window.removeEventListener("pointerup", bubbleDrag.onUp);
  window.removeEventListener("pointermove", cardDrag.onMove);
  window.removeEventListener("pointerup", cardDrag.onUp);
});

// ── 发送 ──
async function send() {
  const text = inputText.value.trim();
  if (!text || sending.value) return;
  inputText.value = "";
  messages.value.push({ role: "user", content: text });
  const aiMsg = { role: "assistant", content: "", _streaming: true };
  messages.value.push(aiMsg);
  const aiIdx = messages.value.length - 1;
  sending.value = true;
  scrollDown();

  const history = messages.value.slice(0, -1).map(m => ({ role: m.role, content: m.content }));
  try {
    abortCtrl = new AbortController();
    const token = localStorage.getItem("access_token");
    const resp = await fetch("/api/v1/assistants/student/clip-chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify({ message: text, clip_id: props.clipId, history: history.slice(-10) }),
      signal: abortCtrl.signal,
    });
    if (!resp.ok) throw new Error("请求失败");
    if (!resp.body) throw new Error("无响应");

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
          if (evt.type === "content") {
            messages.value[aiIdx].content += evt.content;
          } else if (evt.type === "done") {
            messages.value[aiIdx]._streaming = false;
          } else if (evt.type === "error") {
            messages.value[aiIdx].content = evt.message || "";
            messages.value[aiIdx]._streaming = false;
          }
        } catch { /* */ }
      }
      messages.value[aiIdx]._streaming = messages.value[aiIdx].content === "";
      scrollDown();
    }
  } catch (e) {
    if (e.name !== "AbortError") {
      messages.value[aiIdx].content = messages.value[aiIdx].content || "网络错误，请重试";
    }
  } finally {
    sending.value = false;
    messages.value[aiIdx]._streaming = false;
    abortCtrl = null;
  }
}

async function fetchClipSuggestions() {
  const cacheKey = `assistant_suggestions_clip_${props.clipId}`;
  const cached = sessionStorage.getItem(cacheKey);
  if (cached) {
    try { suggestions.value = JSON.parse(cached); } catch { /* */ }
    return;
  }
  suggestionsLoading.value = true;
  try {
    const token = localStorage.getItem("access_token");
    const resp = await fetch("/api/v1/assistants/student/clip-chat/suggestions", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify({ clip_id: props.clipId }),
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
  send();
}
function refreshClipSuggestions() {
  const cacheKey = `assistant_suggestions_clip_${props.clipId}`;
  sessionStorage.removeItem(cacheKey);
  suggestions.value = [];
  fetchClipSuggestions();
}

function scrollDown() { nextTick(() => { if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight; }); }
function onKey(e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }
function toggle() { isOpen.value = !isOpen.value; persist(); if (isOpen.value) nextTick(scrollDown); }
</script>

<template>
  <!-- 气泡 -->
  <div
    class="fab"
    :class="{ on: isOpen }"
    :style="{ left: bubbleX + 'px', top: bubbleY + 'px' }"
    @pointerdown="bubbleDrag.onDown"
    @click="toggle"
    title="片段学习助手"
  >
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <path d="M20 2H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4l4 4 4-4h4a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z"/>
      <circle cx="7.5" cy="10.5" r="1.5" fill="currentColor" opacity=".6"/>
      <circle cx="12" cy="10.5" r="1.5" fill="currentColor" opacity=".6"/>
      <circle cx="16.5" cy="10.5" r="1.5" fill="currentColor" opacity=".6"/>
    </svg>
  </div>

  <!-- 卡片 -->
  <Transition name="card">
    <div v-if="isOpen" class="card" :style="{ left: cardX + 'px', top: cardY + 'px' }">
      <div class="card-bar" @pointerdown="cardDrag.onDown">
        <span class="bar-title">{{ clipTitle ? clipTitle.slice(0, 14) : '片段助手' }}</span>
        <button class="bar-close" @click="toggle">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <div ref="chatBody" class="card-msgs">
        <div v-if="messages.length === 0" class="empty">
          <div class="empty-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#58CC02" stroke-width="1.5">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              <line x1="8" y1="9" x2="16" y2="9" stroke="#58CC02" stroke-width="1.5" opacity=".5"/>
              <line x1="8" y1="13" x2="13" y2="13" stroke="#58CC02" stroke-width="1.5" opacity=".5"/>
            </svg>
          </div>
          <p>关于这段视频中的词汇、语法、</p>
          <p>文化背景，随时问我</p>

          <div v-if="suggestionsLoading" class="s-skel-wrap">
            <div class="s-skel" /><div class="s-skel" /><div class="s-skel" />
          </div>

          <div v-else-if="suggestions.length > 0" class="suggestions">
            <div
              v-for="(s, i) in suggestions"
              :key="i"
              class="suggestion-chip"
              :style="{ animationDelay: `${i * 0.05}s` }"
              @click="useSuggestion(s)"
            >{{ s }}</div>
            <button class="suggestions-refresh" title="换一批" @click="refreshClipSuggestions">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
              <span>换一批</span>
            </button>
          </div>
        </div>

        <div v-for="(m, i) in messages" :key="i" class="msg-wrap" :class="m.role">
          <div class="msg-avatar">{{ m.role === "user" ? "我" : "AI" }}</div>
          <div class="msg-bub" :class="{ streaming: m._streaming }">
            <span v-if="m.role === 'assistant'" v-html="md.render(m.content || '')" />
            <template v-else>{{ m.content }}</template>
            <span v-if="m._streaming && !m.content" class="dot-wave"><i /><i /><i /></span>
          </div>
        </div>
      </div>

      <div class="card-foot">
        <input v-model="inputText" placeholder="输入问题..." :disabled="sending" @keydown="onKey" />
        <button class="send" :disabled="sending || !inputText.trim()" @click="send">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"/></svg>
        </button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
/* ── 气泡 ── */
.fab {
  position: fixed; z-index: 1000;
  width: 44px; height: 44px; border-radius: 50%;
  background: linear-gradient(135deg, #58CC02, #4CAF00);
  color: #fff; display: flex; align-items: center; justify-content: center;
  cursor: grab; box-shadow: 0 4px 16px rgba(88,204,2,.38);
  transition: transform .2s, box-shadow .2s;
  touch-action: none; user-select: none;
}
.fab:hover { transform: scale(1.12); box-shadow: 0 6px 22px rgba(88,204,2,.52); }
.fab:active { cursor: grabbing; }
.fab.on { background: linear-gradient(135deg, #3d8705, #306a00); }

/* ── 卡片 ── */
.card {
  position: fixed; z-index: 999;
  width: 380px; height: 500px; background: #fff;
  border-radius: 18px; box-shadow: 0 12px 40px rgba(0,0,0,.18);
  display: flex; flex-direction: column; overflow: hidden;
}
.card-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px; height: 44px;
  background: linear-gradient(135deg, #58CC02, #4CAF00);
  color: #fff; cursor: grab; user-select: none; flex-shrink: 0;
}
.card-bar:active { cursor: grabbing; }
.bar-title { font-size: 13px; font-weight: 700; }
.bar-close {
  width: 26px; height: 26px; border: none; border-radius: 50%;
  background: rgba(255,255,255,.18); color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.bar-close:hover { background: rgba(255,255,255,.32); }

/* ── 消息 ── */
.card-msgs {
  flex: 1; overflow-y: auto; padding: 14px 14px 8px;
  background: radial-gradient(ellipse at 50% 0%, rgba(88,204,2,.012) 0%, transparent 60%), #fff;
  display: flex; flex-direction: column; gap: 10px;
}
.empty { text-align: center; padding: 40px 16px; color: #AFAFAF; font-size: 13px; }
.empty-icon { width: 64px; height: 64px; border-radius: 16px; background: linear-gradient(135deg, rgba(88,204,2,.06), rgba(88,204,2,.01)); display: flex; align-items: center; justify-content: center; margin: 0 auto 14px; }
.empty p { margin: 0; }

.s-skel-wrap { margin-top: 16px; display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
.s-skel { height: 32px; width: 150px; border-radius: 12px; background: linear-gradient(90deg, #f0f0f0 25%, #e8e8e8 50%, #f0f0f0 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

.suggestions { margin-top: 16px; display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
.suggestion-chip {
  padding: 8px 14px;
  border-radius: 12px;
  background: rgba(88,204,2,.05);
  border: 1px solid rgba(88,204,2,.12);
  color: #4A7A30;
  font-size: 12px;
  cursor: pointer;
  transition: all .2s cubic-bezier(.4,0,.2,1);
  line-height: 1.4;
  text-align: center;
  animation: clipChipIn .35s cubic-bezier(.16,1,.3,1) both;
  box-shadow: 0 1px 2px rgba(0,0,0,.02);
}
@keyframes clipChipIn { from { opacity: 0; transform: translateY(6px) scale(.95); } to { opacity: 1; transform: translateY(0) scale(1); } }
.suggestion-chip:hover {
  background: rgba(88,204,2,.10);
  border-color: rgba(88,204,2,.28);
  box-shadow: 0 3px 10px rgba(88,204,2,.10);
  transform: translateY(-1px);
}
.suggestion-chip:active { transform: scale(.96); }

.suggestions-refresh {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 4px 10px; border: none; border-radius: 8px;
  background: transparent; color: rgba(75,75,75,.22);
  font-size: 10.5px; cursor: pointer; transition: all .2s;
  font-family: inherit; letter-spacing: .03em;
  width: 100%; justify-content: center; margin-top: 2px;
}
.suggestions-refresh:hover { color: #58CC02; background: rgba(88,204,2,.05); }
.suggestions-refresh:active { transform: scale(.97); }
.suggestions-refresh svg { transition: transform .35s cubic-bezier(.4,0,.2,1); }
.suggestions-refresh:hover svg { transform: rotate(180deg); }

.msg-wrap { display: flex; gap: 8px; animation: in .3s ease both; }
.msg-wrap.user { flex-direction: row-reverse; }
@keyframes in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.msg-avatar {
  width: 30px; height: 30px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; box-shadow: 0 2px 4px rgba(0,0,0,.08);
}
.msg-wrap.assistant .msg-avatar { background: linear-gradient(135deg, #58CC02, #4CAF00); color: #fff; }
.msg-wrap.user .msg-avatar { background: linear-gradient(135deg, #1CB0F6, #0E9DE0); color: #fff; }

.msg-bub {
  max-width: 82%; padding: 10px 14px; border-radius: 14px;
  font-size: 13px; line-height: 1.65; word-break: break-word;
}
.msg-wrap.assistant .msg-bub { background: #F5F5F7; color: #3A3A3A; border-bottom-left-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
.msg-wrap.user .msg-bub { background: linear-gradient(135deg, #58CC02, #4CAF00); color: #fff; border-bottom-right-radius: 4px; box-shadow: 0 2px 8px rgba(88,204,2,.25); }
.msg-bub.streaming { border-left: 3px solid #58CC02; background: #FCFCFE; }

.msg-bub :deep(p) { margin: 0 0 3px; }
.msg-bub :deep(p:last-child) { margin: 0; }
.msg-bub :deep(strong) { color: #303133; }
.msg-bub :deep(code) { background: #e8e8e8; padding: 1px 5px; border-radius: 3px; font-size: 11px; }
.msg-bub :deep(ul), .msg-bub :deep(ol) { margin: 4px 0; padding-left: 16px; }

/* typing */
.dot-wave { display: inline-flex; gap: 3px; align-items: center; }
.dot-wave i { width: 5px; height: 5px; border-radius: 50%; background: #58CC02; animation: pop .8s infinite both; }
.dot-wave i:nth-child(2) { animation-delay: .15s; }
.dot-wave i:nth-child(3) { animation-delay: .3s; }
@keyframes pop { 0%,60%,100% { transform: scale(.6); opacity: .3; } 30% { transform: scale(1); opacity: 1; } }

/* ── 输入 ── */
.card-foot {
  display: flex; gap: 8px; padding: 10px 14px;
  border-top: 1px solid #F0F0F0; flex-shrink: 0;
}
.card-foot input {
  flex: 1; border: 1.5px solid #E5E5E5; border-radius: 22px;
  padding: 8px 16px; font-size: 13px; outline: none; background: #F9F9F9;
  transition: border-color .2s, background .2s;
}
.card-foot input:focus { border-color: #58CC02; background: #fff; }
.send {
  width: 36px; height: 36px; border: none; border-radius: 50%;
  background: linear-gradient(135deg, #58CC02, #4CAF00); color: #fff;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; box-shadow: 0 2px 6px rgba(88,204,2,.25); transition: transform .15s;
}
.send:hover:not(:disabled) { transform: scale(1.08); }
.send:disabled { background: #D9D9D9; box-shadow: none; cursor: default; }

/* card enter/leave */
.card-enter-active { transition: opacity .25s, transform .25s cubic-bezier(.34,1.56,.64,1); }
.card-leave-active { transition: opacity .18s, transform .18s ease; }
.card-enter-from, .card-leave-to { opacity: 0; transform: scale(.92); }
</style>
