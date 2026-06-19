# 外网 IP 播报工具

一个用于查询本机外网 IP、工作日信息并发送飞书通知的 Python 工具。

## 核心能力
- 并发查询 `IPv4` / `IPv6` / `Location`
- `IPv4` / `IPv6` 查询分别强制使用对应协议族网络
- 查询工作日信息（`iamwawa.cn`）
- 保存查询记录到 `db/ip_records.csv`
- 输出运行日志到 `log/YYYYMMDD.log`，并自动清理 30 天前日志
- 支持飞书机器人多配置、多模式发送
- 支持消息标题（命令行优先，其次环境变量）
- 支持 `--only_work` 工作日类型过滤发送
- 支持 `--noipw` 跳过 `4.ifconfig.me/ip` 和 `6.ifconfig.me/ip`
- 支持按飞书配置 `tag` 动态开关发送（如 `--user1`）
- 支持 `--diff` 变化播报模式：与上一轮结果一致则不播报（仍记日志），不一致才播报

## 项目结构
```text
get_ipw_v2026/
├── main.py               # 主入口
├── main.bat              # Windows 启动脚本
├── ip_fetcher.py         # IP/工作日查询与数据落盘
├── feishu_notify.py      # 飞书消息发送
├── config/
│   └── FeiShu.csv        # 飞书配置
├── db/
│   └── ip_records.csv    # 查询记录
├── log/
│   └── YYYYMMDD.log      # 日志文件
└── README.md
```

## 环境要求
- Python 3.12+
- 依赖：`aiohttp`

安装依赖：
```bash
pip install aiohttp
```

## 运行方式
按项目规则推荐：
```bash
cmd /c main.bat
```

或直接运行：
```bash
python main.py
```

## 命令行参数
```bash
python main.py [--title "标题"] [--only_work "类型"] [--noipw] [--diff] [--diff_window N] [--<tag>]
```

参数说明：
- `--title`：飞书消息标题
- `--only_work`：仅当天类型匹配时才发送飞书（例如：`工作日`）
- `--noipw`：跳过 `4.ifconfig.me/ip` 和 `6.ifconfig.me/ip` 请求，仅保留 `Location` 与工作日查询
- `--diff`：变化播报模式。与「上一轮」记录的 4 行 IP 结果对比，一致则不播报（仍记日志），不一致才播报
- `--diff_window N`：`--diff` 的回看时间窗（分钟），默认 `3`。上一轮记录距今超出该时间窗则视为「无有效上一轮」
- `--<tag>`：启用指定 tag 的飞书配置（例如：`--user1`）

### diff 变化播报模式说明
配合外部计划任务定时调度（例如每 3 分钟一次）使用：
- 每次运行读取 `db/ip_records.csv` 中最近一组记录作为「上一轮」
- 对比时**提取纯 IP**（剥离 `Location` 的「来自于…」文本），按 `IPv4` / `IPv6` / `Location_v4` / `Location_v6` 同类对比
- **请求失败项自动剔除**：本轮或上一轮该项为空（请求失败）时跳过该项，不参与对比、不视为变化
- 仅当某项成功取到的 IP 与上一轮不同 → 照常播报；全部一致或无可对比项 → 跳过播报，仅记日志留痕
- 以下情况视为「无有效上一轮」，照常播报：首次运行、上一轮记录超出 `--diff_window` 时间窗
- `diff_window` 建议略大于调度间隔（如每 3 分钟调度，可设 `--diff_window 4`），避免调度抖动导致误判为超时
- `diff_window` 也可由环境变量 `diff_window` / `DIFF_WINDOW` 提供（命令行优先）

示例：
```bash
python main.py --diff --diff_window 4 --user1
```

## 查询源说明
- `IPv4`：`http://4.ifconfig.me/ip`（强制 `AF_INET`）
- `IPv6`：`http://6.ifconfig.me/ip`（强制 `AF_INET6`）
- `Location_v4`：`http://myip.ipip.net`（强制 `AF_INET`）
- `Location_v6`：`http://myip.ipip.net`（强制 `AF_INET6`）
- 工作日接口：`https://www.iamwawa.cn/workingday/api`

## 标题优先级
1. `--title`
2. 环境变量 `fei_title` / `FEI_TITLE`
3. 环境变量 `title` / `TITLE`
4. 默认值：`播报标题`

