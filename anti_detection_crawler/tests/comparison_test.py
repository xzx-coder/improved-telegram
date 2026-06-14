"""
对比实验脚本

对比三种爬虫方案的反检测效果：
1. 裸 requests (无任何反检测)
2. 基础 Playwright (无反检测)
3. 完整反检测 (指纹伪装 + 行为模拟 + Stealth)
"""

import asyncio
import time
import json
import random
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

from core.crawler import AntiDetectionCrawler
from core.storage import DataStore


TEST_URLS = [
    "https://bot.sannysoft.com/",
    "https://browserleaks.com/javascript",
    "https://httpbin.org/user-agent",
    "https://httpbin.org/headers",
    "https://www.example.com/",
]


async def test_bare_requests(url: str) -> Dict[str, Any]:
    """
    测试1: 裸 requests

    无任何伪装，直接发送HTTP请求
    """
    if not HAS_REQUESTS:
        return {"strategy": "裸requests", "url": url, "success": False, "error": "requests未安装"}

    start = time.time()
    result = {
        "strategy": "裸requests",
        "url": url,
        "timestamp": datetime.now().isoformat()
    }

    try:
        response = requests.get(url, timeout=15, headers={
            "User-Agent": "python-requests/2.31.0"  # 暴露爬虫特征
        })
        result["status_code"] = response.status_code
        result["success"] = True
        result["response_time"] = time.time() - start
        result["content_length"] = len(response.text)

        # 简单的反爬检测
        signals = []
        if response.status_code in [403, 503, 429]:
            signals.append(f"http_status_{response.status_code}")

        # 检查 User-Agent 是否被服务器识别
        if "python-requests" in response.request.headers.get("User-Agent", ""):
            signals.append("user_agent_exposed")

        result["detected"] = len(signals) > 0
        result["detection_signals"] = signals

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        result["response_time"] = time.time() - start

    return result


async def test_basic_playwright(url: str) -> Dict[str, Any]:
    """
    测试2: 基础 Playwright

    使用Playwright但无任何反检测措施
    """
    if not HAS_PLAYWRIGHT:
        return {"strategy": "基础Playwright", "url": url, "success": False, "error": "Playwright未安装"}

    start = time.time()
    result = {
        "strategy": "基础Playwright",
        "url": url,
        "timestamp": datetime.now().isoformat()
    }

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()

            response = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            result["status_code"] = response.status if response else 0
            result["title"] = await page.title()
            result["content_length"] = len(await page.content())

            # 反爬检测
            is_webdriver = await page.evaluate("() => navigator.webdriver")
            has_chrome = await page.evaluate("() => !!window.chrome")
            plugin_count = await page.evaluate("() => navigator.plugins.length")

            signals = []
            if is_webdriver:
                signals.append("webdriver_true")
            if not has_chrome:
                signals.append("no_chrome")
            if plugin_count == 0:
                signals.append("no_plugins")

            # 检查WebGL
            webgl = await page.evaluate("""() => {
                try {
                    const canvas = document.createElement('canvas');
                    const gl = canvas.getContext('webgl');
                    if (!gl) return null;
                    const ext = gl.getExtension('WEBGL_debug_renderer_info');
                    if (!ext) return null;
                    return gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
                } catch(e) { return 'error'; }
            }""")

            if webgl and "swiftshader" in str(webgl).lower():
                signals.append(f"swiftshader_webgl")

            result["detected"] = len(signals) > 0
            result["detection_signals"] = signals
            result["webgl_renderer"] = webgl
            result["success"] = True
            result["response_time"] = time.time() - start

            await browser.close()

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        result["response_time"] = time.time() - start

    return result


async def test_full_stealth(crawler: AntiDetectionCrawler, url: str) -> Dict[str, Any]:
    """
    测试3: 完整反检测

    使用完整的AntiDetectionCrawler
    """
    result = await crawler.fetch(url, simulate_behavior=True, detect=True)
    result_dict = result.to_dict()
    result_dict["strategy"] = "完整反检测"
    return result_dict


