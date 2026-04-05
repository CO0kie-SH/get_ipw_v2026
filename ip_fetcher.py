import asyncio
import aiohttp
import csv
import os
import ipaddress
from datetime import datetime


class IPFetcher:
    """外网IP查询类"""
    
    def __init__(self, logger):
        # IP查询URL配置
        self.ip_urls = [
            ("http://4.ipw.cn", "IPv4"),
            ("http://6.ipw.cn", "IPv6"),
            ("http://myip.ipip.net", "Location")
        ]
        # 工作日查询API配置
        self.workingday_api = "https://www.iamwawa.cn/workingday/api"
        # 数据库配置
        self.db_dir = "db"
        self.csv_file = os.path.join(self.db_dir, "ip_records.csv")
        # 日志器
        self.logger = logger
        # 请求头配置
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    
    def save_to_csv(self, results):
        """保存IP记录到CSV文件"""
        os.makedirs(self.db_dir, exist_ok=True)
        file_exists = os.path.exists(self.csv_file)
        
        timestamp = int(datetime.now().timestamp())
        data = []
        for (url, ip_type), result in zip(self.ip_urls, results):
            ip_address = "" if "请求失败" in result or "请求异常" in result else result
            data.append({
                'timestamp': timestamp,
                'ip_type': ip_type,
                'url': url,
                'ip_address': ip_address
            })
        
        try:
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timestamp', 'ip_type', 'url', 'ip_address']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(data)
            self.logger.info(f"IP记录已保存到 {self.csv_file}")
        except Exception as e:
            self.logger.error(f"保存CSV文件失败: {str(e)}")

    def _save_to_csv(self, results):
        """兼容旧调用，后续统一使用公开方法 save_to_csv"""
        self.save_to_csv(results)
    
    async def _fetch_url(self, session, url, timeout=2, is_json=False):
        """
        通用的URL请求方法
        
        Args:
            session: aiohttp会话
            url: 请求URL
            timeout: 超时时间（秒）
            is_json: 是否返回JSON格式
        
        Returns:
            str/dict: 响应内容
        """
        try:
            self.logger.info(f"开始请求: {url}")
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status == 200:
                    if is_json:
                        data = await response.json()
                        self.logger.info(f"请求成功: {url}")
                        return data
                    else:
                        text = await response.text()
                        text = text.strip()
                        self.logger.info(f"成功获取: {url} -> {text}")
                        return text
                else:
                    error_msg = f"请求失败，状态码: {response.status}"
                    self.logger.error(f"{url} - {error_msg}")
                    return error_msg
        except Exception as e:
            error_msg = f"请求异常: {str(e)}"
            self.logger.error(f"{url} - {error_msg}")
            return error_msg
    
    async def fetch_all_ips(self, timeout=2):
        """获取所有IP地址"""
        self.logger.info("开始获取所有IP地址")
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_url(session, url, timeout) for url, _ in self.ip_urls]
            results = await asyncio.gather(*tasks)
            self.logger.info("IP地址获取完成")
            return results
    
    async def fetch_workingday(self, date=None, timeout=2):
        """
        查询指定日期是否为工作日
        
        Args:
            date: 查询日期，格式为YYYY-MM-DD，默认为今天
            timeout: 超时时间（秒），默认5秒
        
        Returns:
            dict: 包含工作日信息的字典，失败返回None
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        url = f"{self.workingday_api}?date={date}"
        self.logger.info(f"开始查询工作日: {date}")
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            result = await self._fetch_url(session, url, timeout, is_json=True)
            if isinstance(result, dict):
                self.logger.info(f"工作日查询成功: {result}")
                return result
            else:
                self.logger.error(f"工作日查询失败")
                return None
    
    async def fetch_all_data(self, ip_timeout=2, workingday_timeout=2):
        """
        获取所有数据（IP地址和工作日信息）
        
        Args:
            ip_timeout: IP请求超时时间（秒）
            workingday_timeout: 工作日请求超时时间（秒）
        
        Returns:
            tuple: (IP结果列表, 工作日信息字典)
        """
        self.logger.info("开始获取所有数据")
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            # 并行获取IP地址
            ip_tasks = [self._fetch_url(session, url, ip_timeout) for url, _ in self.ip_urls]
            ip_results = await asyncio.gather(*ip_tasks)
            
            # 获取工作日信息
            date = datetime.now().strftime("%Y-%m-%d")
            workingday_url = f"{self.workingday_api}?date={date}"
            self.logger.info(f"开始查询工作日: {date}")
            workingday_result = await self._fetch_url(session, workingday_url, workingday_timeout, is_json=True)
            
            self.logger.info("所有数据获取完成")
            return ip_results, workingday_result
    
    def get_recent_ips(self, seconds=5):
        """
        读取CSV文件中最近指定秒数内的IP地址数据
        
        Args:
            seconds: 查询的时间范围（秒），默认5秒
        
        Returns:
            list: 包含IP记录的列表
        """
        if not os.path.exists(self.csv_file):
            self.logger.warning(f"CSV文件不存在: {self.csv_file}")
            return []
        
        try:
            current_timestamp = int(datetime.now().timestamp())
            cutoff_timestamp = current_timestamp - seconds
            recent_records = []
            
            with open(self.csv_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    record_timestamp = int(row['timestamp'])
                    if record_timestamp >= cutoff_timestamp:
                        recent_records.append({
                            'timestamp': int(row['timestamp']),
                            'ip_type': row['ip_type'],
                            'url': row['url'],
                            'ip_address': row['ip_address']
                        })
            
            self.logger.info(f"获取到 {len(recent_records)} 条最近{seconds}秒内的IP记录")
            return recent_records
        except Exception as e:
            self.logger.error(f"读取CSV文件失败: {str(e)}")
            return []
    
    def display_results(self, ip_results, workingday_info=None):
        """显示查询结果"""
        print("=" * 40)
        print("外网IP查询结果")
        print("=" * 40)
        for (url, ip_type), result in zip(self.ip_urls, ip_results):
            print(f"{ip_type}地址 ({url}): {result}")
        print("=" * 40)
        
        if workingday_info:
            print("工作日信息")
            print("=" * 40)
            print(f"日期: {workingday_info.get('date', '')}")
            print(f"星期: {workingday_info.get('week', '')}")
            print(f"类型: {workingday_info.get('info', '')}")
            print("=" * 40)
    
    def log_summary(self, ip_results, workingday_info=None):
        """输出日志摘要并返回播报文本"""
        ip_info = {"IPv4": "", "IPv6": "", "Location": ""}
        for (url, ip_type), result in zip(self.ip_urls, ip_results):
            if "请求失败" not in result and "请求异常" not in result:
                ip_info[ip_type] = result
        
        text = "播报："
        if workingday_info:
            text += f"\n今日日期：{workingday_info.get('date', '')}"
            text += f"\n今日星期：{workingday_info.get('week', '')}"
            text += f"\n今日类型：{workingday_info.get('info', '')}"
        text += f"\n当前 V4：{ip_info['IPv4']}"
        if self._is_valid_ipv6(ip_info['IPv6']):
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
    
    def run(self):
        """执行完整的查询流程"""
        # 获取所有数据
        ip_results, workingday_info = asyncio.run(self.fetch_all_data())
        
        # 显示结果
        self.display_results(ip_results, workingday_info)
        
        # 保存到CSV
        self.save_to_csv(ip_results)
        
        # 输出日志摘要
        self.log_summary(ip_results, workingday_info)


def main(logger):
    """主函数"""
    fetcher = IPFetcher(logger)
    fetcher.run()
