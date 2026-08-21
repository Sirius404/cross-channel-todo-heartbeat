# Cross-channel Todo Heartbeat

用 Codex Heartbeat 每天只读扫描微信、Telegram、Lark 和 Codex 任务，找出需要自己处理、回复、拍板或继续的事项。它不使用 cron，不自动回消息、续跑任务或写入 Linear。

## 安全边界

- 消息源只读；不改变已读状态，不导出微信附件。
- 微信密钥、数据库、Telegram session、Lark token 和扫描结果永不进 Git。
- 微信密钥发现完全委托给本机安装的 `wx init`；本仓库不包含提取器、补丁二进制或真实密钥。

## 初始化

```bash
git clone <private-repo-url>
cd cross-channel-todo-heartbeat
cp config.example.json config.json
cp .env.example .env
chmod +x scripts/*
```

依赖：macOS、Node.js、Python 3.11+、`jq`、`sqlite3`、已登录的 `tg` 和 `lark-cli`。

### 微信 CLI 与密钥定位

当前验证版本是 `@jackwener/wx-cli@0.3.0`。其上游 GitHub 仓库目前返回 HTTP 451，因此本仓库不镜像任何源码或二进制。确认使用符合你的权限和当地规则后，显式安装并初始化：

```bash
npm install -g @jackwener/wx-cli@0.3.0
scripts/wx-setup.sh
```

`wx init` 负责检测本机微信数据目录和扫描数据库密钥，通常创建：

- `~/.wx-cli/config.json`：包含 `db_dir`、`decrypted_dir`、`keys_file` 路径；
- `~/.wx-cli/all_keys.json`：每个数据库对应的 `enc_key`，必须保持在本机；
- `~/.wx-cli/cache/`：查询缓存，不是仓库数据。

安全检查不会显示密钥值：

```bash
scripts/wx-doctor.sh
```

`scripts/wx-local` 是可移植版兼容入口。若 `wx` 不在 PATH，设置 `WX_BIN=/absolute/path/to/wx`。它只在解密缓存缺失 `SessionTable` 时创建兼容视图，不修改微信源数据库。

### Telegram 客户群

编辑 `config.json`，用群名正则和稳定的 chat ID 共同覆盖客户群。不要只写一个品牌词：群名经常是双方品牌、中文项目名或产品名。

```bash
python3 scripts/tg_live_scan.py \
  --hours 24 \
  --name-regex 'customer-a|project-b|中文项目名' \
  --chat-id -1001234567890
```

脚本使用现有 tg-cli/Telethon session 实时读取，不调用 `tg refresh/sync`，也不写 tg-cli 消息缓存。

### 微信扫描

```bash
python3 scripts/wx_scan.py \
  --keyword 待办 \
  --keyword 请确认 \
  --keyword 请回复
```

即使 `new-messages` 返回 0，也会继续检查真人未读和最近会话，避免漏掉增量游标之外的内容。

### Lark

仓库不保存 token。先在本机完成 lark-cli 用户登录，然后 Heartbeat 使用以下只读命令：

```bash
opencli lark-cli im +chat-list --as user --sort active_time --format json
opencli lark-cli im +chat-messages-list --as user --chat-id oc_xxx --start '<ISO>' --end '<ISO>' --format json
opencli lark-cli im +messages-search --as user --is-at-me --start '<ISO>' --end '<ISO>' --page-all --format json
```

### Codex 没有回应 / 应该继续

Heartbeat 先读取最近任务和全部置顶任务，再只检查可疑任务的最近几轮：

- 用户最后一条消息之后没有助手最终回应；
- `systemError`；
- `active` 超过 30 分钟没有新进展，且最近请求仍未完成；
- 助手明确说将继续，但任务中途停止且没有最终交付。

`idle`、`notLoaded`、正常完成、等待用户输入都不会仅凭状态被列入。扫描只报告任务、卡点和建议动作，不会自动续跑、发消息、归档或修改任务。

## Heartbeat，不用 cron

在 Codex 创建每天 09:00、时区 `Asia/Shanghai` 的 Heartbeat，粘贴 [heartbeat/prompt.md](heartbeat/prompt.md) 的完整内容，并把仓库路径写成绝对路径。`heartbeat/automation.toml.example` 仅展示调度结构，真实 automation/thread ID 不应提交。

可选的 Codex session 图片压缩也已包含。默认是 dry-run；实际修改必须显式加 `--apply`。修复器会拒绝打开中的 session，修改前备份到 `~/Documents/Codex Session Backups`，原图按哈希去重保存到 `~/Documents/Codex Session Images`：

```bash
scripts/compress_sessions.py --apply \
  --protected-cwd '/absolute/client/workspace-a' \
  --protected-cwd '/absolute/client/workspace-b'
```

## 验证

```bash
python3 -m unittest discover -s tests -v
scripts/wx-doctor.sh
git grep -nE '(gho_|LARK_USER_ACCESS_TOKEN=.+|enc_key.{0,10}[0-9a-fA-F]{16})' -- . ':!README.md'
```
