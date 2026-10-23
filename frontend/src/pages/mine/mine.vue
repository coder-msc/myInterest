<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="我的" subtitle="账户、汇率、提醒与数据" /><!-- #endif -->

    <!-- 用户卡（头像/昵称可点修改，参考 eatWhat 账户设置） -->
    <view class="profile-card">
      <view class="avatar avatar-editable" @click="showAvatarPicker">
        <text v-if="user?.avatar">{{ user.avatar }}</text>
        <text v-else>{{ (user?.nickname || user?.username || '投')[0] }}</text>
      </view>
      <view class="profile-info" @click="showNicknameEdit">
        <text class="nick">{{ user?.nickname || user?.username || '用户' }} <text class="edit-link">✎</text></text>
        <text v-if="isAdmin" class="admin-badge">管理员</text>
        <text class="profile-sub">数据按用户隔离 · 仅本人可见</text>
      </view>
    </view>

    <!-- 功能菜单（参考 eatWhat：emoji 图标 + 标题/副标题双行 + 大号字） -->
    <view class="card menu-card">
      <view class="menu-row" @click="go('/pages/assets/assets')">
        <text class="m-ic">🏦</text>
        <view class="m-main">
          <text class="m-label">家庭资产</text>
          <text class="m-sub-text">存款 · 房产 · 负债 · 净值趋势</text>
        </view>
        <text class="m-arrow">›</text>
      </view>
      <view class="menu-row" @click="go('/pages/holdings/holdings')">
        <text class="m-ic">📈</text>
        <view class="m-main">
          <text class="m-label">投资持仓</text>
          <text class="m-sub-text">持仓批次 · 分红预告 · 分红日历</text>
        </view>
        <text class="m-arrow">›</text>
      </view>
      <view class="menu-row" @click="go('/pages/notifications/notifications')">
        <text class="m-ic">🔔</text>
        <view class="m-main">
          <text class="m-label">提醒中心</text>
          <text class="m-sub-text">重要日子的站内消息</text>
        </view>
        <text v-if="unread" class="m-badge">{{ unread > 99 ? '99+' : unread }}</text>
        <text class="m-arrow">›</text>
      </view>
      <view class="menu-row" @click="go('/pages/recycle/recycle')">
        <text class="m-ic">♻️</text>
        <view class="m-main">
          <text class="m-label">回收站</text>
          <text class="m-sub-text">删掉的东西还能捞回来</text>
        </view>
        <text class="m-arrow">›</text>
      </view>
      <view class="menu-row" @click="exportData">
        <text class="m-ic">📤</text>
        <view class="m-main">
          <text class="m-label">导出我的数据</text>
          <text class="m-sub-text">全部记录导出为 JSON 文件</text>
        </view>
        <text class="m-arrow">›</text>
      </view>
      <view class="menu-row" @click="showBindEmail">
        <text class="m-ic">📧</text>
        <view class="m-main">
          <text class="m-label">绑定邮箱</text>
          <text class="m-sub-text">{{ user?.email || '未绑定 · 可用于登录找回' }}</text>
        </view>
        <text class="m-arrow">›</text>
      </view>
      <view class="menu-row no-border" @click="showAccountSwitch">
        <text class="m-ic">🔁</text>
        <view class="m-main">
          <text class="m-label">投资账户切换</text>
          <text class="m-sub-text">当前：{{ currentAccountText }}（仅影响投资模块）</text>
        </view>
        <text class="m-arrow">›</text>
      </view>
    </view>

    <!-- v8：账户切换弹窗（含账户管理） -->
    <view v-if="acctVisible" class="modal-mask" @click="acctVisible = false">
      <view class="modal-card" @click.stop>
        <view class="modal-title">账户切换</view>
        <view class="modal-tip">选择账户后，所有页面数据将跟随切换；选择「全部」显示所有账户汇总。左滑或点击右侧按钮可归档/编辑。</view>
        <view class="acct-list">
          <view :class="['acct-row', userStore.currentAccount === '__all__' ? 'on' : '']"
                @click="pickAccount('__all__')">
            <text class="acct-dot" style="background:#1e3a8a"></text>
            <text class="acct-name">全部账户</text>
            <text v-if="userStore.currentAccount === '__all__'" class="acct-check">✓</text>
          </view>
          <view v-for="a in accountList" :key="a.name"
                :class="['acct-row', userStore.currentAccount === a.name ? 'on' : '', a.archived ? 'archived' : '']"
                @click="pickAccount(a.name)">
            <text class="acct-dot" :style="{ background: a.color || '#94a3b8' }"></text>
            <text class="acct-name">{{ a.name }}</text>
            <text class="acct-count">{{ a.holding_count }}只</text>
            <view class="acct-ops">
              <text class="op-btn" @click.stop="toggleArchive(a)">归档</text>
            </view>
            <text v-if="userStore.currentAccount === a.name" class="acct-check">✓</text>
          </view>
        </view>
        <view class="modal-actions">
          <button class="btn-cancel" @click="acctVisible = false">关闭</button>
        </view>
      </view>
    </view>

    <!-- 绑定邮箱弹窗（已绑定时支持更换/解绑，参考 eatWhat） -->
    <view v-if="bindVisible" class="modal-mask" @click="bindVisible = false">
      <view class="modal-card" @click.stop>
        <view class="modal-title">{{ user?.email ? '修改 / 解绑邮箱' : '绑定邮箱' }}</view>
        <view class="modal-tip" v-if="!user?.email">绑定后可用邮箱验证码登录、找回密码；若邮箱已被其他账号使用，将合并数据到该账号下。</view>
        <view class="modal-tip" v-else>当前已绑定 {{ user?.email }}；解绑后此邮箱可重新绑定或用于新账号注册。</view>
        <view class="field">
          <text class="f-label">邮箱</text>
          <input class="f-input" v-model="bindForm.email" placeholder="请输入邮箱" />
        </view>
        <view class="field code-field">
          <text class="f-label">验证码</text>
          <view class="code-row">
            <input class="f-input code-input" v-model="bindForm.code" placeholder="6 位验证码" />
            <button class="btn-code" :disabled="bindCooldown > 0" @click="sendBindCode">
              {{ bindCooldown > 0 ? `${bindCooldown}s` : '获取' }}
            </button>
          </view>
        </view>
        <view class="modal-actions">
          <button class="btn-cancel" @click="bindVisible = false">取消</button>
          <button v-if="user?.email" class="btn-danger-plain" :loading="unbindLoading" @click="confirmUnbind">解绑当前</button>
          <button class="btn-confirm" :loading="bindLoading" @click="confirmBind">确认绑定</button>
        </view>
      </view>
    </view>

    <!-- 头像 emoji 候选弹窗（点选即保存，参考 eatWhat） -->
    <view v-if="avatarVisible" class="modal-mask" @click="avatarVisible = false">
      <view class="modal-card" @click.stop>
        <view class="modal-title">选择头像</view>
        <view class="emoji-grid">
          <view v-for="em in AVATAR_POOL" :key="em"
                :class="['emoji-cell', em === user?.avatar ? 'on' : '']"
                @click="saveAvatar(em)">{{ em }}</view>
        </view>
        <view class="modal-actions">
          <button class="btn-cancel" @click="avatarVisible = false">关闭</button>
        </view>
      </view>
    </view>

    <!-- 修改昵称弹窗 -->
    <view v-if="nickVisible" class="modal-mask" @click="nickVisible = false">
      <view class="modal-card" @click.stop>
        <view class="modal-title">修改昵称</view>
        <view class="field">
          <input class="f-input" v-model="nickForm" placeholder="新的昵称" maxlength="20" />
        </view>
        <view class="modal-actions">
          <button class="btn-cancel" @click="nickVisible = false">取消</button>
          <button class="btn-confirm" :loading="nickLoading" @click="saveNickname">保存</button>
        </view>
      </view>
    </view>

    <!-- 退出登录 -->
    <view class="logout-wrap">
      <view class="card logout-card" @click="logout">
        <text class="logout-ic">🚪</text>
        <text class="logout-text">退出登录</text>
      </view>
      <!-- 注销账户危险区（双确认：警告 → 输入「确认注销」，参考 eatWhat；管理员不可自助注销，不显示入口） -->
      <view v-if="!isAdmin" class="card danger-card" @click="showDelete">
        <text class="danger-ic">⚠️</text>
        <view class="danger-info">
          <text class="danger-title">注销账户</text>
          <text class="danger-sub">将永久删除你的全部手札记录、照片与账户，不可恢复</text>
        </view>
      </view>
    </view>

    <!-- 注销确认弹窗（双确认：先列清楚要删什么，再输入「确认注销」，PRD M7） -->
    <view v-if="deleteVisible" class="modal-mask" @click="deleteVisible = false">
      <view class="modal-card" @click.stop>
        <template v-if="deleteStep === 1">
          <view class="modal-title danger">⚠️ 确认注销？</view>
          <view class="modal-tip">
            将永久删除
            <text class="danger-text">{{ delStats.total }} 条记录、{{ delStats.photos }} 张照片</text>，
            以及你的账户本身。此操作不可恢复，也不进回收站。
          </view>
          <view v-if="delStats.total" class="del-breakdown">
            <view v-for="(v, k) in delStats.counts" :key="k" class="db-row">
              <text class="db-label">{{ typeLabel(k) }}</text>
              <text class="db-val">{{ v }} 条</text>
            </view>
          </view>
          <view class="modal-actions">
            <button class="btn-cancel" @click="deleteVisible = false">再想想</button>
            <button class="btn-danger" @click="deleteStep = 2">继续注销</button>
          </view>
        </template>
        <template v-else>
          <view class="modal-title danger">最后确认</view>
          <view class="modal-tip">请输入 <text class="danger-text">确认注销</text> 来真的删除所有数据</view>
          <view class="field">
            <input class="f-input" v-model="deleteConfirmText" placeholder="输入：确认注销" />
          </view>
          <view class="modal-actions">
            <button class="btn-cancel" @click="deleteVisible = false">取消</button>
            <button class="btn-danger" :loading="deleteLoading" :disabled="deleteConfirmText !== '确认注销'" @click="doDelete">确认注销</button>
          </view>
        </template>
      </view>
    </view>

    <view style="height: 140rpx"></view>
    <BackTop :scroll-top="pageScroll" />
    <!-- #ifdef H5 --><CustomTab current="/pages/mine/mine" /><!-- #endif -->
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad, onShow, onPageScroll } from '@dcloudio/uni-app'
import {
  apiRates, apiSettings, apiSaveSettings, apiLogout,
  apiSendCode, apiBindEmail, apiMe, apiAccounts, apiAccountsMeta,
  apiUpdateProfile, apiUnbindEmail, apiDeleteMe,
  apiJournalStats, apiUnreadCount, apiExportFull,
} from '@/api'
import { userStore, setAuth, clearAuth, syncFromSettings, setCurrentAccount } from '@/store/user'
import WebLayout from '@/components/WebLayout.vue'
import CustomTab from '@/components/CustomTab.vue'
import BackTop from '@/components/BackTop.vue'

