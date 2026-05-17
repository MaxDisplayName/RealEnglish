import request from "@/api/shared/request";

export const listThreads = (role = "student") =>
  request.get("/assistants/threads", { params: { role } });

export const createThread = (role = "student") =>
  request.post("/assistants/threads", null, { params: { role } });

export const renameThread = (threadId, title) =>
  request.patch(`/assistants/threads/${threadId}`, { title });

export const deleteThread = (threadId) =>
  request.delete(`/assistants/threads/${threadId}`);

export const getThreadMessages = (threadId) =>
  request.get(`/assistants/threads/${threadId}/messages`);
