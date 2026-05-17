<script setup>
import { useUserStore } from "@/stores/user";
import { useRouter } from "vue-router";

const userStore = useUserStore();
const router = useRouter();

function handleLogout() {
  userStore.logout();
  router.push("/login");
}
</script>

<template>
  <div class="profile-page">
    <el-card class="profile-card" shadow="never">
      <div class="profile-header">
        <el-avatar :size="72" class="profile-avatar">
          {{ userStore.userInfo?.username?.charAt(0)?.toUpperCase() || "U" }}
        </el-avatar>
        <div class="profile-meta">
          <h2>{{ userStore.userInfo?.username || "匿名用户" }}</h2>
          <p class="profile-email">{{ userStore.userInfo?.email || "" }}</p>
          <el-tag v-if="userStore.level" :type="'warning'" size="small">
            {{ userStore.level }} 级
          </el-tag>
          <el-tag :type="userStore.role === 'teacher' ? 'danger' : 'primary'" size="small" style="margin-left: 6px">
            {{ userStore.role === "teacher" ? "教师" : "学生" }}
          </el-tag>
        </div>
      </div>

      <el-divider />

      <div class="profile-info">
        <div class="info-row">
          <span class="info-label">用户名</span>
          <span>{{ userStore.userInfo?.username || "—" }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">邮箱</span>
          <span>{{ userStore.userInfo?.email || "—" }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">身份</span>
          <span>{{ userStore.role === "teacher" ? "教师" : "学生" }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">等级</span>
          <span>{{ userStore.isTeacher ? "不适用" : (userStore.level || "未定级") }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">注册时间</span>
          <span>{{ userStore.userInfo?.created_at ? new Date(userStore.userInfo.created_at).toLocaleDateString() : "—" }}</span>
        </div>
      </div>

      <el-divider />

      <div class="profile-actions">
        <el-button v-if="userStore.isLoggedIn" type="danger" @click="handleLogout">
          退出登录
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 520px;
  margin: 0 auto;
  padding-top: 40px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 20px;
}

.profile-avatar {
  background: var(--color-primary);
  color: #fff;
  font-size: 28px;
  font-weight: 700;
}

.profile-meta h2 {
  font-size: 20px;
  margin: 0 0 4px;
  color: #303133;
}

.profile-email {
  font-size: 14px;
  color: #909399;
  margin: 0 0 8px;
}

.profile-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: #606266;
}

.info-label {
  color: #909399;
}

.profile-actions {
  text-align: center;
}

.login-hint {
  font-size: 14px;
  color: #909399;
}

.login-hint a {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 600;
}
</style>
