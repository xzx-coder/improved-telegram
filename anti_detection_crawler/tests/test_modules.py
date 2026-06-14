"""
测试脚本：对各个模块进行独立测试

使用pytest或unittest运行：
    python -m pytest tests/test_modules.py -v
    python tests/test_modules.py
"""

import asyncio
import json
import sys
import unittest
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tls_camouflage import TLSCamouflage
from core.fingerprint import FingerprintManager
from core.stealth import StealthManager
from core.behavior import BezierCurve, HumanBehavior
from core.proxy_manager import ProxyManager, SimpleProxyRotator
from core.storage import DataStore


class TestTLSCamouflage(unittest.TestCase):
    """TLS伪装模块测试"""

    def setUp(self):
        self.tls = TLSCamouflage()

    def test_load_profiles(self):
        """测试加载配置文件"""
        profiles = self.tls.profiles
        self.assertIn("profiles", profiles)
        self.assertGreater(len(profiles["profiles"]), 0)
        print(f"  [OK] 加载了 {len(profiles['profiles'])} 个TLS配置")

    def test_get_profile(self):
        """测试获取配置"""
        profile = self.tls.get_profile("chrome_120")
        self.assertIsNotNone(profile)
        self.assertIn("user_agent", profile)
        print(f"  [OK] Chrome 120 配置: {profile.get('name')}")

    def test_impersonate_target(self):
        """测试impersonate目标"""
        target = self.tls.get_impersonate_target("chrome_120")
        self.assertIn("chrome", target)
        print(f"  [OK] Chrome 120 impersonate target: {target}")


class TestFingerprintManager(unittest.TestCase):
    """指纹管理模块测试"""

    def setUp(self):
        self.mgr = FingerprintManager()

    def test_load_scripts(self):
        """测试加载JS脚本"""
        scripts = self.mgr.scripts
        self.assertGreater(len(scripts), 0)
        print(f"  [OK] 加载了 {len(scripts)} 个JS脚本")
        for name in scripts.keys():
            self.assertGreater(len(scripts[name]), 0)
            print(f"    - {name}: {len(scripts[name])} 字符")

    def test_combine_scripts(self):
        """测试脚本合并"""
        combined = self.mgr.get_all_scripts()
        self.assertIn("Canvas", combined)  # canvas.js应包含Canvas
        self.assertIn("WebGL", combined)  # webgl.js应包含WebGL
        print(f"  [OK] 合并脚本长度: {len(combined)} 字符")


class TestStealthManager(unittest.TestCase):
    """Stealth模块测试"""

    def setUp(self):
        self.mgr = StealthManager()

    def test_browser_args(self):
        """测试浏览器启动参数"""
        args = self.mgr.get_browser_args()
        self.assertIn("--disable-blink-features=AutomationControlled", args)
        print(f"  [OK] 浏览器参数数量: {len(args)}")

    def test_stealth_config(self):
        """测试stealth配置"""
        config = self.mgr.get_stealth_config()
        self.assertTrue(config["hide_webdriver"])
        self.assertTrue(config["navigator_plugins"])
        print(f"  [OK] Stealth配置项: {len(config)} 项")


class TestBehavior(unittest.TestCase):
    """行为模拟模块测试"""

    def setUp(self):
        self.bezier = BezierCurve()

    def test_bezier_path(self):
        """测试贝塞尔曲线生成"""
        path = self.bezier.generate_natural_path((0, 0), (100, 100))
        self.assertGreater(len(path), 0)
        # 起点应接近原点（允许±2的随机抖动）
        start_x, start_y = path[0]
        self.assertAlmostEqual(start_x, 0, delta=3)
        self.assertAlmostEqual(start_y, 0, delta=3)
        # 终点应接近目标
        end_x, end_y = path[-1]
        self.assertAlmostEqual(end_x, 100, delta=10)
        self.assertAlmostEqual(end_y, 100, delta=10)
        print(f"  [OK] 贝塞尔曲线生成了 {len(path)} 个点")

    def test_long_path(self):
        """测试长距离路径"""
        path = self.bezier.generate_natural_path((100, 100), (800, 600))
        self.assertGreater(len(path), 30)
        print(f"  [OK] 长路径生成了 {len(path)} 个点")

    def test_timestamps(self):
        """测试时间戳生成"""
        ts = self.bezier.generate_timestamps(30)
        self.assertEqual(len(ts), 30)
        self.assertGreater(sum(ts), 0)
        print(f"  [OK] 时间戳生成: {len(ts)} 个, 总时长 {sum(ts):.2f}s")


class TestProxyManager(unittest.TestCase):
    """代理管理模块测试"""

    def setUp(self):
        self.mgr = ProxyManager()

    def test_add_proxy(self):
        """测试添加代理"""
        proxy = self.mgr.add_proxy("127.0.0.1", 8080)
        self.assertEqual(proxy.host, "127.0.0.1")
        self.assertEqual(proxy.port, 8080)
        print(f"  [OK] 代理已添加: {proxy.host}:{proxy.port}")

    def test_get_proxy(self):
        """测试获取代理"""
        self.mgr.add_proxy("127.0.0.1", 8080)
        self.mgr.add_proxy("127.0.0.1", 8081)
        proxy = self.mgr.get_proxy("round_robin")
        self.assertIsNotNone(proxy)
        print(f"  [OK] 轮询获取: {proxy.host}:{proxy.port}")

    def test_statistics(self):
        """测试统计信息"""
        self.mgr.add_proxy("127.0.0.1", 8080)
        self.mgr.add_proxy("127.0.0.1", 8081)
        stats = self.mgr.get_statistics()
        self.assertEqual(stats["total_proxies"], 2)
        self.assertEqual(stats["healthy_proxies"], 2)
        print(f"  [OK] 统计: {stats}")


class TestDataStore(unittest.TestCase):
    """数据存储模块测试"""

    def setUp(self):
        self.store = DataStore()

    def test_save_crawl_result(self):
        """测试保存爬取结果"""
        result = self.store.save_crawl_result({
            "url": "https://test.com",
            "success": True,
            "response_time": 1.5
        })
        self.assertTrue(result)
        print(f"  [OK] 爬取结果已保存")

    def test_save_fingerprint(self):
        """测试保存指纹"""
        result = self.store.save_fingerprint({
            "canvas_hash": "abc123",
            "webgl_renderer": "NVIDIA"
        })
        self.assertTrue(result)
        print(f"  [OK] 指纹已保存")

    def test_statistics(self):
        """测试统计"""
        stats = self.store.get_statistics()
        self.assertIn("total_crawls", stats)
        print(f"  [OK] 统计信息: {stats}")


class TestIntegration(unittest.TestCase):
    """集成测试：完整爬虫流程"""

    def test_module_compatibility(self):
        """测试模块间的兼容性"""
        # 验证所有模块能正常导入和初始化
        tls = TLSCamouflage()
        fp = FingerprintManager()
        stealth = StealthManager()
        proxy = ProxyManager()
        store = DataStore()

        self.assertIsNotNone(tls.profiles)
        self.assertGreater(len(fp.scripts), 0)
        self.assertGreater(len(stealth.get_browser_args()), 0)
        self.assertIsNotNone(store.data_dir)
        print(f"  [OK] 所有模块初始化成功")


def run_all_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 60)
    print("反检测爬虫系统 - 模块单元测试")
    print("=" * 60)
    print()

    success = run_all_tests()

    print()
    print("=" * 60)
    if success:
        print("[OK] 所有测试通过！")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)

    sys.exit(0 if success else 1)
