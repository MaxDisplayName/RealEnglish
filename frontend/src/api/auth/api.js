import request from "@/modules/shared/request";

export const register = (username, email, password, role = "student", inviteCode = "") =>
  request.post("/auth/register", { username, email, password, role, invite_code: inviteCode || undefined });

export const login = (loginValue, password) =>
  request.post("/auth/login", { login: loginValue, password });

export const getMe = () => request.get("/auth/me");

export const mergeDevice = (deviceId) =>
  request.post("/auth/merge-device", { device_id: deviceId });
