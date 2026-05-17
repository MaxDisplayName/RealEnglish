import { ref } from "vue";

/**
 * 录音逻辑封装（MediaRecorder PCM 16kHz/16bit/单声道）。
 * 用于口语练习的语音录制。
 */
export function useRecorder() {
  const mediaRecorder = ref(null);
  const audioChunks = ref([]);
  const isRecording = ref(false);
  const streamRef = ref(null);
  let _startTime = null;

  async function startRecording() {
    if (isRecording.value) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.value = stream;
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      mediaRecorder.value = new MediaRecorder(stream, { mimeType });
      audioChunks.value = [];
      _startTime = Date.now();
      mediaRecorder.value.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.value.push(e.data);
      };
      mediaRecorder.value.start();
      isRecording.value = true;
    } catch (err) {
      console.error("麦克风权限被拒或录音初始化失败:", err);
      throw new Error("无法访问麦克风，请检查权限设置");
    }
  }

  function stopRecording() {
    return new Promise((resolve, reject) => {
      if (!mediaRecorder.value || !isRecording.value) {
        reject(new Error("未在录音中"));
        return;
      }
      const duration = _startTime ? Math.round((Date.now() - _startTime) / 1000) : 0;
      mediaRecorder.value.onstop = () => {
        const blob = new Blob(audioChunks.value, { type: mediaRecorder.value.mimeType || "audio/webm" });
        if (streamRef.value) {
          streamRef.value.getTracks().forEach((track) => track.stop());
          streamRef.value = null;
        }
        isRecording.value = false;
        resolve({ blob, duration });
      };
      mediaRecorder.value.stop();
    });
  }

  function getDuration() {
    return _startTime ? Math.round((Date.now() - _startTime) / 1000) : 0;
  }

  return { isRecording, startRecording, stopRecording, getDuration };
}
