<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from "vue";
import { WarningFilled } from "@element-plus/icons-vue";

const props = defineProps({
  bvid: { type: String, required: true },
  page: { type: Number, default: 1 },
  startSec: { type: Number, default: 0 },
  endSec: { type: Number, default: 0 },
  title: { type: String, default: "" },
});

const emit = defineEmits(["time-up", "error"]);

const duration = computed(() => props.endSec - props.startSec);
const iframeRef = ref(null);

const loadError = ref(false);
const timeUp = ref(false);
const showStartOverlay = ref(true);
const isPlaying = ref(false);
const iframeLoading = ref(false);
const currentTime = ref(props.startSec);
const clipProgress = ref(0);

// internal timer state (not refs)
let resumeTime = props.startSec;
let resumeWallTime = null;
let progressTimer = null;
let durationTimer = null;
let readyTimer = null;

function createIframeUrl(t) {
  return `https://player.bilibili.com/player.html?bvid=${props.bvid}&page=${props.page}&autoplay=1&high_quality=1&t=${Math.round(t)}&jsapi=1&danmaku=0&_tstamp=${Date.now()}`;
}

const iframeUrl = ref(createIframeUrl(props.startSec));

// 当 props 变化（如同一个页面切换到不同片段）时重新生成 URL
watch(() => [props.bvid, props.page, props.startSec], () => {
  iframeUrl.value = createIframeUrl(props.startSec);
  // 重置状态
  showStartOverlay.value = true;
  timeUp.value = false;
  isPlaying.value = false;
  loadError.value = false;
  iframeLoading.value = false;
  currentTime.value = props.startSec;
  clipProgress.value = 0;
  stopProgressTimer();
  clearTimeout(durationTimer);
  clearTimeout(readyTimer);
  durationTimer = null;
  readyTimer = null;
});

function formatTime(sec) {
  const s = Math.max(0, Math.round(sec));
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}


/* ---------- progress timer ---------- */

function startProgressTimer() {
  stopProgressTimer();
  resumeWallTime = Date.now();
  progressTimer = setInterval(() => {
    if (resumeWallTime == null) return;
    currentTime.value = resumeTime + (Date.now() - resumeWallTime) / 1000;

    if (currentTime.value >= props.endSec) {
      onTimeUp();
      return;
    }
    clipProgress.value = Math.min(
      1,
      (currentTime.value - props.startSec) / Math.max(1, props.endSec - props.startSec),
    );
  }, 100);
}

function stopProgressTimer() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
  resumeWallTime = null;
}

/* ---------- duration cutoff timer ---------- */

function startDurationTimer() {
  clearTimeout(durationTimer);
  const remaining = Math.max(0, (props.endSec - Math.min(currentTime.value, props.endSec)) * 1000);
  if (remaining <= 0) {
    onTimeUp();
    return;
  }
  durationTimer = setTimeout(() => onTimeUp(), remaining);
}

function pauseDurationTimer() {
  if (!durationTimer) return;
  clearTimeout(durationTimer);
  durationTimer = null;
}

function resumeDurationTimer() {
  if (durationTimer) return;
  const remaining = Math.max(0, (props.endSec - Math.min(currentTime.value, props.endSec)) * 1000);
  if (remaining <= 0) {
    onTimeUp();
    return;
  }
  durationTimer = setTimeout(() => onTimeUp(), remaining);
}

/* ---------- player state sync ---------- */

function syncPause() {
  if (!isPlaying.value) return;
  isPlaying.value = false;
  resumeTime = currentTime.value;
  stopProgressTimer();
  pauseDurationTimer();
}

function syncPlay() {
  if (isPlaying.value) return;
  isPlaying.value = true;
  startProgressTimer();
  resumeDurationTimer();
}

/* ---------- user actions ---------- */

/** Unified handler called after iframe finishes loading (initial or seek-reload) */
let pausedByUser = false;

function onFrameReady() {
  if (iframeLoading.value) iframeLoading.value = false;
  // 如果用户在加载期间点了暂停，不要恢复播放
  if (pausedByUser) {
    pausedByUser = false;
    return;
  }
  syncPlay();
}

