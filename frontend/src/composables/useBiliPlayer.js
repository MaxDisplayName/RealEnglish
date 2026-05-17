/**
 * B站 iframe 播放器 postMessage 控制 + 时间区间限制。
 *
 * 原理：
 * - B站 iframe 启用 jsapi=1 后，会通过 postMessage 发送播放事件
 * - 可发送 {"event":"pause"} 暂停播放
 * - 无法通过 postMessage seek，因此"重新播放"需重载 iframe
 */
import { ref, computed, onMounted, onUnmounted } from "vue";

export function useBiliPlayer(props) {
  const { startSec, endSec, iframeUrl } = props;

  const isPlaying = ref(false);
  const currentTime = ref(0);
  const isTimeUp = ref(false);
  const iframeLoaded = ref(false);
  /** 递增此值强制 <iframe :key> 重渲染，实现重新播放 */
  const playerKey = ref(0);

  const playerUrl = computed(() => {
    if (!iframeUrl) return "";
    try {
      const base = iframeUrl.includes("player.bilibili.com")
        ? iframeUrl
        : `https://player.bilibili.com/player.html?bvid=${iframeUrl}`;
      const url = new URL(base);
      if (startSec > 0) url.searchParams.set("t", startSec);
      url.searchParams.set("danmaku", "0");
      url.searchParams.set("jsapi", "1");
      url.searchParams.set("autoplay", "0");
      return url.toString();
    } catch {
      return iframeUrl;
    }
  });

  /** 向 iframe 发送暂停消息 */
  function postPause() {
    const iframe = document.querySelector(".bili-iframe");
    if (iframe?.contentWindow) {
      iframe.contentWindow.postMessage(
        JSON.stringify({ event: "pause" }),
        "https://player.bilibili.com"
      );
    }
  }

  function handleMessage(event) {
    if (event.origin !== "https://player.bilibili.com") return;

    try {
      const data =
        typeof event.data === "string" ? JSON.parse(event.data) : event.data;

      if (data?.info?.currentTime !== undefined) {
        currentTime.value = data.info.currentTime;
      }
      if (data?.info?.paused !== undefined) {
        isPlaying.value = !data.info.paused;
      }
      if (data?.event === "loaded" || data?.event === "error") {
        iframeLoaded.value = true;
      }

      // 到达结束时间 → 暂停
      if (endSec > 0 && currentTime.value >= endSec && !isTimeUp.value) {
        isTimeUp.value = true;
        isPlaying.value = false;
        postPause();
      }
    } catch {
      // 非 JSON 消息（如 B站心跳包）
    }
  }

  function play() {
    isTimeUp.value = false;
    isPlaying.value = true;
  }

  function pause() {
    postPause();
    isPlaying.value = false;
  }

  function reset() {
    pause();
    currentTime.value = 0;
    isTimeUp.value = false;
  }

  /** 重载 iframe（通过递增 key 强制 Vue 重新挂载） */
  function reload() {
    reset();
    playerKey.value++;
  }

  onMounted(() => {
    window.addEventListener("message", handleMessage);
  });

  onUnmounted(() => {
    window.removeEventListener("message", handleMessage);
    postPause();
  });

  return {
    isPlaying,
    currentTime,
    isTimeUp,
    iframeLoaded,
    playerKey,
    playerUrl,
    play,
    pause,
    reset,
    reload,
  };
}
