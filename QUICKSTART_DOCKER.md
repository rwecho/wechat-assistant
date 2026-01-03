# 快速开始指南（Docker）

## 一键部署

```bash
# 1. 初始化项目
make init

# 2. 编辑配置文件
vim .env
vim config/groups.yaml

# 3. 完整部署
make all
```

## 详细步骤

### 步骤 1: 准备环境

确保已安装：
- Docker (>= 20.10)
- Docker Compose (>= 2.0)

检查安装：
```bash
docker --version
docker-compose --version
```

### 步骤 2: 克隆项目

```bash
git clone <repository-url>
cd wechat-assistant
```

### 步骤 3: 初始化

```bash
make init
```

这会创建必要的目录结构：
```
wechat-assistant/
├── data/          # 数据存储
├── logs/          # 日志文件
├── backup/        # 备份目录
└── .env          # 环境变量
```

### 步骤 4: 配置环境变量

编辑 `.env` 文件：

```bash
vim .env
```

必要配置：

```env
# n8n Webhook 地址（必填）
N8N_WEBHOOK_URL=https://n8n.aishuohua.art/webhook/your-webhook-id

# 微信 API 地址
WECHAT_API_BASE=https://wechat-assistant.qnap.aishuohua.art/wechat-plugin/

# 机器人名称
BOT_NAME=阿祖
MENTION_TRIGGER=@阿祖

# 轮询间隔（秒）
POLL_INTERVAL=2
```

### 步骤 5: 配置群组

编辑 `config/groups.yaml`：

```bash
vim config/groups.yaml
```

示例配置：

```yaml
groups:
  - id: "19988917800@chatroom"
    name: "测试群组"
    enabled: true
    system_prompt: "你是一个友好的助手"

  - id: "123456789@chatroom"
    name: "另一个群组"
    enabled: false
```

### 步骤 6: 启动服务

```bash
# 方式 1: 使用 Make（推荐）
make all

# 方式 2: 使用 Docker Compose
docker-compose up -d

# 方式 3: 分步执行
make build
make up
```

### 步骤 7: 查看日志

```bash
make logs
```

或使用 Docker Compose：

```bash
docker-compose logs -f
```

## 常用命令

### 服务管理

```bash
make up          # 启动服务
make down        # 停止服务
make restart     # 重启服务
make status      # 查看状态
make logs        # 查看日志
```

### 维护操作

```bash
make backup      # 备份数据
make clean       # 清理容器
make rebuild     # 重新构建
make check       # 快速检查
```

### 开发调试

```bash
make dev         # 开发模式（不用 Docker）
make lint        # 代码检查
make test        # 运行测试
```

## 验证部署

### 1. 检查容器状态

```bash
docker-compose ps
```

正常输出：
```
NAME                    STATUS
wechat-assistant        Up (healthy)
```

### 2. 查看日志

```bash
docker-compose logs -f --tail=50
```

应该看到：
```
[INFO] 微信机器人初始化
[INFO] 监听群组数量: 5
[INFO] 轮询间隔: 2 秒
[INFO] 机器人开始运行...
```

### 3. 测试连接

```bash
# 进入容器
docker-compose exec wechat-assistant bash

# 测试微信 API
python3 -c "
from core.wechat import WeChat
w = WeChat(base_url='https://wechat-assistant.qnap.aishuohua.art/wechat-plugin/')
users = w.get_users()
print(f'✅ 连接成功，获取到 {len(users)} 个联系人')
"
```

## 更新部署

### 代码更新

```bash
# 拉取最新代码
git pull

# 重新构建并启动
make rebuild
```

### 配置更新

```bash
# 编辑配置
vim .env
vim config/groups.yaml

# 重启服务
make restart
```

## 故障排查

### 问题 1: 容器启动失败

```bash
# 查看详细日志
docker-compose logs

# 检查配置
make check
```

### 问题 2: 无法连接微信 API

检查 `.env` 中的 `WECHAT_API_BASE` 是否正确：

```bash
# 测试连接
curl -I https://wechat-assistant.qnap.aishuohua.art/wechat-plugin/
```

### 问题 3: n8n 调用失败

检查 webhook URL：

```bash
# 测试 webhook
curl -X POST https://n8n.aishuohua.art/webhook/your-webhook-id \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

## 生产环境建议

### 1. 设置日志轮转

在 `docker-compose.yml` 中已配置：

```yaml
logging:
  options:
    max-size: "10m"
    max-file: "3"
```

### 2. 定期备份

```bash
# 添加到 crontab
crontab -e

# 每天凌晨 2 点备份
0 2 * * * cd /path/to/wechat-assistant && make backup
```

### 3. 监控告警

使用健康检查：

```bash
# 检查容器健康状态
docker inspect --format='{{.State.Health.Status}}' wechat-assistant
```

### 4. 资源限制

已在 `docker-compose.yml` 中配置：

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
```

## 卸载

```bash
# 停止并删除容器
make down

# 清理数据（谨慎！）
make clean

# 删除项目目录
cd ..
rm -rf wechat-assistant
```

## 下一步

- [配置 n8n 工作流](./N8N_WORKFLOW.md)
- [完整部署文档](./DEPLOYMENT.md)
- [项目 README](./README.md)
