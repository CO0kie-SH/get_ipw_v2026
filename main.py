"""
主入口文件
从 ip_fetcher 模块导入 main 函数并执行
"""

import logging
import os
import sys
import asyncio
import argparse
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
    parser = argparse.ArgumentParser(description='IP地址获取与播报系统')
    parser.add_argument('--title', type=str, help='消息标题')
    parser.add_argument('--only_work', type=str, help='指定今日类型相等时才发送飞书消息')
    args = parser.parse_args()
    
    logger = setup_logging()
    
    fetcher = IPFetcher(logger)
    ip_results, workingday_info = asyncio.run(fetcher.fetch_all_data())
    fetcher.display_results(ip_results, workingday_info)
    fetcher._save_to_csv(ip_results)
    
    summary_text = fetcher.log_summary(ip_results, workingday_info)
    
    if args.title:
        v_title = args.title
    else:
        title_env = os.environ.get('title') or os.environ.get('TITLE')
        if title_env:
            title_env = title_env.strip('"').strip("'")
        v_title = title_env if title_env else "播报标题"
    
    # 判断是否需要发送飞书消息
    should_send = True
    if args.only_work:
        if workingday_info:
            today_type = workingday_info.get('info', '')
            if today_type != args.only_work:
                logger.info(f"only_work 模式启用，今日类型为 [{today_type}]，跳过飞书消息发送")
                should_send = False
            else:
                logger.info(f"only_work 模式启用，今日类型为 [{today_type}]，继续发送飞书消息")
        else:
            logger.warning("only_work 模式启用，但未获取到工作日信息，跳过飞书消息发送")
            should_send = False
    
    if should_send:
        notifier = FeishuNotifier(logger=logger)
        results = asyncio.run(notifier.send_message(summary_text, v_title=v_title))
        logger.info(f"飞书发送结果: {results}")
