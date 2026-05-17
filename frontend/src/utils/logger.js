/**
 * 前端日志工具。
 * 在控制台输出的同时，将日志（按时间戳+信息）发送到后端统一写入文件。
 * 同时维护一个内存缓冲区，可通过 downloadLogs() 导出。
 */

const MAX_BUFFER = 200;
const FLUSH_INTERVAL = 30000; // 30 秒批量上传一次
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const buffer = [];
let _originalError = null;
let _originalWarn = null;
let flushTimer = null;

function addEntry(level, message, detail) {
  const entry = {
    timestamp: new Date().toISOString(),
    level,
    message,
    detail,
    url: location.href,
    userAgent: navigator.userAgent,
  };
  buffer.push(entry);
  if (buffer.length > MAX_BUFFER) buffer.shift();
}

async function flushToBackend() {
  if (buffer.length === 0) return;
  const entries = buffer.splice(0, buffer.length);
  try {
    await fetch(`${API_BASE}/logs/frontend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        level: "BATCH",
        message: `Flushing ${entries.length} frontend log entries`,
        detail: entries
          .map((e) => `[${e.timestamp}] ${e.level} ${e.message}`)
          .join("\n"),
      }),
    });
  } catch {
    // 静默失败，不递归
    // 把没发成功的放回缓冲区
    buffer.unshift(...entries);
  }
}

export function initLogger() {
  if (_originalError) return; // 已初始化

  _originalError = console.error;
  _originalWarn = console.warn;

  console.error = function (...args) {
    const msg = args.map((a) => (typeof a === "object" ? safeStringify(a) : String(a))).join(" ");
    addEntry("ERROR", msg, "");
    _originalError.apply(console, args);
  };

  console.warn = function (...args) {
    const msg = args.map((a) => (typeof a === "object" ? safeStringify(a) : String(a))).join(" ");
    addEntry("WARNING", msg, "");
    _originalWarn.apply(console, args);
  };

  // 捕获全局未处理错误
  window.addEventListener("error", (event) => {
    addEntry("ERROR", event.message, event.filename + ":" + event.lineno);
  });

  window.addEventListener("unhandledrejection", (event) => {
    addEntry("ERROR", "Unhandled Promise rejection", event.reason?.message || String(event.reason));
  });

  // 定期刷新到后端
  flushTimer = setInterval(flushToBackend, FLUSH_INTERVAL);

  // 页面关闭前尝试一次同步发送
  window.addEventListener("beforeunload", () => {
    if (flushTimer) clearInterval(flushTimer);
    // 同步发送剩余日志 (navigator.sendBeacon)
    if (buffer.length > 0) {
      try {
        navigator.sendBeacon(
          `${API_BASE}/logs/frontend`,
          JSON.stringify({
            level: "BATCH",
            message: `Flushing ${buffer.length} entries on beforeunload`,
            detail: buffer
              .map((e) => `[${e.timestamp}] ${e.level} ${e.message}`)
              .join("\n"),
          }),
        );
      } catch {
        // ignore
      }
    }
  });
}

export function downloadLogs() {
  const text = buffer
    .map((e) => `[${e.timestamp}] [${e.level}] ${e.message}${e.detail ? " | " + e.detail : ""}`)
    .join("\n");
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `frontend-log-${new Date().toISOString().slice(0, 10)}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

function safeStringify(obj) {
  try {
    return JSON.stringify(obj);
  } catch {
    return String(obj);
  }
}
