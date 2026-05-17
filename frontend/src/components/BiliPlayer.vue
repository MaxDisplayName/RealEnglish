<script setup>
import { ref, computed } from "vue";
import { WarningFilled } from "@element-plus/icons-vue";
import { useBiliPlayer } from "@/composables/useBiliPlayer";

const props = defineProps({
  videoUrl: { type: String, default: "" },
  startSec: { type: Number, default: 0 },
  endSec: { type: Number, default: 0 },
  title: { type: String, default: "" },
});

const emit = defineEmits(["time-up"]);

const duration = computed(() => props.endSec - props.startSec);

const {
  isPlaying,
  currentTime,
  isTimeUp,
  iframeLoaded,
  playerKey,
  playerUrl,
  reload,
} = useBiliPlayer({
  startSec: props.startSec,
  endSec: props.endSec,
  iframeUrl: props.videoUrl,
});

const showStartOverlay = ref(true);
const iframeDomLoaded = ref(false);

function onIframeLoad() {
  iframeDomLoaded.value = true;
}

function formatTime(sec) {
  const m = Math.floor(Math.max(0, sec) / 60);
  const s = Math.max(0, sec) % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function startWatching() {
  showStartOverlay.value = false;
}

function replay() {
  showStartOverlay.value = false;
  iframeDomLoaded.value = false;
  reload();
}

function backToStart() {
  showStartOverlay.value = true;
  iframeDomLoaded.value = false;
  reload();
}

// 监听 time-up 事件
import { watch } from "vue";
watch(isTimeUp, (val) => {
  if (val) emit("time-up");
});
</script>

<template>
  <div class="video-wrapper">
    <div class="video-container">
      <!-- B站 iframe 播放器 -->
      <iframe
        v-if="playerUrl"
        :key="playerKey"
        :src="playerUrl"
        class="bili-iframe"
        :class="{ hidden: showStartOverlay }"
        allow="autoplay; fullscreen"
        scrolling="no"
        frameborder="no"
        referrerpolicy="no-referrer"
        @load="onIframeLoad"
      />

      <!-- 加载中（iframe DOM 已加载后隐藏） -->
      <div v-if="!iframeDomLoaded && !showStartOverlay" class="loading-overlay">
        <div class="loading-spinner" />
        <p>播放器加载中...</p>
      </div>

      <!-- 开始观看覆盖层 -->
      <Transition name="fade">
        <div v-if="showStartOverlay && !isTimeUp" class="start-overlay">
          <div class="overlay-content">
            <h3>{{ title || "影视片段" }}</h3>
            <p class="overlay-range">
              播放区间 {{ formatTime(startSec) }} ~
              {{ formatTime(endSec) }}
            </p>
            <p class="overlay-hint">
              共 {{ duration }} 秒，请集中精力观看
            </p>
            <el-button type="primary" size="large" @click="startWatching">
              开始观看
            </el-button>
          </div>
        </div>
      </Transition>

      <!-- 播放完毕屏障 -->
      <Transition name="fade">
        <div v-if="isTimeUp" class="time-barrier">
          <div class="barrier-content">
            <el-icon :size="32" color="#fff"><WarningFilled /></el-icon>
            <p class="barrier-title">片段播放完毕</p>
            <p class="barrier-hint">请继续答题或选择其他片段</p>
            <div class="barrier-actions">
              <el-button type="primary" size="small" @click="replay">
                重新播放
              </el-button>
              <el-button size="small" @click="backToStart">
                返回开始
              </el-button>
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <!-- 底部状态栏 -->
    <div v-if="duration > 0" class="video-controls">
      <span class="timer" :class="{ expired: isTimeUp }">
        {{
          isTimeUp
            ? "播放完毕"
            : isPlaying
              ? "播放中"
              : showStartOverlay || !iframeDomLoaded
                ? "未开始"
                : "已暂停"
        }}
      </span>
      <span class="time-range">
        {{ formatTime(startSec) }} / {{ formatTime(endSec) }}
      </span>
      <template v-if="isTimeUp">
        <el-button size="small" type="primary" @click="replay">
          重新播放
        </el-button>
        <el-button size="small" @click="backToStart">返回</el-button>
      </template>
      <template v-else-if="showStartOverlay">
        <el-button size="small" type="primary" @click="startWatching">
          开始
        </el-button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.video-wrapper {
  margin-bottom: 16px;
}

.video-container {
  position: relative;
  width: 100%;
  padding-top: 56.25%;
  border-radius: var(--radius-base);
  overflow: hidden;
  background: #000;
}

.bili-iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
}

.bili-iframe.hidden {
  visibility: hidden;
}

/* ===== 加载中 ===== */
.loading-overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: #1a1a1a;
  color: #909399;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #333;
  border-top-color: var(--color-primary, #409eff);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ===== 开始覆盖层 ===== */
.start-overlay {
  position: absolute;
  inset: 0;
  z-index: 5;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
}

.overlay-content {
  text-align: center;
  color: #fff;
  padding: 32px;
}

.overlay-content h3 {
  font-size: 20px;
  margin-bottom: 8px;
}

.overlay-range {
  font-size: 14px;
  opacity: 0.8;
  margin-bottom: 4px;
}

.overlay-hint {
  font-size: 13px;
  opacity: 0.6;
  margin-bottom: 24px;
}

/* ===== 时间到屏障 ===== */
.time-barrier {
  position: absolute;
  inset: 0;
  z-index: 6;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
}

.barrier-content {
  text-align: center;
  color: #fff;
}

.barrier-title {
  font-size: 20px;
  font-weight: 600;
  margin: 12px 0 4px;
}

.barrier-hint {
  font-size: 14px;
  opacity: 0.7;
  margin-bottom: 20px;
}

.barrier-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}

/* ===== 过渡动画 ===== */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ===== 底部控制栏 ===== */
.video-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 8px 12px;
  background: #fff;
  border-radius: var(--radius-base);
}

.timer {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-primary);
  margin-right: auto;
}

.timer.expired {
  color: var(--color-danger);
}

.time-range {
  font-size: 12px;
  color: #c0c4cc;
  margin-right: 8px;
}
</style>
