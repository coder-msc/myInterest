---
name: xi-release-ops
description: Deploy and troubleshoot the xi backend and WeChat mini program — 部署, 重启, stale API responses, port conflicts, Caddy /api 404, custom tabBar 消失. Use when release or production issues appear; not for feature work.
---

# 纯牛马人生手札 发布与线上运维

三端结构：`backend/`（FastAPI，8000）、`frontend/`（uni-app，H5 + mp-weixin）、`frontend-pc/`（Vue3 + Element Plus）。

线上映射：`www.icefun.cn` → `frontend-pc` 构建产物，`mobile.icefun.cn` → H5 构建产物，两者 `/api/*` 均反代到本机 `127.0.0.1:8000`；同机还有 eatWhat 占 8001，不要动。

## 一、更新后端

服务器：`/mydata/myinvesttools/backend`，venv `/mydata/myinvesttools/backend/.venv`（python3.11），服务 `xi-api.service`（`WorkingDirectory` 与 `ExecStart` 都指向该目录，单 worker）。

```bash
cd /mydata/myinvesttools/backend
# 上传代码后必须先清缓存，否则可能继续加载旧 .pyc
find . -name "__pycache__" -type d -prune -exec rm -rf {} +
find . -name "*.pyc" -delete
sudo systemctl restart xi-api
systemctl status xi-api --no-pager | head -6
```

改代码后**必须重启**：uvicorn 不带 `--reload`。

`.env` 首次部署才需要（含随机 `XI_SECRET_KEY`）；`.env`、`data/`（SQLite + 本地媒体）在覆盖代码时绝不能被删。

## 二、线上接口行为像旧代码 —— 按顺序排查

症状：磁盘上的代码已是新的，接口却仍返回旧逻辑/旧文案。

1. 现网行为取证，不要凭本地代码猜：

```bash
curl -s https://mobile.icefun.cn/api/health
curl -s -X POST https://mobile.icefun.cn/api/auth/send-code -H "Content-Type: application/json" \
  -d '{"channel":"email","target":"test@qq.com","purpose":"login"}'
```

2. 确认磁盘代码是否为新版（用新代码里的注释/字段做标记）：

```bash
grep -n "mail_enabled 不再拦截" app/api/auth.py
```

3. 看服务状态。出现 `activating (auto-restart)`、`Result: exit-code`、`status=3` 即启动失败：

```bash
systemctl status xi-api --no-pager | head -6
ss -lntp | grep 8000
```

4. 关键判据：`ss` 里的 PID 若不属于 systemd 的 MainPID，说明有一个**手动启动的残留 uvicorn**占着 8000，systemd 新进程起不来，旧进程继续用内存里的旧代码响应——此时重启多少次都无效。

```bash
kill -9 <残留PID>
sleep 2
ss -lntp | grep 8000          # 应无输出
sudo systemctl restart xi-api
sleep 2
ss -lntp | grep 8000          # PID 必须是新的
```

5. 仍返回旧行为时，确认 Python 实际加载的模块路径，排除 venv 内旧副本：

```bash
cd /mydata/myinvesttools/backend
.venv/bin/python -c "import app.api.auth as m; print(m.__file__)"
grep -rn "<旧文案关键字>" app/ | head
```

6. 服务起不来时看真实报错：`journalctl -u xi-api -n 50 --no-pager`。

常见历史坑：`python-multipart` 缺失会让启动直接崩（已写入 `requirements.txt`）；Windows 上传的 `__pycache__`/`.pyc` 会让旧字节码顶替新源码。

## 三、Caddy 反代

- `/api/*` 的 reverse_proxy **不能**写 `uri strip_prefix /api`，会把前缀剥掉导致后端 404（返回 `code:1005`）。
- 后端只监听 `127.0.0.1:8000`，公网只开 22/80/443。
- 改完 Caddyfile：`caddy validate --config /etc/caddy/Caddyfile && systemctl reload caddy`，再逐个域名验证：

```bash
for h in www mobile; do echo -n "$h: "; curl -s https://$h.icefun.cn/api/health; echo; done
```

期望 `{"code":0,...,"service":"xi-api"}`。

## 四、微信小程序自定义 tabBar

`pages.json` 里 `tabBar.custom: true` 时，根目录必须存在原生组件 `custom-tab-bar/index.{js,json,wxml,wxss}`；uni-app **原样拷贝**该目录，不编译其中 `.vue`。

两个致命坑：

1. `manifest.json` 的 `mp-weixin.lazyCodeLoading: "requiredComponents"` 与自定义 tabBar 冲突，首屏（含清缓存后首次启动）不注入组件，表现就是底部栏空白。使用自定义 tabBar 时**不要开**这个配置。
2. `custom-tab-bar/index.js` 不能 `require('./tabs.json')`。该目录不参与打包，微信原生运行时不支持加载 JSON 模块，`list` 会变空 → 底部栏渲染为空。tab 列表必须内联在 `index.js`。

tab 三处需同步：`custom-tab-bar/index.js` 内联数组、`custom-tab-bar/tabs.json`（H5 端 `CustomTab.vue` 引用）、`pages.json` 的 `tabBar.list`，页面路径要与 `src/pages/` 下真实目录一致。

验证流程：微信开发者工具 → 清缓存 → 全部清除 → 重新编译 → 导入目录必须是 `frontend/dist/build/mp-weixin`（不是 `src`、不是 `dist/dev`）。登录页是普通页面（不在 tabBar.list 中），**本来就不显示底栏**；登录进「手札」后才应出现。底栏异常时看 Console 第一条红色报错，常见为 `module ... is not defined` 或组件找不到。

## 五、请求地址

- H5（生产）：`BASE_URL = ''`，走同域相对路径由 Caddy 反代。
- 微信小程序：`BASE_URL` 必须是完整 HTTPS 域名（如 `https://mobile.icefun.cn`），不支持相对路径；本地联调才临时改 `http://127.0.0.1:8000` 并勾选「不校验合法域名」。
- 小程序请求不会发出去且无 Network 记录时，先查 `utils/config.js` 的 `BASE_URL` 是否为空串。

## 六、发布检查清单

1. 后端：`systemctl status xi-api` 为 `active (running)`，`ss` 里 8000 只有一个 PID 且属于该服务
2. 接口：`curl .../api/health` 返回 `code:0`
3. H5：`frontend/dist/build/h5` 已重新构建；站点根路径部署（资源为 `/assets/*` 绝对路径）
4. 小程序：`frontend/dist/build/mp-weixin` 已重新构建，清缓存后可正常登录且底栏可见
5. 未提交的改动先确认再 commit，不要顺手把 `data/`、`.env` 带进仓库
