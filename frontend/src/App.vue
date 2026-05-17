<script setup>
import AnnouncementBar from "@/components/AnnouncementBar.vue";
</script>

<template>
  <AnnouncementBar />
  <router-view v-slot="{ Component }">
    <transition name="page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<style>
.page-enter-active {
  animation: pageIn 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.page-leave-active {
  animation: pageOut 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}
@keyframes pageIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes pageOut {
  from { opacity: 1; }
  to { opacity: 0; }
}
</style>