const pageScroll = ref(0)

const TYPE_LABEL = {
  ledger: '账本流水', trip: '旅游足迹', event: '大事件',
  countdown: '重要日子', asset_snapshot: '资产盘点',
}
function typeLabel(k) { return TYPE_LABEL[k] || k }

// 提醒中心未读数（顶栏/菜单红点）
const unread = ref(0)

// 头像 emoji 候选池（投资主题，前端内置，参考 eatWhat 池化思路）
const AVATAR_POOL = ['💰', '📈', '🐷', '🏦', '💹', '☕', '⚡', '🐉', '🍀', '📊', '🍵', '🏠']

const user = computed(() => userStore.user)
// 管理员徽标展示 + 隐藏注销入口（对齐 eatWhat：管理员不可自助注销）
const isAdmin = computed(() => ['admin', 'super_admin'].includes(user.value?.role || ''))
const rates = ref({})
const settings = reactive({})
// v8：账户切换
const acctVisible = ref(false)
const accountList = ref([])
const currentAccountText = computed(() => {
  if (!accountList.value.length) return '未配置'
  if (userStore.currentAccount === '__all__') return '全部账户'
  const a = accountList.value.find(x => x.name === userStore.currentAccount)
  return a ? a.name : '全部账户'
})

async function load() {
  try {
    const [r, s] = await Promise.all([apiRates(), apiSettings()])
    rates.value = r.rates || {}
    Object.assign(settings, s)
    // v8：从 settings 同步币种配置到 store
    syncFromSettings(s)
    // 同步最新用户信息（has_wx 等可能变化）
    try {
      const u = await apiMe()
      if (u) userStore.user = { ...userStore.user, ...u }
    } catch (e) {}
    // v8：加载账户列表
    try {
      const data = await apiAccounts()
      accountList.value = data.items || []
    } catch (e) {}
    // 提醒中心未读数
    try {
      const u = await apiUnreadCount()
      unread.value = u.unread || 0
    } catch (e) {}
  } catch (e) {}
}
onShow(load)
onPageScroll((e) => { pageScroll.value = e.scrollTop })

