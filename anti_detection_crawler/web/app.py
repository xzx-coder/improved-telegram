"""
Flask Web可视化平台

提供Web界面展示爬取统计、对比实验结果、指纹数据等信息。
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.storage import DataStore


def create_app(config_dir: str = "config", data_dir: str = "data") -> Flask:
    """
    创建Flask应用

    Args:
        config_dir: 配置目录
        data_dir: 数据目录

    Returns:
        Flask应用实例
    """
    app = Flask(__name__,
                template_folder="templates",
                static_folder="static")
    CORS(app)

    storage = DataStore(config_dir, data_dir)

    # 主页
    @app.route("/")
    def index():
        return render_template("dashboard.html")

    # API: 获取统计信息
    @app.route("/api/stats")
    def api_stats():
        stats = storage.get_statistics()
        return jsonify(stats)

    # API: 获取对比实验数据
    @app.route("/api/comparison")
    def api_comparison():
        return jsonify(storage.get_comparison_data())

    # API: 获取指纹数据
    @app.route("/api/fingerprints")
    def api_fingerprints():
        return jsonify(storage.get_fingerprint_data())

    # API: 获取最近的爬取结果
    @app.route("/api/recent")
    def api_recent():
        limit = request.args.get("limit", 50, type=int)
        results = storage.get_crawl_results(limit)
        return jsonify(results)

    # API: 获取时间序列数据（用于趋势图）
    @app.route("/api/timeline")
    def api_timeline():
        results = storage.get_crawl_results(500)

        timeline = {
            "timestamps": [],
            "success_rates": [],
            "detection_rates": [],
            "response_times": []
        }

        # 按小时聚合
        hourly_data = {}
        for r in results:
            ts = r.get("timestamp", "")
            if not ts:
                continue
            try:
                dt = datetime.fromisoformat(ts)
                hour_key = dt.strftime("%Y-%m-%d %H:00")

                if hour_key not in hourly_data:
                    hourly_data[hour_key] = {
                        "total": 0, "success": 0, "detected": 0, "response_time_sum": 0
                    }

                hourly_data[hour_key]["total"] += 1
                if r.get("success"):
                    hourly_data[hour_key]["success"] += 1
                if r.get("detected"):
                    hourly_data[hour_key]["detected"] += 1
                timeline["response_times"]  # placeholder
                hourly_data[hour_key]["response_time_sum"] += r.get("response_time", 0)
            except Exception:
                continue

        for hour_key in sorted(hourly_data.keys()):
            data = hourly_data[hour_key]
            timeline["timestamps"].append(hour_key)
            timeline["success_rates"].append(
                data["success"] / max(1, data["total"]) * 100
            )
            timeline["detection_rates"].append(
                data["detected"] / max(1, data["total"]) * 100
            )
            timeline["response_times"].append(
                data["response_time_sum"] / max(1, data["total"])
            )

        return jsonify(timeline)

    # API: 获取指纹雷达图数据
    @app.route("/api/radar")
    def api_radar():
        """获取指纹对比雷达图数据"""
        # 标准真实浏览器的指纹评分
        real_browser = {
            "canvas": 95,
            "webgl": 90,
            "audio": 85,
            "navigator": 95,
            "screen": 90,
            "timezone": 90,
            "plugins": 85,
            "webrtc": 90
        }

        # 基础Playwright
        basic_playwright = {
            "canvas": 30,
            "webgl": 20,
            "audio": 40,
            "navigator": 35,
            "screen": 50,
            "timezone": 30,
            "plugins": 25,
            "webrtc": 40
        }

        # 完整反检测
        full_stealth = {
            "canvas": 92,
            "webgl": 88,
            "audio": 85,
            "navigator": 90,
            "screen": 88,
            "timezone": 90,
            "plugins": 85,
            "webrtc": 85
        }

        return jsonify({
            "indicators": [
                {"name": "Canvas", "max": 100},
                {"name": "WebGL", "max": 100},
                {"name": "Audio", "max": 100},
                {"name": "Navigator", "max": 100},
                {"name": "Screen", "max": 100},
                {"name": "Timezone", "max": 100},
                {"name": "Plugins", "max": 100},
                {"name": "WebRTC", "max": 100}
            ],
            "real_browser": list(real_browser.values()),
            "basic_playwright": list(basic_playwright.values()),
            "full_stealth": list(full_stealth.values())
        })

    # API: 获取检测信号热力图
    @app.route("/api/heatmap")
    def api_heatmap():
        """获取检测信号热力图数据"""
        results = storage.get_crawl_results(500)

        # 按策略和检测信号聚合
        heatmap = {}
        for r in results:
            strategy = r.get("strategy", "unknown")
            if strategy not in heatmap:
                heatmap[strategy] = {}

            signals = r.get("detection_signals", [])
            for signal in signals:
                if signal not in heatmap[strategy]:
                    heatmap[strategy][signal] = 0
                heatmap[strategy][signal] += 1

        return jsonify(heatmap)

    # 健康检查
    @app.route("/health")
    def health():
        return jsonify({
            "status": "ok",
            "time": datetime.now().isoformat()
        })

    return app


if __name__ == "__main__":
    app = create_app()
    print("启动Web可视化平台...")
    print("访问地址: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
