"""
人类行为模拟模块

模拟真实用户的鼠标轨迹、键盘输入、滚动行为、页面停留等操作。
核心是使用贝塞尔曲线生成自然的鼠标轨迹，避免被反爬系统通过
行为分析识别为机器人。
"""

import math
import random
import time
from typing import List, Tuple, Optional, Callable
from loguru import logger

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("numpy未安装，将使用纯Python实现")


class BezierCurve:
    """贝塞尔曲线生成器"""

    @staticmethod
    def cubic_bezier(p0: Tuple[float, float],
                     p1: Tuple[float, float],
                     p2: Tuple[float, float],
                     p3: Tuple[float, float],
                     num_points: int = 50) -> List[Tuple[int, int]]:
        """
        三次贝塞尔曲线

        B(t) = (1-t)^3 P0 + 3(1-t)^2 t P1 + 3(1-t) t^2 P2 + t^3 P3
        """
        points = []
        for i in range(num_points + 1):
            t = i / num_points
            # 计算贝塞尔曲线上的点
            one_minus_t = 1 - t
            x = (one_minus_t ** 3 * p0[0] +
                 3 * one_minus_t ** 2 * t * p1[0] +
                 3 * one_minus_t * t ** 2 * p2[0] +
                 t ** 3 * p3[0])
            y = (one_minus_t ** 3 * p0[1] +
                 3 * one_minus_t ** 2 * t * p1[1] +
                 3 * one_minus_t * t ** 2 * p2[1] +
                 t ** 3 * p3[1])
            points.append((int(x), int(y)))
        return points

    @staticmethod
    def generate_natural_path(start: Tuple[int, int],
                              end: Tuple[int, int],
                              num_control_points: int = 2,
                              num_points: int = 30) -> List[Tuple[int, int]]:
        """
        生成自然的鼠标轨迹

        在起点和终点之间插入随机控制点，生成贝塞尔曲线
        路径，并加入随机抖动模拟真实鼠标。
        """
        sx, sy = start
        ex, ey = end

        # 计算距离
        distance = math.sqrt((ex - sx) ** 2 + (ey - sy) ** 2)

        # 根据距离决定控制点数量和路径点数
        if distance < 50:
            num_control_points = 1
            num_points = max(10, int(distance / 3))
        elif distance < 200:
            num_control_points = 2
            num_points = max(20, int(distance / 5))
        else:
            num_control_points = random.randint(2, 4)
            num_points = max(30, int(distance / 8))

        # 生成控制点
        control_points = [(sx, sy)]
        for i in range(num_control_points):
            t = (i + 1) / (num_control_points + 1)
            # 在起点到终点连线的垂直方向上偏移
            base_x = sx + (ex - sx) * t
            base_y = sy + (ey - sy) * t

            # 垂直偏移（增强真实感）
            perp_x = -(ey - sy) / max(distance, 1)
            perp_y = (ex - sx) / max(distance, 1)

            offset = random.randint(-int(distance * 0.3), int(distance * 0.3))
            cx = base_x + perp_x * offset + random.randint(-20, 20)
            cy = base_y + perp_y * offset + random.randint(-20, 20)

            # 确保控制点在屏幕范围内
            cx = max(0, min(1920, cx))
            cy = max(0, min(1080, cy))

            control_points.append((cx, cy))
        control_points.append((ex, ey))

        # 使用三次贝塞尔曲线（分段）
        all_points = []
        for i in range(len(control_points) - 1):
            p0 = control_points[i]
            p3 = control_points[i + 1]
            # 生成中间控制点
            if i == 0:
                p1 = (p0[0] + (p3[0] - p0[0]) * 0.3 + random.randint(-30, 30),
                      p0[1] + (p3[1] - p0[1]) * 0.3 + random.randint(-30, 30))
            else:
                p1 = ((p0[0] + p3[0]) / 2 + random.randint(-20, 20),
                      (p0[1] + p3[1]) / 2 + random.randint(-20, 20))
            p2 = (p3[0] - (p3[0] - p0[0]) * 0.3 + random.randint(-30, 30),
                  p3[1] - (p3[1] - p0[1]) * 0.3 + random.randint(-30, 30))

            segment_points = BezierCurve.cubic_bezier(p0, p1, p2, p3, num_points // (len(control_points) - 1))
            if i > 0:
                segment_points = segment_points[1:]  # 去掉重复点
            all_points.extend(segment_points)

        # 添加微小随机抖动
        for i in range(len(all_points)):
            x, y = all_points[i]
            x += random.randint(-2, 2)
            y += random.randint(-2, 2)
            all_points[i] = (x, y)

        return all_points

    @staticmethod
    def generate_timestamps(num_points: int,
                           base_delay: float = 0.01,
                           variance: float = 0.005) -> List[float]:
        """
        为轨迹点生成时间戳

        使用变速模拟（开始慢、中间快、结束慢）
        """
        timestamps = []
        for i in range(num_points):
            # 使用ease-in-out曲线
            t = i / num_points
            # Sigmoid函数
            speed = math.exp(-((t - 0.5) * 5) ** 2) + 0.3
            delay = base_delay / speed + random.uniform(-variance, variance)
            timestamps.append(max(0.001, delay))
        return timestamps


class HumanBehavior:
    """
    人类行为模拟器

    模拟真实用户的行为模式，包括：
    - 鼠标轨迹（贝塞尔曲线）
    - 键盘输入（真人节奏）
    - 页面滚动（不规则）
    - 点击行为（带偏移）
    """

    def __init__(self, page=None, config: Optional[dict] = None):
        """
        初始化行为模拟器

        Args:
            page: Playwright page对象
            config: 行为配置
        """
        self.page = page
        self.config = config or {}
        self.bezier = BezierCurve()

    def set_page(self, page) -> None:
        """设置page对象"""
        self.page = page

    async def random_sleep(self, min_ms: int = 100, max_ms: int = 500) -> None:
        """随机延时"""
        delay = random.randint(min_ms, max_ms) / 1000
        await self.page.wait_for_timeout(delay)

    async def simulate_mouse_move(self,
                                  start: Optional[Tuple[int, int]] = None,
                                  end: Optional[Tuple[int, int]] = None) -> List[Tuple[int, int]]:
        """
        模拟鼠标移动

        Args:
            start: 起点坐标 (None则使用当前位置)
            end: 终点坐标 (None则随机)

        Returns:
            移动路径点列表
        """
        if self.page is None:
            return []

        # 获取当前鼠标位置
        if start is None:
            try:
                pos = await self.page.evaluate("() => ({x: window.__mouseX || 100, y: window.__mouseY || 100})")
                start = (pos.get("x", 100), pos.get("y", 100))
            except:
                start = (100, 100)

        # 生成目标位置
        if end is None:
            viewport = self.page.viewport_size
            end = (random.randint(100, viewport["width"] - 100),
                   random.randint(100, viewport["height"] - 100))

        # 生成轨迹
        path = self.bezier.generate_natural_path(start, end)
        timestamps = self.bezier.generate_timestamps(len(path))

        # 移动鼠标
        for (x, y), delay in zip(path, timestamps):
            await self.page.mouse.move(x, y)
            # 记录当前位置
            await self.page.evaluate(f"() => {{ window.__mouseX = {x}; window.__mouseY = {y}; }}")
            await self.page.wait_for_timeout(int(delay * 1000))

        return path

    async def simulate_click(self,
                            selector: Optional[str] = None,
                            position: Optional[Tuple[int, int]] = None) -> None:
        """
        模拟点击

        Args:
            selector: 元素选择器
            position: 点击坐标 (与selector二选一)
        """
        if self.page is None:
            return

        if selector:
            # 先移动到目标元素
            element = await self.page.query_selector(selector)
            if element is None:
                logger.warning(f"元素未找到: {selector}")
                return

            box = await element.bounding_box()
            if box is None:
                logger.warning(f"元素无边界: {selector}")
                return

            # 在元素内随机选点（带高斯分布）
            cx = box["x"] + box["width"] / 2
            cy = box["y"] + box["height"] / 2

            # 真实点击位置会有少量偏移
            offset_x = random.gauss(0, box["width"] / 6)
            offset_y = random.gauss(0, box["height"] / 6)

            target_x = int(max(box["x"] + 2, min(box["x"] + box["width"] - 2, cx + offset_x)))
            target_y = int(max(box["y"] + 2, min(box["y"] + box["height"] - 2, cy + offset_y)))

            # 先移动到目标位置
            await self.simulate_mouse_move(end=(target_x, target_y))
            await self.random_sleep(50, 200)

            # 点击（带mousedown和mouseup的间隔）
            await self.page.mouse.down()
            await self.page.wait_for_timeout(random.randint(50, 150))
            await self.page.mouse.up()

        elif position:
            await self.simulate_mouse_move(end=position)
            await self.random_sleep(50, 200)
            await self.page.mouse.click(position[0], position[1])

        else:
            # 随机位置点击
            await self.simulate_mouse_move()
            await self.random_sleep(50, 200)
            viewport = self.page.viewport_size
            x = random.randint(100, viewport["width"] - 100)
            y = random.randint(100, viewport["height"] - 100)
            await self.page.mouse.click(x, y)

    async def simulate_typing(self, selector: str, text: str) -> None:
        """
        模拟键盘输入

        Args:
            selector: 输入框选择器
            text: 要输入的文本
        """
        if self.page is None:
            return

        # 先点击输入框
        await self.simulate_click(selector)

        # 清空原有内容
        await self.page.evaluate(f"() => {{ const el = document.querySelector('{selector}'); if (el) el.value = ''; }}")

        # 逐字输入，模拟真人节奏
        for i, char in enumerate(text):
            # 字符间延迟（中文+英文不同）
            if '\u4e00' <= char <= '\u9fff':
                delay = random.gauss(150, 40)
            else:
                delay = random.gauss(80, 25)

            # 偶尔出现停顿（思考/选字）
            if random.random() < 0.05:
                delay += random.randint(300, 800)

            # 偶尔打错回退
            if random.random() < 0.02 and i > 0:
                await self.page.keyboard.press("Backspace")
                await self.page.wait_for_timeout(random.randint(100, 300))

            await self.page.keyboard.type(char, delay=0)
            await self.page.wait_for_timeout(int(max(20, delay)))

    async def simulate_scroll(self, direction: str = "down",
                             amount: Optional[int] = None) -> None:
        """
        模拟页面滚动

        Args:
            direction: 滚动方向 (up/down)
            amount: 滚动距离 (None则随机)
        """
        if self.page is None:
            return

        if amount is None:
            amount = random.randint(100, 500)

        # 分多次滚动，模拟真实
        steps = random.randint(3, 8)
        step_amount = amount // steps
        direction_mult = 1 if direction == "down" else -1

        for _ in range(steps):
            scroll_delta = step_amount * direction_mult
            # 添加随机变化
            scroll_delta += random.randint(-20, 20)
            await self.page.mouse.wheel(0, scroll_delta)
            await self.page.wait_for_timeout(random.randint(100, 300))

        # 偶尔回滚一下
        if random.random() < 0.3:
            await self.page.mouse.wheel(0, -step_amount // 2)
            await self.page.wait_for_timeout(random.randint(200, 500))

    async def simulate_page_stay(self, min_seconds: float = 2, max_seconds: float = 8) -> None:
        """
        模拟在页面停留

        Args:
            min_seconds: 最小停留秒数
            max_seconds: 最大停留秒数
        """
        if self.page is None:
            return

        stay_time = random.uniform(min_seconds, max_seconds)
        logger.debug(f"页面停留 {stay_time:.1f} 秒")

        # 在停留期间做随机行为
        elapsed = 0
        while elapsed < stay_time:
            action_delay = random.uniform(0.5, 1.5)
            await self.page.wait_for_timeout(int(action_delay * 1000))
            elapsed += action_delay

            # 随机行为
            rand = random.random()
            if rand < 0.3:
                # 鼠标小幅移动
                viewport = self.page.viewport_size
                x = random.randint(100, viewport["width"] - 100)
                y = random.randint(100, viewport["height"] - 100)
                await self.simulate_mouse_move(end=(x, y))
            elif rand < 0.6:
                # 轻微滚动
                if random.random() < 0.5:
                    await self.simulate_scroll("down", random.randint(50, 200))
                else:
                    await self.simulate_scroll("up", random.randint(50, 150))

    async def simulate_browsing_session(self, url: str, duration: int = 30) -> None:
        """
        模拟完整的浏览会话

        Args:
            url: 目标URL
            duration: 持续时间（秒）
        """
        if self.page is None:
            return

        logger.info(f"开始模拟浏览会话: {url}")

        # 访问页面
        await self.page.goto(url, wait_until="domcontentloaded")

        # 初始停留
        await self.simulate_page_stay(2, 5)

        # 持续时间内的随机行为
        start_time = time.time()
        while time.time() - start_time < duration:
            action = random.choice(["scroll", "move", "click", "stay"])

            if action == "scroll":
                await self.simulate_scroll()
            elif action == "move":
                await self.simulate_mouse_move()
            elif action == "click":
                # 30%概率点击页面上的链接
                if random.random() < 0.3:
                    links = await self.page.query_selector_all("a")
                    if links:
                        link = random.choice(links)
                        try:
                            await self.simulate_click(element=None if not hasattr(self, 'element') else self.element)
                        except:
                            pass
            else:
                await self.simulate_page_stay(1, 3)

        logger.info("浏览会话结束")


def generate_mouse_path(start: Tuple[int, int],
                       end: Tuple[int, int],
                       num_points: int = 20) -> List[Tuple[int, int]]:
    """快捷函数：生成鼠标路径"""
    return BezierCurve.generate_natural_path(start, end, num_points=num_points)


if __name__ == "__main__":
    # 测试贝塞尔曲线
    path = generate_mouse_path((100, 100), (500, 400))
    print(f"生成了 {len(path)} 个轨迹点")
    print(f"起点: {path[0]}")
    print(f"终点: {path[-1]}")
    print(f"前5个点: {path[:5]}")
    print(f"后5个点: {path[-5:]}")

    # 测试时间戳生成
    ts = BezierCurve.generate_timestamps(20)
    print(f"\n生成 {len(ts)} 个时间戳")
    print(f"总时长: {sum(ts):.2f} 秒")
    print(f"平均间隔: {sum(ts)/len(ts)*1000:.1f} ms")