// 微信新用户登录后 reLaunch 到本页 ?bind=1：自动弹出绑定邮箱引导（对齐 eatWhat redirect=bind）
onLoad((options) => {
  if (options?.bind === '1') showBindEmail()
})

// v8：账户切换
function showAccountSwitch() {
  acctVisible.value = true
}
function pickAccount(name) {
  setCurrentAccount(name)
  acctVisible.value = false
  uni.showToast({ title: name === '__all__' ? '已切换到全部账户' : `已切换到「${name}」`, icon: 'none' })
}

// v8：归档/取消归档账户
async function toggleArchive(a) {
  const meta = accountList.value.map(x => ({
    name: x.name,
    broker: x.broker || '',
    color: x.color,
    sort: x.sort || 0,
    archived: x.name === a.name ? !x.archived : (x.archived || false),
  }))
  try {
    await apiAccountsMeta(meta)
    uni.showToast({ title: a.archived ? '已取消归档' : '已归档', icon: 'none' })
    const data = await apiAccounts()
    accountList.value = data.items || []
  } catch (e) { /* toast 已统一 */ }
}

function go(url) {
  uni.navigateTo({
    url,
    fail: () => uni.switchTab({ url, fail: () => uni.showToast({ title: '页面未就绪', icon: 'none' }) }),
  })
}

