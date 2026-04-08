import asyncio
import csv
import ipaddress
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import aiohttp


@dataclass(frozen=True)
class IPSource:
    url: str
    ip_type: str


class IPFetcher:
    """Public IP query helper."""

    ERROR_KEYWORDS = ("request failed", "request exception", "请求失败", "请求异常")

    def __init__(self, logger):
        self.ip_sources = [
            IPSource("http://4.ipw.cn", "IPv4"),
            IPSource("http://6.ipw.cn", "IPv6"),
            IPSource("http://myip.ipip.net", "Location"),
        ]
        self.workingday_api = "https://www.iamwawa.cn/workingday/api"
        self.db_dir = "db"
        self.csv_file = os.path.join(self.db_dir, "ip_records.csv")
        self.logger = logger
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        self.workingday_response_date_gmt = ""
        self.workingday_response_date_local = ""

    @classmethod
    def _is_success_result(cls, result: str) -> bool:
        return not any(keyword in result for keyword in cls.ERROR_KEYWORDS)

    def _active_ip_sources(self, noipw: bool = False) -> list[IPSource]:
        if not noipw:
            return self.ip_sources
        return [source for source in self.ip_sources if source.ip_type == "Location"]

    @staticmethod
    def _gmt_to_local_time_str(gmt_date_str: str, offset_hours: int = 8) -> str:
        if not gmt_date_str:
            return ""
        try:
            dt = parsedate_to_datetime(gmt_date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local_tz = timezone(timedelta(hours=offset_hours))
            local_dt = dt.astimezone(local_tz)
            return local_dt.strftime("%Y-%m-%d %H:%M:%S %z")
        except (TypeError, ValueError):
            return ""

    def _log_workingday_response_headers(self, url: str, response: aiohttp.ClientResponse) -> None:
        if url.startswith(self.workingday_api):
            headers = dict(response.headers)
            self.logger.info(f"workingday_api response headers: {headers}")
            date_header = headers.get("Date", "")
            self.workingday_response_date_gmt = date_header
            self.workingday_response_date_local = self._gmt_to_local_time_str(date_header)

    def save_to_csv(self, results: list[str]) -> None:
        """Save IP records to CSV."""
        os.makedirs(self.db_dir, exist_ok=True)
        file_exists = os.path.exists(self.csv_file)

        timestamp = int(datetime.now().timestamp())
        data = []
        for source, result in zip(self.ip_sources, results):
            ip_address = result if self._is_success_result(result) else ""
            data.append(
                {
                    "timestamp": timestamp,
                    "ip_type": source.ip_type,
                    "url": source.url,
                    "ip_address": ip_address,
                }
            )

        try:
            with open(self.csv_file, "a", newline="", encoding="utf-8") as csvfile:
                fieldnames = ["timestamp", "ip_type", "url", "ip_address"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(data)
            self.logger.info(f"IP records saved to {self.csv_file}")
        except Exception as e:
            self.logger.error(f"failed to save CSV: {str(e)}")

    async def _fetch_url(
        self,
        session: aiohttp.ClientSession,
        url: str,
        timeout: int = 2,
        is_json: bool = False,
    ) -> str | dict[str, Any]:
        """Generic URL request helper."""
        try:
            self.logger.info(f"start request: {url}")
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                self._log_workingday_response_headers(url, response)
                if response.status == 200:
                    if is_json:
                        data = await response.json(content_type=None)
                        self.logger.info(f"request success: {url}")
                        return data
                    text = (await response.text()).strip()
                    self.logger.info(f"fetch success: {url} -> {text}")
                    return text
                error_msg = f"request failed, status code: {response.status}"
                self.logger.error(f"{url} - {error_msg}")
                return error_msg
        except Exception as e:
            error_msg = f"request exception: {str(e)}"
            self.logger.error(f"{url} - {error_msg}")
            return error_msg

    async def fetch_all_data(
        self,
        ip_timeout: int = 2,
        workingday_timeout: int = 2,
        noipw: bool = False,
    ) -> tuple[list[str], dict[str, Any] | None]:
        """Fetch IP data and workingday info in one session."""
        self.logger.info("start fetching all data")

        async with aiohttp.ClientSession(headers=self.headers) as session:
            date = datetime.now().strftime("%Y-%m-%d")
            workingday_url = f"{self.workingday_api}?date={date}"

            active_sources = self._active_ip_sources(noipw=noipw)
            if noipw:
                self.logger.info("noipw mode enabled, skip 4.ipw.cn and 6.ipw.cn")

            ip_tasks = [self._fetch_url(session, source.url, ip_timeout) for source in active_sources]
            workingday_task = self._fetch_url(session, workingday_url, workingday_timeout, is_json=True)
            all_results = await asyncio.gather(*ip_tasks, workingday_task)

            ip_raw = all_results[:-1]
            ip_type_to_result = {source.ip_type: "" for source in self.ip_sources}
            for source, item in zip(active_sources, ip_raw):
                ip_type_to_result[source.ip_type] = item if isinstance(item, str) else str(item)
            ip_results = [ip_type_to_result[source.ip_type] for source in self.ip_sources]

            workingday_raw = all_results[-1]
            workingday_result = workingday_raw if isinstance(workingday_raw, dict) else None
            self.logger.info("all data fetched")
            return ip_results, workingday_result

    def display_results(self, ip_results: list[str], workingday_info: dict[str, Any] | None = None) -> None:
        """Print query results."""
        print("=" * 40)
        print("外网IP查询结果")
        print("=" * 40)
        for source, result in zip(self.ip_sources, ip_results):
            print(f"{source.ip_type}地址 ({source.url}): {result}")
        print("=" * 40)

        if workingday_info:
            print("工作日信息")
            print("=" * 40)
            print(f"日期: {workingday_info.get('date', '')}")
            print(f"星期: {workingday_info.get('week', '')}")
            print(f"类型: {workingday_info.get('info', '')}")
            if self.workingday_response_date_gmt:
                print(f"workingday_api Date (GMT): {self.workingday_response_date_gmt}")
            if self.workingday_response_date_local:
                print(f"workingday_api Date (+08:00): {self.workingday_response_date_local}")
            print("=" * 40)

    def log_summary(self, ip_results: list[str], workingday_info: dict[str, Any] | None = None) -> str:
        """Build and log summary text."""
        ip_info = {"IPv4": "", "IPv6": "", "Location": ""}
        for source, result in zip(self.ip_sources, ip_results):
            if self._is_success_result(result):
                ip_info[source.ip_type] = result

        text = "播报："
        if workingday_info:
            text += f"\n今日日期：{workingday_info.get('date', '')}"
            text += f"\n今日星期：{workingday_info.get('week', '')}"
            text += f"\n今日类型：{workingday_info.get('info', '')}"

        if self.workingday_response_date_local:
            text += f"\n当前时间：{self.workingday_response_date_local.split(' ')[1]}"

        if "." in ip_info["IPv4"]:
            text += f"\n当前 V4：{ip_info['IPv4']}"
        if self._is_valid_ipv6(ip_info["IPv6"]):
            text += f"\n当前 V6：{ip_info['IPv6']}"

        text += f"\n{ip_info['Location']}"
        self.logger.info(text)
        return text

    @staticmethod
    def _is_valid_ipv6(value: str) -> bool:
        if not value:
            return False
        try:
            return isinstance(ipaddress.ip_address(value), ipaddress.IPv6Address)
        except ValueError:
            return False
