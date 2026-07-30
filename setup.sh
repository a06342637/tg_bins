#!/usr/bin/env bash
# tg_bins 交互式部署向导:问几个问题 -> 生成 config.yaml -> 启动容器。
# 用法:  bash setup.sh
set -e

echo "======================================"
echo "        tg_bins 部署向导"
echo "======================================"
echo

read -rp "1) Telegram Bot Token (BotFather 提供): " BOT_TOKEN
read -rp "2) 管理员 user id(多个用英文逗号分隔): " ADMIN_RAW

while true; do
  read -rp "3) 要配置几个 HandyAPI 账号做轮询? " N
  [[ "$N" =~ ^[1-9][0-9]*$ ]] && break
  echo "   请输入一个正整数。"
done

declare -a FKS BKS
for ((i = 1; i <= N; i++)); do
  echo
  echo "--- HandyAPI 账号 $i ---"
  read -rp "   Frontend API Key (PUB-...): " FK
  read -rp "   Backend  API Key (HAS-...): " BK
  FKS[i]="$FK"
  BKS[i]="$BK"
done

read -rp "4) 日志按钮显示最近几条?[默认 20]: " LOG_LINES
LOG_LINES="${LOG_LINES:-20}"

# ---- 生成 config.yaml ----
{
  echo "telegram:"
  echo "  bot_token: \"$BOT_TOKEN\""
  echo "  admin_ids:"
  IFS=',' read -ra IDS <<< "$ADMIN_RAW"
  for id in "${IDS[@]}"; do
    id="$(echo "$id" | xargs)"
    [ -n "$id" ] && echo "    - $id"
  done
  echo "handyapi:"
  echo "  accounts:"
  for ((i = 1; i <= N; i++)); do
    echo "    - name: \"acct$i\""
    echo "      frontend_key: \"${FKS[i]}\""
    echo "      backend_key: \"${BKS[i]}\""
  done
  echo "settings:"
  echo "  log_lines: $LOG_LINES"
} > config.yaml

echo
echo "✅ 已生成 config.yaml(后期可直接编辑此文件,再点机器人里的『重启』即可生效)"
echo

if ! command -v docker >/dev/null 2>&1; then
  echo "⚠️  未检测到 docker,请先安装 Docker,然后运行: docker compose up -d --build"
  exit 1
fi

echo "🚀 正在构建并启动容器…"
docker compose up -d --build
echo
echo "✅ 完成!常用命令:"
echo "   实时日志: docker compose logs -f"
echo "   停止:     docker compose down"
echo "   在 Telegram 里给你的 bot 发 /start 打开管理面板。"
