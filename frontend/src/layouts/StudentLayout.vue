<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "@/stores/user";
import ProfileDialog from "@/components/ProfileDialog.vue";
import request from "@/api/shared/request";

const router = useRouter();
const userStore = useUserStore();
const showProfile = ref(false);
let unreadTimer = null;

async function fetchUnread() {
  if (!userStore.userInfo?.teacher_id) return;
  try {
    const res = await request.get("/student/interactions/unread-count");
    userStore.unreadCount = (res.data?.messages || res?.messages || 0) + (res.data?.tasks || res?.tasks || 0);
  } catch { /* */ }
}

onMounted(() => { fetchUnread(); unreadTimer = setInterval(fetchUnread, 10000); });
onUnmounted(() => { if (unreadTimer) clearInterval(unreadTimer); });

function handleLogout() {
  showProfile.value = false;
  userStore.logout();
  window.location.href = "/";
}
</script>

<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="header-left">
        <router-link to="/student" class="app-logo">
          <span class="logo-icon">R</span>RealEnglish
        </router-link>
      </div>
      <div class="header-right">
        <router-link to="/student" class="nav-link">学习概览</router-link>
        <router-link to="/student/clips" class="nav-link">片段库</router-link>
        <router-link to="/student/accumulate" class="nav-link">我的积累</router-link>
        <router-link to="/student/free-talk" class="nav-link">情景对话</router-link>
        <router-link to="/student/interactions" class="nav-link">
          互动中心
          <el-badge v-if="userStore.unreadCount > 0" :value="userStore.unreadCount" class="nav-badge" />
        </router-link>
        <router-link to="/student/assistant" class="nav-link nav-cta">学习助手</router-link>
        <span class="nav-link nav-user" @click="showProfile = true">
          {{ userStore.userInfo?.username || "个人中心" }}
        </span>
        <span v-if="userStore.level" class="level-badge" :class="'level-' + userStore.level.toLowerCase()">
          {{ userStore.level }}
        </span>
        <el-button size="small" text @click="handleLogout">退出</el-button>
      </div>
    </header>
    <main class="app-main">
      <router-view />
    </main>

    <ProfileDialog
      v-if="showProfile"
      @close="showProfile = false"
      @logout="handleLogout"
    />
  </div>
</template>

<style scoped>
.app-layout{min-height:100vh;display:flex;flex-direction:column;background:var(--bg-page)}
.app-header{
  height:56px;display:flex;align-items:center;justify-content:space-between;
  padding:0 24px;background:var(--color-primary);position:sticky;top:0;z-index:100;
  box-shadow:0 2px 0 #45A502
}
.app-logo{font-size:18px;font-weight:800;color:#fff;text-decoration:none;display:flex;align-items:center;gap:8px}
.logo-icon{
  width:28px;height:28px;border-radius:8px;background:rgba(255,255,255,.25);
  display:flex;align-items:center;justify-content:center;font-size:15px
}
.header-right{display:flex;align-items:center;gap:20px}
.nav-link{color:rgba(255,255,255,.85);text-decoration:none;font-size:14px;font-weight:600;transition:all .15s var(--ease)}
.nav-link:hover{color:#fff}
.nav-link.router-link-active{color:#fff;font-weight:800}
.nav-cta{background:rgba(255,255,255,.2);padding:6px 14px;border-radius:20px;color:#fff}
.nav-cta.router-link-active{background:rgba(255,255,255,.3)}
.nav-user{opacity:.75;font-size:13px}
.level-badge{padding:2px 10px;border-radius:20px;font-size:12px;font-weight:800;color:#fff}
.level-a{background:var(--color-primary)}
.level-b{background:var(--color-blue)}
.level-c{background:var(--color-purple)}
.app-main{flex:1;padding:20px 24px;width:100%;margin:0 auto}
.nav-badge :deep(.el-badge__content){transform:translate(6px,-6px)}
</style>
