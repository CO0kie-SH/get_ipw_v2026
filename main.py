"""
主入口文件
从 ip_fetcher 模块导入 main 函数并执行
"""

import logging
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from ip_fetcher import IPFetcher
from feishu_notify import FeishuNotifier


def setup_logging():
    """配置日志系统"""
    # 确保日志目录存在
    log_dir = "log"
    os.makedirs(log_dir, exist_ok=True)

    # 日志文件名格式：YYYYMMDD.log
    log_filename = datetime.now().strftime("%Y%m%d.log")
    log_path = os.path.join(log_dir, log_filename)

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info("日志系统初始化完成")
    
    # 输出路径信息
    logger.info(f"当前工作目录: {os.getcwd()}")
    logger.info(f"项目路径: {Path(__file__).parent.resolve()}")
    logger.info(f"解释器路径: {sys.executable}")
    
    return logger


if __name__ == "__main__":
    logger = setup_logging()
    
    fetcher = IPFetcher(logger)
    ip_results, workingday_info = asyncio.run(fetcher.fetch_all_data())
    fetcher.display_results(ip_results, workingday_info)
    fetcher._save_to_csv(ip_results)
    fetcher.log_summary(ip_results, workingday_info)
    
    notifier = FeishuNotifier(logger=logger)
    
    ip_info = {"IPv4": "", "IPv6": "", "Location": ""}
    for (url, ip_type), result in zip(fetcher.ip_urls, ip_results):
        if "请求失败" not in result and "请求异常" not in result:
            ip_info[ip_type] = result
    
    message = "总结："
    if workingday_info:
        message += f"\n今日日期：{workingday_info.get('date', '')}"
        message += f"\n今日星期：{workingday_info.get('week', '')}"
        message += f"\n今日类型：{workingday_info.get('info', '')}"
    message += f"\n当前 V4：{ip_info['IPv4']}"
    message += f"\n当前 V6：{ip_info['IPv6']}"
    message += f"\n{ip_info['Location']}"
    
    results = asyncio.run(notifier.send_message(message))
    logger.info(f"飞书发送结果: {results}")
