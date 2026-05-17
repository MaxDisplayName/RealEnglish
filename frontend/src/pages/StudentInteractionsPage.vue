<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import { useUserStore } from "@/stores/user";
import request from "@/api/shared/request";

const userStore = useUserStore();
const myUserId = computed(() => userStore.userInfo?.id || "");

// ── 会话 ──
const conversations = [
  { type: "teacher", id: "teacher", name: "我的教师" },
  { type: "group", id: "class", name: "我的小组" },
];
const activeConv = ref("teacher");
const unreadByConv = ref({ teacher: 0, group: 0 });

// ── 绑定状态 ──
const bound = ref(true);
const bindCode = ref("");
const bindLoading = ref(false);

async function checkBound() {
  try {
    await request.get("/student/interactions/messages");
    bound.value = true;
  } catch (e) {
    if (e.response?.status === 403) bound.value = false;
  }
}

async function handleBind() {
  if (!bindCode.value.trim()) return;
  bindLoading.value = true;
  try {
    await request.post("/bind-invite", { invite_code: bindCode.value });
    ElMessage.success("绑定成功！");
    bound.value = true;
    bindCode.value = "";
    loadMessages(); loadTasks(); loadGroupInfo();
  } catch (e) { ElMessage.error(e.response?.data?.detail || "绑定失败"); }
  finally { bindLoading.value = false; }
}

// ── 消息 ──
const messages = ref([]);
const inputText = ref("");
const sending = ref(false);
const chatBody = ref(null);
const lastPollTime = ref("");
const knownIds = ref(new Set());
let pollTimer = null;

// ── 任务+分组弹窗 ──
const infoVisible = ref(false);
const tasks = ref([]);
const groupInfo = ref({ group_name: "加载中...", member_count: 0 });

function selectConv(type) {
  activeConv.value = type;
  messages.value = [];
  knownIds.value = new Set();
  lastPollTime.value = new Date(Date.now() - 60000).toISOString();
  loadMessages().then(() => markAsRead());
}

async function loadMessages() {
  try {
    const res = await request.get("/student/interactions/messages");
    const all = res?.items || res.data?.items || [];
    const filtered = activeConv.value === "teacher"
      ? all.filter(m => !m.group_id)
      : all.filter(m => m.group_id);
    messages.value = filtered;
    for (const m of filtered) knownIds.value.add(m.id);
    // 计算未读
    updateUnreadBadges();
    scrollDown(true);
  } catch { /* */ }
}

function updateUnreadBadges() {
  // 从后端数据中计算各会话未读数
  // 简化：轮询时更新 store
}

async function pollNewMessages() {
  if (!lastPollTime.value) return;
  try {
    const res = await request.get("/student/interactions/messages/poll", { params: { since: lastPollTime.value } });
    const items = res?.items || res.data?.items || [];
    lastPollTime.value = new Date().toISOString();
    const existingKeys = new Set(messages.value.map(x => `${x.sender_id}|${x.content}|${x.created_at}`));
    for (const m of items) {
      const key = `${m.sender_id}|${m.content}|${m.created_at}`;
      if (existingKeys.has(key)) continue;
      existingKeys.add(key);
      const match = activeConv.value === "teacher" ? !m.group_id : !!m.group_id;
      if (match) {
        messages.value.push(m);
        // 如果非自己发送的，增加当前会话未读数
        if (m.sender_id !== myUserId.value && !m.is_read) {
          unreadByConv.value[activeConv.value] = (unreadByConv.value[activeConv.value] || 0) + 1;
        }
      } else {
        // 其他会话的新消息，更新对应未读数
        const otherConv = m.group_id ? "group" : "teacher";
        if (m.sender_id !== myUserId.value && !m.is_read) {
          unreadByConv.value[otherConv] = (unreadByConv.value[otherConv] || 0) + 1;
        }
      }
    }
    if (items.length > 0) scrollDown();
  } catch { /* */ }
}

async function markAsRead() {
  unreadByConv.value[activeConv.value] = 0;
  const unreadIds = messages.value.filter(m => m.sender_id !== myUserId.value && !m.is_read).map(m => m.id);
  if (unreadIds.length === 0) return;
  try {
    await request.post("/student/interactions/messages/read", { message_ids: unreadIds });
    userStore.unreadCount = Math.max(0, userStore.unreadCount - unreadIds.length);
  } catch { /* */ }
}

