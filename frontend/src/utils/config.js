/**
 * 环境与接口地址配置（docs/05-前端三端设计.md §2 baseUrl 策略）
 * - H5 生产：走同域相对路径，/api 由 Caddy 反代到后端（mobile.icefun.cn）
 * - 小程序：同域相对路径（经配置的合法域名/代理）
 * - 真机调试：如需改地址，把 BASE_URL 改成局域网 IP 或 https 域名
 */
// #ifdef H5
// 生产走同域相对路径：/api 由 Caddy 反代到后端（mobile.icefun.cn）
export const BASE_URL = ''
// #endif
// #ifndef H5
export const BASE_URL = ''
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
