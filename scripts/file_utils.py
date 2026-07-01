"""
固定目录订单文件读写工具：与 yeeap-cli / yeeap-wallet 约定的 ~/.yeeap/orders/<app_id>/<order_no>.json 协议保持一致。
"""

import json
import os
import platform


def get_orders_base_dir(app_id: str) -> str:
    home_dir = os.path.expanduser("~")
    if platform.system() == "Windows":
        return os.path.join(home_dir, "yeeap", "orders", app_id)
    return os.path.join(home_dir, ".yeeap", "orders", app_id)


def load_order(app_id: str, order_no: str) -> dict:
    base_dir = get_orders_base_dir(app_id)
    json_path = os.path.join(base_dir, f"{order_no}.json")
    if not os.path.isfile(json_path):
        raise RuntimeError(f"订单文件不存在: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_order(app_id: str, order_no: str, order_data: dict) -> str:
    base_dir = get_orders_base_dir(app_id)
    os.makedirs(base_dir, exist_ok=True)
    json_path = os.path.join(base_dir, f"{order_no}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(order_data, f, ensure_ascii=False, indent=2)
    return json_path