/** Attach load listener + fallback timeout to the current iframe element */
function setupFrameLoadHandler() {
  const iframe = iframeRef.value;
  if (!iframe) return;

  const onLoad = () => {
    iframe.removeEventListener("load", onLoad);
    clearTimeout(readyTimer);
    readyTimer = setTimeout(onFrameReady, 800);
  };
  iframe.addEventListener("load", onLoad);

  readyTimer = setTimeout(() => {
    iframe.removeEventListener("load", onLoad);
    onFrameReady();
  }, 8000);
}

/** Reload the iframe with a new start-second `t` param to force seek */
function seekTo(targetSec) {
  const t = Math.round(Math.max(props.startSec, Math.min(props.endSec, targetSec)));

  stopProgressTimer();
  pauseDurationTimer();
  clearTimeout(readyTimer);

  pausedByUser = false;   // seek = 明确要播放
  isPlaying.value = false; // re-enable syncPlay() after iframe reload
  currentTime.value = t;
  resumeTime = t;
  clipProgress.value = (t - props.startSec) / Math.max(1, props.endSec - props.startSec);

  const iframe = iframeRef.value;
  if (iframe) {
    iframe.src = createIframeUrl(t);
    setupFrameLoadHandler();
  }
}

function handleProgressClick(event) {
  if (timeUp.value || showStartOverlay.value) return;
  const rect = event.currentTarget.getBoundingClientRect();
  const fraction = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
  seekTo(props.startSec + fraction * (props.endSec - props.startSec));
}

function togglePlayPause() {
  if (isPlaying.value) {
    // 暂停：停止计时器 + 销毁 iframe（真正停止 B站 播放）
    syncPause();
    pausedByUser = true;
    clearTimeout(readyTimer);
    readyTimer = null;
    const iframe = iframeRef.value;
    if (iframe) {
      iframe.src = "about:blank";
    }
  } else {
    // 播放：从暂停位置重建 iframe，强制从该时间点开始
    pausedByUser = false;
    resumeTime = currentTime.value;
    isPlaying.value = false;
    const iframe = iframeRef.value;
    if (iframe) {
      iframe.src = createIframeUrl(resumeTime);
      setupFrameLoadHandler();
    }
  }
}

/* ---------- lifecycle ---------- */

function startWatching() {
  loadError.value = false;
  timeUp.value = false;
  showStartOverlay.value = false;
  isPlaying.value = false;
  pausedByUser = false;
  iframeLoading.value = true;
  resumeTime = props.startSec;
  currentTime.value = props.startSec;
  clipProgress.value = 0;
  // 强制全新 URL，避免 B站 缓存上次播放位置
  iframeUrl.value = createIframeUrl(props.startSec);

  nextTick(setupFrameLoadHandler);
}

function onTimeUp() {
  if (timeUp.value) return;
  stopProgressTimer();
  clearTimeout(durationTimer);
  durationTimer = null;
  clearTimeout(readyTimer);
  readyTimer = null;
  isPlaying.value = false;
  timeUp.value = true;
  emit("time-up");
}

function replay() {
  timeUp.value = false;
  startWatching();
}

function backToStart() {
  stopProgressTimer();
  clearTimeout(durationTimer);
  durationTimer = null;
  clearTimeout(readyTimer);
  readyTimer = null;
  showStartOverlay.value = true;
  timeUp.value = false;
  isPlaying.value = false;
  loadError.value = false;
  iframeLoading.value = false;
  currentTime.value = props.startSec;
  clipProgress.value = 0;
}

/* ---------- receive bilibili player events ---------- */

function handlePlayerMessage(event) {
  if (!event.data || typeof event.data.type !== "string") return;
  const { type, data } = event.data;

  switch (type) {
    case "player:play":
      syncPlay();
      break;
    case "player:pause":
      syncPause();
      break;
    case "player:timeupdate":
      if (data?.currentTime != null) {
        if (Math.abs(data.currentTime - currentTime.value) > 2) {
          currentTime.value = data.currentTime;
          resumeTime = data.currentTime;
          if (resumeWallTime) resumeWallTime = Date.now();
        }
      }
      break;
    case "player:ended":
      onTimeUp();
      break;
  }
}

onMounted(() => {
  window.addEventListener("message", handlePlayerMessage);
});

onUnmounted(() => {
  window.removeEventListener("message", handlePlayerMessage);
  stopProgressTimer();
  clearTimeout(durationTimer);
  clearTimeout(readyTimer);
});
</script>

