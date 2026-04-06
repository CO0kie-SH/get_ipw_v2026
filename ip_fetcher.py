import asyncio
import csv
import ipaddress
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp


@dataclass(frozen=True)
class IPSource:
    url: str
    ip_type: str


class IPFetcher:
    """外网IP查询类"""

    ERROR_KEYWORDS = ("请求失败", "请求异常")

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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    @classmethod
    def _is_success_result(cls, result: str) -> bool:
        return not any(keyword in result for keyword in cls.ERROR_KEYWORDS)

    def save_to_csv(self, results: list[str]) -> None:
        """保存IP记录到CSV文件"""
        os.makedirs(self.db_dir, exist_ok=True)
        file_exists = os.path.exists(self.csv_file)

        timestamp = int(datetime.now().timestamp())
        data = []
        for source, result in zip(self.ip_sources, results):
            ip_address = result if self._is_success_result(result) else ""
            data.append({
                "timestamp": timestamp,
                "ip_type": source.ip_type,
                "url": source.url,
                "ip_address": ip_address,
            })

        try:
            with open(self.csv_file, "a", newline="", encoding="utf-8") as csvfile:
                fieldnames = ["timestamp", "ip_type", "url", "ip_address"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(data)
            self.logger.info(f"IP记录已保存到 {self.csv_file}")
        except Exception as e:
            self.logger.error(f"保存CSV文件失败: {str(e)}")

    def _save_to_csv(self, results: list[str]) -> None:
        """兼容旧调用，后续统一使用公开方法 save_to_csv"""
        self.save_to_csv(results)

    async def _fetch_url(
        self,
        session: aiohttp.ClientSession,
        url: str,
        timeout: int = 2,
        is_json: bool = False,
    ) -> str | dict[str, Any]:
        """
        通用的URL请求方法
        """
        try:
            self.logger.info(f"开始请求: {url}")
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status == 200:
                    if is_json:
                        data = await response.json(content_type=None)
                        self.logger.info(f"请求成功: {url}")
                        return data
                    text = (await response.text()).strip()
                    self.logger.info(f"成功获取: {url} -> {text}")
                    return text
                error_msg = f"请求失败，状态码: {response.status}"
                self.logger.error(f"{url} - {error_msg}")
                return error_msg
        except Exception as e:
            error_msg = f"请求异常: {str(e)}"
            self.logger.error(f"{url} - {error_msg}")
            return error_msg

    async def fetch_all_ips(self, timeout: int = 2) -> list[str]:
        """获取所有IP地址"""
        self.logger.info("开始获取所有IP地址")
        async with aiohttp.ClientSession(headers=self.headers) as session:
            tasks = [self._fetch_url(session, source.url, timeout) for source in self.ip_sources]
            raw_results = await asyncio.gather(*tasks)
            results = [result if isinstance(result, str) else str(result) for result in raw_results]
            self.logger.info("IP地址获取完成")
            return results

    async def fetch_workingday(self, date: str | None = None, timeout: int = 2) -> dict[str, Any] | None:
        """
        查询指定日期是否为工作日
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        url = f"{self.workingday_api}?date={date}"
        self.logger.info(f"开始查询工作日: {date}")

        async with aiohttp.ClientSession(headers=self.headers) as session:
            result = await self._fetch_url(session, url, timeout, is_json=True)
            if isinstance(result, dict) and result:
                self.logger.info(f"工作日查询成功: {result}")
                return result
            self.logger.error("工作日查询失败")
            return None

    async def fetch_all_data(self, ip_timeout: int = 2, workingday_timeout: int = 2) -> tuple[list[str], dict[str, Any] | None]:
        """
        获取所有数据（IP地址和工作日信息）
        """
        self.logger.info("开始获取所有数据")

        async with aiohttp.ClientSession(headers=self.headers) as session:
            date = datetime.now().strftime("%Y-%m-%d")
            workingday_url = f"{self.workingday_api}?date={date}"
            ip_tasks = [self._fetch_url(session, source.url, ip_timeout) for source in self.ip_sources]
            workingday_task = self._fetch_url(session, workingday_url, workingday_timeout, is_json=True)
            all_results = await asyncio.gather(*ip_tasks, workingday_task)

            ip_raw = all_results[:-1]
            ip_results = [item if isinstance(item, str) else str(item) for item in ip_raw]
            workingday_raw = all_results[-1]
            workingday_result = workingday_raw if isinstance(workingday_raw, dict) else None
            self.logger.info("所有数据获取完成")
            return ip_results, workingday_result

    def get_recent_ips(self, seconds: int = 5) -> list[dict[str, Any]]:
        """
        读取CSV文件中最近指定秒数内的IP地址数据
        """
        if not os.path.exists(self.csv_file):
            self.logger.warning(f"CSV文件不存在: {self.csv_file}")
            return []

        try:
            current_timestamp = int(datetime.now().timestamp())
            cutoff_timestamp = current_timestamp - seconds
            recent_records = []

            with open(self.csv_file, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if "timestamp" not in row:
                        continue
                    record_timestamp = int(row["timestamp"])
                    if record_timestamp >= cutoff_timestamp:
                        recent_records.append({
                            "timestamp": record_timestamp,
                            "ip_type": row.get("ip_type", ""),
                            "url": row.get("url", ""),
                            "ip_address": row.get("ip_address", ""),
                        })

            self.logger.info(f"获取到 {len(recent_records)} 条最近{seconds}秒内的IP记录")
            return recent_records
        except Exception as e:
            self.logger.error(f"读取CSV文件失败: {str(e)}")
            return []

    def display_results(self, ip_results: list[str], workingday_info: dict[str, Any] | None = None) -> None:
        """显示查询结果"""
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
            print("=" * 40)

    def log_summary(self, ip_results: list[str], workingday_info: dict[str, Any] | None = None) -> str:
        """输出日志摘要并返回播报文本"""
        ip_info = {"IPv4": "", "IPv6": "", "Location": ""}
        for source, result in zip(self.ip_sources, ip_results):
            if self._is_success_result(result):
                ip_info[source.ip_type] = result

        text = "播报："
        if workingday_info:
            text += f"\n今日日期：{workingday_info.get('date', '')}"
            text += f"\n今日星期：{workingday_info.get('week', '')}"
            text += f"\n今日类型：{workingday_info.get('info', '')}"
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
    
    def run(self) -> None:
        """执行完整的查询流程"""
        ip_results, workingday_info = asyncio.run(self.fetch_all_data())
        self.display_results(ip_results, workingday_info)
        self.save_to_csv(ip_results)
        self.log_summary(ip_results, workingday_info)


def main(logger) -> None:
    """主函数"""
    fetcher = IPFetcher(logger)
    fetcher.run()