async function sendMessage() {
  const text = inputText.value.trim();
  if (!text || sending.value) return;
  inputText.value = "";
  sending.value = true;
  try {
    const body = { content: text };
    if (activeConv.value === "group") body.group_id = "group";
    await request.post("/student/interactions/messages", body);
    lastPollTime.value = new Date(Date.now() - 2000).toISOString();
    await pollNewMessages();
    scrollDown(true);
  } catch { ElMessage.error("发送失败"); }
  finally { sending.value = false; }
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
function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function openInfo() {
  loadTasks(); loadGroupInfo(); infoVisible.value = true;
}
async function loadTasks() {
  try { const res = await request.get("/student/interactions/tasks"); tasks.value = res.data || []; } catch { /* */ }
}
async function loadGroupInfo() {
  try { const res = await request.get("/student/interactions/group-info"); groupInfo.value = res.data || { group_name: "未分组", member_count: 0 }; } catch { /* */ }
}
function taskPct(t) {
  const total = (t.practice_goal||0)+(t.speaking_goal||0)+(t.free_talk_goal||0)+(t.clip_goal||0);
  const done = (t.practice_done||0)+(t.speaking_done||0)+(t.free_talk_done||0)+(t.clips_done||0);
  return total > 0 ? Math.round(done/total*100) : 0;
}

function avatarChar(name) { return (name || "?")[0]; }

onMounted(() => {
  checkBound().then(() => {
    if (bound.value) { loadMessages(); lastPollTime.value = new Date().toISOString(); pollTimer = setInterval(pollNewMessages, 3000); }
  });
});
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer); });
</script>

