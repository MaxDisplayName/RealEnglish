<script setup>
import { ref, onMounted, onUnmounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQuizStore } from "@/stores/quiz";
import { getClipDetail, lookupWord, saveWord } from "@/modules/student/api";
import VideoPlayer from "@/components/VideoPlayer.vue";
import FloatingAssistant from "@/components/FloatingAssistant.vue";
import { parseDialogue } from "@/utils/dialogueParser";
import { useSpeech } from "@/composables/useSpeech";
import { ArrowLeft, Promotion, Headset } from "@element-plus/icons-vue";

const route = useRoute();
const router = useRouter();
const quizStore = useQuizStore();
const { speakText, speakDialogues, stopSpeaking } = useSpeech();

const clip = ref(null);
const loading = ref(true);
const error = ref(null);
const generating = ref(false);
const userLevel = ref(localStorage.getItem("userLevel") || "B");

// 中英对照控制
const showEnglish = ref(true);
const showChinese = ref(false);
const translating = ref(false);
const dialogueZhText = ref(""); // 流式翻译累积结果
const translationError = ref("");

// 单词查询 popover
const lookupWordRef = ref("");
const lookupDef = ref("");
const lookupLoading = ref(false);
const lookupSaved = ref(false);
const lookupVisible = ref(false);
const lookupX = ref(0);
const lookupY = ref(0);
let dragState = null;

function startDrag(e) {
  if (e.target.tagName === "BUTTON" || e.target.tagName === "INPUT") return;
  dragState = { sx: e.clientX, sy: e.clientY, px: lookupX.value, py: lookupY.value };
  document.addEventListener("mousemove", onDragMove);
  document.addEventListener("mouseup", stopDrag);
  e.preventDefault();
}

function onDragMove(e) {
  if (!dragState) return;
  lookupX.value = Math.max(0, Math.min(window.innerWidth - 320, dragState.px + e.clientX - dragState.sx));
  lookupY.value = Math.max(0, Math.min(window.innerHeight - 40, dragState.py + e.clientY - dragState.sy));
}

function stopDrag() {
  dragState = null;
  document.removeEventListener("mousemove", onDragMove);
  document.removeEventListener("mouseup", stopDrag);
}

