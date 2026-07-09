# 中医知识问答 - 部署指南

## 部署到 Railway（推荐，免费额度足够）

### 第1步：注册 Railway
打开 https://railway.app → 用 GitHub 账号登录

### 第2步：上传代码到 GitHub
1. 在 GitHub 新建仓库（如 `tcm-agent`）
2. 把 `/workspace/tcm-agent-server/` 目录下所有文件上传到仓库

### 第3步：在 Railway 部署
1. Railway 控制台 → **New Project** → **Deploy from GitHub repo**
2. 选择你刚建的仓库
3. 进入 **Settings** → 设置环境变量：

| 变量名 | 值 |
|---|---|
| `IMA_OPENAPI_CLIENTID` | `d39da832a3285437af00a1dbc6d11581` |
| `IMA_OPENAPI_APIKEY` | `Ta0Z2ZslUrB3ICRrBWFeh6GworUMQwxxQjxxTVqKieKKRZh1BLI72cFoyBYyDHdV618o6oz2AA==` |
| `DEEPSEEK_API_KEY` | `sk-1421314d63634de08de8b11ea27d95ec` |
| `PORT` | `8088` |

4. Railway 会自动构建部署，几分钟后给你一个公网域名：
   `https://tcm-agent-production.up.railway.app`

### 第4步：转发给微信好友
直接把这个 Railway 域名发给微信好友即可，7×24 在线，不受沙箱休眠影响。

---

## 部署到 Render（备选，也有免费额度）

1. 打开 https://render.com → 注册
2. **New** → **Web Service** → 连接 GitHub 仓库
3. 配置：
   - Build Command: `pip install -r requirements.txt`（如无则留空，纯Python无依赖）
   - Start Command: `python3 server.py`
   - 环境变量同上
4. 部署后获得域名：`https://你的应用名.onrender.com`

---

## 文件说明

```
tcm-agent-server/
├── server.py       后端服务（纯Python，无外部依赖）
├── index.html      前端页面
├── railway.json    Railway 部署配置
└── start.sh        本地启动脚本
```