<template>
  <!-- 锁定覆盖层 -->
  <div v-if="!bound" class="lock-overlay">
    <div class="lock-card">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#C0C4CC" stroke-width="1.5">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
      </svg>
      <h2>功能已锁定</h2>
      <p>请绑定教师邀请码后使用互动中心</p>
      <div class="lock-input">
        <input v-model="bindCode" placeholder="输入 4 位邀请码" maxlength="4" style="text-transform:uppercase" @keyup.enter="handleBind" />
        <button :disabled="bindLoading || !bindCode.trim()" @click="handleBind">{{ bindLoading ? '绑定中...' : '绑定' }}</button>
      </div>
    </div>
  </div>

  <div class="sip-page" v-if="bound">
    <div class="sip-chat">
      <!-- 左侧栏 -->
      <aside class="sc-sidebar">
        <div class="sidebar-title">会话</div>
        <div v-for="c in conversations" :key="c.id"
          class="sc-item" :class="{ active: activeConv === c.type }"
          @click="selectConv(c.type)"
        >
          <div class="sc-avatar" :class="c.type">{{ avatarChar(c.name) }}</div>
          <div class="sc-item-info">
            <span>{{ c.name }}</span>
            <span v-if="unreadByConv[c.type] > 0 && activeConv !== c.type" class="sc-badge">{{ unreadByConv[c.type] }}</span>
          </div>
        </div>
        <div class="sidebar-spacer" />
        <button class="info-btn" @click="openInfo">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
          <span>任务分组</span>
        </button>
      </aside>

      <!-- 右侧聊天主区 -->
      <main class="sc-main">
        <div class="chat-topbar">
          <div class="ct-avatar" :class="activeConv">{{ avatarChar(activeConv === 'teacher' ? '教师' : '小组') }}</div>
          <span class="ct-name">{{ activeConv === 'teacher' ? '我的教师' : '我的小组' }}</span>
        </div>

        <div ref="chatBody" class="chat-messages">
          <div v-for="(m, i) in messages" :key="i" class="msg-row" :class="{ mine: m.sender_id === myUserId }">
            <div class="msg-avatar" v-if="m.sender_id !== myUserId">{{ (m.sender_name || '?')[0] }}</div>
            <div class="msg-bubble">
              <div class="msg-sender" v-if="m.sender_id !== myUserId">{{ m.sender_name || '' }}</div>
              <div class="msg-text">{{ m.content }}</div>
              <div class="msg-time">{{ m.created_at }}</div>
            </div>
            <div class="msg-avatar mine-avatar" v-if="m.sender_id === myUserId">我</div>
          </div>
          <div v-if="messages.length === 0" class="msg-empty">暂无消息，发送第一条吧</div>
        </div>

        <div class="chat-input-bar">
          <textarea v-model="inputText" class="chat-textarea" placeholder="输入消息... (Enter 发送)" :disabled="sending" @keydown="handleKey" rows="2" />
          <button class="send-btn" :disabled="sending || !inputText.trim()" @click="sendMessage">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"/></svg>
          </button>
        </div>
      </main>
    </div>

    <!-- 任务分组悬浮面板 -->
    <teleport to="body">
      <transition name="info-fade">
        <div v-if="infoVisible" class="info-overlay" @click.self="infoVisible = false">
          <div class="info-panel">
            <button class="info-close" @click="infoVisible = false">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
            <h2 class="info-title">任务与分组</h2>
            <div class="info-grid">
              <!-- 任务 -->
              <div class="info-sec">
                <h3>我的任务</h3>
                <div v-if="tasks.length === 0" class="info-empty">暂无任务</div>
                <div v-for="t in tasks" :key="t.id" class="tk-card">
                  <div class="tk-hd">
                    <span class="tk-title">{{ t.title }}</span>
                    <span v-if="t.is_completed" class="tk-done">已完成</span>
                    <span v-else class="tk-active">进行中</span>
                  </div>
                  <div class="tk-goals">
                    <div><b>{{ t.practice_done }}/{{ t.practice_goal }}</b><small>练习</small></div>
                    <div><b>{{ t.speaking_done }}/{{ t.speaking_goal }}</b><small>口语</small></div>
                    <div><b>{{ t.free_talk_done }}/{{ t.free_talk_goal }}</b><small>对话</small></div>
                    <div><b>{{ t.clips_done }}/{{ t.clip_goal }}</b><small>片段</small></div>
                  </div>
                  <div class="tk-bar"><div class="tk-fill" :style="{ width: taskPct(t) + '%' }" /></div>
                  <div class="tk-foot">{{ taskPct(t) }}%<span v-if="t.deadline"> 截止 {{ t.deadline }}</span></div>
                </div>
              </div>
              <!-- 分组 -->
              <div class="info-sec">
                <h3>我的分组</h3>
                <div class="group-card">
                  <div class="gc-badge">{{ groupInfo.group_name }}</div>
                  <p class="gc-desc" v-if="groupInfo.description">{{ groupInfo.description }}</p>
                  <p class="gc-count">{{ groupInfo.member_count }} 名成员</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<style scoped>
