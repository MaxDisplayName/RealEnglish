<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "@/stores/user";
import { ElMessage } from "element-plus";

const router = useRouter();
const userStore = useUserStore();

const username = ref("");
const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const inviteCode = ref("");
const role = ref("student");
const loading = ref(false);

async function handleRegister() {
  if (!username.value || !email.value || !password.value) {
    ElMessage.warning("请填写所有必填项");
    return;
  }
  if (password.value !== confirmPassword.value) {
    ElMessage.warning("两次输入的密码不一致");
    return;
  }
  if (password.value.length < 8) {
    ElMessage.warning("密码长度至少 8 位");
    return;
  }
  if (!/[a-zA-Z]/.test(password.value) || !/\d/.test(password.value)) {
    ElMessage.warning("密码需同时包含字母和数字");
    return;
  }
  loading.value = true;
  try {
    await userStore.registerByAccount(username.value, email.value, password.value, role.value, inviteCode.value);
    ElMessage.success("注册成功");
    router.push(userStore.getDefaultRoute());
  } catch (e) {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="auth-page">
    <el-card class="auth-card" shadow="never">
      <h2 class="auth-title">注册</h2>
      <p class="auth-desc">创建你的 RealEnglish 账号</p>

      <el-form label-position="top" @submit.prevent="handleRegister">
        <el-form-item label="用户名">
          <el-input
            v-model="username"
            placeholder="2-50 个字符"
            size="large"
            autocomplete="username"
          />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input
            v-model="email"
            type="email"
            placeholder="your@email.com"
            size="large"
            autocomplete="email"
          />
        </el-form-item>
        <el-form-item label="身份">
          <el-radio-group v-model="role">
            <el-radio value="student">学生</el-radio>
            <el-radio value="teacher">教师</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="password"
            type="password"
            placeholder="至少 8 位，含字母和数字"
            size="large"
            autocomplete="new-password"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input
            v-model="confirmPassword"
            type="password"
            placeholder="再次输入密码"
            size="large"
            autocomplete="new-password"
            show-password
          />
        </el-form-item>
        <el-form-item v-if="role === 'student'" label="教师邀请码（选填）">
          <el-input
            v-model="inviteCode"
            placeholder="输入教师邀请码以绑定班级"
            size="large"
            maxlength="4"
            style="text-transform:uppercase"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="auth-btn"
            native-type="submit"
          >
            注册
          </el-button>
        </el-form-item>
      </el-form>

      <p class="auth-footer">
        已有账号？
        <router-link to="/login" class="auth-link">立即登录</router-link>
      </p>
    </el-card>
  </div>
</template>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  padding-top: 40px;
}

.auth-card {
  width: 420px;
  padding: 32px;
  border-radius: var(--radius-base);
}

.auth-title {
  font-size: 24px;
  text-align: center;
  margin-bottom: 4px;
  color: #303133;
}

.auth-desc {
  text-align: center;
  color: #909399;
  font-size: 14px;
  margin-bottom: 24px;
}

.auth-btn {
  width: 100%;
}

.auth-footer {
  text-align: center;
  font-size: 14px;
  color: #909399;
  margin-top: 16px;
}

.auth-link {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 600;
}
</style>
