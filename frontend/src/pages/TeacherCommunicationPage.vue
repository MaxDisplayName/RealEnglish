<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from "vue";
import { ArrowLeft } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import request from "@/api/shared/request";
import { useUserStore } from "@/stores/user";

const userStore = useUserStore();
const myUserId = computed(() => userStore.userInfo?.id || "");

// ── 会话列表 ──
const conversations = ref([]);
const convLoading = ref(false);
const activeConv = ref(null); // { type, id, name }
const searchText = ref("");

const studentConvs = computed(() =>
  conversations.value.filter(c => c.type === "student" && (!searchText.value || c.name.includes(searchText.value))),
);
const groupConvs = computed(() =>
  conversations.value.filter(c => c.type === "group" && (!searchText.value || c.name.includes(searchText.value))),
);

// ── 消息 ──
const messages = ref([]);
const msgLoading = ref(false);
const inputText = ref("");
const sending = ref(false);
const chatBody = ref(null);

async function markConvAsRead() {
  const unreadIds = messages.value.filter(m => m.sender_id !== myUserId.value && !m.is_read).map(m => m.id);
  if (unreadIds.length === 0) return;
  try {
    await request.post("/teacher/communication/messages/read", { message_ids: unreadIds });
    userStore.unreadCount = Math.max(0, userStore.unreadCount - unreadIds.length);
  } catch { /* */ }
}

function selectConv(conv) {
  activeConv.value = conv;
  messages.value = [];
  knownIds.value = new Set();
  lastPollTime.value = new Date(Date.now() - 60000).toISOString();
  loadMessages().then(() => markConvAsRead());
}

async function loadConversations() {
  convLoading.value = true;
  try {
    const res = await request.get("/teacher/communication/conversations");
    conversations.value = res.data || [];
  } finally { convLoading.value = false; }
}

async function loadMessages() {
  if (!activeConv.value) return;
  msgLoading.value = true;
  messages.value = [];
  const { type, id } = activeConv.value;
  try {
    const url = type === "student"
      ? `/teacher/communication/messages/with/${id}`
      : `/teacher/communication/messages/group/${id}`;
    const res = await request.get(url);
    messages.value = res.data || [];
    knownIds.value = new Set(messages.value.map(m => m.id));
    lastPollTime.value = new Date().toISOString();
  } catch { /* */ }
  finally {
    msgLoading.value = false;
    scrollDown(true);
  }
}

async function sendMessage() {
  const text = inputText.value.trim();
  if (!text || !activeConv.value || sending.value) return;
  inputText.value = "";
  sending.value = true;
  try {
    const { type, id } = activeConv.value;
    const body = { content: text };
    if (type === "student") body.receiver_id = id;
    else body.group_id = id;
    await request.post("/teacher/communication/messages/send", body);
    // 立即轮询获取真实消息，不做乐观推送
    lastPollTime.value = new Date(Date.now() - 2000).toISOString();
    await pollTeacherMessages();
    scrollDown(true);
    loadConversations();
  } catch { ElMessage.error("发送失败"); }
  finally { sending.value = false; }
}

const lastPollTime = ref("");
const knownIds = ref(new Set());
let pollTimer = null;

async function pollTeacherMessages() {
  if (!activeConv.value || !lastPollTime.value) return;
  try {
    const params = { since: lastPollTime.value };
    if (activeConv.value.type === "student") params.student_id = activeConv.value.id;
    else if (activeConv.value.type === "group") params.group_id = activeConv.value.id;
    const res = await request.get("/teacher/communication/messages/poll", { params });
    const items = res?.items || res.data?.items || [];
    lastPollTime.value = new Date().toISOString();
    const existingKeys = new Set(messages.value.map(x => `${x.sender_id}|${x.content}|${x.created_at}`));
    for (const m of items) {
      const key = `${m.sender_id}|${m.content}|${m.created_at}`;
      if (existingKeys.has(key)) continue;
      existingKeys.add(key);
      messages.value.push(m);
    }
    if (items.length > 0) scrollDown();
  } catch { /* */ }
}

function isNearBottom() {
  const el = chatBody.value;
  if (!el) return false;
  return el.scrollHeight - el.scrollTop - el.clientHeight < 80;
}
function scrollDown(force = false) {
  nextTick(() => {
    if (!chatBody.value) return;
    if (force || isNearBottom()) chatBody.value.scrollTop = chatBody.value.scrollHeight;
  });
}