async def run_comparison(test_urls: List[str] = None):
    """运行对比实验"""
    if test_urls is None:
        test_urls = TEST_URLS

    print("=" * 70)
    print("反检测爬虫对比实验")
    print("=" * 70)
    print(f"测试URL数量: {len(test_urls)}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    storage = DataStore()
    all_results = []

    # 测试1: 裸requests
    print("=" * 70)
    print("[1/3] 测试裸requests（无任何伪装）")
    print("=" * 70)
    for url in test_urls:
        print(f"\n测试: {url}")
        result = await test_bare_requests(url)
        print(f"  状态: {result.get('status_code')}, "
              f"成功: {result.get('success')}, "
              f"耗时: {result.get('response_time', 0):.2f}s, "
              f"检测: {result.get('detected')}")
        if result.get('detection_signals'):
            print(f"  检测信号: {result['detection_signals']}")
        all_results.append(result)
        storage.save_crawl_result(result)

    # 测试2: 基础Playwright
    print("\n" + "=" * 70)
    print("[2/3] 测试基础Playwright（无反检测）")
    print("=" * 70)
    for url in test_urls:
        print(f"\n测试: {url}")
        result = await test_basic_playwright(url)
        print(f"  状态: {result.get('status_code')}, "
              f"成功: {result.get('success')}, "
              f"耗时: {result.get('response_time', 0):.2f}s, "
              f"检测: {result.get('detected')}")
        if result.get('detection_signals'):
            print(f"  检测信号: {result['detection_signals']}")
        if result.get('webgl_renderer'):
            print(f"  WebGL: {result['webgl_renderer']}")
        all_results.append(result)
        storage.save_crawl_result(result)

    # 测试3: 完整反检测
    print("\n" + "=" * 70)
    print("[3/3] 测试完整反检测（指纹伪装+行为模拟+Stealth）")
    print("=" * 70)
    crawler = AntiDetectionCrawler(
        headless=False,  # 显示窗口方便观察
        use_proxy=False,
        use_fingerprint_spoof=True,
        use_behavior_sim=True
    )

    try:
        await crawler.start()

        for url in test_urls:
            print(f"\n测试: {url}")
            result = await test_full_stealth(crawler, url)
            print(f"  状态: {result.get('status_code')}, "
                  f"成功: {result.get('success')}, "
                  f"耗时: {result.get('response_time', 0):.2f}s, "
                  f"检测: {result.get('detected')}")
            if result.get('detection_signals'):
                print(f"  检测信号: {result['detection_signals']}")
            if result.get('fingerprint'):
                fp = result['fingerprint']
                print(f"  WebGL: {fp.get('webgl_renderer', 'N/A')}")
                print(f"  Canvas: {fp.get('canvas', 'N/A')[:50]}...")
                print(f"  平台: {fp.get('platform')}")
            all_results.append(result)
            storage.save_crawl_result(result)

    finally:
        await crawler.stop()

    # 汇总统计
    print("\n" + "=" * 70)
    print("对比实验结果汇总")
    print("=" * 70)

    strategies = {}
    for r in all_results:
        strategy = r.get("strategy", "unknown")
        if strategy not in strategies:
            strategies[strategy] = {"total": 0, "success": 0, "detected": 0, "response_time_sum": 0}

        strategies[strategy]["total"] += 1
        if r.get("success"):
            strategies[strategy]["success"] += 1
        if r.get("detected"):
            strategies[strategy]["detected"] += 1
        strategies[strategy]["response_time_sum"] += r.get("response_time", 0)

    print(f"\n{'策略':<20} {'总数':<8} {'成功':<8} {'成功率':<10} {'被检测':<10} {'检测率':<10} {'平均耗时':<10}")
    print("-" * 80)
    for strategy, data in strategies.items():
        success_rate = data["success"] / max(1, data["total"]) * 100
        detection_rate = data["detected"] / max(1, data["total"]) * 100
        avg_time = data["response_time_sum"] / max(1, data["total"])
        print(f"{strategy:<20} {data['total']:<8} {data['success']:<8} "
              f"{success_rate:<10.1f} {data['detected']:<10} {detection_rate:<10.1f} {avg_time:<10.2f}")

    # 保存汇总
    summary = {
        "test_time": datetime.now().isoformat(),
        "test_urls": test_urls,
        "strategies": strategies,
        "all_results": all_results
    }

    summary_path = Path("data/comparison_results.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n详细结果已保存到: {summary_path}")
    return summary


if __name__ == "__main__":
    asyncio.run(run_comparison())
