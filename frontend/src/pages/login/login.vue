<template>
  <view class="login-page">
    <view class="hero">
      <view class="logo">牛</view>
      <view class="brand">纯牛马人生手札</view>
      <view class="slogan">认真活着，随手记着</view>
    </view>

    <view class="login-card">
      <!-- 微信小程序端：一键登录（必须用户点击触发；H5/App 不编译此块） -->
      <!-- #ifdef MP-WEIXIN -->
      <view class="wx-block">
        <button class="btn-wx" :loading="wxLoading" @click="onWxLogin">
          <text class="wx-icon">✦</text> 微信一键登录
        </button>
        <view class="hint wx-hint">登录后可在「我的」中绑定邮箱</view>
        <view class="divider"><text class="divider-text">或 用邮箱验证码登录</text></view>
      </view>
      <!-- #endif -->

      <!-- 邮箱验证码：登录/注册合一（未注册邮箱自动建号，参考 eatWhat） -->
      <view class="form">
        <view class="field">
          <text class="f-label">邮箱</text>
          <input class="f-input" v-model="emailForm.email" placeholder="请输入邮箱地址" />
        </view>
        <view class="field code-field">
          <text class="f-label">验证码</text>
          <view class="code-row">
            <input class="f-input code-input" v-model="emailForm.code" placeholder="6 位验证码" />
            <button class="btn-code" :disabled="cooldown > 0" @click="sendCode">
              {{ cooldown > 0 ? `${cooldown}s` : '获取验证码' }}
            </button>
          </view>
        </view>
        <button class="btn-primary submit" :loading="loading" @click="submitEmail">
          登录 / 注册
        </button>
        <view class="hint">未注册的邮箱验证通过后将自动创建账号</view>
      </view>

      <!-- 未登录也可先浏览：审核与体验都需要「不登录也能看功能」 -->
      <view class="skip-row" @click="skipLogin">
        <text class="skip-text">暂不登录，先逛逛 →</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { onShow, onUnload } from '@dcloudio/uni-app'
import { apiWxLogin, apiSendCode, apiEmailLogin } from '@/api'
import { setAuth } from '@/store/user'

const loading = ref(false)
const wxLoading = ref(false)
const cooldown = ref(0)

// 验证码冷却截止时间存本地：离开登录页再回来不会把 60 秒倒计时清零
const CODE_DEADLINE_KEY = 'xi_code_deadline'
let cooldownTimer = null

function stopCooldown() {
  if (cooldownTimer) { clearInterval(cooldownTimer); cooldownTimer = null }
}

function tickCooldown() {
  stopCooldown()
  const remain = Math.ceil(((uni.getStorageSync(CODE_DEADLINE_KEY) || 0) - Date.now()) / 1000)
  cooldown.value = remain > 0 ? remain : 0
  if (cooldown.value <= 0) {
    uni.removeStorageSync(CODE_DEADLINE_KEY)
    return
  }
  cooldownTimer = setInterval(() => {
    const r = Math.ceil(((uni.getStorageSync(CODE_DEADLINE_KEY) || 0) - Date.now()) / 1000)
    cooldown.value = r > 0 ? r : 0
    if (cooldown.value <= 0) {
      stopCooldown()
      uni.removeStorageSync(CODE_DEADLINE_KEY)
    }
  }, 1000)
}

function startCooldown(seconds) {
  uni.setStorageSync(CODE_DEADLINE_KEY, Date.now() + seconds * 1000)
  tickCooldown()
}

onShow(tickCooldown)
onUnload(stopCooldown)

const emailForm = reactive({ email: '', code: '' })

// ---------- 邮箱验证码（登录/注册合一） ----------
async function sendCode() {
  if (!emailForm.email) {
    return uni.showToast({ title: '请先填写邮箱', icon: 'none' })
  }
  try {
    await apiSendCode('email', emailForm.email, 'login')
    uni.showToast({ title: '验证码已发送', icon: 'none' })
    startCooldown(60)
  } catch (e) {
    // 错误已统一处理
  }
}

// 暂不登录：返回来源页（若是从页面引导而来），否则进首页浏览
function skipLogin() {
  const pages = getCurrentPages()
  if (pages.length > 1) {
    uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/journal/journal' }) })
    return
  }
  uni.reLaunch({ url: '/pages/journal/journal' })
}

// 登录后去向：从页面按需登录进来（栈内有上一页）→ 返回原页面继续操作；
// 直接打开登录页 → 进手札首页
function goAfterLogin() {
  const pages = getCurrentPages()
  if (pages.length > 1) {
    uni.navigateBack({
      fail: () => uni.reLaunch({ url: '/pages/journal/journal' }),
    })
    return
  }
  uni.reLaunch({ url: '/pages/journal/journal' })
}