/* ── 锁定覆盖层 ── */
.lock-overlay { height: calc(100vh - 130px); display: flex; align-items: center; justify-content: center; }
.lock-card { text-align: center; background: #fff; border-radius: 20px; padding: 40px 36px; border: 1px solid #EBEDF0; box-shadow: 0 4px 20px rgba(0,0,0,.06); max-width: 380px; width: 100%; }
.lock-card h2 { font-size: 18px; font-weight: 800; color: #303133; margin: 16px 0 8px; }
.lock-card p { font-size: 13px; color: #909399; margin: 0 0 20px; }
.lock-input { display: flex; gap: 8px; }
.lock-input input { flex: 1; border: 1.5px solid #E4E7ED; border-radius: 10px; padding: 10px 14px; font-size: 16px; letter-spacing: 4px; text-align: center; outline: none; text-transform: uppercase; }
.lock-input input:focus { border-color: #58CC02; }
.lock-input button { padding: 0 20px; border: none; border-radius: 10px; background: linear-gradient(135deg, #58CC02, #4CAF00); color: #fff; font-weight: 700; font-size: 13px; cursor: pointer; white-space: nowrap; font-family: inherit; }
.lock-input button:disabled { opacity: .4; cursor: default; }

.sip-page { height: calc(100vh - 56px - 40px); display: flex; flex-direction: column; }

/* ── 聊天主布局：撑满 ── */
.sip-chat { display: flex; flex: 1; background: #fff; border-radius: 0; border: none; overflow: hidden; }

/* ── 侧栏 ── */
.sc-sidebar { width: 200px; min-width: 200px; display: flex; flex-direction: column; background: linear-gradient(180deg, #F8FAF6 0%, #F2F5EE 100%); border-right: 1px solid rgba(88,204,2,.08); padding: 16px 8px 10px; }
.sidebar-title { font-size: 11px; color: #909399; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; padding: 0 10px 10px; }
.sc-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px;
  border-radius: 10px; cursor: pointer; transition: all .18s; font-size: 13px; font-weight: 500; color: #5A5A5A; position: relative;
}
.sc-item:hover { background: rgba(255,255,255,.6); }
.sc-item.active { background: #fff; color: #4A7A30; font-weight: 600; box-shadow: 0 1px 3px rgba(88,204,2,.08); }
.sc-item-info { flex: 1; display: flex; align-items: center; justify-content: space-between; }
.sc-avatar {
  width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: #fff; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,.08);
}
.sc-avatar.teacher { background: linear-gradient(135deg, #E6A23C, #D4942E); }
.sc-avatar.group { background: linear-gradient(135deg, #1CB0F6, #0E9DE0); }
.sc-badge {
  width: 20px; height: 20px; border-radius: 50%; background: #F56C6C;
  color: #fff; font-size: 11px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.sidebar-spacer { flex: 1; }
.info-btn {
  display: flex; align-items: center; gap: 6px; width: 100%; padding: 10px 12px;
  border: none; border-radius: 10px; cursor: pointer; font-size: 12px; color: #909399; font-weight: 500;
  transition: all .15s; font-family: inherit; background: transparent; border-top: 1px solid rgba(0,0,0,.04);
}
.info-btn:hover { background: rgba(255,255,255,.5); color: #58CC02; }

/* ── 主聊天区 ── */
.sc-main { flex: 1; display: flex; flex-direction: column; min-width: 0; background: radial-gradient(ellipse at 50% 0%, rgba(88,204,2,.012), transparent 60%), #fff; }
.chat-topbar { display: flex; align-items: center; gap: 10px; padding: 14px 20px; border-bottom: 1px solid #F0F0F0; flex-shrink: 0; }
.ct-avatar {
  width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: #fff; box-shadow: 0 2px 4px rgba(0,0,0,.08);
}
.ct-avatar.teacher { background: linear-gradient(135deg, #E6A23C, #D4942E); }
.ct-avatar.group { background: linear-gradient(135deg, #1CB0F6, #0E9DE0); }
.ct-name { font-size: 14px; font-weight: 700; color: #303133; }

.chat-messages { flex: 1; overflow-y: auto; padding: 18px 20px; display: flex; flex-direction: column; gap: 12px; }
.msg-row { display: flex; gap: 8px; align-items: flex-end; animation: msgIn .25s ease both; }
.msg-row.mine { justify-content: flex-end; }
@keyframes msgIn { from { opacity: 0; transform: translateY(6px); } }
.msg-avatar {
  width: 28px; height: 28px; border-radius: 9px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; color: #fff;
  background: linear-gradient(135deg, #1CB0F6, #0E9DE0);
}
.mine-avatar { background: linear-gradient(135deg, #58CC02, #4CAF00); }
.msg-bubble { max-width: 68%; padding: 10px 15px; border-radius: 15px; font-size: 13px; line-height: 1.5; word-break: break-word; }
.msg-row:not(.mine) .msg-bubble { background: #F5F5F7; color: #3A3A3A; border-bottom-left-radius: 5px; box-shadow: 0 1px 2px rgba(0,0,0,.03); }
.msg-row.mine .msg-bubble { background: linear-gradient(135deg, #58CC02, #4CAF00); color: #fff; border-bottom-right-radius: 5px; box-shadow: 0 2px 8px rgba(88,204,2,.25); }
.msg-sender { font-size: 11px; color: #E6A23C; font-weight: 600; margin-bottom: 2px; }
.msg-text { word-break: break-word; }
.msg-time { font-size: 10px; margin-top: 4px; opacity: .35; }
.msg-row.mine .msg-time { text-align: right; }
.msg-empty { text-align: center; color: #C0C4CC; padding: 50px 0; font-size: 13px; flex: 1; display: flex; align-items: center; justify-content: center; }

.chat-input-bar { display: flex; gap: 10px; padding: 12px 18px; border-top: 1px solid #F0F0F0; align-items: flex-end; background: rgba(255,255,255,.98); flex-shrink: 0; }
.chat-textarea {
  flex: 1; border: 1.5px solid #E4E7ED; border-radius: 14px; padding: 10px 16px;
  font-size: 13px; outline: none; resize: none; font-family: inherit; background: #F9F9FB;
  transition: border .2s; box-sizing: border-box;
}
.chat-textarea:focus { border-color: #58CC02; background: #fff; }
.send-btn {
  width: 42px; height: 42px; border-radius: 50%; border: none;
  background: linear-gradient(135deg, #58CC02, #4CAF00); color: #fff;
  cursor: pointer; flex-shrink: 0; display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 8px rgba(88,204,2,.25); transition: transform .15s;
}
.send-btn:hover:not(:disabled) { transform: scale(1.08); }
.send-btn:disabled { background: #D9D9D9; box-shadow: none; cursor: default; }

/* ── 悬浮面板 ── */
.info-overlay {
  position: fixed; inset: 0; z-index: 2000;
  background: rgba(0,0,0,.3); display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(4px);
}
.info-panel {
  background: #fff; border-radius: 20px; padding: 28px 32px;
  width: 620px; max-height: 80vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,.15); position: relative;
}
.info-close {
  position: absolute; top: 16px; right: 16px; width: 32px; height: 32px; border-radius: 50%;
  border: none; background: #F5F5F7; cursor: pointer; display: flex; align-items: center; justify-content: center;
  color: #909399; transition: all .15s;
}
.info-close:hover { background: #EBEBEB; color: #303133; }
.info-title { font-size: 18px; font-weight: 800; color: #303133; margin: 0 0 20px; }
.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.info-sec { min-width: 0; }
.info-sec h3 { font-size: 13px; font-weight: 700; color: #606266; margin: 0 0 10px; }
.info-empty { text-align: center; color: #C0C4CC; font-size: 13px; padding: 20px 0; }

.tk-card { padding: 10px 0; border-bottom: 1px solid #F5F5F5; }
.tk-card:last-child { border-bottom: none; }
.tk-hd { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.tk-title { font-size: 13px; font-weight: 700; color: #303133; }
.tk-done { font-size: 10px; font-weight: 600; color: #67C23A; background: rgba(103,194,58,.08); padding: 1px 6px; border-radius: 5px; }
.tk-active { font-size: 10px; font-weight: 600; color: #E6A23C; background: rgba(230,162,60,.08); padding: 1px 6px; border-radius: 5px; }
.tk-goals { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; margin-bottom: 6px; }
.tk-goals div { text-align: center; background: #F5F5F7; border-radius: 6px; padding: 6px 2px; }
.tk-goals b { display: block; font-size: 13px; color: #58CC02; font-weight: 800; }
.tk-goals small { font-size: 9px; color: #909399; }
.tk-bar { height: 4px; background: #F0F0F0; border-radius: 2px; margin-bottom: 4px; overflow: hidden; }
.tk-fill { height: 100%; background: linear-gradient(90deg, #58CC02, #85D63A); border-radius: 2px; transition: width .4s; }
.tk-foot { font-size: 10px; color: #909399; }
.tk-foot span { color: #E6A23C; }

.group-card { text-align: center; padding: 16px 0; }
.gc-badge { font-size: 20px; font-weight: 800; color: #E6A23C; background: linear-gradient(135deg, rgba(230,162,60,.1), rgba(230,162,60,.04)); padding: 10px 24px; border-radius: 12px; display: inline-block; }
.gc-desc { color: #909399; font-size: 13px; margin: 12px 0 4px; }
.gc-count { color: #C0C4CC; font-size: 12px; }

/* 面板动画 */
.info-fade-enter-active { transition: all .3s cubic-bezier(.34,1.56,.64,1); }
.info-fade-leave-active { transition: all .2s ease; }
.info-fade-enter-from { opacity: 0; }
.info-fade-enter-from .info-panel { transform: scale(.9) translateY(20px); }
.info-fade-leave-to { opacity: 0; }
.info-fade-leave-to .info-panel { transform: scale(.95); }
</style>
