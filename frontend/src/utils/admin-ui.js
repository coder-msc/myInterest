/**
 * 管理后台（仅 H5）使用的 Element Plus 组件集合。
 * 本文件只会被 pages/admin/admin.vue 及其子面板引用，
 * 小程序构建不注册 admin 页面，因此不会被进包。
 */
import { ElLoading } from 'element-plus'

export {
  ElButton,
  ElCheckbox,
  ElDatePicker,
  ElDialog,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus'

/** v-loading 指令（Element Plus 只导出 directive 实例，这里转成脚本作用域变量） */
export const vLoading = ElLoading.directive