async function submitEmail() {
  if (!emailForm.email || !emailForm.code) {
    return uni.showToast({ title: '请填写邮箱和验证码', icon: 'none' })
  }
  loading.value = true
  try {
    // 未注册邮箱由后端自动建号，无需区分登录/注册
    const data = await apiEmailLogin(emailForm.email, emailForm.code)
    setAuth(data.access_token, data.user)
    uni.showToast({ title: data.is_new_user ? '注册并登录成功' : '登录成功', icon: 'success' })
    setTimeout(goAfterLogin, 400)
  } catch (e) {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

// ---------- 微信小程序一键登录（仅 MP-WEIXIN 编译，H5/App 不存在该函数调用） ----------
async function onWxLogin() {
  if (wxLoading.value) return
  wxLoading.value = true
  try {
    // 1. wx.login 拿临时 code
    const loginRes = await new Promise((resolve, reject) => {
      uni.login({ provider: 'weixin', success: resolve, fail: reject })
    })
    if (!loginRes.code) throw new Error('微信登录失败：未获取到 code')

    // 2. 尝试获取昵称头像（用户拒绝也可登录，只是无资料）
    let nickname = null, avatar = null
    try {
      const profile = await new Promise((resolve, reject) => {
        uni.getUserProfile({ desc: '用于完善会员资料', success: resolve, fail: reject })
      })
      nickname = profile.userInfo?.nickName || null
      avatar = profile.userInfo?.avatarUrl || null
    } catch (e) {
      // 用户拒绝授权头像昵称，仍可登录
    }

    // 3. 调后端 wx-login 换 token
    const data = await apiWxLogin(loginRes.code, nickname, avatar)
    setAuth(data.access_token, data.user)
    uni.showToast({ title: data.is_new_user ? '登录成功' : '欢迎回来', icon: 'success' })
    // 微信新用户引导绑定邮箱（对齐 eatWhat redirect=bind），其余返回来源页
    if (data.is_new_user) {
      setTimeout(() => uni.reLaunch({ url: '/pages/mine/mine?bind=1' }), 400)
    } else {
      setTimeout(goAfterLogin, 400)
    }
  } catch (e) {
    // 错误 toast 已由 request 统一处理
  } finally {
    wxLoading.value = false
  }
}
</script>

<style scoped>
.login-page { min-height: 100vh; background: linear-gradient(180deg, #D97742 0%, #E8A96B 42%, #FBF7F2 42%); }
.hero { text-align: center; padding: 110rpx 0 70rpx; color: #fff; }
.logo {
  width: 120rpx; height: 120rpx; line-height: 120rpx; margin: 0 auto;
  background: rgba(255,255,255,0.18); border: 2rpx solid rgba(255,255,255,0.5);
  border-radius: 30rpx; font-size: 60rpx; font-weight: 700;
}
.brand { font-size: 44rpx; font-weight: 700; margin-top: 24rpx; letter-spacing: 2rpx; }
.slogan { font-size: 26rpx; opacity: 0.9; margin-top: 12rpx; }
.login-card {
  background: #fff; border-radius: 28rpx; margin: 0 40rpx;
  padding: 44rpx 40rpx 50rpx; box-shadow: 0 12rpx 40rpx rgba(185,92,46,0.14);
}
.field { padding: 26rpx 0; border-bottom: 1rpx solid #F6EFE7; }
.f-label { display: block; font-size: 24rpx; color: #9C9187; margin-bottom: 12rpx; }
.f-input { font-size: 30rpx; height: 44rpx; align-items: center; }
.submit { margin-top: 50rpx; }
.skip-row { text-align: center; padding: 32rpx 0 8rpx; }
.skip-text { font-size: 26rpx; color: #9C9187; }

/* 验证码行 */
.code-field { border-bottom: none; padding-bottom: 0; }
.code-row { display: flex; align-items: center; gap: 16rpx; }
.code-input { flex: 1; }
.btn-code {
  flex-shrink: 0; min-width: 180rpx; height: 60rpx; line-height: 60rpx;
  font-size: 24rpx; padding: 0 16rpx; margin: 0;
  background: #D97742; color: #fff; border-radius: 12rpx; border: none;
}
.btn-code[disabled] { background: #DCC8B8; }
.btn-code::after { border: none; }

/* 微信一键登录块（仅小程序渲染） */
.wx-block { margin-bottom: 10rpx; }
.btn-wx {
  background: #07c160; color: #fff; border-radius: 44rpx;
  font-size: 30rpx; height: 88rpx; line-height: 88rpx; text-align: center;
  border: none; display: flex; align-items: center; justify-content: center;
}
.btn-wx::after { border: none; }
.wx-icon { margin-right: 10rpx; font-size: 32rpx; }
.wx-hint { margin-top: 20rpx; }

.divider { display: flex; align-items: center; margin: 34rpx 0 6rpx; }
.divider::before, .divider::after {
  content: ''; flex: 1; height: 1rpx; background: #EDE3D8;
}
.divider-text {
  padding: 0 20rpx; font-size: 24rpx; color: #9C9187;
}

.hint { text-align: center; margin-top: 28rpx; font-size: 26rpx; color: #9C9187; }
</style>
