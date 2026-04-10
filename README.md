# 外网 IP 播报工具

一个用于查询本机外网 IP、工作日信息并发送飞书通知的 Python 工具。

## 核心能力
- 并发查询 `IPv4` / `IPv6` / `Location`
- 查询工作日信息（`iamwawa.cn`）
- 保存查询记录到 `db/ip_records.csv`
- 输出运行日志到 `log/YYYYMMDD.log`，并自动清理 30 天前日志
- 支持飞书机器人多配置、多模式发送
- 支持消息标题（命令行优先，其次环境变量）
- 支持 `--only_work` 工作日类型过滤发送
- 支持 `--noipw` 跳过 `4.ipw.cn` 和 `6.ipw.cn`
- 支持按飞书配置 `tag` 动态开关发送（如 `--user1`）

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
python main.py [--title "标题"] [--only_work "类型"] [--noipw] [--<tag>]
```

参数说明：
- `--title`：飞书消息标题
- `--only_work`：仅当天类型匹配时才发送飞书（例如：`工作日`）
- `--noipw`：跳过 `4.ipw.cn` 和 `6.ipw.cn` 请求，仅保留 `Location` 与工作日查询
- `--<tag>`：启用指定 tag 的飞书配置（例如：`--user1`）

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
当前版本：`26.4.10A`
最后更新：`2026-04-10`

## 更新日志
### 26.4.10A (2026-04-10)
- 新增：飞书配置 `tag` 动态开关机制（`--<tag>`）
- 新增：`tag` 为空默认发送，非空按命令行开关启用
- 优化：飞书配置读取兼容 `utf-8-sig`
- 优化：`tag` 匹配统一为不区分大小写
- 文档：重写 README，补充新配置格式与发送规则
