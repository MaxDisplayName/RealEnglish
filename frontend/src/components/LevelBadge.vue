<script setup>
defineProps({
  level: { type: String, required: true },
});
</script>

<template>
  <span class="level-badge" :class="'level-' + level.toLowerCase()">{{ level }}级</span>
</template>

<style scoped>
.level-badge {
  display: inline-block;
  padding: 4px 14px;
  border-radius: 16px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.level-a { background: var(--level-a); }
.level-b { background: var(--level-b); }
.level-c { background: var(--level-c); }
</style>
