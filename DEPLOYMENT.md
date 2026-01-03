# Docker 部署指南

## 使用 Docker Compose 部署（推荐）

### 1. 准备配置文件

确保 `.env` 文件已正确配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置必要的环境变量：

```env
# n8n 配置
N8N_WEBHOOK_URL=https://n8n.aishuohua.art/webhook/your-webhook-id

# 微信配置（远程地址）
WECHAT_API_BASE=https://wechat-assistant.qnap.aishuohua.art/wechat-plugin/

# 机器人配置
BOT_NAME=阿祖
MENTION_TRIGGER=@阿祖
POLL_INTERVAL=2
```

### 2. 构建并启动

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 3. 常用命令

```bash
# 重启服务
docker-compose restart

# 查看状态
docker-compose ps

# 进入容器
docker-compose exec wechat-assistant bash

# 更新代码后重新构建
docker-compose up -d --build

# 清理数据（谨慎使用）
docker-compose down -v
```

## 使用 Docker 直接部署

### 1. 构建镜像

```bash
docker build -t wechat-assistant:latest .
```

### 2. 运行容器

```bash
docker run -d \
  --name wechat-assistant \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/.env:/app/.env:ro \
  -v $(pwd)/config/groups.yaml:/app/config/groups.yaml:ro \
  -e TZ=Asia/Shanghai \
  wechat-assistant:latest
```

### 3. 管理容器

```bash
# 查看日志
docker logs -f wechat-assistant

# 停止容器
docker stop wechat-assistant

# 启动容器
docker start wechat-assistant

# 删除容器
docker rm wechat-assistant

# 查看资源使用
docker stats wechat-assistant
```

## 使用 GitHub Container Registry

### 1. 拉取镜像

```bash
docker pull ghcr.io/your-username/wechat-assistant:latest
```

### 2. 运行

```bash
docker run -d \
  --name wechat-assistant \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/.env:/app/.env:ro \
  ghcr.io/your-username/wechat-assistant:latest
```

## 生产环境建议

### 1. 使用健康检查

Docker Compose 已配置健康检查，可以配合自动重启：

```yaml
restart: unless-stopped
healthcheck:
  test: ["CMD", "python3", "-c", "import sys; sys.exit(0)"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### 2. 日志管理

限制日志大小，防止磁盘占满：

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 3. 资源限制

防止容器占用过多资源：

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
```

### 4. 数据持久化

重要数据已通过 volume 挂载：

- `/app/data` - 数据存储
- `/app/logs` - 日志文件

### 5. 配置热更新

配置文件以只读方式挂载，更新后需重启：

```bash
# 修改配置文件
vim config/groups.yaml

# 重启服务
docker-compose restart
```

## 故障排查

### 1. 查看日志

```bash
# 查看所有日志
docker-compose logs

# 查看最近 100 行
docker-compose logs --tail=100

# 实时跟踪
docker-compose logs -f
```

### 2. 进入容器调试

```bash
docker-compose exec wechat-assistant bash

# 检查配置
cat /app/.env

# 手动运行测试
python3 -c "from core.wechat import WeChat; print('OK')"
```

### 3. 网络问题

如果容器无法访问外部服务：

```bash
# 测试网络连接
docker-compose exec wechat-assistant curl -I https://n8n.aishuohua.art
```

### 4. 权限问题

确保挂载的目录权限正确：

```bash
# 修复权限
sudo chown -R $(id -u):$(id -g) data logs
```

## 更新部署

### 方式 1: 使用 Docker Compose

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 清理旧镜像
docker image prune -f
```

### 方式 2: 使用 GitHub Registry

```bash
# 拉取最新镜像
docker pull ghcr.io/your-username/wechat-assistant:latest

# 重新创建容器
docker-compose up -d

# 或使用 docker run
docker stop wechat-assistant
docker rm wechat-assistant
docker run -d ... (同上)
```

## CI/CD 自动部署

推送代码到 GitHub 后，GitHub Actions 会自动：

1. **代码检查** - 运行 lint 和类型检查
2. **构建镜像** - 构建 Docker 镜像
3. **推送镜像** - 推送到 GitHub Container Registry

查看 Actions 状态：
```bash
# 在 GitHub 仓库页面
Actions -> 查看工作流运行状态
```

## 监控和告警

### 1. 日志监控

```bash
# 监控错误日志
docker-compose logs -f | grep ERROR

# 统计处理数量
docker-compose logs -f | grep "处理了.*条消息"
```

### 2. 性能监控

```bash
# 查看资源使用
docker stats wechat-assistant

# 查看容器详情
docker inspect wechat-assistant
```

## 备份和恢复

### 备份

```bash
# 备份数据
tar -czf wechat-assistant-backup-$(date +%Y%m%d).tar.gz data/ logs/

# 备份配置
tar -czf wechat-assistant-config-$(date +%Y%m%d).tar.gz .env config/
```

### 恢复

```bash
# 停止服务
docker-compose down

# 恢复数据
tar -xzf wechat-assistant-backup-20240103.tar.gz

# 重启服务
docker-compose up -d
```
