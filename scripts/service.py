"""
公益捐赠 Skill - 阶段三：凭支付凭证完成捐款同步 + 取证。

凭借 yeeap-wallet 写回订单文件的 payCredential，调用 yeeap 后端 /api/skill-demo/charity-donation/service，
由后端完成「捐款记录同步到公益平台 + 获取捐赠证书」，返回证书地址。
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from file_utils import load_order

DEFAULT_BASE_URL = "https://qaap.yeepay.com/yeeap"
SERVICE_URL = os.environ.get("YEEAP_DEMO_BASE_URL", DEFAULT_BASE_URL).rstrip("/") + \
    "/api/charity-donation/service"


def find_order_app_id(order_no: str) -> str:
    home_dir = os.path.expanduser("~")
    orders_root = os.path.join(home_dir, ".yeeap", "orders")
    if not os.path.isdir(orders_root):
        raise RuntimeError(f"订单根目录不存在: {orders_root}")
    for candidate in os.listdir(orders_root):
        order_path = os.path.join(orders_root, candidate, f"{order_no}.json")
        if os.path.isfile(order_path):
            return candidate
    raise RuntimeError(f"未找到订单 {order_no}，请先执行阶段一创建订单")


def complete_donation(order_no: str, credential: str) -> dict:
    payload = json.dumps({
        "orderNo": order_no,
        "credential": credential,
    }).encode("utf-8")
    req = urllib.request.Request(
        SERVICE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            envelope = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"取证请求失败：{e}") from e

    body = envelope.get("resultData") if isinstance(envelope, dict) else None
    if body is None:
        raise RuntimeError(f"响应格式异常: {envelope}")
    if body.get("responseCode") != "200":
        raise RuntimeError(
            f"取证失败: {body.get('responseMessage', 'unknown error')}"
        )
    return body


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Complete charity donation and fetch certificate")
    parser.add_argument("order_no", help="阶段一生成的订单号")
    args = parser.parse_args()

    try:
        app_id = find_order_app_id(args.order_no)
        order_data = load_order(app_id, args.order_no)
        credential = order_data.get("payCredential")
        if not credential:
            raise RuntimeError("订单文件中缺少 payCredential 字段，请先完成阶段二支付")
        body = complete_donation(args.order_no, credential)
    except Exception as e:
        print("PAY_STATUS: ERROR")
        print(f"ERROR_INFO: {e}")
        sys.exit(1)

    pay_status = body.get("payStatus", "UNKNOWN")
    print(f"PAY_STATUS: {pay_status}")

    if pay_status == "ERROR":
        print(f"ERROR_INFO: {body.get('errorInfo', '未知错误')}")
        sys.exit(1)

    print(f"ORDER_NO={body.get('orderNo')}")
    print(f"CERT_STATUS={body.get('certStatus')}")
    print(f"CERT_URL={body.get('certUrl')}")
    print(f"PROJECT_TITLE={body.get('projectTitle')}")
    print(f"CHARITY_NAME={body.get('charityName')}")
    amount = body.get("amount")
    if amount is not None:
        print(f"AMOUNT={amount}")