## 飞书配置
文件：`config/FeiShu.csv`

支持两种格式（兼容）：

### 新格式（推荐）
```csv
name,url,mode,tag
机器人A,https://open.feishu.cn/open-apis/bot/v2/hook/***,text,
机器人B,https://open.feishu.cn/open-apis/bot/v2/hook/***,title,user1
```

字段说明：
- `name`：机器人名称（唯一标识）
- `url`：Webhook
- `mode`：`none` / `text` / `post` / `title`
- `tag`：分组标签（可为空）

发送规则：
- `tag` 为空：默认发送
- `tag` 非空：需命令行传对应参数（例如 `--user1`）才发送

### 旧格式（兼容）
```csv
tag,url,mode
默认机器人,https://open.feishu.cn/open-apis/bot/v2/hook/***,text
```

说明：
- 旧格式下第一列 `tag` 会被当作机器人名称使用

## 输出说明
控制台会输出：
- IP 查询结果
- 工作日信息
- `workingday_api` 返回的 GMT 时间
- GMT 转换后的北京时间（+08:00）

日志会记录：
- 请求过程
- 关键响应头（含 `Date`）
- 飞书发送结果

## 数据文件
`db/ip_records.csv` 字段：
- `timestamp`
- `ip_type`
- `url`
- `ip_address`

## 版本
当前版本：`26.6.19D`
最后更新：`2026-06-19`

## 更新日志
### 26.6.19D (2026-06-19)
- 新增：IP 与工作日接口请求失败时自动重试，默认最多请求 3 次
- 改进：重试日志显示当前尝试次数与重试等待时间，保留原有失败清空与 diff 跳过逻辑

### 26.6.19C (2026-06-19)
- 修复：diff 模式将请求失败误判为「变化」而触发播报的问题
- 改进：diff 对比改为提取纯 IP（剥离 `Location` 的「来自于…」文本），按 IP 类型同类对比
- 改进：请求失败项（本轮或上一轮为空）自动剔除，不参与对比、不视为变化

### 26.6.19B (2026-06-19)
- 新增：`--diff` 变化播报模式，与上一轮 4 行结果一致则不播报（仍记日志留痕），不一致才播报
- 新增：`--diff_window N` 回看时间窗（分钟，默认 3），支持 `diff_window` / `DIFF_WINDOW` 环境变量
- 新增：`IPFetcher.load_last_record_group` 读取上一轮记录、`build_record_map` 复用落盘与对比逻辑

### 26.6.19A (2026-06-19)
- 新增：`myip.ipip.net` 同时强制走 `AF_INET` / `AF_INET6` 查询（复用 IPv4/IPv6 的协议族逻辑），归属地接入 IPv6
- 改进：播报文本输出 4 行 IP —— 前两行为 `ifconfig.me` 的 V4/V6，后两行为 `myip.ipip.net` 的 V4/V6
- 改进：`--noipw` 现保留 `myip.ipip.net` 的 V4 与 V6 两条查询

### 26.5.23A (2026-05-23)
- 修复：`only_work` 环境变量未被读取的 bug，现在命令行未传 `--only_work` 时回退读取 `only_work` / `ONLY_WORK` 环境变量
- 新增：`only_work` 英文别名自动映射（`Workday` → `工作日`，`Weekend` → `周末`，`Holiday` → `节假日`）
- 新增：各模块添加版本号和构建日期标识
- 改进：`main.bat` 标题显示版本号

### 26.4.23A (2026-04-23)
- 调整：将 `IPv4` / `IPv6` 查询源由 `4.ipw.cn`、`6.ipw.cn` 切换为 `4.ifconfig.me/ip`、`6.ifconfig.me/ip`
- 新增：`IPv4` 请求强制走 `AF_INET`，`IPv6` 请求强制走 `AF_INET6`
- 文档：更新 `--noipw` 说明与查询源说明，确保 README 与代码一致

### 26.4.10A (2026-04-10)
- 新增：飞书配置 `tag` 动态开关机制（`--<tag>`）
- 新增：`tag` 为空默认发送，非空按命令行开关启用
- 优化：飞书配置读取兼容 `utf-8-sig`
- 优化：`tag` 匹配统一为不区分大小写
- 文档：重写 README，补充新配置格式与发送规则
