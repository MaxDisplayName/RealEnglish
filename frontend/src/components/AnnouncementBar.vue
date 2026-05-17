<script setup>
import { ref, onMounted } from "vue";
import { useUserStore } from "@/stores/user";
import request from "@/api/shared/request";

const userStore = useUserStore();
const visible = ref(false);
const announcements = ref([]);

async function loadAnnouncements() {
  if (!userStore.isStudent) return;
  if (!userStore.userInfo?.teacher_id) return;
  try {
    const res = await request.get("/student/interactions/announcements");
    const items = res.data?.items || [];
    const stored = sessionStorage.getItem("ann_read");
    const readIds = stored ? JSON.parse(stored) : [];
    // 只显示未读的
    announcements.value = items.filter(a => !readIds.includes(a.id));
    if (announcements.value.length > 0) visible.value = true;
  } catch { /* */ }
}

function dismissAll() {
  const stored = sessionStorage.getItem("ann_read");
  const readIds = stored ? JSON.parse(stored) : [];
  for (const a of announcements.value) {
    if (!readIds.includes(a.id)) readIds.push(a.id);
  }
  sessionStorage.setItem("ann_read", JSON.stringify(readIds.slice(-50)));
  visible.value = false;
}

onMounted(loadAnnouncements);
</script>

<template>
  <teleport to="body">
    <transition name="ann-modal">
      <div v-if="visible" class="ann-overlay">
        <div class="ann-modal">
          <div class="ann-modal-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#58CC02" stroke-width="1.5">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>
            </svg>
          </div>
          <h2>公告通知</h2>
          <div class="ann-list">
            <div v-for="a in announcements" :key="a.id" class="ann-item">
              <div class="ann-title">{{ a.title }}</div>
              <p class="ann-content">{{ a.content }}</p>
              <span class="ann-time">{{ a.created_at }}</span>
            </div>
          </div>
          <button class="ann-dismiss-btn" @click="dismissAll">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            已读确认
          </button>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<style scoped>
.ann-overlay {
  position: fixed; inset: 0; z-index: 3000;
  background: rgba(0,0,0,.35); display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(6px);
}
.ann-modal {
  background: #fff; border-radius: 20px; padding: 32px 36px 24px;
  width: 480px; max-height: 70vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,.15); text-align: center;
}
.ann-modal-icon { margin-bottom: 8px; }
.ann-modal h2 { font-size: 18px; font-weight: 800; color: #303133; margin: 0 0 18px; }

.ann-list { text-align: left; display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; }
.ann-item { background: #F8FAF6; border-radius: 12px; padding: 14px 16px; border: 1px solid rgba(88,204,2,.08); }
.ann-title { font-weight: 700; font-size: 14px; color: #303133; margin-bottom: 4px; }
.ann-content { font-size: 13px; color: #606266; margin: 0; line-height: 1.5; }
.ann-time { font-size: 11px; color: #C0C4CC; margin-top: 6px; display: block; }

.ann-dismiss-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 10px 28px; border: none; border-radius: 12px;
  background: linear-gradient(135deg, #58CC02, #4CAF00); color: #fff;
  font-size: 14px; font-weight: 700; cursor: pointer; font-family: inherit;
  box-shadow: 0 4px 0 #45A502; transition: all .12s;
}
.ann-dismiss-btn:hover { filter: brightness(1.05); transform: translateY(1px); box-shadow: 0 2px 0 #45A502; }
.ann-dismiss-btn:active { transform: translateY(3px); box-shadow: none; }

.ann-modal-enter-active { transition: all .3s cubic-bezier(.34,1.56,.64,1); }
.ann-modal-leave-active { transition: all .2s ease; }
.ann-modal-enter-from { opacity: 0; }
.ann-modal-enter-from .ann-modal { transform: scale(.85) translateY(30px); opacity: 0; }
.ann-modal-leave-to { opacity: 0; }
</style>
