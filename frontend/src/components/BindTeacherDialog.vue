<script setup>
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { useUserStore } from "@/stores/user";
import request from "@/api/shared/request";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "bound"]);

const userStore = useUserStore();
const inviteCode = ref("");
const loading = ref(false);

async function handleBind() {
  const code = inviteCode.value.trim().toUpperCase();
  if (!code) {
    ElMessage.warning("请输入邀请码");
    return;
  }
  loading.value = true;
  try {
    await request.post("/bind-invite", { invite_code: code });
    ElMessage.success("绑定成功！互动中心已解锁");
    await userStore.checkAuth();
    emit("bound");
    emit("update:modelValue", false);
  } catch (e) {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false;
  }
}

function handleSkip() {
  localStorage.setItem("bind_skipped", "true");
  emit("update:modelValue", false);
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    title="绑定教师"
    :close-on-click-modal="false"
    width="400px"
    align-center
  >
    <p class="bind-desc">
      输入教师的 4 位邀请码，即可解锁互动中心，与教师沟通并获取学习任务和反馈。
    </p>
    <el-input
      v-model="inviteCode"
      placeholder="输入 4 位邀请码"
      maxlength="4"
      size="large"
      class="bind-input"
    />

    <template #footer>
      <el-button @click="handleSkip">跳过</el-button>
      <el-button type="primary" :loading="loading" @click="handleBind">绑定</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.bind-desc {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 16px;
}

.bind-input :deep(.el-input__inner) {
  text-align: center;
  letter-spacing: 8px;
  font-size: 20px;
  font-weight: 600;
}
</style>
