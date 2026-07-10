# CloudStudio 部署指南

## 前提
你已经在 CloudStudio 里打开了项目，且 CloudStudio 能访问 8088 端口（预览地址类似 `https://webview.e2b.sh2.sandbox.cloudstudio.club/?x-cs-sandbox-id=xxx&x-cs-sandbox-port=8088`）。

## 方式一：从 GitHub 拉取最新代码

在 CloudStudio 终端里执行：

```bash
git clone https://github.com/Franklin-creator-source/tcm-agent.git
cd tcm-agent
pip3 install -r requirements.txt
python3 server.py
```

## 方式二：手动创建文件（如果 git clone 失败）

如果 CloudStudio 网络访问 GitHub 不稳定，可以手动创建两个文件：

### 1. 创建 server.py

在 CloudStudio 终端里执行：

```bash
curl -o server.py https://raw.githubusercontent.com/Franklin-creator-source/tcm-agent/master/server.py
curl -o index.html https://raw.githubusercontent.com/Franklin-creator-source/tcm-agent/master/index.html
```

如果 curl 也失败，直接从 GitHub 网页复制代码粘贴到 CloudStudio 编辑器中。

### 2. 启动服务

```bash
python3 server.py
```

看到 `🚀 服务启动 / Server started: http://0.0.0.0:8088` 就说明成功了。

然后打开 CloudStudio 的 Web Preview（端口 8088），就能看到中医问答页面。

## 验证

启动后，在 CloudStudio 预览窗口应该看到：
- 顶部有 🌿 中医知识问答 标题
- 右上角有「中文 / EN」切换按钮
- 点击中文/EN 切换语言
- 输入问题测试问答功能

## 注意事项
- API Key 已经内置在 server.py 里，不需要额外配置
- CloudStudio 沙箱休眠后需要重新运行 `python3 server.py`
- 如果端口 8088 被占用，执行 `PORT=8089 python3 server.py` 换端口