async function handleWordClick(word, event) {
  const clean = word.replace(/[^a-zA-Z'-]/g, "").toLowerCase();
  if (clean.length < 2) return;
  lookupWordRef.value = word;
  lookupDef.value = "";
  lookupLoading.value = true;
  lookupSaved.value = false;
  lookupX.value = Math.min(event.clientX, winWidth.value - 320);
  lookupY.value = event.clientY + 16;
  lookupVisible.value = true;
  try {
    const res = await lookupWord(clean, clip.value?.id);
    lookupDef.value = res.data?.definition || "";
  } catch {
    lookupDef.value = "查询失败，请重试";
  } finally {
    lookupLoading.value = false;
  }
}

async function handleSaveLookup() {
  if (!lookupWordRef.value) return;
  const clean = lookupWordRef.value.replace(/[^a-zA-Z'-]/g, "").toLowerCase();
  try {
    await saveWord(clean, clip.value?.id, lookupDef.value);
    lookupSaved.value = true;
  } catch { /* */ }
}

const winWidth = ref(window.innerWidth);

function closeLookup() {
  lookupVisible.value = false;
}

/** 加载缓存的翻译 */
function loadCachedTranslation(clipId) {
  const cache = localStorage.getItem(`clip_zh_${clipId}`);
  return cache || "";
}

/** 保存翻译缓存 */
function saveCachedTranslation(clipId, text) {
  localStorage.setItem(`clip_zh_${clipId}`, text);
}

/** 解析中文翻译文本为行数组 */
const dialogueLinesZh = computed(() => {
  if (!dialogueZhText.value) return [];
  return parseDialogue(dialogueZhText.value, clip.value?.character_genders);
});

/** 解析后的对话行 */
const dialogueLines = computed(() => {
  if (!clip.value?.dialogue_text) return [];
  return parseDialogue(clip.value.dialogue_text, clip.value.character_genders);
});

/** 获取中文翻译文本（按索引匹配） */
function getZhText(idx) {
  if (idx < dialogueLinesZh.value.length) {
    return dialogueLinesZh.value[idx].text;
  }
  return "";
}

/** 获取角色的性别图标/标签 */
function genderLabel(gender) {
  return gender === "male" ? "男声" : "女声";
}

function genderTagType(gender) {
  return gender === "male" ? "info" : "success";
}

onUnmounted(() => { stopSpeaking(); });

onMounted(async () => {
  const id = route.params.id;
  try {
    const clipRes = await getClipDetail(id);
    clip.value = clipRes.data;
    dialogueZhText.value = loadCachedTranslation(id);
  } catch (e) {
    error.value = e.response?.data?.detail || "加载片段失败";
  } finally {
    loading.value = false;
  }
});

/** 流式调用大模型翻译 */
async function handleTranslate() {
  if (!clip.value) return;
  const clipId = clip.value.id;

  // 切换回英文
  if (showChinese.value) {
    showChinese.value = false;
    return;
  }

  // 已有缓存直接显示
  if (dialogueZhText.value) {
    showChinese.value = true;
    return;
  }

  // 开始流式翻译
  showChinese.value = true;
  translating.value = true;
  translationError.value = "";
  dialogueZhText.value = "";

  try {
    const token = localStorage.getItem("access_token");
    const resp = await fetch(`/api/v1/clips/${clipId}/translate/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    });
    if (!resp.ok) throw new Error("翻译请求失败");
    if (!resp.body) throw new Error("无响应");

    const reader = resp.body.getReader();
    const dec = new TextDecoder("utf-8");
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() || "";
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const evt = JSON.parse(line);
          if (evt.type === "content") {
            dialogueZhText.value += evt.content;
          } else if (evt.type === "error") {
            translationError.value = evt.message || "翻译失败";
          }
        } catch { /* */ }
      }
    }

    if (dialogueZhText.value) {
      saveCachedTranslation(clipId, dialogueZhText.value);
    }
  } catch {
    if (!dialogueZhText.value) translationError.value = "翻译服务暂不可用，请稍后重试";
  } finally {
    translating.value = false;
  }
}

/** 重新生成翻译 */
function handleRegenerate() {
  const clipId = clip.value?.id;
  if (clipId) localStorage.removeItem(`clip_zh_${clipId}`);
  dialogueZhText.value = "";
  translationError.value = "";
  handleTranslate();
}

async function handleGenerate() {
  if (!clip.value) return;
  generating.value = true;
  try {
    await quizStore.generateQuestionsForClip(clip.value.id, userLevel.value);
    router.push(`/practice/${clip.value.id}`);
  } finally {
    generating.value = false;
  }
}

function handlePlayLine(line) {
  stopSpeaking();
  speakText(line.text, line.gender || "female", "en-US");
}

function handlePlayAll() {
  if (isSpeaking.value) {
    stopSpeaking();
    isSpeaking.value = false;
    return;
  }
  isSpeaking.value = true;
  speakDialogues(dialogueLines.value);
  // 监听朗读结束
  const checkEnd = setInterval(() => {
    if (!window.speechSynthesis.speaking) {
      isSpeaking.value = false;
      clearInterval(checkEnd);
    }
  }, 200);
}

</script>

<template>
  <div class="clip-detail">
    <!-- Loading -->
    <div v-if="loading">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="state-wrap">
      <el-result icon="error" title="加载失败" :sub-title="error">
        <template #extra>
          <el-button size="small" :icon="ArrowLeft" text @click="router.push('/clips')">返回片段库</el-button>
        </template>
      </el-result>
    </div>

    <!-- 404 -->
    <div v-else-if="!clip" class="state-wrap">
      <el-result icon="warning" title="片段不存在">
        <template #extra>
          <el-button type="primary" @click="router.push('/clips')">返回片段库</el-button>
        </template>
      </el-result>
    </div>

    <!-- Content -->
    <div v-else class="detail-content">
      <!-- 顶部返回按钮 -->
      <div class="page-top">
        <el-button size="small" :icon="ArrowLeft" text @click="router.push('/clips')">返回片段库</el-button>
      </div>

      <!-- B站 iframe 播放器（遮罩层防止用户操纵，定时器控制片段时长） -->
      <div v-if="clip.bvid" class="video-section">
        <VideoPlayer
          :bvid="clip.bvid"
          :page="clip.page || 1"
          :start-sec="clip.start_sec"
          :end-sec="clip.end_sec"
          :title="clip.title"
        />
      </div>

      <!-- 信息区 -->
      <div class="info-section">
        <div class="info-header">
          <h2>{{ clip.title }}</h2>
          <span class="diff-badge" :class="'diff-' + clip.difficulty.toLowerCase()">{{ clip.difficulty }}级</span>
        </div>
        <p class="info-meta">
          {{ clip.category }} &middot; 字幕来源: {{ clip.subtitle_source || "未知" }}
        </p>
      </div>

      <!-- 对话文本：分角色显示 + 朗读 -->
      <div class="dialogue-section">
        <div class="dialogue-header">
          <h3>对话文本</h3>
          <div class="header-actions">
            <div class="toggle-group">
              <el-check-tag :checked="showEnglish" @change="showEnglish = $event">英文原文</el-check-tag>
              <el-check-tag
                :checked="showChinese"
                @change="handleTranslate"
                :type="showChinese ? 'primary' : 'info'"
              >大模型翻译</el-check-tag>
              <el-button
                v-if="dialogueZhText && !translating"
                size="small"
                class="regenerate-btn"
                @click="handleRegenerate"
              >重新生成</el-button>
            </div>
            <el-button
              v-if="dialogueLines.length > 0"
              :type="isSpeaking ? 'danger' : 'default'"
              size="small"
              @click="handlePlayAll"
            >
              <el-icon v-if="!isSpeaking" style="margin-right:4px"><Promotion /></el-icon>
              {{ isSpeaking ? "停止朗读" : "朗读全部" }}
            </el-button>
          </div>
        </div>

        <div v-if="dialogueLines.length === 0" class="dialogue-empty">
          暂无对话文本
        </div>

        <div v-else class="dialogue-list">
          <div
            v-for="(line, idx) in dialogueLines"
            :key="idx"
            class="dialogue-line"
          >
            <div class="line-speaker">
              <span class="speaker-name">{{ line.speaker }}</span>
              <el-tag :type="genderTagType(line.gender)" size="small" class="gender-tag">
                {{ genderLabel(line.gender) }}
              </el-tag>
            </div>
            <div class="line-content">
              <div v-if="showEnglish" class="line-en">
                <span
                  v-for="(w, wi) in line.text.split(' ')"
                  :key="wi"
                  class="line-word"
                  @click.stop="handleWordClick(w, $event)"
                >{{ w }}{{ wi < line.text.split(' ').length - 1 ? ' ' : '' }}</span>
              </div>
              <div v-if="showChinese && translating && !dialogueZhText" class="line-zh-streaming">
                <span class="zh-placeholder">翻译生成中，请稍候</span>
                <span class="dot-wave"><i /><i /><i /></span>
              </div>
              <div v-else-if="showChinese && translationError" class="line-zh">
                <span class="zh-placeholder">{{ translationError }}</span>
              </div>
              <div v-else-if="showChinese" class="line-zh">
                <template v-if="getZhText(idx)">{{ getZhText(idx) }}</template>
                <span v-else-if="translating" class="zh-placeholder">...</span>
                <span v-else class="zh-placeholder">翻译加载中或暂不可用</span>
              </div>
            </div>
            <div class="line-actions">
              <el-button
                size="small"
                circle
                :title="'朗读此句'"
                @click="handlePlayLine(line)"
              >
                <el-icon><Headset /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 剧情摘要 -->
      <div v-if="clip.summary" class="summary-section">
        <h3>剧情摘要</h3>
        <p>{{ clip.summary }}</p>
      </div>

      <!-- 操作按钮 -->
      <div class="action-section">
        <el-button type="primary" :loading="generating" @click="handleGenerate">
          {{ generating ? "AI 正在出题..." : "AI 智能出题" }}
        </el-button>
        <el-button type="success" @click="router.push(`/speaking/${clip.id}`)">
          口语练习
        </el-button>
      </div>
    </div>

    <!-- 单词查询弹出卡片 -->
    <teleport to="body">
      <div
        v-if="lookupVisible"
        class="word-lookup-card"
        :style="{ left: lookupX + 'px', top: lookupY + 'px' }"
      >
        <div class="wlc-header" @mousedown="startDrag">
          <strong>{{ lookupWordRef }}</strong>
          <button class="wlc-close" @click="closeLookup">&times;</button>
        </div>
        <div class="wlc-body">
          <el-skeleton v-if="lookupLoading" :rows="2" animated />
          <p v-else>{{ lookupDef || '未找到释义' }}</p>
        </div>
        <div class="wlc-footer">
          <el-button size="small" :type="lookupSaved ? 'success' : 'primary'" :disabled="lookupSaved || lookupLoading" @click="handleSaveLookup">
            {{ lookupSaved ? '已收藏' : '收藏到单词本' }}
          </el-button>
        </div>
      </div>
    </teleport>

    <!-- 点击空白关闭 -->
    <div v-if="lookupVisible" class="wlc-backdrop" @click="closeLookup" />

    <!-- 悬浮片段学习助手 -->
    <FloatingAssistant
      v-if="clip"
      :clip-id="clip.id"
      :clip-title="clip.title"
    />
  </div>
</template>

<style scoped>
.clip-detail {
  max-width: 800px;
  margin: 0 auto;
}

.page-top {
  margin-bottom: 16px;
}

.state-wrap {
  margin-top: 60px;
}

.detail-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.video-section {
  margin-bottom: 16px;
}

.info-section {
  margin: 20px 0;
  padding: 16px 20px;
  background: #fff;
  border-radius: var(--radius-base);
}

.info-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.info-header h2 {
  font-size: 20px;
  color: var(--text-main);
}

.info-meta {
  font-size: 13px;
  color: var(--text-secondary);
}

/* ===== 对话区域 ===== */
.dialogue-section,
.summary-section {
  margin-bottom: 20px;
  padding: 20px;
  background: #fff;
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-card);
}

.dialogue-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
}

.dialogue-header h3,
.summary-section h3 {
  font-size: 16px;
  color: var(--text-main);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toggle-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.regenerate-btn {
  background: #FF9600 !important;
  border-color: #FF9600 !important;
  color: #fff !important;
  box-shadow: 0 3px 0 #D97D00;
  transform: translateY(0);
  transition: all .15s ease;
}
.regenerate-btn:hover {
  transform: translateY(2px);
  box-shadow: 0 1px 0 #D97D00;
}
.regenerate-btn:active {
  transform: translateY(3px);
  box-shadow: none;
}

.dialogue-empty {
  color: var(--text-secondary);
  font-size: 14px;
  text-align: center;
  padding: 30px 0;
}

.dialogue-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.dialogue-line {
  display: flex;
  align-items: flex-start;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
  gap: 12px;
}

.dialogue-line:last-child {
  border-bottom: none;
}

.line-speaker {
  min-width: 80px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.speaker-name {
  font-weight: 700;
  font-size: 14px;
  color: var(--color-primary);
  white-space: nowrap;
}

.gender-tag {
  font-size: 10px;
}

.line-content {
  flex: 1;
  min-width: 0;
}

.line-en {
  font-size: 14px;
  color: var(--text-main);
  line-height: 1.6;
}

.line-word {
  cursor: pointer; border-radius: 3px; transition: all .12s; padding: 1px 0;
}
.line-word:hover { background: #E5F8D1; color: #58CC02; }

/* word lookup card */
.word-lookup-card {
  position: fixed; z-index: 2500; width: 300px;
  background: #fff; border-radius: 14px; box-shadow: 0 12px 40px rgba(0,0,0,.15);
  border: 1px solid #EBEDF0; overflow: hidden;
}
.wlc-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; background: #F8FAF6; border-bottom: 1px solid #EBEDF0;
  cursor: grab; user-select: none;
}
.wlc-header:active { cursor: grabbing; }
.wlc-header strong { font-size: 15px; color: #303133; }
.wlc-close {
  width: 24px; height: 24px; border-radius: 50%; border: none;
  background: #EBEBEB; cursor: pointer; font-size: 14px; display: flex;
  align-items: center; justify-content: center; color: #909399;
}
.wlc-close:hover { background: #F56C6C; color: #fff; }
.wlc-body { padding: 12px 16px; font-size: 13px; color: #606266; line-height: 1.7; white-space: pre-line; min-height: 48px; }
.wlc-footer { padding: 10px 16px; border-top: 1px solid #EBEDF0; text-align: right; }

.wlc-backdrop { position: fixed; inset: 0; z-index: 2499; }

.line-zh {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-top: 4px;
}

.zh-placeholder {
  color: #C0C4CC;
  font-style: italic;
  font-size: 12px;
}

.line-zh-streaming {
  font-size: 13px;
  color: #58CC02;
  line-height: 1.6;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot-wave {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.dot-wave i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #58CC02;
  animation: dotPulse 1.2s ease-in-out infinite;
}
.dot-wave i:nth-child(2) { animation-delay: 0.2s; }
.dot-wave i:nth-child(3) { animation-delay: 0.4s; }
@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}

.line-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.summary-section p {
  font-size: 14px;
  line-height: 1.8;
  color: #606266;
}

.action-section {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  flex-wrap: wrap;
}
</style>
