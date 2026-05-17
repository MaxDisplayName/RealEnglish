# RealEnglish 前端代码编写规范

> 本规范适用于项目前端（Vue 3 + Vite + Pinia + Element Plus）的所有代码编写，要求 AI 生成的代码严格遵循。

## 1. 技术栈与工具

- **框架**: Vue 3 (Composition API + `<script setup>`)
- **构建工具**: Vite
- **状态管理**: Pinia
- **UI 库**: Element Plus (按需导入)
- **HTTP 客户端**: Axios
- **路由**: Vue Router (如有多页面)
- **代码规范**: ESLint + Prettier (项目根目录需配置)
- **包管理器**: npm 或 yarn

## 2. 命名规范

| 类型                         | 命名规则          | 示例                                     |
| ---------------------------- | ----------------- | ---------------------------------------- |
| 组件文件名                   | PascalCase        | `VideoPlayer.vue`                        |
| 组件内 `<script setup>` 名称 | 与文件名一致      | `defineOptions({ name: 'VideoPlayer' })` |
| 普通 JS 文件名               | camelCase         | `useSpeech.js`                           |
| 常量                         | UPPER_SNAKE_CASE  | `MAX_RETRY_COUNT`                        |
| 变量/函数                    | camelCase         | `getUserInfo`, `isLoading`               |
| CSS 类名                     | kebab-case 或 BEM | `.video-player`, `.question-card__title` |
| Pinia store 命名             | useXxxStore       | `useUserStore`                           |

## 3. Vue 组件编写规范

### 3.1 基本结构

```vue
<script setup>
// 1. 导入
import { ref, computed, onMounted } from "vue";
import { useUserStore } from "@/stores/user";

// 2. Props 定义
const props = defineProps({
  videoId: { type: String, required: true },
});

// 3. Emits 定义
const emit = defineEmits(["update-score", "close"]);

// 4. Store 使用
const userStore = useUserStore();

// 5. 响应式状态
const isLoading = ref(false);

// 6. 计算属性
const displayTitle = computed(() => props.videoId);

// 7. 方法
const handleSubmit = () => {
  /* ... */
};

// 8. 生命周期
onMounted(() => {
  /* ... */
});
</script>

<template>
  <div class="component-container">
    <!-- 模板内容 -->
  </div>
</template>

<style scoped>
.component-container {
  /* 样式 */
}
</style>
```

### 3.2 Props 校验

必须定义 type，复杂类型使用 validator。

推荐使用 required: true 或提供 default。

### 3.3 事件命名

使用 kebab-case：@update-score，@close-dialog。

在 emits 数组中声明所有事件。

## 4. 状态管理 (Pinia)

Store 文件按模块划分。

使用 setup 语法定义 store：

```javascript
// stores/user.js
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  const deviceId = ref(localStorage.getItem('deviceId') || '')
  const level = ref('B')

  function setLevel(newLevel) {
    level.value = newLevel
  }

  return { deviceId, level, setLevel }
})
禁止在组件中直接修改 store 状态（必须通过 store 提供的 action/mutation）。
```

## 5. API 请求规范

### 5.1 Axios 实例配置 (api/request.js)

```javascript
import axios from "axios";
import { ElMessage } from "element-plus";

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
});

// 请求拦截器：添加设备 ID
request.interceptors.request.use((config) => {
  const deviceId = localStorage.getItem("deviceId");
  if (deviceId) config.headers["X-Device-Id"] = deviceId;
  return config;
});

// 响应拦截器：统一错误处理
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    ElMessage.error(error.response?.data?.message || "网络错误");
    return Promise.reject(error);
  },
);

export default request;
```

### 5.2 API 模块定义 (api/quiz.js)

```javascript
import request from "./request";

export const getRandomQuestions = (params) => {
  return request.get("/questions/random", { params });
};

export const submitAnswer = (data) => {
  return request.post("/answers/submit", data);
};
```

## 6. 样式规范

使用 scoped 避免全局污染。

优先使用 Flex/Grid，避免绝对定位。

颜色、间距等设计变量统一放在 styles/variables.css。

移动端适配：根字体使用 16px，布局使用 rem 或 vw，设置 viewport。

## 7. 性能与体验规范

懒加载：路由组件使用 () => import()，图片使用 v-lazy。

防抖/节流：搜索、滚动等高频事件必须使用 lodash 的 debounce/throttle。

长列表：超过 100 项时使用虚拟滚动（vue-virtual-scroller）。

音频/视频：组件销毁前必须释放资源（pause()、revokeObjectURL）。

## 8. 错误处理

所有 try/catch 必须捕获并记录错误（可上报或控制台输出）。

用户交互错误（如网络失败、权限被拒）使用 ElMessage 友好提示。

开发阶段保留 console.error，生产环境应移除或条件输出。

## 9. 注释与文档

每个组件顶部注释说明用途。

复杂函数必须使用 JSDoc 注释：

```javascript
/**
 * 录音并上传评测
 * @param {Blob} audioBlob - PCM 音频数据
 * @returns {Promise<Object>} 评分结果
 */
```

常量和枚举集中定义并注释含义。

## 10. Git 提交前检查

运行 npm run lint 修复格式问题。

确保无 ESLint 错误或警告。

不得包含 debugger 语句。

最后更新: 2026-05-02
维护者: RealEnglish 开发团队
