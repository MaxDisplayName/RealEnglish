<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ArrowLeft, Document, Collection } from "@element-plus/icons-vue";
import { getVocabulary, deleteWord, toggleMastered } from "@/api/student/api";
import request from "@/api/shared/request";

const router = useRouter();
const activeTab = ref("vocab");

// ═══ 单词本 ═══
const words = ref([]);
const vLoading = ref(true);
const vTotal = ref(0);
const sort = ref("newest");
const reviewMode = ref(false);
const showDef = ref({});

async function loadWords() {
  vLoading.value = true;
  try {
    const res = await getVocabulary({ page_size: 200, sort: sort.value });
    words.value = res.data?.items || [];
    vTotal.value = res.data?.total || 0;
  } catch { words.value = []; }
  finally { vLoading.value = false; }
}

async function handleDeleteWord(vid) {
  await deleteWord(vid);
  words.value = words.value.filter(w => w.id !== vid);
  vTotal.value = Math.max(0, vTotal.value - 1);
}

async function handleToggleMastered(vid) {
  try {
    const res = await toggleMastered(vid);
    const w = words.value.find(v => v.id === vid);
    if (w) w.mastered = res.data.mastered;
  } catch { /* */ }
}

function toggleReview() { reviewMode.value = !reviewMode.value; showDef.value = {}; }
function toggleDef(id) { showDef.value[id] = !showDef.value[id]; }

const masteredCount = computed(() => words.value.filter(w => w.mastered).length);
const vocabPct = computed(() => vTotal.value > 0 ? Math.round(masteredCount.value / vTotal.value * 100) : 0);

// ═══ 检测模式 ═══
const quizVisible = ref(false);
const quizQuestions = ref([]);
const quizStep = ref(0);
const quizAnswers = ref([]);
const quizLoading = ref(false);
const quizResult = ref(null);

async function startQuiz() {
  if (words.value.length < 4) return;
  quizLoading.value = true;
  try {
    const res = await request.post("/vocabulary/quiz/generate", { count: Math.min(5, words.value.length) });
    quizQuestions.value = res.data?.questions || [];
    quizStep.value = 0;
    quizAnswers.value = quizQuestions.value.map(() => -1);
    quizResult.value = null;
    quizVisible.value = true;
  } catch { /* */ }
  finally { quizLoading.value = false; }
}

function selectQuizOption(qIdx, optIdx) {
  quizAnswers.value[qIdx] = optIdx;
}

function nextQuizStep() {
  if (quizStep.value < quizQuestions.value.length - 1) {
    quizStep.value++;
  }
}

async function submitQuiz() {
  const answers = quizQuestions.value.map((q, i) => ({
    word: q.word,
    selected: quizAnswers.value[i],
    correct: q.answer,
  }));
  try {
    const res = await request.post("/vocabulary/quiz/submit", { answers });
    quizResult.value = res.data;
    await loadWords();
  } catch { /* */ }
}

function closeQuiz() {
  quizVisible.value = false;
  quizQuestions.value = [];
  quizResult.value = null;
}

// ═══ 错题本 ═══
const wrongNotes = ref([]);
const wLoading = ref(true);
const wTotal = ref(0);
const wError = ref(null);
const wPage = ref({ current: 1, pageSize: 20 });

async function loadWrongNotes() {
  wLoading.value = true; wError.value = null;
  try {
    const skip = (wPage.value.current - 1) * wPage.value.pageSize;
    const res = await request.get("/answers/wrong-notes", { params: { skip, limit: wPage.value.pageSize } });
    wrongNotes.value = res.data?.items || [];
    wTotal.value = res.data?.total || 0;
  } catch { wError.value = "加载失败"; }
  finally { wLoading.value = false; }
}

function handleWPageChange(page) { wPage.value.current = page; loadWrongNotes(); }

function goClip(clipId) {
  router.push(`/student/clips/${clipId}`);
}

