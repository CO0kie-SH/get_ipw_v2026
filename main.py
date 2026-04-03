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
    
    summary_text = fetcher.log_summary(ip_results, workingday_info)
    
    notifier = FeishuNotifier(logger=logger)
    results = asyncio.run(notifier.send_message(summary_text))
    logger.info(f"飞书发送结果: {results}")
