<script setup>
import { ref, computed, onMounted } from "vue";
import { useUserStore } from "@/stores/user";
import { ElMessage } from "element-plus";
import request from "@/api/shared/request";

const emit = defineEmits(["close", "logout"]);
const userStore = useUserStore();
const inviteCode = ref("");

async function loadInviteCode() {
  if (!userStore.isTeacher) return;
  try {
    const res = await request.get("/teacher/invite-code");
    inviteCode.value = res?.invite_code || res.data?.invite_code || "";
  } catch { /* */ }
}

function copyInviteCode() {
  if (!inviteCode.value) return;
  navigator.clipboard.writeText(inviteCode.value);
  ElMessage.success("邀请码已复制");
}

onMounted(loadInviteCode);

const levelClass = computed(() => {
  const lv = userStore.level;
  return lv ? "diff-" + lv.toLowerCase() : "";
});
</script>

<template>
  <teleport to="body">
    <div class="profile-overlay" @click.self="emit('close')">
      <div class="profile-dialog">
        <button class="profile-close" @click="emit('close')">&times;</button>

        <div class="dialog-body">
          <div class="profile-avatar-wrap">
            <div class="profile-avatar">
              {{ userStore.userInfo?.username?.charAt(0)?.toUpperCase() || "U" }}
            </div>
          </div>

          <h2 class="profile-name">{{ userStore.userInfo?.username || "匿名用户" }}</h2>
          <p class="profile-email">{{ userStore.userInfo?.email || "" }}</p>

          <div class="profile-tags">
            <span v-if="userStore.level" class="diff-badge-solid" :class="levelClass">
              {{ userStore.level }}级
            </span>
            <span class="role-badge">
              {{ userStore.role === "teacher" ? "教师" : "学生" }}
            </span>
          </div>

          <el-divider />

          <div class="profile-details">
            <div class="detail-row">
              <span class="detail-label">用户名</span>
              <span class="detail-value">{{ userStore.userInfo?.username || "—" }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">邮箱</span>
              <span class="detail-value">{{ userStore.userInfo?.email || "—" }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">身份</span>
              <span class="detail-value">{{ userStore.role === "teacher" ? "教师" : "学生" }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">等级</span>
              <span class="detail-value">{{ userStore.isTeacher ? "不适用" : (userStore.level || "未定级") }}</span>
            </div>
            <div v-if="userStore.isTeacher" class="detail-row">
              <span class="detail-label">邀请码</span>
              <span class="detail-value">
                <code style="background:#F5F5F7;padding:2px 8px;border-radius:4px;font-size:14px;letter-spacing:2px;cursor:pointer" @click="copyInviteCode">{{ inviteCode || '加载中...' }}</code>
              </span>
            </div>
            <div class="detail-row">
              <span class="detail-label">注册时间</span>
              <span class="detail-value">
                {{ userStore.userInfo?.created_at ? new Date(userStore.userInfo.created_at).toLocaleDateString() : "—" }}
              </span>
            </div>
          </div>

          <el-divider />

          <div class="dialog-actions">
            <el-button type="danger" @click="emit('logout')">退出登录</el-button>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<style scoped>
.profile-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.profile-dialog {
  background: #fff;
  border-radius: var(--radius-md, 16px);
  width: 400px;
  max-width: 90vw;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg, 0 8px 32px rgba(0,0,0,.1));
  position: relative;
  animation: popIn 0.25s var(--ease-bounce, cubic-bezier(0.34,1.56,0.64,1));
}

@keyframes popIn {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}

.profile-close {
  position: absolute;
  top: 12px;
  right: 16px;
  background: none;
  border: none;
  font-size: 24px;
  color: var(--text-light, #C2C2C2);
  cursor: pointer;
  line-height: 1;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 0.15s ease;
}
.profile-close:hover {
  color: var(--text-main, #4B4B4B);
  background: var(--bg-surface, #F7F7F7);
}

.dialog-body {
  padding: 40px 32px 32px;
  text-align: center;
}

.profile-avatar-wrap {
  margin-bottom: 16px;
}

.profile-avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--color-primary, #58CC02);
  color: #fff;
  font-size: 28px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
}

.profile-name {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main, #4B4B4B);
  margin: 0 0 4px;
}

.profile-email {
  font-size: 14px;
  color: var(--text-secondary, #AFAFAF);
  margin: 0 0 12px;
}

.profile-tags {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.role-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 700;
  background: var(--color-primary-light, #E5F8D1);
  color: var(--color-primary-dark, #46A302);
}

.profile-details {
  display: flex;
  flex-direction: column;
  gap: 10px;
  text-align: left;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--text-main, #4B4B4B);
}

.detail-label {
  color: var(--text-secondary, #AFAFAF);
}

.detail-value {
  font-weight: 500;
}

.dialog-actions {
  text-align: center;
}
</style>
