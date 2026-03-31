"""
主入口文件
从 ip_fetcher 模块导入 main 函数并执行
"""

import logging
import os
from datetime import datetime
from ip_fetcher import main


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
    return logger


if __name__ == "__main__":
    logger = setup_logging()
    main(logger)
