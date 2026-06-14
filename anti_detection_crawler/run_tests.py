"""
运行测试的入口脚本

使用方法：
    python run_tests.py
    python run_tests.py --module behavior
"""

import sys
import argparse
import unittest
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))


def main():
    parser = argparse.ArgumentParser(description="运行反检测爬虫测试")
    parser.add_argument("--module", help="指定测试模块 (tls, fingerprint, stealth, behavior, proxy, storage, all)")
    parser.add_argument("--comparison", action="store_true", help="运行对比实验")
    parser.add_argument("--unit", action="store_true", help="运行单元测试")
    args = parser.parse_args()

    if args.comparison:
        from tests.comparison_test import run_comparison
        import asyncio
        asyncio.run(run_comparison())
        return

    if args.unit or args.module is None:
        # 运行单元测试
        from tests.test_modules import run_all_tests
        success = run_all_tests()
        sys.exit(0 if success else 1)

    # 运行指定模块的测试
    module_map = {
        "tls": "TestTLSCamouflage",
        "fingerprint": "TestFingerprintManager",
        "stealth": "TestStealthManager",
        "behavior": "TestBehavior",
        "proxy": "TestProxyManager",
        "storage": "TestDataStore"
    }

    if args.module in module_map:
        suite = unittest.TestLoader().loadTestsFromName(
            f"tests.test_modules.{module_map[args.module]}"
        )
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        sys.exit(0 if result.wasSuccessful() else 1)
    else:
        print(f"未知模块: {args.module}")
        print(f"可用模块: {list(module_map.keys())}")


if __name__ == "__main__":
    main()
