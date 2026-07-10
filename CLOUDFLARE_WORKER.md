# Cloudflare Worker 反向代理配置

## 目的
Vercel 的 `*.vercel.app` 域名在中国大陆被 DNS 污染，无法直接访问。
通过 Cloudflare Worker 做反向代理，绕过 DNS 污染，获得一个国内可访问的 `*.workers.dev` 域名。

## 步骤

### 1. 注册 Cloudflare 账号
访问 https://dash.cloudflare.com/sign-up 注册（免费）

### 2. 创建 Worker
- 登录后，左侧菜单点击 **Workers & Pages**
- 点击 **Create application**
- 点击 **Create Worker**
- 给 Worker 起个名字，如 `tcm-proxy`
- 点击 **Deploy**
- 然后点击 **Edit code**（编辑代码）

### 3. 粘贴以下代码

将下面代码全部复制，粘贴到编辑器中（覆盖原有内容）：

```javascript
export default {
  async fetch(request) {
    const url = new URL(request.url)
    url.hostname = "tcm-agent1.vercel.app"
    // 保持路径和查询参数不变
    const newRequest = new Request(url, request)
    return fetch(newRequest)
  }
}
```

### 4. 部署
- 点击右上角 **Deploy** 按钮
- 部署成功后，你会得到一个地址，类似：
  `https://tcm-proxy.你的用户名.workers.dev`

### 5. 访问
用这个 `*.workers.dev` 地址就能在国内打开中医问答页面了！

## 注意事项
- Cloudflare Workers 免费版每天有 100,000 次请求额度，个人使用完全够
- `*.workers.dev` 域名在中国大陆可以正常访问
- 如果以后 Vercel 地址变了（重新部署等），只需修改代码中的 `tcm-agent1.vercel.app`
