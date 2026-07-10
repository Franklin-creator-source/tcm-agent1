FROM python:3.11-slim

WORKDIR /app

# 复制项目文件
COPY server.py .
COPY index.html .

# 暴露端口
EXPOSE 8088

# 设置环境变量默认值（实际值在 Koyeb 控制台配置）
ENV PORT=8088
ENV IMA_OPENAPI_CLIENTID=""
ENV IMA_OPENAPI_APIKEY=""
ENV DEEPSEEK_API_KEY=""
ENV KB_ID="SV1LP_ohoX7Fq_Up6P1ssrCAuEKyoyL2hQCqunxxrFk="

# 启动服务
CMD ["python3", "server.py"]