function avatarChar(name) {
  return (name || "?")[0];
}

function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

onMounted(() => {
  loadConversations();
  lastPollTime.value = new Date().toISOString();
  pollTimer = setInterval(pollTeacherMessages, 3000);
});
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer); });
</script>

<template>
  <div class="chat-page">
    <!-- 左侧栏 -->
    <aside class="chat-sidebar">
      <div class="sidebar-hd">
        <el-button size="small" :icon="ArrowLeft" text @click="$router.back()">返回</el-button>
        <span class="sidebar-title">消息</span>
      </div>
      <div class="sidebar-search">
        <input v-model="searchText" placeholder="搜索会话..." class="search-input" />
      </div>
      <div class="conv-list" v-loading="convLoading">
        <!-- 学生 -->
        <div class="conv-section-label">学生</div>
        <div
          v-for="c in studentConvs" :key="c.id"
          class="conv-item"
          :class="{ active: activeConv?.id === c.id && activeConv?.type === c.type }"
          @click="selectConv(c)"
        >
          <div class="conv-avatar">{{ avatarChar(c.name) }}</div>
          <div class="conv-info">
            <div class="conv-name">{{ c.name }}</div>
            <div class="conv-preview">点击查看消息</div>
          </div>
          <span v-if="c.unread > 0" class="conv-badge">{{ c.unread }}</span>
        </div>
        <!-- 群组 -->
        <div class="conv-section-label">群组</div>
        <div
          v-for="c in groupConvs" :key="c.id"
          class="conv-item"
          :class="{ active: activeConv?.id === c.id && activeConv?.type === c.type }"
          @click="selectConv(c)"
        >
          <div class="conv-avatar group-avatar">{{ avatarChar(c.name) }}</div>
          <div class="conv-info">
            <div class="conv-name">{{ c.name }}</div>
            <div class="conv-preview">群发消息</div>
          </div>
        </div>
        <div v-if="conversations.length === 0 && !convLoading" class="conv-empty">暂无会话</div>
      </div>
    </aside>

    <!-- 右侧聊天区 -->
    <main class="chat-main">
      <template v-if="!activeConv">
        <div class="chat-placeholder">
          <div class="ph-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#D0D0D0" stroke-width="1.2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <p>选择左侧会话开始聊天</p>
        </div>
      </template>
      <template v-else>
        <div class="chat-topbar">
          <div class="ct-avatar">{{ avatarChar(activeConv.name) }}</div>
          <span class="ct-name">{{ activeConv.name }}</span>
        </div>
        <div ref="chatBody" class="chat-messages" v-loading="msgLoading">
          <div v-for="(m, i) in messages" :key="i" class="msg-row" :class="{ mine: m.sender_id === myUserId }">
            <div class="msg-avatar" v-if="m.sender_id !== myUserId">{{ (m.sender_name || '?')[0] }}</div>
            <div class="msg-bubble">
              <div class="msg-sender" v-if="m.sender_id !== myUserId">{{ m.sender_name }}</div>
              <div class="msg-text">{{ m.content }}</div>
              <div class="msg-time">{{ m.created_at }}</div>
            </div>
            <div class="msg-avatar mine-avatar" v-if="m.sender_id === myUserId">我</div>
          </div>
          <div v-if="messages.length === 0 && !msgLoading" class="msg-empty">暂无消息，发送第一条吧</div>
        </div>
        <div class="chat-input-bar">
          <textarea
            v-model="inputText" class="chat-textarea"
            placeholder="输入消息... (Enter 发送)" :disabled="sending"
            @keydown="handleKey" rows="2"
          />
          <button class="send-btn" :disabled="sending || !inputText.trim()" @click="sendMessage">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"/></svg>
          </button>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
