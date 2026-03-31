import asyncio
import aiohttp
import csv
import os
from datetime import datetime


class IPFetcher:
    """外网IP查询类"""
    
    def __init__(self, logger):
        self.urls = [
            ("http://4.ipw.cn", "IPv4"),
            ("http://6.ipw.cn", "IPv6"),
            ("http://myip.ipip.net", "Location")
        ]
        self.db_dir = "db"
        self.csv_file = os.path.join(self.db_dir, "ip_records.csv")
        self.logger = logger
    
    def _save_to_csv(self, results):
        """保存IP记录到CSV文件"""
        # 确保数据库目录存在
        os.makedirs(self.db_dir, exist_ok=True)
        
        # 检查文件是否存在，不存在则创建并写入表头
        file_exists = os.path.exists(self.csv_file)
        
        # 准备数据
        timestamp = int(datetime.now().timestamp())
        data = []
        for (url, ip_type), result in zip(self.urls, results):
            # 如果结果包含错误信息，则保存为空
            ip_address = "" if "请求失败" in result or "请求异常" in result else result
            data.append({
                'timestamp': timestamp,
                'ip_type': ip_type,
                'url': url,
                'ip_address': ip_address
            })
        
        # 写入CSV文件
        try:
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timestamp', 'ip_type', 'url', 'ip_address']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # 如果文件不存在，写入表头
                if not file_exists:
                    writer.writeheader()
                
                # 写入数据
                writer.writerows(data)
            
            self.logger.info(f"IP记录已保存到 {self.csv_file}")
        except Exception as e:
            self.logger.error(f"保存CSV文件失败: {str(e)}")
    
    async def fetch_ip(self, session, url):
        """获取指定URL的外网IP"""
        try:
            self.logger.info(f"开始请求: {url}")
            async with session.get(url) as response:
                if response.status == 200:
                    ip = await response.text()
                    ip = ip.strip()
                    self.logger.info(f"成功获取IP: {url} -> {ip}")
                    return ip
                else:
                    error_msg = f"请求失败，状态码: {response.status}"
                    self.logger.error(f"{url} - {error_msg}")
                    return error_msg
        except Exception as e:
            error_msg = f"请求异常: {str(e)}"
            self.logger.error(f"{url} - {error_msg}")
            return error_msg
    
    async def fetch_all(self):
        """获取所有IP地址"""
        self.logger.info("开始获取所有IP地址")
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url, _ in self.urls:
                task = self.fetch_ip(session, url)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            self.logger.info("IP地址获取完成")
            return results
    
    def display_results(self, results):
        """显示查询结果"""
        print("=" * 40)
        print("外网IP查询结果")
        print("=" * 40)
        for (url, ip_type), result in zip(self.urls, results):
            print(f"{ip_type}地址 ({url}): {result}")
        print("=" * 40)


def main(logger):
    """主函数"""
    fetcher = IPFetcher(logger)
    
    # 运行异步任务
    results = asyncio.run(fetcher.fetch_all())
    
    # 显示结果
    fetcher.display_results(results)
    
    # 保存到CSV
    fetcher._save_to_csv(results)
