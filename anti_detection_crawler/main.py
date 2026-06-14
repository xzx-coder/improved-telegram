#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于浏览器指纹伪装与行为模拟的爬虫反检测技术研究
主入口程序

使用方法:
    # 启动爬虫测试
    python main.py --mode test --url https://bot.sannysoft.com/

    # 批量爬取
    python main.py --mode batch --urls urls.txt

    # 启动Web可视化平台
    python main.py --mode web

    # 运行对比实验
    python main.py --mode comparison

    # 运行单元测试
    python main.py --mode unit-test
"""

import asyncio
import argparse
import sys
import json
from pathlib import Path
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO",
          format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")
logger.add("logs/main.log", rotation="10 MB", retention="7 days", level="DEBUG")


def cmd_test(args):
    """测试模式：访问单个URL并展示反检测效果"""
    from core.crawler import AntiDetectionCrawler

    async def run():
        crawler = AntiDetectionCrawler(
            headless=args.headless,
            use_proxy=args.proxy,
            use_fingerprint_spoof=not args.no_fingerprint,
            use_behavior_sim=not args.no_behavior
        )

        try:
            await crawler.start()
            result = await crawler.fetch(args.url, simulate_behavior=not args.no_behavior)

            print("\n" + "=" * 60)
            print("测试结果")
            print("=" * 60)
            print(f"URL: {result.url}")
            print(f"成功: {'✓' if result.success else '✗'}")
            print(f"状态码: {result.status_code}")
            print(f"标题: {result.title}")
            print(f"响应时间: {result.response_time:.2f}s")
            print(f"被检测: {'是' if result.detected else '否'}")

            if result.detection_signals:
                print(f"检测信号: {result.detection_signals}")

            if result.fingerprint:
                print(f"\n浏览器指纹:")
                fp = result.fingerprint
                print(f"  平台: {fp.get('platform')}")
                print(f"  语言: {fp.get('languages')}")
                print(f"  WebGL: {fp.get('webgl_renderer', 'N/A')[:80]}")
                print(f"  屏幕: {fp.get('screenWidth')}x{fp.get('screenHeight')}")
                print(f"  Canvas: {str(fp.get('canvas', ''))[:80]}...")

            print(f"\n总体统计: {crawler.get_stats()}")

        finally:
            await crawler.stop()

    asyncio.run(run())


def cmd_batch(args):
    """批量模式：爬取多个URL"""
    from core.crawler import AntiDetectionCrawler

    # 读取URL列表
    if args.urls:
        with open(args.urls, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
    else:
        urls = args.url_list

    if not urls:
        print("错误: 未提供URL列表")
        return

    async def run():
        crawler = AntiDetectionCrawler(
            headless=args.headless,
            use_proxy=args.proxy
        )

        try:
            await crawler.start()
            results = await crawler.fetch_batch(urls)

            # 统计
            print("\n" + "=" * 60)
            print("批量爬取结果")
            print("=" * 60)

            success_count = sum(1 for r in results if r.success)
            detected_count = sum(1 for r in results if r.detected)

            print(f"总数: {len(results)}")
            print(f"成功: {success_count}")
            print(f"被检测: {detected_count}")
            print(f"成功率: {success_count/len(results)*100:.1f}%")
            print(f"检测率: {detected_count/len(results)*100:.1f}%")

            print(f"\n详细结果:")
            for i, r in enumerate(results, 1):
                status = "✓" if r.success else "✗"
                detect = "🚨" if r.detected else "✓"
                print(f"  [{i:3d}] {status} {detect} {r.url} ({r.response_time:.2f}s)")

        finally:
            await crawler.stop()

    asyncio.run(run())


def cmd_web(args):
    """Web模式：启动可视化平台"""
    from web.app import create_app

    app = create_app()
    print("=" * 60)
    print("反检测爬虫可视化平台")
    print("=" * 60)
    print(f"访问地址: http://localhost:{args.port}")
    print(f"按 Ctrl+C 停止")
    print("=" * 60)

    app.run(host="0.0.0.0", port=args.port, debug=False)


def cmd_comparison(args):
    """对比实验模式"""
    from tests.comparison_test import run_comparison
    asyncio.run(run_comparison())


def cmd_unit_test(args):
    """单元测试模式"""
    import unittest
    from tests.test_modules import run_all_tests
    success = run_all_tests()
    sys.exit(0 if success else 1)


def main():
    parser = argparse.ArgumentParser(
        description="基于浏览器指纹伪装与行为模拟的爬虫反检测技术研究",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py --mode test --url https://bot.sannysoft.com/
  python main.py --mode batch --urls urls.txt
  python main.py --mode web --port 5000
  python main.py --mode comparison
        """
    )

    parser.add_argument("--mode", required=True,
                       choices=["test", "batch", "web", "comparison", "unit-test"],
                       help="运行模式")
    parser.add_argument("--url", help="目标URL（test模式）")
    parser.add_argument("--urls", help="URL列表文件（batch模式）")
    parser.add_argument("--url-list", nargs="+", help="URL列表（batch模式）")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--proxy", action="store_true", help="使用代理")
    parser.add_argument("--no-fingerprint", action="store_true", help="禁用指纹伪装")
    parser.add_argument("--no-behavior", action="store_true", help="禁用行为模拟")
    parser.add_argument("--port", type=int, default=5000, help="Web端口")

    args = parser.parse_args()

    # 检查参数
    if args.mode == "test" and not args.url:
        print("错误: test模式需要提供 --url")
        return 1

    # 分发命令
    commands = {
        "test": cmd_test,
        "batch": cmd_batch,
        "web": cmd_web,
        "comparison": cmd_comparison,
        "unit-test": cmd_unit_test,
    }

    try:
        commands[args.mode](args)
    except KeyboardInterrupt:
        print("\n用户中断")
        return 1
    except Exception as e:
        logger.error(f"运行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
