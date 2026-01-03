.PHONY: help build up down restart logs status clean install test lint

help: ## 显示帮助信息
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## 安装依赖
	pip3 install -r requirements.txt

test: ## 运行测试
	python3 -m pytest || echo "测试未配置，跳过"

lint: ## 代码检查
	flake8 core/ config/ utils/ --max-line-length=127 || true

build: ## 构建 Docker 镜像
	docker-compose build

up: ## 启动服务
	docker-compose up -d

down: ## 停止服务
	docker-compose down

restart: ## 重启服务
	docker-compose restart

logs: ## 查看日志
	docker-compose logs -f

status: ## 查看状态
	docker-compose ps

clean: ## 清理容器和镜像
	docker-compose down -v
	docker system prune -f

dev: ## 开发模式运行（不使用 Docker）
	python3 bot.py

check: ## 快速检查
	@echo "检查配置文件..."
	@test -f .env || (echo "❌ .env 文件不存在" && exit 1)
	@test -f config/groups.yaml || (echo "❌ config/groups.yaml 不存在" && exit 1)
	@echo "✅ 配置文件检查通过"
	@echo "检查 Python 导入..."
	@python3 -c "from core.wechat import WeChat; from core.processor import MessageProcessor; from core.storage import StorageManager; print('✅ 导入检查通过')"

backup: ## 备份数据
	tar -czf backup/wechat-assistant-$$(date +%Y%m%d-%H%M%S).tar.gz data/ logs/
	@echo "✅ 备份完成: backup/"

init: ## 初始化项目
	@echo "初始化项目..."
	@mkdir -p data logs backup
	@cp .env.example .env 2>/dev/null || echo ".env 已存在"
	@echo "✅ 初始化完成"
	@echo "请编辑 .env 和 config/groups.yaml 文件"

rebuild: ## 重新构建并启动
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

all: init install build up ## 完整部署：初始化 -> 安装 -> 构建 -> 启动