<template>
  <div class="video-wrapper">
    <div class="video-container">
      <iframe
        v-if="!showStartOverlay && !timeUp"
        ref="iframeRef"
        :src="iframeUrl"
        class="bili-iframe"
        allow="autoplay"
        frameborder="0"
        scrolling="no"
      />

      <div v-if="!showStartOverlay && !timeUp && !loadError" class="player-mask">
        <div v-if="!isPlaying && !iframeLoading" class="paused-hint">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor" opacity="0.8">
            <path d="M8 5v14l11-7z"/>
          </svg>
          <span>点击下方按钮继续播放</span>
        </div>
      </div>

      <div v-if="iframeLoading" class="loading-placeholder">
        <p>视频加载中...</p>
      </div>

      <div v-if="loadError" class="error-placeholder">
        <el-icon :size="48" color="#c0c4cc"><WarningFilled /></el-icon>
        <p>Player failed to load</p>
      </div>

      <Transition name="fade">
        <div v-if="showStartOverlay && !timeUp && !loadError" class="start-overlay">
          <div class="overlay-content">
            <h3>{{ title || "clip" }}</h3>
            <p class="overlay-range">{{ formatTime(startSec) }} ~ {{ formatTime(endSec) }}</p>
            <p class="overlay-hint">{{ duration }} seconds, focus and watch carefully</p>
            <el-button type="primary" size="large" @click="startWatching">
              Start Watching
            </el-button>
          </div>
        </div>
      </Transition>

      <Transition name="fade">
        <div v-if="timeUp" class="time-barrier">
          <div class="barrier-content">
            <el-icon :size="32" color="#fff"><WarningFilled /></el-icon>
            <p class="barrier-title">Clip Finished</p>
            <p class="barrier-hint">Continue to practice or choose another clip</p>
            <div class="barrier-actions">
              <el-button type="primary" size="small" @click="replay">Replay</el-button>
              <el-button size="small" @click="backToStart">Back</el-button>
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <!-- bottom controls -->
    <div v-if="duration > 0" class="video-controls">
      <template v-if="showStartOverlay">
        <span class="timer">Not started</span>
        <span class="time-range">{{ formatTime(startSec) }} / {{ formatTime(endSec) }}</span>
        <el-button size="small" type="primary" @click="startWatching">Start</el-button>
      </template>

      <template v-else-if="!timeUp">
        <div class="progress-bar" @click="handleProgressClick">
          <div class="progress-fill" :style="{ width: clipProgress * 100 + '%' }" />
        </div>
        <button class="play-pause-btn" @click="togglePlayPause" :title="isPlaying ? '暂停' : '播放'">
          <!-- 暂停图标 -->
          <svg v-if="isPlaying" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="4" width="4" height="16" rx="1"/>
            <rect x="14" y="4" width="4" height="16" rx="1"/>
          </svg>
          <!-- 播放图标 -->
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z"/>
          </svg>
        </button>
        <span class="time-range">{{ formatTime(currentTime) }} / {{ formatTime(endSec) }}</span>
      </template>

      <template v-else>
        <span class="timer expired">Finished</span>
        <span class="time-range">{{ formatTime(startSec) }} / {{ formatTime(endSec) }}</span>
        <el-button size="small" type="primary" @click="replay">Replay</el-button>
        <el-button size="small" @click="backToStart">Back</el-button>
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
  border: none;
  z-index: 1;
}

.player-mask {
  position: absolute;
  inset: 0;
  z-index: 3;
  background: transparent;
  cursor: pointer;
}

.paused-hint {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: rgba(0, 0, 0, 0.45);
  color: rgba(255, 255, 255, 0.85);
  font-size: 14px;
  transition: opacity 0.3s;
}

.loading-placeholder,
.error-placeholder {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: #f5f7fa;
  color: #909399;
}

.start-overlay {
  position: absolute;
  inset: 0;
  z-index: 5;
  background: rgba(0, 0, 0, 0.6);
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

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

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

.progress-bar {
  flex: 1;
  height: 6px;
  background: #e5e6eb;
  border-radius: 3px;
  cursor: pointer;
  position: relative;
  min-width: 60px;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 3px;
  pointer-events: none;
}

.play-pause-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.2s;
}
.play-pause-btn:hover {
  background: var(--color-primary-dark, #2563eb);
}

.time-range {
  font-size: 12px;
  color: #c0c4cc;
  white-space: nowrap;
}
</style>
