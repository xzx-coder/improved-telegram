"""
TLS指纹伪装模块

使用 curl_cffi 库实现JA3 TLS指纹伪装，模拟主流浏览器的TLS握手特征。
通过这种方式，可以让纯HTTP请求看起来像真实浏览器发出的请求。
"""

import json
import random
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False
    logger.warning("curl_cffi未安装，将使用标准requests")


class TLSCamouflage:
    """
    TLS指纹伪装器

    支持模拟不同浏览器的TLS握手特征，绕过基于JA3/JA4指纹的反爬检测。
    """

    def __init__(self, profile_dir: str = "config"):
        """
        初始化TLS伪装器

        Args:
            profile_dir: TLS配置文件目录
        """
        self.profile_dir = Path(profile_dir)
        self.profiles = self._load_profiles()
        self.current_profile = self.profiles.get("default", "chrome_120")

    def _load_profiles(self) -> Dict[str, Any]:
        """加载TLS配置文件"""
        profile_file = self.profile_dir / "tls_profiles.json"
        if not profile_file.exists():
            logger.warning(f"TLS配置文件不存在: {profile_file}")
            return {"default": "chrome_120", "profiles": {}}

        with open(profile_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_profile(self, name: str = None) -> Dict[str, Any]:
        """
        获取TLS配置

        Args:
            name: 浏览器配置名称 (chrome_120, chrome_119, firefox_121)

        Returns:
            浏览器配置字典
        """
        if name is None:
            name = self.current_profile

        profile = self.profiles.get("profiles", {}).get(name)
        if profile is None:
            logger.warning(f"配置 {name} 不存在，使用默认配置")
            profile = self.profiles.get("profiles", {}).get(self.profiles.get("default"))

        return profile

    def get_impersonate_target(self, name: str = None) -> str:
        """
        获取curl_cffi的impersonate目标

        curl_cffi支持的版本: chrome99, chrome100, chrome101 ... chrome120, firefox109等

        Args:
            name: 浏览器配置名称

        Returns:
            impersonate目标字符串
        """
        if name is None:
            name = self.current_profile

        # 从配置名提取版本号
        if "chrome_120" in name:
            return "chrome120"
        elif "chrome_119" in name:
            return "chrome119"
        elif "chrome_110" in name:
            return "chrome110"
        elif "firefox_121" in name:
            return "firefox121"
        elif "firefox_120" in name:
            return "firefox120"
        elif "safari" in name:
            return "safari17_0"
        else:
            return "chrome120"

    def create_session(self, profile_name: str = None,
                      proxy: Optional[Dict] = None,
                      timeout: int = 30) -> Any:
        """
        创建带TLS指纹伪装的HTTP会话

        Args:
            profile_name: 浏览器配置名称
            proxy: 代理配置
            timeout: 超时时间

        Returns:
            HTTP会话对象
        """
        if not HAS_CURL_CFFI:
            logger.error("curl_cffi未安装，无法创建TLS伪装会话")
            return None

        profile = self.get_profile(profile_name)
        impersonate = self.get_impersonate_target(profile_name)

        logger.info(f"创建TLS伪装会话: {profile.get('name', profile_name)} -> {impersonate}")

        try:
            session = cffi_requests.Session(
                impersonate=impersonate,
                timeout=timeout,
                proxies=proxy
            )
            # 设置通用请求头
            session.headers.update({
                "User-Agent": profile.get("user_agent", ""),
                "Accept": profile.get("accept", "*/*"),
                "Accept-Language": profile.get("accept_language", "zh-CN,zh;q=0.9,en;q=0.8"),
                "Accept-Encoding": profile.get("accept_encoding", "gzip, deflate, br")
            })
            return session
        except Exception as e:
            logger.error(f"创建TLS会话失败: {e}")
            return None

    def fetch(self, url: str, profile_name: str = None,
              proxy: Optional[Dict] = None, **kwargs) -> Optional[Any]:
        """
        使用TLS伪装发起请求

        Args:
            url: 目标URL
            profile_name: 浏览器配置
            proxy: 代理配置
            **kwargs: 其他请求参数

        Returns:
            Response对象或None
        """
        session = self.create_session(profile_name, proxy)
        if session is None:
            return None

        try:
            response = session.get(url, **kwargs)
            logger.debug(f"TLS伪装请求: {url} -> {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"请求失败 {url}: {e}")
            return None

    def test_ja3(self, url: str = "https://ja3er.com/json") -> Optional[Dict]:
        """
        测试JA3指纹

        Args:
            url: JA3测试URL

        Returns:
            JA3指纹信息
        """
        logger.info("正在测试JA3指纹...")
        response = self.fetch(url, timeout=15)
        if response is None:
            return None

        try:
            data = response.json()
            logger.info(f"JA3指纹信息: {data}")
            return data
        except Exception as e:
            logger.error(f"解析JA3响应失败: {e}")
            return None

    def compare_fingerprints(self, urls: Optional[list] = None) -> Dict[str, Any]:
        """
        对比不同配置的TLS指纹

        Args:
            urls: 测试URL列表

        Returns:
            对比结果
        """
        if urls is None:
            urls = ["https://tls.peet.ws/api/all"]

        results = {}
        for profile_name in self.profiles.get("profiles", {}).keys():
            logger.info(f"测试配置: {profile_name}")
            for url in urls:
                response = self.fetch(url, profile_name=profile_name, timeout=15)
                if response:
                    try:
                        data = response.json()
                        results[profile_name] = data
                        logger.info(f"{profile_name} 指纹获取成功")
                    except Exception:
                        results[profile_name] = {"raw": response.text[:500]}
                break  # 每个配置只测试一个URL

        return results


def get_tls_session(profile: str = "chrome_120", proxy: Optional[Dict] = None) -> Any:
    """
    快捷函数：获取TLS伪装会话

    Args:
        profile: 浏览器配置
        proxy: 代理配置

    Returns:
        HTTP会话
    """
    camo = TLSCamouflage()
    return camo.create_session(profile, proxy)


if __name__ == "__main__":
    # 简单测试
    camo = TLSCamouflage()
    print("已加载TLS配置文件:", list(camo.profiles.get("profiles", {}).keys()))
    print("默认配置:", camo.current_profile)
    print("可用impersonate目标:", camo.get_impersonate_target())
