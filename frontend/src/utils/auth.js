/**
 * 登录态与「按需登录」控制
 *
 * 产品要求（微信审核）：未登录也可以浏览各功能模块，只有真正产生数据
 * （新增/修改/删除/上传）时才引导登录。
 * - isLoggedIn()：本地是否有 token
 * - requireLogin()：写操作前调用，未登录时弹确认框，用户确认才跳登录页
 * - goLogin()：以页面栈压栈方式打开登录页，保留返回能力（不做 reLaunch）
 */
import { TOKEN_KEY } from './config'

export function isLoggedIn() {
  return !!uni.getStorageSync(TOKEN_KEY)
}

export function currentRoute() {
  const pages = getCurrentPages()
  return pages.length ? pages[pages.length - 1].route : ''
}

export function goLogin() {
  if (currentRoute() === 'pages/login/login') return
  uni.navigateTo({
    url: '/pages/login/login',
    fail: () => uni.reLaunch({ url: '/pages/login/login' }),
  })
}

let prompting = false

/**
 * 写操作前的登录校验。
 * 已登录返回 true；未登录弹一次确认框并返回 false。
 * @param {string} tip 弹窗文案
 */
export function requireLogin(tip = '登录后才能保存记录，你的数据只保存在自己的账号里') {
  if (isLoggedIn()) return true
  if (prompting) return false
  prompting = true
  uni.showModal({
    title: '需要登录',
    content: tip,
    confirmText: '去登录',
    cancelText: '先看看',
    success: (res) => {
      if (res.confirm) goLogin()
    },
    complete: () => {
      setTimeout(() => { prompting = false }, 400)
    },
  })
  return false
}
