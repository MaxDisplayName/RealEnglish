import { defineStore } from "pinia";
import { studentApi } from "@/app";

export const useQuizStore = defineStore("quiz", {
  state: () => ({
    currentQuestions: [],
    currentAnswers: [],
    loading: false,
    error: null,
    placementResult: null,
    aiQuestions: [],
  }),
  actions: {
    async fetchPlacementQuestions() {
      this.loading = true;
      this.error = null;
      try {
        const res = await studentApi.getPlacementQuestions();
        this.currentQuestions = res.data || [];
        this.currentAnswers = [];
      } catch (error) {
        this.error = error.response?.data?.detail || "加载题目失败";
        throw error;
      } finally {
        this.loading = false;
      }
    },
    selectAnswer(questionId, optionIndex) {
      const existing = this.currentAnswers.find((item) => item.question_id === questionId);
      if (existing) {
        existing.selected_option = optionIndex;
      } else {
        this.currentAnswers.push({ question_id: questionId, selected_option: optionIndex });
      }
    },
    getSelectedOption(questionId) {
      const found = this.currentAnswers.find((item) => item.question_id === questionId);
      return found ? found.selected_option : null;
    },
    async submitPlacementAnswers() {
      const res = await studentApi.submitPlacement(this.currentAnswers);
      this.placementResult = res.data;
      return res.data;
    },
    async generateQuestionsForClip(clipId, difficulty) {
      const res = await studentApi.generateQuestions(clipId, difficulty);
      this.aiQuestions = res.data || [];
      return this.aiQuestions;
    },
    async submitSingleAnswer(questionId, optionIndex) {
      const res = await studentApi.submitAnswer(questionId, optionIndex);
      return res.data;
    },
  },
});
