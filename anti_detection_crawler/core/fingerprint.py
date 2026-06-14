"""
浏览器指纹伪造管理模块

负责加载和注入所有JS脚本到Playwright页面中，实现对Canvas、WebGL、
AudioContext、Navigator等浏览器指纹的全面伪装。
"""

import json
import random
from pathlib import Path
from typing import Optional, Dict, List, Any
from loguru import logger


class FingerprintManager:
    """
    浏览器指纹管理器

    加载脚本目录下的所有JS注入脚本，组合后注入到浏览器上下文中。
    支持Canvas、WebGL、Audio、Navigator、Screen、WebRTC、Timezone
    等多种指纹维度的伪装。
    """

    def __init__(self, script_dir: str = "scripts", config_dir: str = "config"):
        """
        初始化指纹管理器

        Args:
            script_dir: JS脚本目录
            config_dir: 配置文件目录
        """
        self.script_dir = Path(script_dir)
        self.config_dir = Path(config_dir)
        self.config = self._load_config()
        self.scripts = self._load_scripts()

    def _load_config(self) -> Dict[str, Any]:
        """加载指纹配置"""
        config_file = self.config_dir / "fingerprint_config.json"
        if not config_file.exists():
            logger.warning(f"指纹配置文件不存在: {config_file}")
            return {}

        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_scripts(self) -> Dict[str, str]:
        """加载所有JS注入脚本"""
        scripts = {}
        script_files = [
            "canvas.js",
            "webgl.js",
            "audio.js",
            "navigator.js",
            "screen.js",
            "webrtc.js",
            "timezone.js"
        ]

        for script_file in script_files:
            script_path = self.script_dir / script_file
            if script_path.exists():
                with open(script_path, "r", encoding="utf-8") as f:
                    scripts[script_file] = f.read()
                logger.debug(f"已加载脚本: {script_file}")
            else:
                logger.warning(f"脚本不存在: {script_file}")

        return scripts

    def get_all_scripts(self) -> str:
        """
        获取所有JS脚本的组合（用于一次性注入）

        Returns:
            组合后的JS代码字符串
        """
        combined = "\n".join(self.scripts.values())
        return combined

    def get_init_scripts(self) -> List[str]:
        """
        获取用于page.add_init_script的脚本列表

        add_init_script会在每个页面加载前执行，比add_script_tag更早

        Returns:
            JS脚本字符串列表
        """
        return list(self.scripts.values())

    def randomize_fingerprint(self) -> Dict[str, Any]:
        """
        随机化指纹参数

        Returns:
            随机化后的配置
        """
        cfg = json.loads(json.dumps(self.config))  # 深拷贝

        # 随机选择屏幕分辨率
        if "screen" in cfg and "resolutions" in cfg["screen"]:
            cfg["screen"]["selected"] = random.choice(cfg["screen"]["resolutions"])
            cfg["screen"]["width"] = cfg["screen"]["selected"]["width"]
            cfg["screen"]["height"] = cfg["screen"]["selected"]["height"]

        return cfg

    def inject_fingerprint(self, page, config: Optional[Dict] = None) -> None:
        """
        向页面注入指纹伪装脚本

        Args:
            page: Playwright page对象
            config: 自定义配置（None则使用默认）
        """
        # 使用add_init_script确保在页面脚本前执行
        for script in self.get_init_scripts():
            try:
                page.add_init_script(script)
            except Exception as e:
                logger.error(f"注入脚本失败: {e}")

        logger.info(f"已注入 {len(self.scripts)} 个指纹伪装脚本")

    def extract_fingerprint(self, page) -> Dict[str, Any]:
        """
        从页面提取当前浏览器指纹信息

        Args:
            page: Playwright page对象

        Returns:
            指纹信息字典
        """
        fingerprint_script = """
        () => {
            const fp = {};

            // Canvas指纹
            try {
                const canvas = document.createElement('canvas');
                canvas.width = 200;
                canvas.height = 50;
                const ctx = canvas.getContext('2d');
                ctx.textBaseline = 'top';
                ctx.font = '14px Arial';
                ctx.fillStyle = '#f60';
                ctx.fillRect(125, 1, 62, 20);
                ctx.fillStyle = '#069';
                ctx.fillText('Crawler Test', 2, 15);
                ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
                ctx.fillText('Crawler Test', 4, 17);
                fp.canvas = canvas.toDataURL().substring(0, 100);
            } catch(e) {
                fp.canvas = 'error: ' + e.message;
            }

            // WebGL指纹
            try {
                const canvas = document.createElement('canvas');
                const gl = canvas.getContext('webgl');
                if (gl) {
                    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                    fp.webgl_vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
                    fp.webgl_renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
                }
            } catch(e) {
                fp.webgl_vendor = 'error';
                fp.webgl_renderer = 'error';
            }

            // Navigator信息
            fp.userAgent = navigator.userAgent;
            fp.platform = navigator.platform;
            fp.languages = navigator.languages;
            fp.hardwareConcurrency = navigator.hardwareConcurrency;
            fp.deviceMemory = navigator.deviceMemory;
            fp.webdriver = navigator.webdriver;

            // 屏幕信息
            fp.screenWidth = screen.width;
            fp.screenHeight = screen.height;
            fp.colorDepth = screen.colorDepth;
            fp.devicePixelRatio = window.devicePixelRatio;

            // 时区
            fp.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            fp.timezoneOffset = new Date().getTimezoneOffset();

            // 插件
            fp.pluginsCount = navigator.plugins.length;
            fp.pluginsNames = Array.from(navigator.plugins).map(p => p.name);

            return fp;
        }
        """

        try:
            result = page.evaluate(fingerprint_script)
            return result
        except Exception as e:
            logger.error(f"提取指纹失败: {e}")
            return {}


def create_stealth_scripts() -> str:
    """
    快捷函数：生成所有反检测脚本

    Returns:
        组合的JS代码
    """
    manager = FingerprintManager()
    return manager.get_all_scripts()


if __name__ == "__main__":
    # 测试
    manager = FingerprintManager()
    print(f"已加载 {len(manager.scripts)} 个JS脚本:")
    for name in manager.scripts.keys():
        print(f"  - {name}")

    print(f"\n组合脚本长度: {len(manager.get_all_scripts())} 字符")
