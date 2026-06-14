"""
数据存储模块

支持MongoDB和JSONL两种存储方式，用于保存爬取结果、指纹数据、
检测日志等信息。
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
from loguru import logger

try:
    from pymongo import MongoClient, ASCENDING
    from pymongo.errors import ConnectionFailure
    HAS_MONGO = True
except ImportError:
    HAS_MONGO = False
    logger.warning("pymongo未安装，将仅使用JSONL存储")


class DataStore:
    """
    数据存储器

    支持两种存储后端：
    - MongoDB: 适合大量数据、复杂查询
    - JSONL: 轻量级，每行一个JSON对象
    """

    def __init__(self, config_dir: str = "config", data_dir: str = "data"):
        """
        初始化数据存储

        Args:
            config_dir: 配置目录
            data_dir: 数据目录
        """
        self.config_dir = Path(config_dir)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.config = self._load_config()
        self.mongo_client = None
        self.db = None
        self._init_storage()

    def _load_config(self) -> Dict:
        """加载存储配置"""
        config_file = self.config_dir / "settings.json"
        if not config_file.exists():
            return {"storage": {"use_mongodb": False, "use_jsonl": True}}

        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _init_storage(self) -> None:
        """初始化存储后端"""
        storage_config = self.config.get("storage", {})

        # 初始化JSONL
        if storage_config.get("use_jsonl", True):
            jsonl_path = self.data_dir / "results.jsonl"
            if not jsonl_path.exists():
                jsonl_path.touch()
            logger.info(f"JSONL存储已启用: {jsonl_path}")

        # 初始化MongoDB
        if storage_config.get("use_mongodb", False) and HAS_MONGO:
            try:
                uri = storage_config.get("mongodb_uri", "mongodb://localhost:27017/")
                db_name = storage_config.get("mongodb_db", "anti_detection_crawler")
                self.mongo_client = MongoClient(uri, serverSelectionTimeoutMS=5000)
                self.mongo_client.admin.command('ping')
                self.db = self.mongo_client[db_name]
                self._ensure_indexes()
                logger.info(f"MongoDB已连接: {db_name}")
            except Exception as e:
                logger.error(f"MongoDB连接失败: {e}")
                self.mongo_client = None
                self.db = None

    def _ensure_indexes(self) -> None:
        """确保索引存在"""
        if self.db is None:
            return

        try:
            self.db.crawl_results.create_index([("timestamp", ASCENDING)])
            self.db.crawl_results.create_index([("url", ASCENDING)])
            self.db.fingerprint_records.create_index([("timestamp", ASCENDING)])
            self.db.detection_logs.create_index([("timestamp", ASCENDING)])
        except Exception as e:
            logger.warning(f"创建索引失败: {e}")

    def save_crawl_result(self, result: Dict) -> bool:
        """
        保存爬取结果

        Args:
            result: 爬取结果字典

        Returns:
            是否保存成功
        """
        # 添加时间戳
        if "timestamp" not in result:
            result["timestamp"] = datetime.now().isoformat()

        # JSONL存储
        if self.config.get("storage", {}).get("use_jsonl", True):
            try:
                with open(self.data_dir / "results.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error(f"JSONL保存失败: {e}")
                return False

        # MongoDB存储
        if self.db is not None:
            try:
                self.db.crawl_results.insert_one(result.copy())
            except Exception as e:
                logger.error(f"MongoDB保存失败: {e}")
                return False

        return True

    def save_fingerprint(self, fingerprint: Dict) -> bool:
        """保存浏览器指纹"""
        fingerprint["timestamp"] = datetime.now().isoformat()

        # JSONL
        try:
            with open(self.data_dir / "fingerprints.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(fingerprint, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"指纹保存失败: {e}")
            return False

        # MongoDB
        if self.db is not None:
            try:
                self.db.fingerprint_records.insert_one(fingerprint.copy())
            except Exception as e:
                logger.error(f"MongoDB指纹保存失败: {e}")

        return True

    def save_detection_log(self, log: Dict) -> bool:
        """保存检测日志"""
        log["timestamp"] = datetime.now().isoformat()

        # JSONL
        try:
            with open(self.data_dir / "detection_logs.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"检测日志保存失败: {e}")
            return False

        # MongoDB
        if self.db is not None:
            try:
                self.db.detection_logs.insert_one(log.copy())
            except Exception as e:
                logger.error(f"MongoDB日志保存失败: {e}")

        return True

    def get_crawl_results(self, limit: int = 100) -> List[Dict]:
        """获取最近的爬取结果"""
        results = []

        if self.db is not None:
            cursor = self.db.crawl_results.find().sort("timestamp", -1).limit(limit)
            results = list(cursor)
        else:
            # 从JSONL读取
            jsonl_path = self.data_dir / "results.jsonl"
            if jsonl_path.exists():
                with open(jsonl_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines[-limit:]:
                        try:
                            results.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            continue

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_crawls": 0,
            "successful_crawls": 0,
            "failed_crawls": 0,
            "success_rate": 0,
            "avg_response_time": 0,
            "total_fingerprints": 0,
            "detection_results": {
                "detected": 0,
                "undetected": 0
            }
        }

        # 从JSONL统计
        results_file = self.data_dir / "results.jsonl"
        if results_file.exists():
            with open(results_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        stats["total_crawls"] += 1
                        if data.get("success"):
                            stats["successful_crawls"] += 1
                        else:
                            stats["failed_crawls"] += 1

                        # 检测结果
                        if data.get("detected"):
                            stats["detection_results"]["detected"] += 1
                        else:
                            stats["detection_results"]["undetected"] += 1
                    except json.JSONDecodeError:
                        continue

        # 计算成功率
        if stats["total_crawls"] > 0:
            stats["success_rate"] = stats["successful_crawls"] / stats["total_crawls"]

        # 指纹数量
        fp_file = self.data_dir / "fingerprints.jsonl"
        if fp_file.exists():
            with open(fp_file, "r", encoding="utf-8") as f:
                stats["total_fingerprints"] = sum(1 for _ in f)

        return stats

    def get_fingerprint_data(self) -> Dict[str, List]:
        """获取指纹数据用于可视化"""
        data = {
            "timestamps": [],
            "canvas_hashes": [],
            "webgl_renderers": [],
            "user_agents": [],
            "screen_resolutions": []
        }

        fp_file = self.data_dir / "fingerprints.jsonl"
        if not fp_file.exists():
            return data

        with open(fp_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    fp = json.loads(line.strip())
                    data["timestamps"].append(fp.get("timestamp", ""))
                    data["canvas_hashes"].append(fp.get("canvas_hash", ""))
                    data["webgl_renderers"].append(fp.get("webgl_renderer", ""))
                    data["user_agents"].append(fp.get("userAgent", ""))
                    screen = fp.get("screen", {})
                    data["screen_resolutions"].append(
                        f"{screen.get('width', 0)}x{screen.get('height', 0)}"
                    )
                except json.JSONDecodeError:
                    continue

        return data

    def get_comparison_data(self) -> Dict[str, Any]:
        """获取对比实验数据"""
        # 统计不同策略的成功率
        strategies = {
            "裸requests": {"success": 0, "total": 0},
            "基础Playwright": {"success": 0, "total": 0},
            "完整反检测": {"success": 0, "total": 0}
        }

        results_file = self.data_dir / "results.jsonl"
        if results_file.exists():
            with open(results_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        strategy = data.get("strategy", "完整反检测")
                        if strategy in strategies:
                            strategies[strategy]["total"] += 1
                            if data.get("success"):
                                strategies[strategy]["success"] += 1
                    except json.JSONDecodeError:
                        continue

        # 计算成功率
        result = {}
        for name, data in strategies.items():
            if data["total"] > 0:
                result[name] = {
                    "success_rate": data["success"] / data["total"],
                    "total": data["total"],
                    "success": data["success"]
                }
            else:
                result[name] = {"success_rate": 0, "total": 0, "success": 0}

        return result

    def close(self) -> None:
        """关闭连接"""
        if self.mongo_client is not None:
            self.mongo_client.close()
            logger.info("MongoDB连接已关闭")


if __name__ == "__main__":
    # 测试
    ds = DataStore()
    print("存储配置:", ds.config.get("storage", {}))
    print("MongoDB已连接:", ds.db is not None)

    # 保存测试数据
    ds.save_crawl_result({
        "url": "https://example.com",
        "success": True,
        "response_time": 1.23,
        "strategy": "完整反检测"
    })

    # 获取统计
    print("统计:", ds.get_statistics())
