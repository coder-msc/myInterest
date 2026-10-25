<template>
  <div class="admin-shell">
    <!-- 顶部栏 -->
    <header class="admin-topbar">
      <div class="topbar-left">
        <div class="brand" @click="panel = 'dashboard'">
          <div class="logo">牛</div>
          <div class="brand-text">
            <div class="brand-name">纯牛马人生手札 · 运营后台</div>
            <div class="brand-sub">Admin Console</div>
          </div>
        </div>
      </div>
      <div class="topbar-right">
        <span class="isolation-tip">数据隔离 · 操作留痕</span>
        <span class="admin-name">{{ userStore.user?.username }}</span>
        <span class="role-tag">{{ roleText }}</span>
        <button class="plain-btn" @click="backToApp">← 返回前台</button>
      </div>
    </header>

    <!-- 无权限 -->
    <div v-if="denied" class="denied">
      <p>当前账号没有后台访问权限</p>
      <button class="plain-btn primary" @click="backToApp">返回前台</button>
    </div>

    <!-- 主体：左侧菜单 + 右侧面板 -->
    <div v-else class="admin-body">
      <aside class="side-menu">
        <div v-for="m in MENUS" :key="m.key"
             class="side-item" :class="{ active: panel === m.key }"
             @click="panel = m.key">
          <span class="side-icon">{{ m.icon }}</span>
          <span>{{ m.label }}</span>
        </div>
      </aside>
      <main class="admin-content">
        <h1 class="page-title">{{ currentMenu.label }}</h1>
        <component :is="currentMenu.comp" v-if="currentMenu.comp" :go="(k) => (panel = k)" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import 'element-plus/dist/index.css'
import { userStore } from '@/store/user'
import AdminDashboard from '@/components/admin/Dashboard.vue'
import AdminSchedules from '@/components/admin/Schedules.vue'
import AdminSecurities from '@/components/admin/Securities.vue'
import AdminUsers from '@/components/admin/Users.vue'
import AdminTreehole from '@/components/admin/Treehole.vue'
import AdminLoginMethods from '@/components/admin/LoginMethods.vue'
import AdminConfig from '@/components/admin/Config.vue'
import AdminNotice from '@/components/admin/Notice.vue'
import AdminLogs from '@/components/admin/Logs.vue'

const MENUS = [
  { key: 'dashboard', label: '运营看板', icon: '📊', comp: AdminDashboard },
  { key: 'schedules', label: '分红预案审核', icon: '📋', comp: AdminSchedules },
  { key: 'securities', label: '证券与白名单', icon: '🔖', comp: AdminSecurities },
  { key: 'users', label: '用户管理', icon: '👥', comp: AdminUsers },
  { key: 'treehole', label: '树洞审核', icon: '🌳', comp: AdminTreehole },
  { key: 'login-methods', label: '系统参数配置', icon: '🧩', comp: AdminLoginMethods },
  { key: 'config', label: '汇率与税率', icon: '💱', comp: AdminConfig },
  { key: 'notice', label: '公告与反馈', icon: '📢', comp: AdminNotice },
  { key: 'logs', label: '操作日志', icon: '🧾', comp: AdminLogs },
]

const panel = ref('dashboard')
const denied = ref(false)

const role = computed(() => userStore.user?.role || '')
const roleText = computed(() => (role.value === 'super_admin' ? '超级管理员' : '管理员'))
const currentMenu = computed(() => MENUS.find((m) => m.key === panel.value) || MENUS[0])

onLoad((query) => {
  if (query?.tab && MENUS.some((m) => m.key === query.tab)) panel.value = query.tab
})

onMounted(() => {
  denied.value = !['admin', 'super_admin'].includes(role.value)
})

function backToApp() {
  uni.reLaunch({ url: '/pages/journal/journal' })
}
</script>

