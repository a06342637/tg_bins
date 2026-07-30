#!/usr/bin/env bash
# tg_bins 一键部署:检查 docker -> 克隆/更新仓库 -> 交互配置 -> 启动容器。
#
# 用法(服务器上一行):
#   bash <(curl -fsSL https://raw.githubusercontent.com/a06342637/tg_bins/main/install.sh)
set -e

REPO_URL="https://github.com/a06342637/tg_bins.git"
DIR="tg_bins"

# 通过管道运行时 stdin 非终端,接到 /dev/tty 保证后续交互输入可用
if [ ! -t 0 ]; then
  exec < /dev/tty
fi

echo "======================================"
echo "        tg_bins 一键部署"
echo "======================================"

# 1) 环境检查
if ! command -v git >/dev/null 2>&1; then
  echo "❌ 未检测到 git,请先安装。"; exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "❌ 未检测到 Docker,请先安装:https://docs.docker.com/engine/install/"; exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "❌ 未检测到 docker compose 插件(需要 Docker Compose v2)。"; exit 1
fi

# 2) 克隆或更新
if [ -d "$DIR/.git" ]; then
  echo "📁 仓库已存在,拉取最新代码…"
  git -C "$DIR" pull --ff-only || true
else
  echo "📥 克隆仓库(含本地 BIN 数据集,约 27MB)…"
  git clone --depth 1 "$REPO_URL" "$DIR"
fi
cd "$DIR"

# 3) 交互配置并启动
bash setup.sh
