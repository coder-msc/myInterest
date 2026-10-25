/**
 * 统一请求封装（docs/05 §2 契约）：
 * - 自动携带 JWT，统一解包 {code,msg,data}
 * - 未登录允许浏览：GET 直接返回「未登录」，页面按空态渲染，不跳登录页
 * - 写操作（POST/PATCH/PUT/DELETE/上传）未登录时才弹「去登录」确认框
 * - token 失效（1003）：清本地登录态并静默返回，由页面展示空态
 * - 业务错误：仅 toast 后端 msg
 */
import { BASE_URL, TOKEN_KEY, USER_KEY } from './config'
import { goLogin, requireLogin } from './auth'

export function request(options) {
  const { url, method = 'GET', data = {}, auth = true, silent = false } = options

  const token = uni.getStorageSync(TOKEN_KEY)
  if (auth && !token) {
    // 浏览类请求不发网络请求，直接在页面展示空态；写操作才引导登录
    if (method !== 'GET') requireLogin()
    return Promise.reject({ code: 1002, msg: '未登录' })
  }

  return new Promise((resolve, reject) => {
    const header = { 'Content-Type': 'application/json' }
    if (auth && token) header.Authorization = 'Bearer ' + token

    uni.request({
      url: BASE_URL + url,
      method,
      data,
      header,
      timeout: 15000,
      success: (res) => {
        const body = res.data || {}
        if (body.code === 0) {
          return resolve(body.data)
        }
        // 1002 未登录 / 1003 token 失效 → 清登录态，静默交给页面渲染空态
        if ([1002, 1003].includes(body.code)) {
          uni.removeStorageSync(TOKEN_KEY)
          uni.removeStorageSync(USER_KEY)
          if (body.code === 1003 && !silent) {
            uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
          }
          return reject(body)
        }
        // 其他业务错误（2001 密码错误 / 2002 已存在 / 3001 / 4001 / 4002 …）
        if (!silent) {
          uni.showToast({ title: body.msg || '请求失败', icon: 'none' })
        }
        reject(body)
      },
      fail: (err) => {
        const msg = (err && err.errMsg) || ''
        console.error('[req fail]', BASE_URL + url, msg)
        if (!silent) {
          // 域名类错误给出可执行的排查指引（体验版最常见的失败原因）
          const tip = /domain|not in domain|url not in/i.test(msg)
            ? '接口域名未加入微信后台白名单'
            : '网络连接失败，请检查网络后重试'
          uni.showToast({ title: tip, icon: 'none' })
        }
        reject(err)
      },
    })
  })
}

export const get = (url, data, opts = {}) => request({ url, method: 'GET', data, ...opts })
export const post = (url, data, opts = {}) => request({ url, method: 'POST', data, ...opts })
export const patch = (url, data, opts = {}) => request({ url, method: 'PATCH', data, ...opts })
export const del = (url, data, opts = {}) => request({ url, method: 'DELETE', data, ...opts })
export const put = (url, data, opts = {}) => request({ url, method: 'PUT', data, ...opts })

/** 图片上传：uni.uploadFile 不走 request 的 JSON 链路，单独封装（统一解包包络） */
export function upload(url, filePath, formData = {}) {
  const token = uni.getStorageSync(TOKEN_KEY)
  if (!token) {
    requireLogin('登录后才能上传图片')
    return Promise.reject({ code: 1002, msg: '未登录' })
  }
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: BASE_URL + url,
      filePath,
      name: 'file',
      formData,
      header: { Authorization: 'Bearer ' + token },
      timeout: 60000,
      success: (res) => {
        let body = {}
        try {
          body = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
        } catch (e) {
          body = {}
        }
        if (body.code === 0) return resolve(body.data)
        uni.showToast({ title: body.msg || '上传失败', icon: 'none' })
        reject(body)
      },
      fail: (err) => {
        uni.showToast({ title: '上传失败，请检查网络', icon: 'none' })
        reject(err)
      },
    })
  })
}
