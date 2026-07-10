# 中医知识问答 - 部署状态 & 解决方案

## ✅ 当前状态：Vercel 部署已成功！

| 项目 | 状态 | 说明 |
|------|------|------|
| 代码推送 | ✅ 完成 | https://github.com/Franklin-creator-source/tcm-agent |
| Vercel 部署 | ✅ 成功 | https://tcm-agent1.vercel.app |
| 知识库 API | ✅ 正常 | 已确认返回 25 部中医经典信息 |
| 问答页面 | ✅ 正常 | 页面正确显示 |
| 国内访问 | ❌ 被墙 | `.vercel.app` 域名在中国大陆被 DNS 污染 |

## ❌ 问题原因

**不是代码问题，不是部署问题，是网络问题。**

`*.vercel.app` 域名在中国大陆被 DNS 污染：
- DNS 解析返回错误 IP（31.13.88.26，实际是 Facebook 的 IP）
- TLS 握手失败，浏览器打不开
- 这影响所有 Vercel 免费域名，不是你的项目独有问题

## 🔧 解决方案（选一个）

### 方案一：Cloudflare Worker 反代（推荐，免费，5 分钟搞定）

详见 `CLOUDFLARE_WORKER.md`

简单步骤：
1. 注册 https://dash.cloudflare.com
2. Workers & Pages → Create Worker
3. 粘贴代码：
```javascript
export default {
  async fetch(request) {
    const url = new URL(request.url)
    url.hostname = "tcm-agent1.vercel.app"
    return fetch(new Request(url, request))
  }
}
```
4. Deploy → 得到 `*.workers.dev` 地址 → 国内可访问

### 方案二：绑定已备案域名

如果你有已备案的域名：
1. Vercel 控制台 → 项目 → Settings → Domains
2. 添加域名（如 `tcm.yourdomain.com`）
3. 去域名服务商添加 CNAME 记录 → `cname.vercel-dns.com`

### 方案三：改用国内云平台

- **Zeabur** (https://zeabur.com) - 支持从 GitHub 直接导入，国内可访问
- **Sealos** (https://sealos.io) - 国内团队，稳定
- **微信云开发** - 最稳定，但需要小程序

## 📁 项目文件说明

```
tcm-agent-server/
├── api/
│   └── index.py        ← Vercel Serverless 函数（Flask 应用）
├── index.html          ← 前端问答页面
├── requirements.txt     ← Python 依赖
├── vercel.toml         ← Vercel 配置
├── server.py           ← 本地运行版（非 Vercel）
├── Dockerfile          ← Docker 部署用
├── CLOUDFLARE_WORKER.md ← Cloudflare 反代教程
└── DEPLOY.md           ← 通用部署说明
```

## 🔑 Vercel 环境变量（确保已配置）

在 Vercel 控制台 → Settings → Environment Variables 中检查：

| 变量名 | 值 |
|--------|---|
| `IMA_OPENAPI_CLIENTID` | `d39da832a3285437af00a1dbc6d11581` |
| `IMA_OPENAPI_APIKEY` | `Ta0Z2ZslUrB3ICRrBWFeh6GworUMQwxxQjxxTVqKieKKRZh1BLI72cFoyBYyDHdV618o6oz2AA==` |
| `DEEPSEEK_API_KEY` | `sk-1421314d63634de08de8b11ea27d95ec` |
| `KB_ID` | `SV1LP_ohoX7Fq_Up6P1ssrCAuEKyoyL2hQCqunxxrFk=` |

## 📝 总结

你的 Vercel 部署已经完全成功，代码没问题，API 正常工作。
**唯一的问题是 `*.vercel.app` 域名在国内被墙。**
用 Cloudflare Worker 反代（方案一）是最快免费的解决办法。
