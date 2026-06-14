"""
代理管理模块

负责代理IP的获取、健康检查、自动切换和负载均衡。
支持多种代理来源：免费代理、付费API、自建代理。
"""

import random
import time
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from loguru import logger


@dataclass
class Proxy:
    """代理对象"""
    host: str
    port: int
    protocol: str = "http"  # http, https, socks5
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    anonymity: str = "anonymous"  # transparent, anonymous, elite
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[float] = None
    last_check: Optional[float] = None
    avg_response_time: float = 0.0
    is_healthy: bool = True

    def to_url(self) -> str:
        """生成代理URL"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    def to_playwright_dict(self) -> Dict:
        """转换为Playwright格式"""
        server = f"{self.protocol}://{self.host}:{self.port}"
        proxy_dict = {"server": server}
        if self.username and self.password:
            proxy_dict["username"] = self.username
            proxy_dict["password"] = self.password
        return proxy_dict

    def to_curl_cffi_dict(self) -> Dict:
        """转换为curl_cffi格式"""
        url = self.to_url()
        return {"http": url, "https": url}


class ProxyManager:
    """
    代理管理器

    功能：
    - 代理池管理（增删改查）
    - 健康检查（自动剔除失效代理）
    - 负载均衡（轮询、随机、按成功率权重）
    - 失败重试（自动切换）
    """

    def __init__(self, config_dir: str = "config"):
        """
        初始化代理管理器

        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.proxies: List[Proxy] = []
        self.config = self._load_config()
        self.current_index = 0
        self.failure_threshold = 3  # 连续失败次数阈值

    def _load_config(self) -> Dict:
        """加载代理配置"""
        config_file = self.config_dir / "settings.json"
        if not config_file.exists():
            return {"proxy": {"enabled": False}}

        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def add_proxy(self, host: str, port: int, **kwargs) -> Proxy:
        """添加代理"""
        proxy = Proxy(host=host, port=port, **kwargs)
        self.proxies.append(proxy)
        logger.info(f"已添加代理: {host}:{port}")
        return proxy

    def add_proxies_from_list(self, proxy_list: List[Dict]) -> int:
        """
        批量添加代理

        Args:
            proxy_list: 代理字典列表，每个包含host, port等字段

        Returns:
            添加的数量
        """
        count = 0
        for item in proxy_list:
            try:
                self.add_proxy(**item)
                count += 1
            except Exception as e:
                logger.error(f"添加代理失败: {e}")
        return count

    def remove_proxy(self, proxy: Proxy) -> None:
        """移除代理"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            logger.info(f"已移除代理: {proxy.host}:{proxy.port}")

    def get_proxy(self, strategy: str = "round_robin") -> Optional[Proxy]:
        """
        获取一个代理

        Args:
            strategy: 选择策略
                - round_robin: 轮询
                - random: 随机
                - best: 成功率最高的

        Returns:
            代理对象，无可用代理返回None
        """
        healthy_proxies = [p for p in self.proxies if p.is_healthy]
        if not healthy_proxies:
            logger.warning("没有健康的代理可用")
            return None

        if strategy == "random":
            proxy = random.choice(healthy_proxies)
        elif strategy == "best":
            proxy = max(healthy_proxies, key=lambda p: (
                p.success_count / max(1, p.success_count + p.failure_count)
            ))
        else:  # round_robin
            if self.current_index >= len(healthy_proxies):
                self.current_index = 0
            proxy = healthy_proxies[self.current_index]
            self.current_index += 1

        proxy.last_used = time.time()
        return proxy

    def mark_success(self, proxy: Proxy, response_time: float = 0) -> None:
        """标记代理使用成功"""
        proxy.success_count += 1
        proxy.failure_count = 0
        proxy.is_healthy = True
        if response_time > 0:
            # 计算移动平均
            if proxy.avg_response_time == 0:
                proxy.avg_response_time = response_time
            else:
                proxy.avg_response_time = proxy.avg_response_time * 0.7 + response_time * 0.3

    def mark_failure(self, proxy: Proxy) -> None:
        """标记代理使用失败"""
        proxy.failure_count += 1
        if proxy.failure_count >= self.failure_threshold:
            proxy.is_healthy = False
            logger.warning(f"代理已标记为不健康: {proxy.host}:{proxy.port} (连续失败{proxy.failure_count}次)")

    async def health_check(self, proxy: Proxy, test_url: str = "https://httpbin.org/ip",
                          timeout: int = 10) -> bool:
        """
        检查代理健康状态

        Args:
            proxy: 代理对象
            test_url: 测试URL
            timeout: 超时时间

        Returns:
            是否健康
        """
        import aiohttp

        proxy_url = proxy.to_url()
        try:
            start = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(test_url, proxy=proxy_url, timeout=timeout) as response:
                    if response.status == 200:
                        elapsed = time.time() - start
                        self.mark_success(proxy, elapsed)
                        proxy.last_check = time.time()
                        return True
            self.mark_failure(proxy)
            return False
        except Exception as e:
            logger.debug(f"代理健康检查失败 {proxy.host}:{proxy.port}: {e}")
            self.mark_failure(proxy)
            return False

    async def check_all(self) -> Dict:
        """
        检查所有代理

        Returns:
            检查结果统计
        """
        import asyncio

        tasks = [self.health_check(p) for p in self.proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        healthy = sum(1 for r in results if r is True)
        return {
            "total": len(self.proxies),
            "healthy": healthy,
            "unhealthy": len(self.proxies) - healthy
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取代理池统计信息"""
        total = len(self.proxies)
        healthy = sum(1 for p in self.proxies if p.is_healthy)
        total_success = sum(p.success_count for p in self.proxies)
        total_failure = sum(p.failure_count for p in self.proxies)

        return {
            "total_proxies": total,
            "healthy_proxies": healthy,
            "unhealthy_proxies": total - healthy,
            "total_success": total_success,
            "total_failure": total_failure,
            "success_rate": total_success / max(1, total_success + total_failure)
        }

    def save_to_file(self, file_path: str) -> None:
        """保存代理池到文件"""
        data = {
            "proxies": [asdict(p) for p in self.proxies],
            "updated_at": datetime.now().isoformat()
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_file(self, file_path: str) -> int:
        """从文件加载代理池"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.proxies = []
        for p_data in data.get("proxies", []):
            self.proxies.append(Proxy(**p_data))

        return len(self.proxies)


class SimpleProxyRotator:
    """
    简单代理轮询器（无需异步）

    适合不需要健康检查的简单场景。
    """

    def __init__(self, proxies: List[str]):
        """
        Args:
            proxies: 代理URL列表，如 ['http://1.2.3.4:8080', ...]
        """
        self.proxies = proxies
        self.index = 0

    def get(self) -> Optional[str]:
        """获取下一个代理"""
        if not self.proxies:
            return None
        proxy = self.proxies[self.index % len(self.proxies)]
        self.index += 1
        return proxy


if __name__ == "__main__":
    # 测试
    pm = ProxyManager()
    pm.add_proxy("127.0.0.1", 8080, protocol="http")
    pm.add_proxy("127.0.0.1", 8081, protocol="socks5")

    print(f"代理总数: {len(pm.proxies)}")
    print(f"统计: {pm.get_statistics()}")

    for _ in range(3):
        proxy = pm.get_proxy("round_robin")
        if proxy:
            print(f"  选用: {proxy.host}:{proxy.port}")