// 导出全部数据（JSON，由后端直接下发给浏览器/小程序保存）
function exportData() {
  uni.showModal({
    title: '导出我的数据',
    content: '将把全部手札记录导出为一个 JSON 文件，包含账本、足迹、日子与资产条目。',
    confirmText: '导出',
    success: async (res) => {
      if (!res.confirm) return
      try {
        const data = await apiExportFull()
        const text = JSON.stringify(data, null, 2)
        // #ifdef H5
        const blob = new Blob([text], { type: 'application/json' })
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        const d = new Date()
        const stamp = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
        a.download = `journal-${stamp}.json`
        a.click()
        URL.revokeObjectURL(a.href)
        uni.showToast({ title: '已导出', icon: 'none' })
        // #endif
        // #ifndef H5
        uni.setClipboardData({ data: text })
        uni.showToast({ title: '数据已复制到剪贴板', icon: 'none' })
        // #endif
      } catch (e) { /* toast 已统一 */ }
    },
  })
}

// ---------- 绑定邮箱 ----------
const bindVisible = ref(false)
const bindLoading = ref(false)
const bindCooldown = ref(0)
const bindForm = reactive({ email: '', code: '' })

function showBindEmail() {
  bindForm.email = user.value?.email || ''
  bindForm.code = ''
  bindVisible.value = true
}

