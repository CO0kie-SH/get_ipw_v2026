import asyncio
import csv
import os
from dataclasses import dataclass
from typing import Optional

import aiohttp


@dataclass(frozen=True)
class FeishuConfig:
    name: str
    url: str
    mode: str
    tag: str = ""


class FeishuNotifier:
    def __init__(self, config_dir: str = "config", logger=None):
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "FeiShu.csv")
        self.logger = logger
        self.configs = self._load_configs()

    def _load_configs(self) -> list[FeishuConfig]:
        if not os.path.exists(self.config_file):
            if self.logger:
                self.logger.warning(f"飞书配置文件不存在: {self.config_file}")
            return []

        configs = []
        try:
            with open(self.config_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                fieldnames = [name.strip().lower() for name in (reader.fieldnames or [])]
                has_name_column = "name" in fieldnames
                for row in reader:
                    if has_name_column:
                        # New format: name,url,mode,tag
                        name = (row.get("name") or "").strip()
                        tag = (row.get("tag") or "").strip()
                    else:
                        # Legacy format: tag,url,mode
                        name = (row.get("tag") or "").strip()
                        tag = ""
                    url = (row.get("url") or "").strip()
                    mode = (row.get("mode") or "").strip().lower()
                    if not name or not url:
                        if self.logger:
                            self.logger.warning(f"存在无效飞书配置，已跳过: {row}")
                        continue
                    configs.append(FeishuConfig(name=name, url=url, mode=mode, tag=tag.lower()))
            if self.logger:
                self.logger.info(f"加载飞书配置 {len(configs)} 条")
        except Exception as e:
            if self.logger:
                self.logger.error(f"加载飞书配置失败: {str(e)}")
        return configs

    def _build_message(self, v_body: str, v_title: Optional[str] = None) -> dict:
        if v_title is None:
            return {
                "msg_type": "text",
                "content": {"text": v_body},
            }
        body_without_first_line = "\n".join(v_body.splitlines()[1:])
        return {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh-CN": {
                        "title": v_title,
                        "content": [[{"tag": "text", "text": body_without_first_line}]],
                    }
                }
            },
        }

    async def _send_to_webhook(self, session: aiohttp.ClientSession, url: str, message: dict) -> bool:
        try:
            async with session.post(url, json=message) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("StatusCode") == 0:
                        if self.logger:
                            self.logger.info(f"飞书消息发送成功")
                        return True
                    if self.logger:
                        self.logger.error(f"飞书消息发送失败: {result}")
                    return False
                if self.logger:
                    self.logger.error(f"飞书消息发送失败，状态码: {response.status}")
                return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"飞书消息发送异常: {str(e)}")
            return False

    async def _send_by_config(
        self,
        session: aiohttp.ClientSession,
        config: FeishuConfig,
        v_body: str,
        v_title: Optional[str],
    ) -> tuple[str, bool]:
        mode = config.mode
        if mode == "none":
            if self.logger:
                self.logger.info(f"飞书机器人 [{config.name}] 模式为 none，跳过发送")
            return config.name, True

        if mode == "text":
            message = self._build_message(v_body, v_title=None)
        elif mode in {"post", "title"}:
            message = self._build_message(v_body, v_title=v_title)
        else:
            if self.logger:
                self.logger.warning(f"飞书机器人 [{config.name}] 未知模式: {config.mode}")
            return config.name, False

        success = await self._send_to_webhook(session, config.url, message)
        return config.name, success

    async def send_message(
        self,
        v_body: str,
        v_title: Optional[str] = None,
        tag: Optional[str] = None,
        enabled_tags: Optional[set[str]] = None,
    ) -> dict[str, bool]:
        results = {}

        if not self.configs:
            if self.logger:
                self.logger.warning("无飞书配置，跳过发送")
            return results

        enabled_tags = {item.lower() for item in (enabled_tags or set())}
        query_tag = (tag or "").strip().lower()
        selected_configs = []
        for config in self.configs:
            config_tag = (config.tag or "").strip()

            # 兼容旧逻辑：显式指定 tag 参数时，只发送匹配的记录
            if query_tag and not (config.tag == query_tag or config.name.lower() == query_tag):
                continue

            # 新逻辑：
            # 1) csv tag 为空 => 默认发送
            # 2) csv tag 非空 => 只有命令行传入对应开关（如 --user1）才发送
            if not config_tag or config_tag in enabled_tags:
                selected_configs.append(config)
            else:
                if self.logger:
                    self.logger.info(
                        f"飞书机器人 [{config.name}] tag=[{config_tag}] 未启用，跳过发送。"
                    )

        if not selected_configs:
            if self.logger:
                self.logger.warning("无匹配的飞书配置，跳过发送")
            return results

        async with aiohttp.ClientSession() as session:
            tasks = [self._send_by_config(session, config, v_body, v_title) for config in selected_configs]
            task_results = await asyncio.gather(*tasks)
            for config_name, success in task_results:
                results[config_name] = success

        return results
