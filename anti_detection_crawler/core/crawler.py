"""
反检测爬虫主类

整合TLS指纹伪装、浏览器指纹伪造、自动化特征隐藏、人类行为模拟、
代理管理、数据存储等所有模块，提供一个统一的爬虫接口。
"""

import asyncio
import time
import json
import random
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.error("Playwright未安装，请运行: pip install playwright && playwright install chromium")

from .tls_camouflage import TLSCamouflage
from .fingerprint import FingerprintManager
from .stealth import StealthManager
from .behavior import HumanBehavior
from .proxy_manager import ProxyManager
from .storage import DataStore


@dataclass
class CrawlResult:
    """爬取结果"""
    url: str
    success: bool
    status_code: int = 0
    response_time: float = 0.0
    title: str = ""
    content_length: int = 0
    detected: bool = False
    detection_signals: List[str] = None
    error: str = ""
    timestamp: str = ""
    strategy: str = "完整反检测"
    proxy_used: str = ""
    fingerprint: Dict = None

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "url": self.url,
            "success": self.success,
            "status_code": self.status_code,
            "response_time": self.response_time,
            "title": self.title,
            "content_length": self.content_length,
            "detected": self.detected,
            "detection_signals": self.detection_signals or [],
            "error": self.error,
            "timestamp": self.timestamp,
            "strategy": self.strategy,
            "proxy_used": self.proxy_used,
            "fingerprint": self.fingerprint or {}
        }


