# tg_bins

Telegram BIN 查询机器人,基于 HandyAPI,支持**多账号轮询**(一个限流自动切换,查询无感),Docker Compose 一键部署。

## 功能

- 直接发**数字**即可查询,无需任何命令或提示:
  - 发完整卡号或 ≥6 位数字 → 自动取**前 6 位**,优先走 HandyAPI;
  - **4–5 位**数字 → 走内置本地库查询(HandyAPI 不支持 4 位);
  - HandyAPI 账号**全部限流**时,自动用本地库兜底,不中断;
  - 支持带空格/横线的卡号(如 `4571 7360 1234 5678`)。
- 查询结果**先英文、后中文**两段显示(卡组织 / 类型 / 等级 / 发卡行 / 国家 + 国旗)。
- **预付卡警告**:任何形式的预付卡(PREPAID),都会在结果最下方追加**三遍**醒目警告。
- **多账号轮询**:配置多个 HandyAPI 账号,某个触发限流(约 10 次/分钟)时自动切到下一个并冷却该账号。
- **权限控制**:只有 `admin_ids` 里的用户能查询和操作,其他人**完全静默**(不回任何内容)。
- **管理面板按钮**:🔄 更新 / ♻️ 重启 / 📜 日志(最近 N 条) / ℹ️ 状态(各账号可用情况)。

## 一键部署

在服务器上:

```bash
git clone https://github.com/a06342637/tg_bins.git
cd tg_bins
bash setup.sh
```

`setup.sh` 会依次询问:Bot Token、管理员 user id、**要几个 HandyAPI 账号轮询(输入 N 就问 N 次 Frontend/Backend key)**、日志条数,然后生成 `config.yaml` 并 `docker compose up -d --build` 启动。

> 不知道自己的 user id?给 bot 发 `/id` 即可获取。

## 配置(后期修改)

所有交互项都写在 **`config.yaml`**,随时可直接编辑,改完点机器人里的『♻️ 重启』(或 `docker compose restart`)即生效。字段见 [`config.example.yaml`](config.example.yaml)。

## 管理按钮说明

- **重启**:进程退出,由 `restart: unless-stopped` 自动拉起(几秒恢复)。
- **更新**:容器内 `git pull` 拉取本仓库最新代码后自动重启。
  - ⚠️ 若本次更新改动了 `requirements.txt`(依赖),需在服务器上手动重建:`docker compose up -d --build`。
- **日志**:返回内存中最近 `log_lines` 条日志(完整日志用 `docker compose logs -f`)。

## 注意事项

- **本仓库是公开的:切勿提交 `config.yaml`**(已在 `.gitignore` 中)。密钥只留在服务器本地。
- HandyAPI 免费版:约 **3000–5000 次/月、10 次/分钟**。多账号轮询可叠加额度。
- **本地 BIN 库**:仓库内置 `data/bin-list-data.csv`(约 37 万条开放数据),用于 4–5 位查询和 HandyAPI 限流兜底,完全离线。数据为静态快照、更新频率低,可自行替换该文件。