<style>
/* 管理台整体样式：仅本页加载（Element Plus 样式也只在本页引入） */
.admin-shell {
  min-height: 100vh;
  background: #f1f5f9;
  color: #1e293b;
  font-size: 14px;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.admin-shell *, .admin-shell *::before, .admin-shell *::after { box-sizing: border-box; }

.admin-topbar {
  height: 60px; background: #0f172a; color: #cbd5e1;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px; position: sticky; top: 0; z-index: 100;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
.topbar-left { display: flex; align-items: center; min-width: 0; }
.brand { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.logo {
  width: 34px; height: 34px; border-radius: 8px; background: rgba(255, 255, 255, 0.12);
  color: #fff; font-weight: 700; font-size: 17px;
  display: flex; align-items: center; justify-content: center;
}
.brand-text { line-height: 1.2; }
.brand-name { color: #fff; font-weight: 700; font-size: 15px; letter-spacing: 0.5px; }
.brand-sub { font-size: 10px; color: #64748b; }
.topbar-right { display: flex; align-items: center; gap: 14px; }
.isolation-tip { font-size: 12px; color: #64748b; }
.admin-name { font-size: 13px; color: #cbd5e1; }
.role-tag {
  font-size: 11px; padding: 2px 8px; border-radius: 4px;
  background: rgba(245, 158, 11, 0.18); color: #fbbf24;
}
.plain-btn {
  font-size: 13px; padding: 6px 14px; border-radius: 8px; cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.18); background: transparent; color: #e2e8f0;
}
.plain-btn:hover { background: rgba(255, 255, 255, 0.1); }
.plain-btn.primary { background: #1e3a8a; border-color: #1e3a8a; color: #fff; }

.admin-body { display: flex; align-items: flex-start; min-height: calc(100vh - 60px); }
.side-menu {
  width: 190px; flex-shrink: 0; background: #fff; border-right: 1px solid #e2e8f0;
  padding: 16px 10px; position: sticky; top: 60px; min-height: calc(100vh - 60px);
}
.side-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px; margin-bottom: 4px;
  border-radius: 8px; font-size: 14px; color: #475569; cursor: pointer;
}
.side-item:hover { background: #f1f5f9; color: #1e293b; }
.side-item.active { background: #1e3a8a; color: #fff; font-weight: 600; }
.side-icon { font-size: 15px; }

.admin-content { flex: 1; min-width: 0; padding: 20px 28px 32px; }
.page-title { font-size: 20px; font-weight: 700; margin: 0 0 16px; color: #0f172a; }

.denied { padding: 80px 0; text-align: center; color: #475569; }

/* ---- 面板通用样式（沿用原 PC 端 global.css）----
   统一挂在 .admin-shell 下做前缀，避免与移动端全局 .card/.text-muted 冲突 */
.admin-shell .card {
  background: #fff; border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.04);
  padding: 20px; border: 1px solid #f1f5f9;
}
.admin-shell .card h3 { font-size: 15px; font-weight: 600; margin: 0 0 16px; }
.admin-shell .card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.admin-shell .card-head h3 { margin: 0; }
.admin-shell .toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.admin-shell .pager { display: flex; justify-content: flex-end; padding-top: 16px; }
.admin-shell .empty-tip { color: #94a3b8; text-align: center; padding: 32px 0; font-size: 13px; }
.admin-shell .text-muted { color: #94a3b8; font-size: 13px; }
.admin-shell .text-emerald { color: #059669; }
.admin-shell .text-amber { color: #d97706; }
.admin-shell .hint-text { font-size: 12px; color: #94a3b8; margin-top: 12px; }
.admin-shell .stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
.admin-shell .stat-card { transition: transform 0.2s; }
.admin-shell .stat-card:hover { transform: translateY(-2px); }
.admin-shell .badge { font-size: 12px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }

@media (max-width: 1100px) {
  .isolation-tip { display: none; }
  .side-menu { width: 64px; padding: 16px 6px; }
  .side-item { justify-content: center; padding: 10px 4px; }
  .side-item span:last-child { display: none; }
  .admin-content { padding: 16px; }
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
