import axios from "axios";
import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { createRouter, createWebHashHistory } from "vue-router";
import { ElMessage } from "element-plus";

import {
  LoginPage,
  RegisterPage,
  StudentDashboardPage,
  PlacementTestPage,
  PlacementResultPage,
  ClipListPage,
  ClipDetailPage,
  PracticePage,
  SpeakingPracticePage,
  StudentAssistantPage,
  AIChatPage,
  FreeTalkPage,
  TeacherDashboardPage,
  TeacherGroupsPage,
  TeacherAssistantPage,
  TeacherCommunicationPage,
  TeacherTasksPage,
  TeacherStudentListPage,
  StudentInteractionsPage,
  AccumulatePage,
  StudentLayoutShell,
  TeacherLayoutShell,
} from "./pages.vue";

// request
export const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  timeout: 30000,
});

request.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("userInfo");
      localStorage.removeItem("userLevel");
    }
    let message = "网络错误";
    const detail = error.response?.data?.detail;
    if (Array.isArray(detail)) {
      message = detail.map((item) => item.msg).join("; ");
    } else if (typeof detail === "string") {
      message = detail;
    } else if (error.response?.data?.message) {
      message = error.response.data.message;
    }
    ElMessage.error(message);
    return Promise.reject(error);
  },
);

// auth
export const authApi = {
  register: (username, email, password, role = "student", inviteCode = "") =>
    request.post("/auth/register", {
      username, email, password, role,
      invite_code: inviteCode || undefined
    }),
  login: (loginValue, password, role = "") =>
    request.post("/auth/login", { login: loginValue, password, role: role || undefined }),
  getMe: () => request.get("/auth/me"),
  mergeDevice: (deviceId) => request.post("/auth/merge-device", { device_id: deviceId }),
};

// student
export const studentApi = {
  getClips: (params) => request.get("/clips", { params }),
  getClipDetail: (id) => request.get(`/clips/${id}`),
  getClipVideoUrl: (id) => request.get(`/clips/${id}/video-url`),
  getClipDashInfo: (id) => request.get(`/clips/${id}/dash`),
  getPlacementQuestions: () => request.get("/questions/placement"),
  generateQuestions: (clipId, difficulty) =>
    request.post("/questions/generate", { clip_id: clipId, difficulty }),
  submitAnswer: (questionId, selectedOption) =>
    request.post("/answers/submit", { question_id: questionId, selected_option: selectedOption }),
  submitPlacement: (answers) => request.post("/answers/submit-placement", { answers }),
  getRecommendedClips: (preference) =>
    request.post("/student/recommendations", { user_preference: preference }),
  sendStudentAssistantMessage: (message, history = []) =>
    request.post("/assistants/student/chat", { message, history }),
};

export async function streamStudentChatMessage({
  message,
  history = [],
  signal,
  onChunk,
  onDone,
  onError,
}) {
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

  const handleBlock = (block) => {
    const lines = block.split("\n");
    for (const rawLine of lines) {
      const line = rawLine.trimEnd();
      if (!line || line.startsWith(":") || !line.startsWith("data: ")) continue;
      const data = line.slice(6);
      if (data === "[DONE]") {
        completed = true;
        onDone?.();
        return;
      }
      try {
        const parsed = JSON.parse(data);
        if (parsed.content) onChunk?.(parsed.content);
        if (parsed.error) throw new Error(parsed.error);
      } catch (error) {
        onError?.(error);
        throw error;
      }
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";
      for (const block of blocks) {
        handleBlock(block);
        if (completed) return;
      }
    }
    buffer += decoder.decode();
    if (buffer.trim()) handleBlock(buffer);
    if (!completed) onDone?.();
  } catch (error) {
    if (error.name === "AbortError") throw error;
    onError?.(error);
    throw error;
  } finally {
    reader.releaseLock();
  }
}

// teacher
export const teacherApi = {
  getStudentList: (params) => request.get("/teacher/students", { params }),
  getLevelDistribution: (params = {}) => request.get("/teacher/students/level-distribution", { params }),
  getStudentDetail: (id) => request.get(`/teacher/students/${id}`),
  getTeacherGroups: () => request.get("/teacher/groups"),
  createTeacherGroup: (data) => request.post("/teacher/groups", data),
  updateTeacherGroup: (groupId, data) => request.put(`/teacher/groups/${groupId}`, data),
  assignStudentGroup: (studentId, groupId) =>
    request.post("/teacher/students/assign-group", { student_id: studentId, group_id: groupId }),
  generateReport: (studentId) => request.post("/teacher/reports/generate", { student_id: studentId }),
  sendTeacherAssistantMessage: (message, history = [], studentId = null, groupId = null) =>
    request.post("/assistants/teacher/chat", {
      message,
      history,
      student_id: studentId,
      group_id: groupId,
    }),
};

