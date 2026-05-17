<script setup>
import { ref, computed, onMounted } from "vue";
import { getVocabulary, deleteWord, toggleMastered } from "@/api/student/api";
import { ArrowLeft } from "@element-plus/icons-vue";

const words = ref([]);
const loading = ref(true);
const total = ref(0);
const page = ref(1);
const pageSize = 50;
const sort = ref("newest");
const reviewMode = ref(false);
const showDef = ref({});

async function loadWords() {
  loading.value = true;
  try {
    const res = await getVocabulary({ page: page.value, page_size: pageSize, sort: sort.value });
    words.value = res.data?.items || [];
    total.value = res.data?.total || 0;
  } catch {
    words.value = [];
  } finally {
    loading.value = false;
  }
}

async function handleDelete(vocabId) {
  await deleteWord(vocabId);
  words.value = words.value.filter(w => w.id !== vocabId);
  total.value = Math.max(0, total.value - 1);
}

async function handleToggle(vocabId) {
  try {
    const res = await toggleMastered(vocabId);
    const w = words.value.find(v => v.id === vocabId);
    if (w) w.mastered = res.data.mastered;
  } catch { /* */ }
}

function toggleReview() {
  reviewMode.value = !reviewMode.value;
  showDef.value = {};
}

function toggleDef(id) {
  showDef.value[id] = !showDef.value[id];
}

const masteredCount = computed(() => words.value.filter(w => w.mastered).length);

const progressPct = computed(() => total.value > 0 ? Math.round(masteredCount.value / total.value * 100) : 0);

onMounted(loadWords);
</script>

<template>
  <div class="vocab-page">
    <!-- 顶部导航 -->
    <div class="page-top">
      <el-button size="small" :icon="ArrowLeft" text @click="$router.push('/student')">返回首页</el-button>
    </div>

    <!-- 标题区 -->
    <div class="page-hero">
      <div class="hero-left">
        <h2 class="hero-title">单词本</h2>
        <p class="hero-sub">{{ total > 0 ? `${total} 个单词 · 已掌握 ${masteredCount} 个` : '在影视片段中点击单词即可收藏' }}</p>
      </div>
      <div v-if="total > 0" class="hero-ring" :style="{ '--pct': progressPct }">
        <svg width="72" height="72" viewBox="0 0 72 72">
          <circle cx="36" cy="36" r="31" fill="none" stroke="#EBEDF0" stroke-width="5" />
          <circle
            cx="36" cy="36" r="31" fill="none" stroke="#58CC02" stroke-width="5"
            stroke-linecap="round" stroke-dasharray="194.8" transform="rotate(-90 36 36)"
            :stroke-dashoffset="194.8 - 194.8 * progressPct / 100"
            style="transition: stroke-dashoffset .8s cubic-bezier(.4,0,.2,1)"
          />
        </svg>
        <span class="ring-num">{{ progressPct }}%</span>
      </div>
    </div>

    <!-- 进度条 -->
    <div v-if="total > 0" class="progress-bar-wrap">
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: progressPct + '%' }" />
      </div>
      <span class="progress-label">{{ masteredCount }} / {{ total }}</span>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <el-radio-group v-model="sort" size="small" @change="loadWords">
        <el-radio-button value="newest">最新</el-radio-button>
        <el-radio-button value="alphabet">A-Z</el-radio-button>
        <el-radio-button value="mastered">未掌握</el-radio-button>
      </el-radio-group>
      <el-button
        size="small"
        :class="reviewMode ? 'review-btn-on' : 'review-btn'"
        @click="toggleReview"
      >{{ reviewMode ? '退出复习' : '复习模式' }}</el-button>
    </div>

    <!-- 加载态 -->
    <div v-if="loading" class="state-wrap">
      <div class="skel-word" v-for="i in 4" :key="i">
        <div class="skel-line w40" /><div class="skel-line w80" />
      </div>
    </div>

    <!-- 空态 -->
    <div v-else-if="words.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#C0C4CC" stroke-width="1.2">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /><line x1="8" y1="7" x2="16" y2="7" /><line x1="8" y1="11" x2="14" y2="11" />
        </svg>
      </div>
      <h3>单词本是空的</h3>
      <p>在影视片段中点击任意英文单词，即可查看释义并收藏到这里</p>
    </div>

    <!-- 单词列表 -->
    <div v-else class="word-list">
      <div
        v-for="(w, idx) in words"
        :key="w.id"
        class="word-card"
        :class="{ mastered: w.mastered, revealed: showDef[w.id] }"
        :style="{ animationDelay: idx * 0.04 + 's' }"
      >
        <div class="card-left">
          <span class="word-index">{{ idx + 1 }}</span>
        </div>
        <div class="card-body">
          <div class="word-head">
            <span
              class="word-text"
              :class="{ clickable: reviewMode }"
              @click="reviewMode && toggleDef(w.id)"
            >{{ w.word }}</span>
            <span v-if="w.mastered" class="mastered-dot" title="已掌握">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#58CC02" stroke-width="3"><polyline points="20 6 9 17 4 12" /></svg>
            </span>
          </div>
          <div v-if="!reviewMode || showDef[w.id]" class="word-def">{{ w.definition || '释义加载中...' }}</div>
          <div v-else class="word-def-masked" @click="toggleDef(w.id)">
            <span class="mask-bars">
              <i v-for="n in 8" :key="n" class="mask-bar" :style="{ height: (12 + Math.sin(n * 1.2) * 8) + 'px' }" />
            </span>
          </div>
        </div>
        <div class="card-actions">
          <button
            class="act-btn master-btn"
            :class="{ on: w.mastered }"
            @click="handleToggle(w.id)"
            :title="w.mastered ? '取消掌握' : '标记已掌握'"
          >
            <svg v-if="w.mastered" width="15" height="15" viewBox="0 0 24 24" fill="#58CC02" stroke="#58CC02" stroke-width="1.5"><polyline points="20 6 9 17 4 12" /></svg>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#909399" stroke-width="1.8"><polyline points="20 6 9 17 4 12" /></svg>
          </button>
          <button class="act-btn del-btn" @click="handleDelete(w.id)" title="删除">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#C0C4CC" stroke-width="1.8"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ════ Layout ════ */
