import request from "@/modules/shared/request";

export const getClips = (params) => request.get("/clips", { params });

export const getClipDetail = (id) => request.get(`/clips/${id}`);

export const getClipVideoUrl = (id) => request.get(`/clips/${id}/video-url`);

export const getClipDashInfo = (id) => request.get(`/clips/${id}/dash`);

export const getPlacementQuestions = () => request.get("/questions/placement");

export const generateQuestions = (clipId, difficulty) =>
  request.post("/questions/generate", { clip_id: clipId, difficulty });

export const submitAnswer = (questionId, selectedOption) =>
  request.post("/answers/submit", { question_id: questionId, selected_option: selectedOption });

export const submitPlacement = (answers) =>
  request.post("/answers/submit-placement", { answers });

export const getRecommendedClips = (preference) =>
  request.post("/student/recommendations", { user_preference: preference });

export const evaluateSpeaking = (audioBlob, referenceText, mode = "repeat", clipId = null, durationSec = 0) => {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");
  formData.append("reference_text", referenceText);
  formData.append("mode", mode);
  formData.append("duration_sec", String(durationSec));
  if (clipId) {
    formData.append("clip_id", clipId);
  }
  return request.post("/speaking/evaluate", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const getDashboard = () => request.get("/student/dashboard");

export const generateSpeakingQuestion = (summary) => {
  const formData = new FormData();
  formData.append("summary", summary);
  return request.post("/speaking/generate-question", formData);
};

export const sendStudentAssistantMessage = (message, history = []) =>
  request.post("/assistants/student/chat", { message, history });

export const startFreeTalk = () =>
  request.post("/free-talk/start");

export const respondFreeTalk = (conversationId, text) => {
  const formData = new FormData();
  formData.append("text", text);
  return request.post(`/free-talk/${conversationId}/respond`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const respondFreeTalkWithVoice = (conversationId, audioBlob) => {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");
  return request.post(`/free-talk/${conversationId}/respond`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const endFreeTalk = (conversationId) =>
  request.post(`/free-talk/${conversationId}/end`);

export const getFreeTalkHistory = (conversationId) =>
  request.get(`/free-talk/${conversationId}`);

export const streamStudentChatMessage = async ({
  message,
  history = [],
  signal,
  onChunk,
  onDone,
  onError,
}) => {
  const token = localStorage.getItem("access_token");
  const headers = {
    Accept: "text/event-stream",
    "Content-Type": "application/json",
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || "/api/v1"}/chat/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({ message, history }),
    signal,
  });

  if (!response.ok) {
    throw new Error("连接流式服务失败");
  }

  if (!response.body) {
    throw new Error("浏览器未返回可读取的流式响应");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let completed = false;

  const handleSseBlock = (block) => {
    const lines = block.split("\n");
    for (const rawLine of lines) {
      const line = rawLine.trimEnd();
      if (!line || line.startsWith(":") || !line.startsWith("data: ")) {
        continue;
      }

      const data = line.slice(6);
      if (data === "[DONE]") {
        completed = true;
        onDone?.();
        return;
      }

      try {
        const parsed = JSON.parse(data);
        if (parsed.content) {
          onChunk?.(parsed.content);
        }
        if (parsed.error) {
          throw new Error(parsed.error);
        }
      } catch (error) {
        onError?.(error);
        throw error;
      }
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";

      for (const block of blocks) {
        handleSseBlock(block);
        if (completed) {
          return;
        }
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) {
      handleSseBlock(buffer);
    }

    if (!completed) {
      onDone?.();
    }
  } catch (error) {
    if (error.name === "AbortError") {
      throw error;
    }
    onError?.(error);
    throw error;
  } finally {
    reader.releaseLock();
  }
};

// Interactions
export const getStudentAnnouncements = () =>
  request.get("/student/interactions/announcements");

export const getStudentMessages = () =>
  request.get("/student/interactions/messages");

export const sendStudentMessage = (data) =>
  request.post("/student/interactions/messages", data);

export const getStudentTasks = () =>
  request.get("/student/interactions/tasks");

// Vocabulary
export const lookupWord = (word, clipId = null) =>
  request.post("/vocabulary/lookup", { word, clip_id: clipId });

export const saveWord = (word, clipId = null, definition = "") =>
  request.post("/vocabulary/save", { word, clip_id: clipId, definition });

export const deleteWord = (vocabId) =>
  request.delete(`/vocabulary/${vocabId}`);

export const getVocabulary = (params = {}) =>
  request.get("/vocabulary", { params });

export const toggleMastered = (vocabId) =>
  request.patch(`/vocabulary/${vocabId}/mastered`);