async function sendBindCode() {
  if (!bindForm.email) return uni.showToast({ title: '请填写邮箱', icon: 'none' })
  try {
    await apiSendCode('email', bindForm.email, 'bind')
    uni.showToast({ title: '验证码已发送', icon: 'none' })
    bindCooldown.value = 60
    const timer = setInterval(() => {
      bindCooldown.value -= 1
      if (bindCooldown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (e) {}
}

async function confirmBind() {
  if (!bindForm.email || !bindForm.code) {
    return uni.showToast({ title: '请填写邮箱和验证码', icon: 'none' })
  }
  bindLoading.value = true
  try {
    const data = await apiBindEmail(bindForm.email, bindForm.code)
    // 合并场景：token 已变化，需要重新 setAuth 切到目标账号
    setAuth(data.access_token, data.user)
    if (data.merged) {
      uni.showToast({ title: '已合并到邮箱账号', icon: 'success' })
    } else {
      uni.showToast({ title: '绑定成功', icon: 'success' })
    }
    bindVisible.value = false
    // 重新加载用户数据
    setTimeout(() => load(), 400)
  } catch (e) {
  } finally {
    bindLoading.value = false
  }
}

function logout() {
  uni.showModal({
    title: '提示', content: '确定退出登录吗？',
    success: async (r) => {
      if (!r.confirm) return
      try { await apiLogout() } catch (e) { /* 即使失败也清本地态 */ }
      clearAuth()
      uni.reLaunch({ url: '/pages/login/login' })
    },
  })
}

// ---------- 个人资料（改昵称 / emoji 头像，参考 eatWhat） ----------
const avatarVisible = ref(false)
const nickVisible = ref(false)
const nickLoading = ref(false)
const nickForm = ref('')

function showAvatarPicker() {
  avatarVisible.value = true
}

async function saveAvatar(em) {
  try {
    const data = await apiUpdateProfile({ avatar: em })
    userStore.user = { ...userStore.user, ...data.user }
    avatarVisible.value = false
    uni.showToast({ title: '头像已更新', icon: 'success' })
  } catch (e) { /* toast 已统一 */ }
}

function showNicknameEdit() {
  nickForm.value = user.value?.nickname || user.value?.username || ''
  nickVisible.value = true
}

async function saveNickname() {
  const v = nickForm.value.trim()
  if (!v) return uni.showToast({ title: '昵称不能为空', icon: 'none' })
  nickLoading.value = true
  try {
    const data = await apiUpdateProfile({ nickname: v })
    userStore.user = { ...userStore.user, ...data.user }
    nickVisible.value = false
    uni.showToast({ title: '已保存', icon: 'success' })
  } catch (e) { /* toast 已统一 */ } finally {
    nickLoading.value = false
  }
}

// ---------- 解绑邮箱（参考 eatWhat） ----------
const unbindLoading = ref(false)

function confirmUnbind() {
  uni.showModal({
    title: '确认解绑？',
    content: '解绑后此邮箱可重新绑定或用于新账号注册',
    success: async (r) => {
      if (!r.confirm) return
      unbindLoading.value = true
      try {
        const data = await apiUnbindEmail()
        userStore.user = { ...userStore.user, ...data.user }
        bindVisible.value = false
        uni.showToast({ title: '已解绑', icon: 'success' })
      } catch (e) { /* toast 已统一 */ } finally {
        unbindLoading.value = false
      }
    },
  })
}

// ---------- 注销账户（双确认：警告 → 输入「确认注销」，参考 eatWhat） ----------
const deleteVisible = ref(false)
const deleteStep = ref(1)
const deleteConfirmText = ref('')
const deleteLoading = ref(false)
// 注销前先展示「将删除多少条记录、多少张照片」（PRD M7）
const delStats = reactive({ total: 0, photos: 0, counts: {} })

async function showDelete() {
  deleteStep.value = 1
  deleteConfirmText.value = ''
  deleteVisible.value = true
  try {
    const data = await apiJournalStats()
    delStats.total = data.total || 0
    delStats.photos = data.photos || 0
    delStats.counts = data.counts || {}
  } catch (e) { /* 统计拿不到也不阻塞注销流程 */ }
}

async function doDelete() {
  if (deleteConfirmText.value !== '确认注销') return
  deleteLoading.value = true
  try {
    await apiDeleteMe()
    clearAuth()
    deleteVisible.value = false
    uni.showToast({ title: '已注销', icon: 'success' })
    setTimeout(() => uni.reLaunch({ url: '/pages/login/login' }), 600)
  } catch (e) { /* toast 已统一 */ } finally {
    deleteLoading.value = false
  }
}
</script>

<style scoped>
.page { padding: 24rpx; }

/* 用户卡 */
.profile-card {
  display: flex; align-items: center; gap: 24rpx;
  background: #fff; border-radius: 24rpx; padding: 36rpx 32rpx;
  border: 1rpx solid var(--line2);
}
.avatar {
  width: 96rpx; height: 96rpx; border-radius: 50%;
  background: var(--brand-l); color: var(--brand-d);
  text-align: center; line-height: 96rpx;
  font-size: 44rpx; font-weight: 700; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.avatar-editable:active { opacity: 0.7; }
.profile-info { flex: 1; min-width: 0; }
.nick { display: block; font-size: 32rpx; font-weight: 600; color: var(--ink); }
.edit-link { font-size: 24rpx; color: var(--brand); font-weight: 400; }
/* 管理员徽标（对齐 eatWhat mine 页） */
.admin-badge {
  display: inline-block; margin-top: 6rpx; padding: 2rpx 14rpx;
  font-size: 20rpx; color: #b45309; background: #fef3c7; border-radius: 8rpx;
}
.profile-sub { display: block; margin-top: 8rpx; font-size: 22rpx; color: var(--ink3); }

/* 头像 emoji 候选网格（4 列，点选即保存，参考 eatWhat） */
.emoji-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10rpx;
  margin-bottom: 12rpx;
}
.emoji-cell {
  text-align: center; font-size: 40rpx; height: 76rpx; line-height: 76rpx;
  border: 1rpx solid var(--line2); border-radius: 10rpx; background: var(--bg);
}
.emoji-cell.on { background: var(--brand); border-color: var(--brand); }

/* 菜单卡（参考 eatWhat：emoji 图标 + 双行标题，字号加大） */
.card {
  background: #fff; border-radius: 24rpx;
  border: 1rpx solid var(--line2);
}
.menu-card { margin-top: 24rpx; padding: 0 28rpx; }
.menu-row {
  display: flex; align-items: center; padding: 28rpx 0;
  border-bottom: 1rpx solid var(--line2);
  gap: 20rpx;
}
.menu-row.no-border { border-bottom: none; }
.menu-row:active { background: var(--bg); }
.m-ic { font-size: 36rpx; flex-shrink: 0; width: 48rpx; text-align: center; }
.m-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4rpx; }
.m-label { font-size: 30rpx; font-weight: 600; color: var(--ink); }
.m-arrow { color: var(--ink3); font-size: 36rpx; flex-shrink: 0; line-height: 1; }
.m-sub-text { font-size: 22rpx; color: var(--ink3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.m-status { font-size: 24rpx; flex-shrink: 0; }
.m-status.on { color: var(--ok); }
.m-status.off { color: var(--ink3); }
.m-badge {
  min-width: 34rpx; height: 34rpx; padding: 0 8rpx; border-radius: 9999rpx;
  background: var(--danger); color: #fff; font-size: 19rpx; line-height: 34rpx;
  text-align: center; flex-shrink: 0;
}

/* 弹窗 */
.modal-mask {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5);
  z-index: 999; display: flex; align-items: center; justify-content: center;
  padding: 0 40rpx;
}
.modal-card {
  background: #fff; border-radius: 24rpx; padding: 40rpx;
  width: 100%; max-width: 600rpx;
}
.modal-title { font-size: 32rpx; font-weight: 600; color: var(--ink); margin-bottom: 16rpx; }
.modal-tip { font-size: 22rpx; color: var(--ink3); line-height: 1.6; margin-bottom: 24rpx; }
.field { padding: 20rpx 0; border-bottom: 1rpx solid var(--line2); }
.f-label { display: block; font-size: 24rpx; color: var(--ink3); margin-bottom: 12rpx; }
.f-input { font-size: 30rpx; height: 44rpx; }
.code-field { border-bottom: none; padding-bottom: 0; }
.code-row { display: flex; align-items: center; gap: 16rpx; }
.code-input { flex: 1; }
.btn-code {
  flex-shrink: 0; min-width: 140rpx; height: 56rpx; line-height: 56rpx;
  font-size: 22rpx; padding: 0 16rpx; margin: 0;
  background: var(--brand); color: #fff; border-radius: 12rpx; border: none;
}
.btn-code[disabled] { background: #DCC8B8; }
.btn-code::after { border: none; }
.modal-actions { display: flex; gap: 16rpx; margin-top: 32rpx; }

/* 注销前删除清单 */
.del-breakdown { background: var(--bg); border-radius: 14rpx; padding: 16rpx 20rpx; }
.db-row { display: flex; align-items: center; justify-content: space-between; padding: 8rpx 0; }
.db-label { font-size: 22rpx; color: var(--ink3); }
.db-val { font-size: 22rpx; color: var(--ink2); }

/* v8：账户切换弹窗 */
.acct-list { max-height: 600rpx; overflow-y: auto; }
.acct-row {
  display: flex; align-items: center; gap: 16rpx;
  padding: 24rpx 16rpx; border-bottom: 1rpx solid var(--line2);
}
.acct-row:last-child { border-bottom: none; }
.acct-row.on { background: var(--brand-sel); box-shadow: inset 3rpx 0 0 var(--brand); }
.acct-row.archived { opacity: 0.5; }
.acct-dot { width: 16rpx; height: 16rpx; border-radius: 50%; flex-shrink: 0; }
.acct-name { flex: 1; font-size: 28rpx; color: var(--ink); }
.acct-count { font-size: 22rpx; color: var(--ink3); }
.acct-ops { margin-left: auto; display: flex; gap: 12rpx; }
.op-btn { font-size: 22rpx; color: var(--brand); padding: 4rpx 12rpx; }
.acct-check { color: var(--brand); font-size: 32rpx; }
.btn-cancel, .btn-confirm {
  flex: 1; height: 80rpx; line-height: 80rpx;
  font-size: 28rpx; border-radius: 16rpx; border: none; padding: 0;
}
.btn-cancel { background: var(--line2); color: var(--ink2); }
.btn-confirm { background: var(--brand); color: #fff; }
.btn-cancel::after, .btn-confirm::after { border: none; }
/* 危险操作按钮（解绑 / 注销） */
.btn-danger-plain {
  background: #fff; color: #dc2626; border: 1rpx solid #fecaca;
}
.btn-danger { background: #dc2626; color: #fff; }
.btn-danger[disabled] { opacity: 0.4; }
.btn-danger-plain::after, .btn-danger::after { border: none; }
.danger-text { color: #dc2626; font-weight: 600; }

/* 退出登录 */
.logout-wrap { margin-top: 32rpx; padding: 0 8rpx; }
.logout-card {
  padding: 30rpx 0; text-align: center;
  display: flex; align-items: center; justify-content: center; gap: 12rpx;
  color: #dc2626;
}
.logout-card:active { background: #f8fafc; }
.logout-ic { font-size: 30rpx; }
.logout-text { font-size: 30rpx; color: #dc2626; font-weight: 500; }

/* 注销账户危险区（参考 eatWhat danger-zone） */
.danger-card {
  margin-top: 20rpx; padding: 26rpx 28rpx;
  display: flex; align-items: center; gap: 18rpx;
  background: #fff5f5; border: 1rpx solid #ffd6d6;
}
.danger-card:active { background: #ffecec; }
.danger-ic { font-size: 34rpx; }
.danger-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4rpx; }
.danger-title { font-size: 28rpx; font-weight: 600; color: #dc2626; }
.danger-sub { font-size: 22rpx; color: #c0392b; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; max-width: 800px; margin: 0 auto; }
}
/* #endif */
</style>