// store
export const useUserStore = defineStore("user", () => {
  const token = ref(localStorage.getItem("access_token") || null);
  const userInfo = ref(JSON.parse(localStorage.getItem("userInfo") || "null"));
  const level = ref(localStorage.getItem("userLevel") || null);

  const unreadCount = ref(0);

  const isLoggedIn = computed(() => !!token.value);
  const role = computed(() => userInfo.value?.role || null);
  const isStudent = computed(() => role.value === "student");
  const isTeacher = computed(() => role.value === "teacher");
  const placementDone = computed(() => !isStudent.value || !!level.value);

  function setLevel(newLevel) {
    level.value = newLevel || null;
    if (newLevel) localStorage.setItem("userLevel", newLevel);
    else localStorage.removeItem("userLevel");
  }

  function setSession(data) {
    token.value = data.access_token;
    userInfo.value = data.user;
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("userInfo", JSON.stringify(data.user));
    setLevel(data.user.level);
  }

  async function loginByAccount(loginValue, password, userRole = "") {
    const res = await authApi.login(loginValue, password, userRole);
    setSession(res.data);
    return res.data;
  }

  async function registerByAccount(username, email, password, userRole = "student", inviteCode = "") {
    const res = await authApi.register(username, email, password, userRole, inviteCode);
    setSession(res.data);
    return res.data;
  }

  function logout() {
    token.value = null;
    userInfo.value = null;
    level.value = null;
    localStorage.removeItem("access_token");
    localStorage.removeItem("userInfo");
    localStorage.removeItem("userLevel");
  }

  async function checkAuth() {
    if (!token.value) return false;
    try {
      const res = await authApi.getMe();
      userInfo.value = res.data;
      localStorage.setItem("userInfo", JSON.stringify(res.data));
      setLevel(res.data.level);
      return true;
    } catch {
      logout();
      return false;
    }
  }

  function getDefaultRoute() {
    if (isTeacher.value) return "/teacher";
    if (isStudent.value) return placementDone.value ? "/student" : "/student/placement-test";
    return "/login";
  }

  return {
    token,
    userInfo,
    level,
    unreadCount,
    role,
    isLoggedIn,
    isStudent,
    isTeacher,
    placementDone,
    setLevel,
    loginByAccount,
    registerByAccount,
    logout,
    checkAuth,
    getDefaultRoute,
  };
});

// router
const routes = [
  { path: "/", redirect: "/login" },
  { path: "/login", name: "Login", component: LoginPage, meta: { public: true, title: "登录" } },
  { path: "/register", name: "Register", component: RegisterPage, meta: { public: true, title: "注册" } },
  { path: "/profile", redirect: "/student" },
  {
    path: "/student",
    component: StudentLayoutShell,
    meta: { requiresAuth: true, role: "student" },
    children: [
      { path: "", name: "StudentDashboard", component: StudentDashboardPage, meta: { title: "学习概览" } },
      { path: "placement-test", name: "PlacementTest", component: PlacementTestPage, meta: { title: "定级测试", allowWithoutPlacement: true } },
      { path: "placement-result", name: "PlacementResult", component: PlacementResultPage, meta: { title: "测试结果", allowWithoutPlacement: true } },
      { path: "clips", name: "ClipList", component: ClipListPage, meta: { title: "影视片段" } },
      { path: "clips/:id", name: "ClipDetail", component: ClipDetailPage, meta: { title: "片段学习" } },
      { path: "practice/:clipId", name: "Practice", component: PracticePage, meta: { title: "答题练习" } },
      { path: "accumulate", name: "Accumulate", component: AccumulatePage, meta: { title: "我的积累" } },
      { path: "wrong-notes", redirect: "/student/accumulate" },
      { path: "vocabulary", redirect: "/student/accumulate" },
      { path: "speaking/:id", name: "SpeakingPractice", component: SpeakingPracticePage, meta: { title: "口语练习" } },
      { path: "assistant", name: "StudentAssistant", component: StudentAssistantPage, meta: { title: "学习助手" } },
      { path: "chat", name: "AIChat", component: AIChatPage, meta: { title: "AI 英语教练" } },
      { path: "free-talk", name: "FreeTalk", component: FreeTalkPage, meta: { title: "自由对话" } },
      { path: "interactions", name: "StudentInteractions", component: StudentInteractionsPage, meta: { title: "互动中心" } },
    ],
  },
  {
    path: "/teacher",
    component: TeacherLayoutShell,
    meta: { requiresAuth: true, role: "teacher" },
    children: [
      { path: "", name: "TeacherDashboard", component: TeacherDashboardPage, meta: { title: "教师看板" } },
      { path: "students", name: "TeacherStudents", component: TeacherStudentListPage, meta: { title: "学生管理" } },
      { path: "groups", redirect: "/teacher/students" },
      { path: "assistant", name: "TeacherAssistant", component: TeacherAssistantPage, meta: { title: "教师助手" } },
      { path: "communication", name: "TeacherCommunication", component: TeacherCommunicationPage, meta: { title: "通信中心" } },
      { path: "tasks", name: "TeacherTasks", component: TeacherTasksPage, meta: { title: "任务管理" } },
    ],
  },
  { path: "/dashboard", redirect: "/student" },
  { path: "/placement-test", redirect: "/student/placement-test" },
  { path: "/placement-result", redirect: "/student/placement-result" },
  { path: "/clips", redirect: "/student/clips" },
  { path: "/clips/:id", redirect: (to) => `/student/clips/${to.params.id}` },
  { path: "/practice/:clipId", redirect: (to) => `/student/practice/${to.params.clipId}` },
  { path: "/wrong-notes", redirect: "/student/wrong-notes" },
  { path: "/speaking/:id", redirect: (to) => `/student/speaking/${to.params.id}` },
  { path: "/ai-chat", redirect: "/student/chat" },
];

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const userStore = useUserStore();
  if (to.meta.public) {
    if (userStore.isLoggedIn) return userStore.getDefaultRoute();
    return true;
  }
  if (!userStore.isLoggedIn) return "/login";
  if (!userStore.userInfo) await userStore.checkAuth();
  if (to.meta.role && userStore.role !== to.meta.role) return userStore.getDefaultRoute();
  if (userStore.isStudent && to.path.startsWith("/student") && !userStore.placementDone && !to.meta.allowWithoutPlacement) {
    return "/student/placement-test";
  }
  return true;
});
