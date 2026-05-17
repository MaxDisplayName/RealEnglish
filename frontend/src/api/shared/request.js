import axios from "axios";
import { ElMessage } from "element-plus";

const request = axios.create({
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

export default request;
