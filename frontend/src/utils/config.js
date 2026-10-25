/**
 * 环境与接口地址配置（docs/05-前端三端设计.md §2 baseUrl 策略）
 * - H5 生产：走同域相对路径，/api 由 Caddy 反代到后端（mobile.icefun.cn）
 * - 小程序：不支持相对路径，必须是完整域名
 * - 当前阶段（本地联调）：dev / build 均指向本机后端；提审发布前把下面的
 *   BASE_URL 换成 https://mobile.icefun.cn
 * - 真机调试：127.0.0.1 不通，改成电脑的局域网 IP（同一 WiFi）
 */
// #ifdef H5
// 生产走同域相对路径：/api 由 Caddy 反代到后端（mobile.icefun.cn）
export const BASE_URL = ''
// #endif
// #ifdef MP-WEIXIN
// 生产环境：小程序不支持相对路径，必须是完整 HTTPS 域名
// 本地联调时临时改回 http://127.0.0.1:8000，并在开发者工具勾选「不校验合法域名」
export const BASE_URL = 'https://mobile.icefun.cn'
// #endif

export const TOKEN_KEY = 'xi_token'
export const USER_KEY = 'xi_user'

/**
 * 媒体地址：本地存储返回的是 /api/media/{id}/raw（需要鉴权），
 * 而 <image src> 无法携带 Authorization 头，因此改用 ?t=<token> 查询参数。
 * 七牛外链是完整 https 地址，原样返回。
 */
export function mediaUrl(url) {
  if (!url) return ''
  if (/^https?:\/\//.test(url)) return url
  const token = uni.getStorageSync(TOKEN_KEY)
  if (!token) return BASE_URL + url
  return `${BASE_URL}${url}${url.includes('?') ? '&' : '?'}t=${encodeURIComponent(token)}`
}
