# 中医知识问答 - Koyeb 部署指南

## 部署步骤（5分钟搞定）

### 第1步：注册 Koyeb
打开 https://www.koyeb.com → 用 GitHub 账号登录

### 第2步：上传代码到 GitHub
1. 在 GitHub 新建仓库（如 `tcm-agent`）
2. 把以下4个文件上传到仓库根目录：
   - `server.py`
   - `index.html`
   - `Dockerfile`
   - `README.md`（可选）

### 第3步：在 Koyeb 部署
1. Koyeb 控制台 → **Create Service** → **GitHub** → 选择你的仓库
2. 配置如下：

| 配置项 | 值 |
|---|---|
| Builder | **Dockerfile** |
| Path | `/` |
| Port | `8088` |
| Instance | **Free**（512MB） |
| Regions | 随便选（推荐 `fra` 或 `sin`） |

3. 展开 **Environment Variables**，添加以下4个变量：

| 变量名 | 值 |
|---|---|
| `IMA_OPENAPI_CLIENTID` | `d39da832a3285437af00a1dbc6d11581` |
| `IMA_OPENAPI_APIKEY` | `Ta0Z2ZslUrB3ICRrBWFeh6GworUMQwxxQjxxTVqKieKKRZh1BLI72cFoyBYyDHdV618o6oz2AA==` |
| `DEEPSEEK_API_KEY` | `sk-1421314d63634de08de8b11ea27d95ec` |
| `PORT` | `8088` |

4. 点 **Deploy**
5. 几分钟后获得公网域名：`https://你的应用名.koyeb.app`

### 第4步：转发给微信好友
直接把 `https://你的应用名.koyeb.app` 发给微信好友即可，**7×24 永久在线，不休眠**。

---

## 文件说明

```
tcm-agent-server/
├── server.py       后端服务（纯Python，无外部依赖）
├── index.html      前端聊天页面
├── Dockerfile      Docker构建配置
├── railway.json    Railway部署配置（备选）
└── DEPLOY.md       通用部署指南
```

## 常见问题

**Q: 部署失败怎么办？**
检查 Koyeb 的 Deploy Logs，确认4个环境变量都正确设置。

**Q: 访问报错 502？**
服务可能还在启动中，等1-2分钟后刷新。

**Q: 如何更新代码？**
修改 GitHub 仓库 → Koyeb 自动重新部署。

**Q: 免费额度用完了？**
Free 实例永久免费，每月750小时（足够31天×24小时）。
