# 外网IP查询工具

一个简单的外网IP地址查询工具，支持IPv4和IPv6地址查询，并自动记录查询结果。

## 功能特性

- 异步查询IPv4和IPv6地址
- 自动记录查询日志
- 将查询结果保存到CSV文件
- 使用unix时间戳记录查询时间
- 异常时CSV保存为空，便于数据分析

## 环境要求

- Python 3.12+
- aiohttp 库

## 安装依赖

```bash
pip install aiohttp
```

## 使用方法

### 运行程序

```bash
python main.py
```

或者使用项目规则指定的命令：

```bash
cmd /c "set PYTHONIOENCODING=utf-8 && D:\0Code2\py312\python main.py"
```

### 输出示例

```
========================================
外网IP查询结果
========================================
IPv4地址 (http://4.ipw.cn): ***.***.***.***
IPv6地址 (http://6.ipw.cn): 请求异常: Cannot connect to host 6.ipw.cn:80 ssl:default [getaddrinfo failed]
========================================
```

## 项目结构

```
m2603/
├── main.py              # 主入口文件
├── ip_fetcher.py        # IP查询功能模块
├── log/                 # 日志目录
│   └── 20260331.log     # 日志文件（格式：YYYYMMDD.log）
├── db/                  # 数据库目录
│   └── ip_records.csv   # IP记录CSV文件
├── README.md            # 项目说明书
└── 项目规则.md          # 项目规则文档
```

## 文件说明

### 日志文件

- 位置：`log/` 目录
- 命名格式：`YYYYMMDD.log`（如 `20260331.log`）
- 保留策略：默认保留30天
- 日志级别：INFO、ERROR

### CSV数据文件

- 位置：`db/ip_records.csv`
- 字段说明：
  - `timestamp`：unix时间戳
  - `ip_type`：IP类型（IPv4/IPv6）
  - `url`：查询URL
  - `ip_address`：IP地址（异常时为空）

### CSV文件示例

```csv
timestamp,ip_type,url,ip_address
1774930569,IPv4,http://4.ipw.cn,***.***.***.***
1774930569,IPv6,http://6.ipw.cn,
```

## 代码结构

### main.py

主入口文件，负责：
- 日志系统初始化
- 调用IP查询功能

### ip_fetcher.py

IP查询功能模块，包含：
- `IPFetcher` 类：封装IP查询功能
  - `fetch_ip()`：获取单个IP地址
  - `fetch_all()`：获取所有IP地址
  - `display_results()`：显示查询结果
  - `_save_to_csv()`：保存结果到CSV文件
- `main()` 函数：主逻辑函数

## 版本历史

### 26.3.31A (2026-03-31)

**初始版本发布**

- 实现IPv4和IPv6地址查询功能
- 添加日志系统，支持文件和控制台输出
- 添加CSV数据存储，使用unix时间戳
- 异常时CSV保存为空，便于数据分析
- 采用模块化设计，职责分离清晰
- 符合项目规则要求

## 注意事项

1. 确保网络连接正常
2. IPv6地址查询需要网络环境支持IPv6
3. 日志文件会自动创建，无需手动创建
4. CSV文件支持追加模式，不会覆盖已有数据
5. 日志文件建议定期清理，保留30天即可

## 许可证

本项目仅供学习和个人使用。

## 联系方式

如有问题或建议，请通过项目仓库提交Issue。
