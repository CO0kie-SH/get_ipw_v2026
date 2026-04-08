# 外网 IP 播报工具

一个用于查询本机外网 IP、工作日信息并发送飞书通知的 Python 工具。

## 核心能力
- 并发查询 `IPv4` / `IPv6` / `Location`。
- 查询工作日信息（`iamwawa.cn`）。
- 保存查询记录到 `db/ip_records.csv`。
- 输出运行日志到 `log/YYYYMMDD.log`，并自动清理 30 天前日志。
- 支持飞书机器人多配置、多模式发送。
- 支持消息标题（命令行优先，其次环境变量）。
- 支持 `--only_work` 工作日类型过滤发送。
- 支持 `--noipw` 跳过 `4.ipw.cn` 和 `6.ipw.cn`。
- 读取并打印 `workingday_api` 响应头中的 `Date`，并转换为北京时间（+08:00）。

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
python main.py [--title "标题"] [--only_work "类型"] [--noipw]
```

参数说明：
- `--title`：飞书消息标题。
- `--only_work`：仅当当天类型匹配时发送飞书（例如：`工作日`）。
- `--noipw`：跳过 `4.ipw.cn` 和 `6.ipw.cn` 请求，只保留 `Location` 与工作日查询。

## 标题优先级
1. `--title`
2. 环境变量 `fei_title` / `FEI_TITLE`
3. 环境变量 `title` / `TITLE`
4. 默认值：`播报标题`

## 飞书配置
文件：`config/FeiShu.csv`

字段：
- `tag`：机器人标识
- `url`：webhook
- `mode`：`none` / `text` / `post` / `title`

说明：
- `none`：跳过发送
- `text`：文本消息
- `post`/`title`：带标题消息（此模式下正文会去掉第一行）

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
当前版本：`26.4.8A`
最后更新：`2026-04-08`

## 更新日志
### 26.4.8A (2026-04-08)
- 优化：精简未使用接口，减少冗余模块代码。
- 新增：`--noipw` 参数支持（跳过 `4.ipw.cn` / `6.ipw.cn`）。
- 新增：打印 `workingday_api` 响应头。
- 新增：将响应头 `Date (GMT)` 转换并展示为北京时间（`+08:00`）。
- 优化：飞书 `title/post` 消息模式下正文去掉第一行。
- 优化：播报文本支持输出当前时间（来自响应头转换结果）。
- 文档：重写 README，统一当前行为与参数说明。