// ═══ 生命周期 ═══
onMounted(() => { loadWords(); if (activeTab.value === "wrong") loadWrongNotes(); });

function onTabChange(tab) {
  if (tab === "wrong") loadWrongNotes();
}
</script>

<template>
  <div class="accumulate-page">
    <!-- 顶部 -->
    <div class="page-top">
      <el-button size="small" :icon="ArrowLeft" text @click="router.push('/student')">返回首页</el-button>
    </div>

    <div class="page-hero">
      <div class="hero-left">
        <h2 class="hero-title">我的积累</h2>
        <p class="hero-sub">{{ activeTab === 'vocab' ? `${vTotal} 个单词 · 已掌握 ${masteredCount}` : `${wTotal} 道错题` }}</p>
      </div>
      <div v-if="vTotal > 0" class="hero-ring" :style="{ '--pct': vocabPct }">
        <svg width="64" height="64" viewBox="0 0 64 64">
          <circle cx="32" cy="32" r="28" fill="none" stroke="#EBEDF0" stroke-width="4.5" />
          <circle cx="32" cy="32" r="28" fill="none" stroke="#58CC02" stroke-width="4.5"
            stroke-linecap="round" stroke-dasharray="175.9" transform="rotate(-90 32 32)"
            :stroke-dashoffset="175.9 - 175.9 * vocabPct / 100"
            style="transition: stroke-dashoffset .8s cubic-bezier(.4,0,.2,1)" />
        </svg>
        <span class="ring-num">{{ vocabPct }}%</span>
      </div>
    </div>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- ═══════════ 单词本 Tab ═══════════ -->
      <el-tab-pane label="单词本" name="vocab">
        <!-- 工具栏 -->
        <div class="toolbar">
          <el-radio-group v-model="sort" size="small" @change="loadWords">
            <el-radio-button value="newest">最新</el-radio-button>
            <el-radio-button value="alphabet">A-Z</el-radio-button>
            <el-radio-button value="mastered">未掌握</el-radio-button>
          </el-radio-group>
          <div class="toolbar-right">
            <el-button size="small" :disabled="words.length < 4" :loading="quizLoading" @click="startQuiz">
              检测模式
            </el-button>
            <el-button size="small" :class="reviewMode ? 'review-on' : ''" @click="toggleReview">
              {{ reviewMode ? '退出复习' : '复习模式' }}
            </el-button>
          </div>
        </div>

        <div v-if="vLoading" class="state-wrap"><el-skeleton :rows="4" animated /></div>
        <div v-else-if="words.length === 0" class="empty-state">
          <el-empty description="单词本是空的" :image-size="80">
            <template #image><el-icon :size="48"><Collection /></el-icon></template>
          </el-empty>
          <p class="empty-hint">在影视片段中点击英文单词即可收藏</p>
        </div>
        <div v-else class="word-list">
          <div v-for="(w, idx) in words" :key="w.id" class="word-card"
            :class="{ mastered: w.mastered, revealed: showDef[w.id] }"
            :style="{ animationDelay: idx * 0.03 + 's' }">
            <span class="w-idx">{{ idx + 1 }}</span>
            <div class="w-body">
              <div class="w-head">
                <span class="w-text" :class="{ clickable: reviewMode }" @click="reviewMode && toggleDef(w.id)">{{ w.word }}</span>
                <span v-if="w.mastered" class="w-mastered">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#58CC02" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                </span>
              </div>
              <div v-if="!reviewMode || showDef[w.id]" class="w-def">{{ w.definition || '暂无释义，可在片段中重新收藏获取' }}</div>
              <div v-else class="w-def-masked" @click="toggleDef(w.id)">
                <span class="mask-bars"><i v-for="n in 8" :key="n" class="mask-bar" :style="{ height: (12 + Math.sin(n * 1.3) * 8) + 'px' }"/></span>
              </div>
            </div>
            <div class="w-actions">
              <button class="w-act" :class="{ on: w.mastered }" @click="handleToggleMastered(w.id)" :title="w.mastered ? '取消掌握' : '标记掌握'">
                <svg width="15" height="15" viewBox="0 0 24 24" :fill="w.mastered ? '#58CC02' : 'none'" :stroke="w.mastered ? '#58CC02' : '#909399'" stroke-width="1.8"><polyline points="20 6 9 17 4 12"/></svg>
              </button>
              <button class="w-act del" @click="handleDeleteWord(w.id)" title="删除">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#C0C4CC" stroke-width="1.8"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ═══════════ 错题本 Tab ═══════════ -->
      <el-tab-pane label="错题本" name="wrong">
        <div v-if="wLoading" class="state-wrap"><el-skeleton :rows="4" animated /></div>
        <div v-else-if="wError" class="state-wrap">
          <el-result icon="error" :title="wError">
            <template #extra><el-button @click="loadWrongNotes">重试</el-button></template>
          </el-result>
        </div>
        <div v-else-if="wrongNotes.length === 0" class="empty-state">
          <el-empty description="暂无错题" :image-size="80">
            <template #image><el-icon :size="48"><Document /></el-icon></template>
          </el-empty>
        </div>
        <div v-else class="wrong-list">
          <div v-for="note in wrongNotes" :key="note.id" class="wrong-card">
            <div class="wn-top">
              <span class="diff-badge" :class="'diff-' + (note.difficulty || 'b').toLowerCase()">{{ note.difficulty || 'B' }}级</span>
              <span class="wn-time">{{ note.answered_at?.slice(0, 16) || '' }}</span>
            </div>
            <div class="wn-question">{{ note.content?.question || '无题目' }}</div>
            <div class="wn-options">
              <div v-for="(opt, oi) in (note.content?.options || [])" :key="oi"
                class="wn-opt"
                :class="{
                  correct: oi === (note.content?.answer ?? -1),
                  wrong: oi === note.selected_option && oi !== (note.content?.answer ?? -1)
                }">
                <span class="wn-opt-letter">{{ String.fromCharCode(65 + oi) }}</span>
                {{ opt }}
                <span v-if="oi === (note.content?.answer ?? -1)" class="wn-check">✓</span>
                <span v-else-if="oi === note.selected_option && oi !== (note.content?.answer ?? -1)" class="wn-cross">✗</span>
              </div>
            </div>
            <div v-if="note.content?.explanation" class="wn-exp">
              <el-alert :title="note.content.explanation" type="info" :closable="false" />
            </div>
          </div>
          <el-pagination v-if="wTotal > wPage.pageSize" small layout="prev, pager, next"
            :total="wTotal" :page-size="wPage.pageSize"
            :current-page="wPage.current" @current-change="handleWPageChange" style="justify-content:center;margin-top:16px" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- ═══════════ 检测模式弹窗 ═══════════ -->
    <el-dialog v-model="quizVisible" title="单词检测" width="520px" :close-on-click-modal="false" @close="closeQuiz">
      <template v-if="quizResult">
        <div class="quiz-result">
          <div class="qr-score">{{ quizResult.correct }} / {{ quizResult.total }}</div>
          <div class="qr-acc">正确率 {{ quizResult.accuracy }}%</div>
          <div v-if="quizResult.correct === quizResult.total" class="qr-msg">完美！全部正确 🎉</div>
          <div v-else class="qr-msg">错题已自动记入错题本，可在错题本 Tab 查看</div>
        </div>
      </template>
      <template v-else-if="quizQuestions.length > 0">
        <div class="quiz-progress">
          <span class="qp-text">{{ quizStep + 1 }} / {{ quizQuestions.length }}</span>
          <el-progress :percentage="Math.round((quizStep + 1) / quizQuestions.length * 100)" :stroke-width="4" color="#58CC02" />
        </div>
        <div class="quiz-question">{{ quizQuestions[quizStep].question }}</div>
        <div class="quiz-options">
          <div v-for="(opt, oi) in quizQuestions[quizStep].options" :key="oi"
            class="quiz-opt" :class="{ selected: quizAnswers[quizStep] === oi }"
            @click="selectQuizOption(quizStep, oi)">
            <span class="qo-letter">{{ String.fromCharCode(65 + oi) }}</span>
            {{ opt }}
          </div>
        </div>
      </template>
      <template #footer>
        <template v-if="quizResult">
          <el-button @click="closeQuiz">关闭</el-button>
          <el-button type="primary" @click="startQuiz">再来一轮</el-button>
        </template>
        <template v-else-if="quizQuestions.length > 0">
          <el-button @click="closeQuiz">退出</el-button>
          <el-button v-if="quizStep < quizQuestions.length - 1" type="primary" :disabled="quizAnswers[quizStep] < 0" @click="nextQuizStep">下一题</el-button>
          <el-button v-else type="primary" :disabled="quizAnswers.some(a => a < 0)" @click="submitQuiz">提交</el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ════ Page Layout ════ */