class AntiDetectionCrawler:
    """
    反检测爬虫

    整合所有反检测技术的爬虫主类。
    """

    def __init__(self,
                 config_dir: str = "config",
                 data_dir: str = "data",
                 log_dir: str = "logs",
                 headless: bool = False,
                 use_proxy: bool = False,
                 use_tls_camo: bool = True,
                 use_fingerprint_spoof: bool = True,
                 use_behavior_sim: bool = True):
        """
        初始化反检测爬虫

        Args:
            config_dir: 配置目录
            data_dir: 数据目录
            log_dir: 日志目录
            headless: 是否无头模式
            use_proxy: 是否使用代理
            use_tls_camo: 是否使用TLS伪装
            use_fingerprint_spoof: 是否使用指纹伪装
            use_behavior_sim: 是否使用行为模拟
        """
        if not HAS_PLAYWRIGHT:
            raise ImportError("请先安装Playwright: pip install playwright && playwright install chromium")

        self.config_dir = Path(config_dir)
        self.data_dir = Path(data_dir)
        self.log_dir = Path(log_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)

        # 配置
        self.headless = headless
        self.use_proxy = use_proxy
        self.use_tls_camo = use_tls_camo
        self.use_fingerprint_spoof = use_fingerprint_spoof
        self.use_behavior_sim = use_behavior_sim

        # 初始化子模块
        self.tls_camo = TLSCamouflage(str(self.config_dir))
        self.fingerprint_mgr = FingerprintManager(
            script_dir=str(Path("scripts")),
            config_dir=str(self.config_dir)
        )
        self.stealth_mgr = StealthManager()
        self.behavior = HumanBehavior()
        self.proxy_mgr = ProxyManager(str(self.config_dir))
        self.storage = DataStore(str(self.config_dir), str(self.data_dir))

        # Playwright
        self.playwright = None
        self.browser: Optional[Browser] = None

        # 统计
        self.stats = {
            "total_crawls": 0,
            "successful_crawls": 0,
            "failed_crawls": 0,
            "detected_crawls": 0
        }

        # 配置日志
        self._setup_logging()

    def _setup_logging(self) -> None:
        """配置日志"""
        log_file = self.log_dir / f"crawler_{datetime.now().strftime('%Y%m%d')}.log"
        logger.add(
            str(log_file),
            rotation="10 MB",
            retention="7 days",
            level="INFO",
            encoding="utf-8"
        )

    async def start(self) -> None:
        """启动爬虫"""
        logger.info("正在启动反检测爬虫...")

        self.playwright = await async_playwright().start()

        # 启动浏览器
        browser_args = self.stealth_mgr.get_browser_args()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=browser_args
        )

        logger.info("反检测爬虫已启动")

    async def stop(self) -> None:
        """停止爬虫"""
        logger.info("正在停止爬虫...")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.storage.close()
        logger.info("爬虫已停止")

    async def create_context(self, profile_name: str = "chrome_120",
                            proxy: Optional[Dict] = None) -> BrowserContext:
        """
        创建浏览器上下文

        Args:
            profile_name: 浏览器配置名
            proxy: 代理配置

        Returns:
            浏览器上下文
        """
        profile = self.tls_camo.get_profile(profile_name)

        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": profile.get("user_agent", ""),
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "permissions": ["geolocation", "notifications"],
            "geolocation": {"latitude": 39.9042, "longitude": 116.4074},  # 北京
            "color_scheme": "light",
            "device_scale_factor": 1,
            "is_mobile": False,
            "has_touch": False,
            "ignore_https_errors": True
        }

        if proxy:
            context_options["proxy"] = proxy

        context = await self.browser.new_context(**context_options)

        # 注入指纹伪装脚本
        if self.use_fingerprint_spoof:
            for script in self.fingerprint_mgr.get_init_scripts():
                await context.add_init_script(script)

        return context

    async def detect_anti_bot(self, page: Page) -> tuple:
        """
        检测页面是否触发了反爬机制

        Returns:
            (is_detected, signals)
        """
        signals = []
        try:
            # 检查页面标题
            title = await page.title()
            if any(kw in title.lower() for kw in ["blocked", "captcha", "robot", "verify", "cloudflare", "access denied"]):
                signals.append(f"suspicious_title: {title}")

            # 检查页面内容
            content = await page.content()
            if any(kw in content.lower() for kw in ["are you a robot", "captcha", "challenge-form", "cf-chl-bypass"]):
                signals.append("captcha_or_challenge")

            # 检查 webdriver
            is_webdriver = await page.evaluate("() => navigator.webdriver")
            if is_webdriver:
                signals.append("webdriver_detected")

            # 检查 headless 特征
            headless_check = await page.evaluate("""() => ({
                hasChrome: !!window.chrome,
                hasPlugins: navigator.plugins.length > 0,
                hasLanguages: navigator.languages.length > 0,
                webglRenderer: (() => {
                    try {
                        const canvas = document.createElement('canvas');
                        const gl = canvas.getContext('webgl');
                        if (!gl) return null;
                        const ext = gl.getExtension('WEBGL_debug_renderer_info');
                        return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : null;
                    } catch(e) { return null; }
                })()
            })""")

            if not headless_check.get("hasChrome"):
                signals.append("no_chrome_object")
            if not headless_check.get("hasPlugins"):
                signals.append("no_plugins")
            if not headless_check.get("webglRenderer") or "swiftshader" in str(headless_check.get("webglRenderer", "")).lower():
                signals.append(f"webgl_suspicious: {headless_check.get('webglRenderer')}")

            # 检查是否被重定向
            current_url = page.url
            if "captcha" in current_url or "challenge" in current_url:
                signals.append(f"redirected: {current_url}")

        except Exception as e:
            logger.warning(f"反爬检测异常: {e}")

        return (len(signals) > 0, signals)

    async def fetch(self, url: str, profile_name: str = "chrome_120",
                   simulate_behavior: bool = True,
                   detect: bool = True) -> CrawlResult:
        """
        抓取单个URL

        Args:
            url: 目标URL
            profile_name: 浏览器配置
            simulate_behavior: 是否模拟人类行为
            detect: 是否进行反爬检测

        Returns:
            爬取结果
        """
        start_time = time.time()
        result = CrawlResult(
            url=url,
            success=False,
            timestamp=datetime.now().isoformat(),
            strategy="完整反检测"
        )

        # 选择代理
        proxy = None
        if self.use_proxy:
            proxy_obj = self.proxy_mgr.get_proxy()
            if proxy_obj:
                proxy = proxy_obj.to_playwright_dict()
                result.proxy_used = f"{proxy_obj.host}:{proxy_obj.port}"

        context = None
        try:
            # 创建上下文
            context = await self.create_context(profile_name, proxy)
            page = await context.new_page()

            # 应用stealth
            self.stealth_mgr.apply_stealth(page, mode="async")

            # 设置页面对象到行为模拟器
            self.behavior.set_page(page)

            # 访问URL
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            result.status_code = response.status if response else 0

            # 模拟人类行为
            if simulate_behavior and self.use_behavior_sim:
                await self.behavior.simulate_page_stay(2, 5)
                if random.random() < 0.5:
                    await self.behavior.simulate_scroll("down", random.randint(200, 500))
            else:
                await page.wait_for_timeout(1000)

            # 提取页面信息
            result.title = await page.title()
            html = await page.content()
            result.content_length = len(html)

            # 提取指纹
            if self.use_fingerprint_spoof:
                result.fingerprint = self.fingerprint_mgr.extract_fingerprint(page)

            # 反爬检测
            if detect:
                is_detected, signals = await self.detect_anti_bot(page)
                result.detected = is_detected
                result.detection_signals = signals

            result.success = True

            # 更新统计
            self.stats["total_crawls"] += 1
            if result.detected:
                self.stats["detected_crawls"] += 1
            self.stats["successful_crawls"] += 1

            if proxy:
                self.proxy_mgr.mark_success(proxy_obj if proxy_obj else None, time.time() - start_time)

        except Exception as e:
            result.success = False
            result.error = str(e)
            self.stats["total_crawls"] += 1
            self.stats["failed_crawls"] += 1
            if proxy:
                self.proxy_mgr.mark_failure(proxy_obj if proxy_obj else None)
            logger.error(f"抓取失败 {url}: {e}")

        finally:
            if context:
                await context.close()

        result.response_time = time.time() - start_time

        # 保存结果
        self.storage.save_crawl_result(result.to_dict())

        return result

    async def fetch_batch(self, urls: List[str], **kwargs) -> List[CrawlResult]:
        """
        批量抓取

        Args:
            urls: URL列表
            **kwargs: 传递给fetch的参数

        Returns:
            爬取结果列表
        """
        results = []
        for i, url in enumerate(urls):
            logger.info(f"正在抓取 [{i+1}/{len(urls)}]: {url}")
            result = await self.fetch(url, **kwargs)
            results.append(result)

            # 间隔避免频率过高
            if i < len(urls) - 1:
                delay = random.uniform(2, 5)
                await asyncio.sleep(delay)

        return results

    async def test_stealth(self, test_url: str = "https://bot.sannysoft.com/") -> CrawlResult:
        """
        测试反检测效果

        Args:
            test_url: 测试URL

        Returns:
            测试结果
        """
        logger.info(f"正在测试反检测效果: {test_url}")
        return await self.fetch(test_url, simulate_behavior=True, detect=True)

    def get_stats(self) -> Dict[str, Any]:
        """获取爬虫统计信息"""
        return {
            **self.stats,
            "success_rate": self.stats["successful_crawls"] / max(1, self.stats["total_crawls"]),
            "detection_rate": self.stats["detected_crawls"] / max(1, self.stats["total_crawls"])
        }


async def main():
    """示例用法"""
    crawler = AntiDetectionCrawler(
        headless=False,
        use_proxy=False,
        use_fingerprint_spoof=True,
        use_behavior_sim=True
    )

    try:
        await crawler.start()

        # 测试反检测效果
        result = await crawler.test_stealth()
        print(f"\n测试结果:")
        print(f"  成功: {result.success}")
        print(f"  状态码: {result.status_code}")
        print(f"  标题: {result.title}")
        print(f"  是否被检测: {result.detected}")
        print(f"  检测信号: {result.detection_signals}")
        print(f"  响应时间: {result.response_time:.2f}s")
        print(f"  指纹信息: {result.fingerprint}")

        print(f"\n总体统计: {crawler.get_stats()}")

    finally:
        await crawler.stop()


if __name__ == "__main__":
    asyncio.run(main())