.chat-page { display: flex; height: calc(100vh - 56px - 40px); overflow: hidden; background: #fff; border-radius: 0; margin: -20px -24px; }

/* ── 侧栏 ── */
.chat-sidebar { width: 280px; min-width: 280px; display: flex; flex-direction: column; background: #F8F9FA; border-right: 1px solid #EBEDF0; }
.sidebar-hd { display: flex; align-items: center; gap: 8px; padding: 14px 16px 10px; }
.sidebar-title { font-size: 15px; font-weight: 700; color: #303133; }
.sidebar-search { padding: 0 14px 10px; }
.search-input { width: 100%; border: 1.5px solid #E4E7ED; border-radius: 10px; padding: 8px 14px; font-size: 13px; outline: none; background: #fff; box-sizing: border-box; transition: border-color .2s; }
.search-input:focus { border-color: #E6A23C; }

.conv-list { flex: 1; overflow-y: auto; padding: 0 8px 8px; }
.conv-section-label { font-size: 11px; color: #909399; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; padding: 10px 10px 6px; }
.conv-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px;
  border-radius: 12px; cursor: pointer; transition: all .15s;
}
.conv-item:hover { background: rgba(230,162,60,.06); }
.conv-item.active { background: rgba(230,162,60,.10); }
.conv-avatar {
  width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 700; color: #fff;
  background: linear-gradient(135deg, #1CB0F6, #0E9DE0);
}
.group-avatar { background: linear-gradient(135deg, #E6A23C, #D4942E); }
.conv-info { flex: 1; min-width: 0; }
.conv-name { font-size: 13px; font-weight: 600; color: #303133; }
.conv-preview { font-size: 11px; color: #C0C4CC; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conv-badge {
  width: 20px; height: 20px; border-radius: 50%; background: #F56C6C;
  color: #fff; font-size: 11px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.conv-empty { text-align: center; color: #C0C4CC; padding: 40px 0; font-size: 13px; }

/* ── 主聊天区 ── */
.chat-main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.chat-placeholder {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: #C0C4CC; font-size: 14px; gap: 12px;
}
.chat-topbar {
  display: flex; align-items: center; gap: 10px; padding: 14px 20px;
  border-bottom: 1px solid #F0F0F0; flex-shrink: 0;
}
.ct-avatar {
  width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: #fff;
  background: linear-gradient(135deg, #1CB0F6, #0E9DE0);
}
.ct-name { font-size: 14px; font-weight: 700; color: #303133; }

.chat-messages { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 12px; background: radial-gradient(ellipse at 50% 0%, rgba(230,162,60,.012), transparent 60%), #fff; }
.msg-row { display: flex; gap: 8px; animation: msgIn .25s ease both; align-items: flex-end; }
.msg-row.mine { justify-content: flex-end; }
@keyframes msgIn { from { opacity: 0; transform: translateY(8px); } }
.msg-avatar {
  width: 30px; height: 30px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: #fff;
  background: linear-gradient(135deg, #1CB0F6, #0E9DE0);
}
.mine-avatar { background: linear-gradient(135deg, #58CC02, #4CAF00); }
.msg-bubble { max-width: 68%; padding: 10px 16px; border-radius: 16px; font-size: 13.5px; line-height: 1.55; }
.msg-row:not(.mine) .msg-bubble { background: #F5F5F7; color: #303133; border-bottom-left-radius: 4px; }
.msg-row.mine .msg-bubble { background: linear-gradient(135deg, #58CC02, #4CAF00); color: #fff; border-bottom-right-radius: 4px; box-shadow: 0 2px 8px rgba(88,204,2,.25); }
.msg-sender { font-size: 11px; color: #E6A23C; font-weight: 600; margin-bottom: 2px; }
.msg-text { word-break: break-word; }
.msg-time { font-size: 10px; margin-top: 4px; opacity: .45; }
.msg-row.mine .msg-time { text-align: right; }
.msg-empty { text-align: center; color: #C0C4CC; padding: 60px 0; font-size: 13px; flex: 1; }

.chat-input-bar { display: flex; gap: 10px; padding: 12px 20px; border-top: 1px solid #F0F0F0; flex-shrink: 0; align-items: flex-end; }
.chat-textarea {
  flex: 1; border: 1.5px solid #E4E7ED; border-radius: 14px;
  padding: 10px 16px; font-size: 13.5px; outline: none; resize: none;
  font-family: inherit; background: #F9F9FB; transition: border-color .2s; box-sizing: border-box;
}
.chat-textarea:focus { border-color: #E6A23C; background: #fff; }
.send-btn {
  width: 42px; height: 42px; border-radius: 50%; border: none;
  background: linear-gradient(135deg, #58CC02, #4CAF00); color: #fff;
  cursor: pointer; flex-shrink: 0; display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 8px rgba(88,204,2,.25); transition: transform .15s;
}
.send-btn:hover:not(:disabled) { transform: scale(1.08); }
.send-btn:disabled { background: #D9D9D9; box-shadow: none; cursor: default; }
</style>