.accumulate-page { max-width: 760px; margin: 0 auto; padding-bottom: 60px; }
.page-top { margin-bottom: 8px; }

/* ════ Hero ════ */
.page-hero { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0; }
.hero-left { display: flex; flex-direction: column; gap: 2px; }
.hero-title { font-size: 26px; font-weight: 800; color: #1D1D1F; margin: 0; letter-spacing: -.03em; }
.hero-sub { margin: 0; font-size: 13px; color: #8E8E93; font-weight: 500; }

/* ring chart */
.hero-ring {
  position: relative; flex-shrink: 0;
  filter: drop-shadow(0 2px 8px rgba(88,204,2,.15));
}
.ring-num {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 800; color: #58CC02; font-variant-numeric: tabular-nums;
}

/* ════ Tabs ════ */
:deep(.el-tabs__header) { margin-bottom: 4px; }
:deep(.el-tabs__nav-wrap::after) { height: 1px; background: #EBEDF0; }
:deep(.el-tabs__item) {
  font-size: 14px; font-weight: 600; color: #909399; padding: 0 20px 10px;
  transition: color .25s; position: relative;
}
:deep(.el-tabs__item:hover) { color: #58CC02; }
:deep(.el-tabs__item.is-active) { color: #1D1D1F; font-weight: 700; }
:deep(.el-tabs__active-bar) {
  height: 3px; border-radius: 3px 3px 0 0;
  background: linear-gradient(135deg, #58CC02, #7BE028);
  transition: all .3s cubic-bezier(.4,0,.2,1);
}
:deep(.el-tab-pane) { padding-top: 8px; }

/* ════ Toolbar ════ */
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.toolbar-right { display: flex; gap: 8px; }
.review-on { background: #E5F8D1; border-color: #58CC02; color: #46A302; font-weight: 700; box-shadow: 0 0 0 3px rgba(88,204,2,.08); }

/* ════ States ════ */
.state-wrap { margin-top: 24px; }
.empty-state { text-align: center; padding: 48px 20px; }
.empty-state :deep(.el-empty__description) { color: #909399; font-size: 13px; }
.empty-hint { font-size: 12px; color: #C0C4CC; margin-top: -6px; }

/* ════ Word Cards ════ */
.word-list { display: flex; flex-direction: column; gap: 6px; }

.word-card {
  background: #fff; border: 1.5px solid #ECEDF0; border-radius: 14px;
  padding: 15px 14px 15px 10px; display: flex; align-items: flex-start; gap: 10px;
  transition: all .25s cubic-bezier(.4,0,.2,1);
  animation: cardIn .42s cubic-bezier(.16,1,.3,1) both;
  position: relative; overflow: hidden;
}
.word-card::after {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: transparent; border-radius: 0 3px 3px 0;
  transition: background .3s cubic-bezier(.4,0,.2,1);
}
.word-card:hover {
  border-color: #D4D8DF; box-shadow: 0 4px 18px rgba(0,0,0,.06);
  transform: translateY(-2px);
}
.word-card:hover::after { background: #58CC02; }
.word-card.mastered { background: #F9FCF6; border-color: rgba(88,204,2,.12); }
.word-card.mastered::after { background: #A8E06E; }

@keyframes cardIn {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

.w-idx {
  display: flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border-radius: 7px;
  background: #F4F5F7; font-size: 11px; font-weight: 700; color: #B0B5BE;
  flex-shrink: 0; margin-top: 1px;
}
.w-body { flex: 1; min-width: 0; }
.w-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.w-text {
  font-size: 17px; font-weight: 700; color: #1D1D1F; letter-spacing: -.02em;
  user-select: none; transition: color .2s;
}
.w-text.clickable { cursor: pointer; }
.w-text.clickable:hover { color: #58CC02; }
.w-mastered { display: flex; flex-shrink: 0; }
.w-def {
  font-size: 12.5px; color: #6B7280; line-height: 1.65;
  white-space: pre-line; animation: reveal .25s ease;
}
@keyframes reveal { from { opacity: 0; transform: translateY(-3px); } to { opacity: 1; transform: translateY(0); } }

/* review mask */
.w-def-masked { cursor: pointer; padding: 5px 0; user-select: none; }
.mask-bars { display: flex; align-items: flex-end; gap: 3px; height: 26px; }
.mask-bar {
  width: 4px; background: #E0E3E8; border-radius: 3px;
  animation: barPulse 1.6s ease-in-out infinite;
}
.mask-bar:nth-child(1) { animation-delay: 0s; height: 16px; }
.mask-bar:nth-child(2) { animation-delay: .08s; height: 22px; }
.mask-bar:nth-child(3) { animation-delay: .16s; height: 14px; }
.mask-bar:nth-child(4) { animation-delay: .24s; height: 24px; }
.mask-bar:nth-child(5) { animation-delay: .32s; height: 18px; }
.mask-bar:nth-child(6) { animation-delay: .40s; height: 20px; }
.mask-bar:nth-child(7) { animation-delay: .48s; height: 15px; }
.mask-bar:nth-child(8) { animation-delay: .56s; height: 23px; }
@keyframes barPulse {
  0%, 100% { background: #E0E3E8; transform: scaleY(1); }
  50%      { background: #C8CDD4; transform: scaleY(1.25); }
}

/* card actions */
.w-actions {
  display: flex; flex-direction: column; gap: 4px; flex-shrink: 0;
  opacity: 0; transform: translateX(6px); transition: all .25s ease;
}
.word-card:hover .w-actions { opacity: 1; transform: translateX(0); }
.w-act {
  width: 32px; height: 32px; border-radius: 9px; border: none;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all .18s; background: transparent;
}
.w-act:hover { background: #F0F9E8; }
.w-act.on { background: #E5F8D1; }
.w-act.del:hover { background: #FEF0F0; }
.w-act.del:hover svg { stroke: #F56C6C; }

/* ════ Wrong Notes ════ */
.wrong-list { display: flex; flex-direction: column; gap: 10px; }

.wrong-card {
  background: #fff; border: 1.5px solid #ECEDF0; border-radius: 14px;
  padding: 18px 20px; position: relative; overflow: hidden;
  transition: all .25s cubic-bezier(.4,0,.2,1);
  animation: cardIn .42s cubic-bezier(.16,1,.3,1) both;
}
.wrong-card::after {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: transparent; border-radius: 0 3px 3px 0;
  transition: background .3s;
}
.wrong-card:hover {
  border-color: #D4D8DF; box-shadow: 0 3px 16px rgba(0,0,0,.05);
  transform: translateY(-1px);
}
.wrong-card:hover::after { background: #E6A23C; }

.wn-top { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.wn-time { font-size: 11px; color: #C0C4CC; margin-left: auto; font-variant-numeric: tabular-nums; }
.wn-question { font-size: 14.5px; font-weight: 650; color: #1D1D1F; margin-bottom: 12px; line-height: 1.65; }
.wn-options { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }
.wn-opt {
  display: flex; align-items: center; gap: 10px; padding: 10px 14px;
  border-radius: 9px; background: #F5F6F8; font-size: 13px; color: #6B7280;
  transition: all .2s; border: 1.5px solid transparent; position: relative;
}
.wn-opt.correct {
  background: linear-gradient(135deg, #EDF7E5, #E5F8D1);
  color: #3D8200; border-color: rgba(88,204,2,.18); font-weight: 600;
}
.wn-opt.wrong {
  background: linear-gradient(135deg, #FEF0F0, #FDE8E8);
  color: #C0392B; border-color: rgba(245,108,108,.18); font-weight: 600;
}
.wn-opt-letter { font-weight: 700; min-width: 22px; font-size: 12px; opacity: .7; }
.wn-check, .wn-cross { font-weight: 700; margin-left: auto; font-size: 13px; }
.wn-check { color: #58CC02; }
.wn-cross { color: #F56C6C; }
.wn-exp { margin-top: 4px; }

/* ════ Quiz Dialog ════ */
.quiz-progress { margin-bottom: 18px; }
.qp-text { font-size: 12px; color: #909399; margin-bottom: 6px; display: block; font-weight: 600; }
.quiz-question {
  font-size: 15.5px; font-weight: 650; color: #1D1D1F;
  margin-bottom: 16px; line-height: 1.75; padding: 12px 16px;
  background: #F9FAFB; border-radius: 10px; border: 1px solid #ECEDF0;
}
.quiz-options { display: flex; flex-direction: column; gap: 9px; }
.quiz-opt {
  display: flex; align-items: center; gap: 10px;
  padding: 13px 16px; border-radius: 11px;
  border: 1.5px solid #ECEDF0; cursor: pointer;
  font-size: 14px; color: #6B7280; background: #fff;
  transition: all .2s cubic-bezier(.4,0,.2,1);
  box-shadow: 0 1px 2px rgba(0,0,0,.02);
}
.quiz-opt:hover {
  border-color: #B0D88A; background: #F9FCF6;
  transform: translateX(3px); box-shadow: 0 2px 8px rgba(88,204,2,.08);
}
.quiz-opt.selected {
  border-color: #58CC02; background: #EDF7E5; color: #3D8200;
  font-weight: 650; transform: translateX(3px);
  box-shadow: 0 0 0 4px rgba(88,204,2,.1);
}
.qo-letter {
  font-weight: 800; min-width: 26px; height: 26px; border-radius: 7px;
  background: #F4F5F7; display: flex; align-items: center; justify-content: center;
  font-size: 12px; color: #909399; transition: all .2s;
}
.quiz-opt.selected .qo-letter { background: #58CC02; color: #fff; }

/* quiz result */
.quiz-result { text-align: center; padding: 28px 20px; }
.qr-score { font-size: 56px; font-weight: 800; color: #58CC02; line-height: 1; letter-spacing: -.03em; }
.qr-acc { font-size: 15px; color: #8E8E93; margin: 6px 0 16px; font-weight: 500; }
.qr-msg { font-size: 13px; color: #6B7280; padding: 10px 16px; background: #F9FAFB; border-radius: 8px; display: inline-block; }

/* ════ Responsive ════ */
@media (max-width: 600px) {
  .w-actions { opacity: 1; transform: none; flex-direction: row; }
  .hero-ring { display: none; }
  .word-card { padding: 12px 12px 12px 8px; }
  .wrong-card { padding: 14px 16px; }
}
</style>
