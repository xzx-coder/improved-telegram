"""
自动化特征隐藏模块

整合 playwright-stealth 和自研补丁，全面隐藏Playwright/Puppeteer/Selenium
等浏览器自动化框架的痕迹，避免被反爬系统通过CDP、WebDriver等特征识别。
"""

from typing import Optional, Dict, List, Any
from loguru import logger

try:
    from playwright_stealth import stealth_sync, stealth_async
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False
    logger.warning("playwright-stealth未安装，将仅使用自研补丁")


class StealthManager:
    """
    自动化特征隐藏管理器

    封装playwright-stealth的stealth_sync/stealth_async方法，
    并添加额外的自研补丁以应对更复杂的检测场景。
    """

    def __init__(self):
        """初始化隐藏管理器"""
        self.applied_patches = []

    @staticmethod
    def get_stealth_config() -> Dict[str, bool]:
        """
        获取playwright-stealth的配置项

        Returns:
            各项stealth功能的开关
        """
        return {
            "hide_webdriver": True,          # 隐藏navigator.webdriver
            "hide_cdc": True,                 # 隐藏CDC变量
            "chrome_app": True,               # 修复chrome.app对象
            "chrome_csi": True,               # 修复chrome.csi
            "chrome_load_times": True,        # 修复chrome.loadTimes
            "chrome_runtime": True,           # 修复chrome.runtime
            "hairline_fix": True,             # 修复hairline特性
            "iframe_content_window": True,    # 修复iframe contentWindow
            "media_codecs": True,             # 修复media codecs
            "navigator_hardware_concurrency": True,  # 修复硬件并发数
            "navigator_languages": True,      # 修复语言列表
            "navigator_permissions": True,    # 修复Permissions
            "navigator_platform": True,       # 修复平台
            "navigator_plugins": True,        # 修复插件
            "navigator_user_agent": True,     # 修复User-Agent
            "navigator_vendor": True,         # 修复vendor
            "sourceurl": True,                # 隐藏sourceURL
            "webgl_vendor": True,             # 修复WebGL vendor
            "webgl_renderer": True,           # 修复WebGL renderer
            "window_outerdimensions": True    # 修复窗口尺寸
        }

    def apply_stealth(self, page, mode: str = "sync") -> None:
        """
        应用playwright-stealth

        Args:
            page: Playwright page对象
            mode: 同步(async/sync)
        """
        if not HAS_STEALTH:
            logger.warning("playwright-stealth未安装，跳过stealth应用")
            return

        try:
            if mode == "sync":
                stealth_sync(page)
            else:
                stealth_async(page)
            self.applied_patches.append("playwright-stealth")
            logger.info("已应用 playwright-stealth")
        except Exception as e:
            logger.error(f"应用playwright-stealth失败: {e}")

    def apply_custom_patches(self, page) -> None:
        """
        应用自研的额外补丁

        Args:
            page: Playwright page对象
        """
        custom_script = """
        (function() {
            'use strict';

            // 1. 修复 Permissions.query 返回值
            if (navigator.permissions && navigator.permissions.query) {
                const originalQuery = navigator.permissions.query.bind(navigator.permissions);
                navigator.permissions.query = function(parameters) {
                    if (parameters && parameters.name === 'notifications') {
                        return Promise.resolve({ state: Notification.permission });
                    }
                    return originalQuery(parameters);
                };
            }

            // 2. 修复 PluginArray
            if (navigator.plugins && navigator.plugins.length === 0) {
                const fakePlugins = [
                    { name: 'PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                    { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }
                ];
                Object.defineProperty(navigator, 'plugins', {
                    get: () => fakePlugins,
                    configurable: true
                });
            }

            // 3. 修复 Function.prototype.toString (避免检测出native function被替换)
            const originalToString = Function.prototype.toString;
            const nativeFunctionString = originalToString.call(originalToString);
            Function.prototype.toString = function() {
                if (this === originalToString) return nativeFunctionString;
                if (this === Function.prototype.toString) return nativeFunctionString;
                return originalToString.call(this);
            };

            // 4. 修复 Error stack trace (避免暴露node/playwright)
            const originalPrepareStackTrace = Error.prepareStackTrace;
            if (originalPrepareStackTrace === undefined) {
                Error.prepareStackTrace = function(err, structuredStackTrace) {
                    return structuredStackTrace;
                };
            }

            // 5. 隐藏 Playwright 内部标识
            if (window.__pwInitScripts) {
                delete window.__pwInitScripts;
            }
            if (window.__playwright) {
                delete window.__playwright;
            }

            // 6. 修复 document.hasFocus (headless 默认返回false)
            if (!document.hasFocus) {
                document.hasFocus = function() { return true; };
            }

            // 7. 修复 iframe.contentWindow
            const originalContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
            if (originalContentWindow && originalContentWindow.get) {
                Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                    get: function() {
                        const win = originalContentWindow.get.call(this);
                        if (win) {
                            try {
                                Object.defineProperty(win, 'chrome', {
                                    get: () => window.chrome,
                                    configurable: true
                                });
                            } catch(e) {}
                        }
                        return win;
                    },
                    configurable: true
                });
            }

            // 8. 修复 Notification.permission 路径
            if (window.Notification) {
                try {
                    Object.defineProperty(Notification, 'permission', {
                        get: () => 'default',
                        configurable: true
                    });
                } catch(e) {}
            }

            // 9. 修复 console.log 不会暴露native code
            // 已通过第3项处理

            // 10. 修复 WebDriver 标记
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
                configurable: true
            });

            console.log('[Anti-Detection] 自研Stealth补丁已应用');
        })();
        """

        try:
            page.add_init_script(custom_script)
            self.applied_patches.append("custom_patches")
            logger.info("已应用自研Stealth补丁")
        except Exception as e:
            logger.error(f"应用自研补丁失败: {e}")

    def apply_all(self, page, mode: str = "sync") -> None:
        """
        应用所有stealth措施

        Args:
            page: Playwright page对象
            mode: 同步/异步模式
        """
        self.apply_stealth(page, mode)
        self.apply_custom_patches(page)

    def get_browser_args(self) -> List[str]:
        """
        获取浏览器启动参数，用于隐藏自动化痕迹

        Returns:
            Chrome启动参数列表
        """
        return [
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-web-security',
            '--disable-features=BlockInsecurePrivateNetworkRequests',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            '--disable-gpu',
            # 关键：禁用自动化控制特征
            '--disable-automation',
            '--disable-infobars',
            # 防止被识别为headless
            '--window-size=1920,1080',
            '--start-maximized',
        ]


def create_stealth_manager() -> StealthManager:
    """快捷函数：创建Stealth管理器"""
    return StealthManager()


if __name__ == "__main__":
    sm = StealthManager()
    print("Stealth配置项:", sm.get_stealth_config())
    print("浏览器启动参数:", sm.get_browser_args())
