"""项目主入口。

版本：26.6.19F
日期：2026-06-19
"""

# 版本信息
VERSION = "26.6.19F"
BUILD_DATE = "2026-06-19"

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
    diff: bool = False
    diff_window: int = 3


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
        parser.add_argument("--diff", action="store_true", help="diff 模式：与上一轮结果一致则不播报（仍记日志）")
        parser.add_argument("--diff_window", type=int, help="diff 模式回看时间窗（分钟），默认 3")
        ns, unknown_args = parser.parse_known_args()

        # 动态标签开关：用于筛选 FeiShu.csv 中非空 tag 的记录
        enabled_tags = IPBroadcastApp._parse_enabled_tags(unknown_args)

        # 命令行未传 --only_work 时，回退读取环境变量
        resolved_only_work = ns.only_work
        if resolved_only_work is None:
            resolved_only_work = (
                os.environ.get("only_work")
                or os.environ.get("ONLY_WORK")
            )

        # diff_window：命令行优先，其次环境变量，最后默认 3
        resolved_diff_window = ns.diff_window
        if resolved_diff_window is None:
            env_window = os.environ.get("diff_window") or os.environ.get("DIFF_WINDOW")
            resolved_diff_window = int(env_window) if env_window and env_window.lstrip("-").isdigit() else 3

        return AppArgs(
            title=ns.title,
            only_work=resolved_only_work,
            noipw=ns.noipw,
            enabled_tags=enabled_tags,
            diff=ns.diff,
            diff_window=resolved_diff_window,
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

    # 关键词自动映射：英文 -> 中文工作日类型
    _WORKDAY_ALIAS_MAP: dict[str, str] = {
        "workday": "工作日",
        "weekend": "周末",
        "holiday": "节假日",
    }

    def _should_send_feishu(self, workingday_info: dict | None) -> bool:
        if not self.args.only_work:
            return True
        if not workingday_info:
            self.logger.warning("only_work 模式启用，但未获取到工作日信息，跳过飞书消息发送")
            return False

        expected = self.args.only_work
        # 自动将英文别名映射为中文类型（如 Workday -> 工作日）
        mapped = self._WORKDAY_ALIAS_MAP.get(expected.strip().lower())
        if mapped:
            self.logger.info(f"only_work 自动映射: [{expected}] -> [{mapped}]")
            expected = mapped

        today_type = workingday_info.get("info", "")
        if today_type != expected:
            self.logger.info(f"only_work 模式启用，今日类型为 [{today_type}]，期望 [{expected}]，跳过飞书消息发送")
            return False
        self.logger.info(f"only_work 模式启用，今日类型为 [{today_type}]，继续发送飞书消息")
        return True

    def _should_broadcast_diff(
        self,
        ip_results: list[str],
        prev_group: tuple[int, dict[str, str]] | None,
    ) -> bool:
        """diff 模式判定：与上一轮对比纯 IP，变化才播报（仍记日志）。

        - 提取纯 IP（去掉 ipip 的「来自于…」文本）后按 ip_type 同类对比
        - 请求失败项（本轮或上一轮为空）直接剔除，不参与对比、不视为变化
        - 无有效上一轮（首次 / 超出时间窗）时照常播报
        """
        if not self.args.diff:
            return True

        current = self.fetcher.build_compare_map(ip_results)

        if prev_group is None:
            self.logger.info("diff 模式：无上一轮记录，照常播报")
            return True

        prev_ts, prev_values_raw = prev_group
        age_sec = int(datetime.now().timestamp()) - prev_ts
        window_sec = self.args.diff_window * 60
        if age_sec > window_sec:
            self.logger.info(
                f"diff 模式：上一轮记录距今 {age_sec}s 超出时间窗 {window_sec}s，照常播报"
            )
            return True

        prev = {ip_type: self.fetcher.extract_ip(raw) for ip_type, raw in prev_values_raw.items()}

        # 仅对比两轮都成功取到 IP 的项，剔除请求失败项
        changed: dict[str, tuple[str, str]] = {}
        compared = 0
        for ip_type, cur_ip in current.items():
            prev_ip = prev.get(ip_type, "")
            if not cur_ip or not prev_ip:
                continue
            compared += 1
            if cur_ip != prev_ip:
                changed[ip_type] = (prev_ip, cur_ip)

        if changed:
            self.logger.info(f"diff 模式：检测到 IP 变化 {changed}，照常播报")
            return True

        if compared == 0:
            self.logger.info("diff 模式：无可对比的成功 IP 项（请求失败），跳过播报")
            return False

        self.logger.info(
            f"diff 模式：{compared} 项 IP 与上一轮一致（距今 {age_sec}s），跳过播报"
        )
        return False

    def run(self) -> None:
        ip_results, workingday_info = asyncio.run(self.fetcher.fetch_all_data(noipw=self.args.noipw))
        self.fetcher.display_results(ip_results, workingday_info)

        # 在写入本轮记录之前读取上一轮，供 diff 模式对比
        prev_group = self.fetcher.load_last_record_group() if self.args.diff else None

        self.fetcher.save_to_csv(ip_results)
        summary_text = self.fetcher.log_summary(ip_results, workingday_info)
        title = self._resolve_title(self.args.title)

        if not self._should_send_feishu(workingday_info):
            return
        if not self._should_broadcast_diff(ip_results, prev_group):
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
