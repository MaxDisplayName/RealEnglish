import request from "@/modules/shared/request";

export const getTeacherDashboard = (params = {}) =>
  request.get("/teacher/dashboard", { params });

export const getTeacherAlerts = () =>
  request.get("/teacher/students/alerts/list");

export const getStudentList = (params) =>
  request.get("/teacher/students", { params });

export const getLevelDistribution = (params = {}) =>
  request.get("/teacher/students/level-distribution", { params });

export const getStudentDetail = (id) =>
  request.get(`/teacher/students/${id}`);

export const getTeacherGroups = () =>
  request.get("/teacher/groups");

export const createTeacherGroup = (data) =>
  request.post("/teacher/groups", data);

export const updateTeacherGroup = (groupId, data) =>
  request.put(`/teacher/groups/${groupId}`, data);

export const assignStudentGroup = (studentId, groupId) =>
  request.post("/teacher/students/assign-group", { student_id: studentId, group_id: groupId });

export const generateReport = (studentId) =>
  request.post("/teacher/reports/generate", { student_id: studentId });

export const getGroupDetail = (groupId) =>
  request.get(`/teacher/groups/${groupId}`);

export const deleteGroup = (groupId) =>
  request.delete(`/teacher/groups/${groupId}`);

export const batchAssignGroups = (studentIds, groupId) =>
  request.post("/teacher/students/batch-assign", { student_ids: studentIds, group_id: groupId });

export const getGroupsComparison = () =>
  request.get("/teacher/groups-comparison");

export const sendTeacherAssistantMessage = (message, history = [], studentId = null, groupId = null) =>
  request.post("/assistants/teacher/chat", {
    message,
    history,
    student_id: studentId,
    group_id: groupId,
  });

// Communication
export const getAnnouncements = (params = {}) =>
  request.get("/teacher/communication/announcements", { params });

export const createAnnouncement = (data) =>
  request.post("/teacher/communication/announcements", data);

export const updateAnnouncement = (id, data) =>
  request.put(`/teacher/communication/announcements/${id}`, data);

export const deleteAnnouncement = (id) =>
  request.delete(`/teacher/communication/announcements/${id}`);

export const pinAnnouncement = (id) =>
  request.patch(`/teacher/communication/announcements/${id}/pin`);

export const getReceivedMessages = () =>
  request.get("/teacher/communication/messages/received");

export const sendMessage = (data) =>
  request.post("/teacher/communication/messages/send", data);

// Tasks
export const getTeacherTasks = (params = {}) =>
  request.get("/teacher/tasks", { params });

export const createTask = (data) =>
  request.post("/teacher/tasks", data);

export const getTaskDetail = (id) =>
  request.get(`/teacher/tasks/${id}`);

export const updateTask = (id, data) =>
  request.put(`/teacher/tasks/${id}`, data);

export const deleteTask = (id) =>
  request.delete(`/teacher/tasks/${id}`);

export const toggleTaskStatus = (id) =>
  request.patch(`/teacher/tasks/${id}/status`);

export const getAllStudents = () =>
  request.get("/teacher/students/all");

export const batchUpdateLevel = (studentIds, level) =>
  request.post("/teacher/students/batch-level", { student_ids: studentIds, level });
