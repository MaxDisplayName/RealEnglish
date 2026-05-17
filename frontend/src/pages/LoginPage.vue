<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "@/stores/user";
import { ElMessage } from "element-plus";

const router = useRouter();
const userStore = useUserStore();

const loginVal = ref("");
const password = ref("");
const role = ref("student");
const loading = ref(false);

async function handleLogin() {
  if (!loginVal.value || !password.value) {
    ElMessage.warning("请输入用户名/邮箱和密码");
    return;
  }
  loading.value = true;
  try {
    await userStore.loginByAccount(loginVal.value, password.value, role.value);
    ElMessage.success("登录成功");
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
      <h2 class="auth-title">登录</h2>
      <p class="auth-desc">使用用户名或邮箱登录 RealEnglish</p>

      <el-form label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="用户名或邮箱">
          <el-input
            v-model="loginVal"
            placeholder="请输入用户名或邮箱"
            size="large"
            autocomplete="username"
          />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="password"
            type="password"
            placeholder="请输入密码"
            size="large"
            autocomplete="current-password"
            show-password
          />
        </el-form-item>
        <el-form-item label="身份">
          <el-radio-group v-model="role">
            <el-radio value="student">学生</el-radio>
            <el-radio value="teacher">教师</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="auth-btn"
            native-type="submit"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <p class="auth-footer">
        还没有账号？
        <router-link to="/register" class="auth-link">立即注册</router-link>
      </p>
    </el-card>
  </div>
</template>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  padding-top: 60px;
}

.auth-card {
  width: 400px;
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