.vocab-page {
  max-width: 720px; margin: 0 auto; padding-bottom: 60px;
}

.page-top { margin-bottom: 8px; }

/* ════ Hero ════ */
.page-hero {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 6px;
}
.hero-title { font-size: 26px; font-weight: 800; color: #2B2B2B; margin: 0; letter-spacing: -.02em; }
.hero-sub { margin: 4px 0 0; font-size: 13px; color: #909399; font-weight: 500; }

.hero-ring { position: relative; flex-shrink: 0; }
.ring-num {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 800; color: #58CC02;
}

/* ════ Progress Bar ════ */
.progress-bar-wrap {
  display: flex; align-items: center; gap: 10px; margin-bottom: 20px;
}
.progress-track {
  flex: 1; height: 6px; background: #F0F2F5; border-radius: 10px; overflow: hidden;
}
.progress-fill {
  height: 100%; background: linear-gradient(90deg, #58CC02, #7BE028); border-radius: 10px;
  transition: width .6s cubic-bezier(.4,0,.2,1);
}
.progress-label { font-size: 11px; font-weight: 700; color: #C0C4CC; white-space: nowrap; min-width: 40px; text-align: right; }

/* ════ Toolbar ════ */
.toolbar {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px;
}
.review-btn {
  background: #F5F7FA; border: 1.5px solid #E4E7ED; color: #606266; font-weight: 600;
  transition: all .2s;
}
.review-btn:hover { border-color: #58CC02; color: #58CC02; }
.review-btn-on {
  background: #E5F8D1; border: 1.5px solid #58CC02; color: #46A302; font-weight: 700;
  box-shadow: 0 0 0 3px rgba(88,204,2,.08);
}

/* ════ Skeleton ════ */
.state-wrap { margin-top: 24px; }
.skel-word {
  background: #fff; border: 1.5px solid #EBEDF0; border-radius: 14px;
  padding: 18px 20px; margin-bottom: 10px;
}
.skel-line { height: 10px; background: #F0F2F5; border-radius: 4px; margin-bottom: 8px; animation: skelPulse 1.5s ease-in-out infinite; }
.skel-line.w40 { width: 40%; }
.skel-line.w80 { width: 80%; }
@keyframes skelPulse { 0%, 100% { opacity: .5; } 50% { opacity: 1; } }

/* ════ Empty ════ */
.empty-state {
  text-align: center; padding: 60px 20px;
}
.empty-icon { margin-bottom: 16px; }
.empty-state h3 { font-size: 18px; font-weight: 700; color: #909399; margin: 0 0 6px; }
.empty-state p { font-size: 13px; color: #C0C4CC; line-height: 1.6; max-width: 300px; margin: 0 auto; }

/* ════ Word List ════ */
.word-list { display: flex; flex-direction: column; gap: 8px; }

.word-card {
  background: #fff; border: 1.5px solid #EBEDF0; border-radius: 14px;
  padding: 16px 16px 16px 12px; display: flex; align-items: flex-start; gap: 12px;
  transition: all .25s cubic-bezier(.4,0,.2,1);
  animation: cardIn .4s cubic-bezier(.16,1,.3,1) both;
  position: relative; overflow: hidden;
}
.word-card::after {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: transparent; border-radius: 0 3px 3px 0; transition: background .25s;
}
.word-card:hover { border-color: #D4D8DF; box-shadow: 0 3px 14px rgba(0,0,0,.05); transform: translateY(-1px); }
.word-card:hover::after { background: #58CC02; }
.word-card.mastered { background: #FBFDF9; }
.word-card.mastered::after { background: #A8E06E; }

@keyframes cardIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.card-left { flex-shrink: 0; padding-top: 2px; }
.word-index {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 6px;
  background: #F5F7FA; font-size: 10px; font-weight: 700; color: #C0C4CC;
}

.card-body { flex: 1; min-width: 0; }

.word-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.word-text {
  font-size: 17px; font-weight: 700; color: #2B2B2B; letter-spacing: -.01em;
  transition: color .15s; user-select: none;
}
.word-text.clickable { cursor: pointer; }
.word-text.clickable:hover { color: #58CC02; }

.mastered-dot { display: flex; flex-shrink: 0; }

.word-def {
  font-size: 13px; color: #606266; line-height: 1.65;
  white-space: pre-line;
  animation: fadeSlideIn .25s ease;
}
@keyframes fadeSlideIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }

.word-def-masked {
  cursor: pointer; padding: 6px 0; user-select: none;
}
.mask-bars {
  display: flex; align-items: flex-end; gap: 3px; height: 28px;
}
.mask-bar {
  width: 4px; background: #E4E7ED; border-radius: 2px;
  animation: barPulse 1.8s ease-in-out infinite;
}
.mask-bar:nth-child(2) { animation-delay: .1s; height: 18px !important; }
.mask-bar:nth-child(3) { animation-delay: .2s; }
.mask-bar:nth-child(4) { animation-delay: .3s; height: 20px !important; }
.mask-bar:nth-child(5) { animation-delay: .4s; }
.mask-bar:nth-child(6) { animation-delay: .5s; height: 16px !important; }
.mask-bar:nth-child(7) { animation-delay: .6s; }
.mask-bar:nth-child(8) { animation-delay: .7s; height: 22px !important; }

@keyframes barPulse {
  0%, 100% { background: #E4E7ED; }
  50% { background: #D0D4DB; }
}

/* ════ Card Actions ════ */
.card-actions {
  display: flex; flex-direction: column; gap: 4px; flex-shrink: 0;
  opacity: 0; transform: translateX(4px);
  transition: all .2s ease;
}
.word-card:hover .card-actions { opacity: 1; transform: translateX(0); }

.act-btn {
  width: 30px; height: 30px; border-radius: 8px; border: none;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all .15s; background: transparent;
}
.master-btn:hover { background: #E5F8D1; }
.master-btn.on { background: #E5F8D1; }
.del-btn:hover { background: #FEF0F0; }
.del-btn:hover svg { stroke: #F56C6C; }

/* ════ Responsive ════ */
@media (max-width: 600px) {
  .word-card { padding: 12px; gap: 8px; }
  .card-actions { opacity: 1; transform: none; flex-direction: row; }
  .card-left { display: none; }
  .hero-ring { display: none; }
}
</style>
