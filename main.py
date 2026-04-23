"""项目主入口。"""

import argparse
import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from feishu_notify import FeishuNotifier
from ip_fetcher import IPFetcher


def cleanup_old_logs(log_dir: str, keep_days: int = 30) -> None:
    """清理超过保留期的日志文件（文件名格式：YYYYMMDD.log）"""
    cutoff_date = datetime.now().date().toordinal() - keep_days
    if not os.path.exists(log_dir):
        return

    for name in os.listdir(log_dir):
        if not name.endswith(".log"):
            continue
        stem = name[:-4]
        if len(stem) != 8 or not stem.isdigit():
            continue
        try:
            log_date = datetime.strptime(stem, "%Y%m%d").date()
        except ValueError:
            continue
        if log_date.toordinal() < cutoff_date:
            try:
                os.remove(os.path.join(log_dir, name))
            except OSError:
                pass


def setup_logging() -> logging.Logger:
    """配置日志系统。"""
    log_dir = "log"
    os.makedirs(log_dir, exist_ok=True)
    log_filename = datetime.now().strftime("%Y%m%d.log")
    log_path = os.path.join(log_dir, log_filename)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("日志系统初始化完成")
    cleanup_old_logs(log_dir=log_dir, keep_days=30)

    logger.info(f"当前工作目录: {os.getcwd()}")
    logger.info(f"项目路径: {Path(__file__).parent.resolve()}")
    logger.info(f"解释器路径: {sys.executable}")

    return logger


@dataclass
class AppArgs:
    title: str | None = None
    only_work: str | None = None
    noipw: bool = False
    enabled_tags: set[str] | None = None


class IPBroadcastApp:
    """IP 播报应用，负责主流程编排。"""

    def __init__(self, logger: logging.Logger, args: AppArgs):
        self.logger = logger
        self.args = args
        self.fetcher = IPFetcher(logger)

    @staticmethod
    def _parse_enabled_tags(unknown_args: Iterable[str]) -> set[str]:
        """从未知命令行参数中提取动态 tag 开关（如 --user1、--dev）。"""
        enabled_tags: set[str] = set()
        for arg in unknown_args:
            if not arg.startswith("--") or len(arg) <= 2:
                continue
            tag = arg[2:].strip()
            if "=" in tag:
                # 兼容 --user1=true 这类写法，本项目仅使用 key
                tag = tag.split("=", 1)[0].strip()
            if tag:
                enabled_tags.add(tag.lower())
        return enabled_tags

    @staticmethod
    def parse_args() -> AppArgs:
        parser = argparse.ArgumentParser(description="IP地址获取与播报系统")
        parser.add_argument("--title", type=str, help="消息标题")
        parser.add_argument("--only_work", type=str, help="指定今日类型相等时才发送飞书消息")
        parser.add_argument("--noipw", action="store_true", help="skip 4.ifconfig.me/ip and 6.ifconfig.me/ip")
        ns, unknown_args = parser.parse_known_args()

        # 动态标签开关：用于筛选 FeiShu.csv 中非空 tag 的记录
        enabled_tags = IPBroadcastApp._parse_enabled_tags(unknown_args)

        return AppArgs(
            title=ns.title,
            only_work=ns.only_work,
            noipw=ns.noipw,
            enabled_tags=enabled_tags,
        )

    @staticmethod
    def _resolve_title(cli_title: str | None) -> str:
        if cli_title:
            return cli_title
        title_env = (
            os.environ.get("fei_title")
            or os.environ.get("FEI_TITLE")
            or os.environ.get("title")
            or os.environ.get("TITLE")
        )
        if title_env:
            title_env = title_env.strip('"').strip("'")
        return title_env if title_env else "播报标题"

    def _should_send_feishu(self, workingday_info: dict | None) -> bool:
        if not self.args.only_work:
            return True
        if not workingday_info:
            self.logger.warning("only_work 模式启用，但未获取到工作日信息，跳过飞书消息发送")
            return False

        today_type = workingday_info.get("info", "")
        if today_type != self.args.only_work:
            self.logger.info(f"only_work 模式启用，今日类型为 [{today_type}]，跳过飞书消息发送")
            return False
        self.logger.info(f"only_work 模式启用，今日类型为 [{today_type}]，继续发送飞书消息")
        return True

    def run(self) -> None:
        ip_results, workingday_info = asyncio.run(self.fetcher.fetch_all_data(noipw=self.args.noipw))
        self.fetcher.display_results(ip_results, workingday_info)
        self.fetcher.save_to_csv(ip_results)
        summary_text = self.fetcher.log_summary(ip_results, workingday_info)
        title = self._resolve_title(self.args.title)

        if not self._should_send_feishu(workingday_info):
            return

        notifier = FeishuNotifier(logger=self.logger)
        results = asyncio.run(
            notifier.send_message(
                summary_text,
                v_title=title,
                enabled_tags=self.args.enabled_tags,
            )
        )
        self.logger.info(f"飞书发送结果: {results}")


if __name__ == "__main__":
    app_logger = setup_logging()
    app_args = IPBroadcastApp.parse_args()
    IPBroadcastApp(app_logger, app_args).run()
