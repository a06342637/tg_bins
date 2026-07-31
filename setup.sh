#!/usr/bin/env bash
# tg_bins 交互式配置向导:问答生成 config.yaml 并启动容器。
# 可单独运行:  bash setup.sh   (或由 install.sh 自动调用)
set -e
[ -t 0 ] || exec < /dev/tty

echo "======================================"
echo "        tg_bins 配置向导"
echo "======================================"
echo

read -rp "1) Telegram Bot Token (BotFather 提供): " BOT_TOKEN
echo "   可选:my.telegram.org 申请的 api_id/api_hash(用于 @用户名 反查任意用户 id,直接回车跳过)"
read -rp "   api_id(纯数字,可留空): " API_ID
API_HASH=""
[ -n "$API_ID" ] && read -rp "   api_hash: " API_HASH
echo "   管理员 user id:第一个是【超级管理员】(可增删用户 / 更新 / 重启 / 看日志),"
echo "   其余仅可查询卡号。不知道 id?先把 bot 跑起来给它发 /id 获取。"
read -rp "   多个用英文逗号分隔: " ADMIN_RAW

while true; do
  read -rp "2) 要配置几个 HandyAPI 账号做轮询? " N
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

read -rp "3) 日志按钮显示最近几条?[默认 20]: " LOG_LINES
LOG_LINES="${LOG_LINES:-20}"

# ---- 生成 config.yaml ----
{
  echo "telegram:"
  echo "  bot_token: \"$BOT_TOKEN\""
  if [ -n "$API_ID" ]; then
    echo "  api_id: $API_ID          # MTProto 用户名反查"
    echo "  api_hash: \"$API_HASH\""
  fi
  echo "  admin_ids:            # 第一个是超级管理员(最高权限),其余仅可查询"
  IFS=',' read -ra IDS <<< "$ADMIN_RAW"
  for id in "${IDS[@]}"; do
    id="$(echo "$id" | xargs)"
    [ -n "$id" ] && echo "    - $id"
  done
  echo "handyapi:"
  echo "  accounts:            # 多账号 round-robin 轮询,限流自动切换"
  for ((i = 1; i <= N; i++)); do
    echo "    - name: \"acct$i\""
    echo "      frontend_key: \"${FKS[i]}\""
    echo "      backend_key: \"${BKS[i]}\""
  done
  echo "settings:"
  echo "  log_lines: $LOG_LINES"
  echo "  log_retention_days: 30"
} > config.yaml

echo
echo "✅ 已生成 config.yaml(后期可直接编辑此文件,再点机器人里『重启』即可生效)"
echo

if ! command -v docker >/dev/null 2>&1; then
  echo "⚠️  未检测到 docker,请先安装,再运行: docker compose up -d --build"
  exit 1
fi

echo "🚀 正在构建并启动容器…"
docker compose up -d --build
echo
echo "✅ 完成!常用命令:"
echo "   实时日志: docker compose logs -f"
echo "   停止:     docker compose down"
echo "   在 Telegram 给 bot 发 /start 打开面板,/id 获取自己的 user id。"
