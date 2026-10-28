import { watch } from 'vue'

/**
 * 小程序的自定义 tabBar 是框架独立渲染的节点，层级高于页面里的 fixed 弹层，
 * 页面内的 z-index 拦不住它 —— 弹层/对话框打开时底部会被 tabBar 压住，内容看不全也点不到。
 * 这里在弹层打开时主动隐藏 tabBar，关闭后恢复。
 * H5 端的 CustomTab 是普通组件（z-index 999），本来就会被 z-index 1000 的蒙层盖住，无需处理。
 */
export function setTabBarHidden(hidden) {
  // #ifdef MP-WEIXIN
  const pages = getCurrentPages()
  const page = pages[pages.length - 1]
  if (!page) return
  // 微信原生 Page 实例带 getTabBar；uni-app Vue3 下也可从 $scope 上取到（基础库差异兜底）
  const bar = typeof page.getTabBar === 'function'
    ? page.getTabBar()
    : (page.$vm && page.$vm.$scope && typeof page.$vm.$scope.getTabBar === 'function'
      ? page.$vm.$scope.getTabBar()
      : null)
  if (bar && typeof bar.setData === 'function') bar.setData({ maskHidden: !!hidden })
  // #endif
}

/** 监听「弹层是否打开」，自动隐藏/恢复自定义 tabBar */
export function watchMask(getter) {
  watch(getter, (open) => setTabBarHidden(!!open))
}
