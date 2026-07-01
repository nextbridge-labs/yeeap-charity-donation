"""
公益捐赠 Skill - 阶段一（下单）：为选定项目创建捐赠订单。

调用 yeeap 后端 /api/skill-demo/charity-donation/create_order，获取 orderNo / amount / encryptedData / skill_id，
并将订单元数据写入 ~/.yeeap/orders/<app_id>/<order_no>.json，供后续 yeeap-wallet 与 service.py 使用。

金额入参单位为「元」（支持小数），脚本内部换算为「分」传给后端。
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from decimal import Decimal, ROUND_HALF_UP

from file_utils import save_order

DEFAULT_BASE_URL = "https://ap.yeepay.com/yeeap"
CREATE_ORDER_URL = os.environ.get("YEEAP_DEMO_BASE_URL", DEFAULT_BASE_URL).rstrip("/") + \
    "/api/charity-donation/create_order"


def to_fen(amount_yuan):
    """元（字符串/数字）转分（整数），四舍五入。"""
    return int((Decimal(str(amount_yuan)) * 100).to_integral_value(rounding=ROUND_HALF_UP))


def create_order(project_id, amount_fen, project_title, charity_name,
                 donor_name, donor_nick_name, comment, donor_mobile, donor_email):
    req_data = {
        "projectId": project_id,
        "amount": amount_fen,
        "projectTitle": project_title or "",
        "charityName": charity_name or "",
        "donorName": donor_name or "",
        "donorNickName": donor_nick_name or "",
        "comment": comment or "",
        "donorMobile": donor_mobile or "",
        "donorEmail": donor_email or "",
    }
    payload = json.dumps(req_data).encode("utf-8")
    req = urllib.request.Request(
        CREATE_ORDER_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            envelope = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"网络请求异常，请确认 yeeap 服务已在 {CREATE_ORDER_URL} 上运行: {e}"
        ) from e

    body = envelope.get("resultData") if isinstance(envelope, dict) else None
    if body is None:
        raise RuntimeError(f"响应格式异常，无法解析 resultData：{envelope}")
    if body.get("responseCode") != "200":
        raise RuntimeError(
            f"订单创建失败: {body.get('responseMessage', 'unknown error')}"
        )

    order_no = body.get("orderNo")
    amount = body.get("amount")
    encrypted_data = body.get("encryptedData")
    app_id = body.get("appId")
    skill_id = body.get("skillId")
    pay_env = body.get("payEnv") or "PRODUCTION"
    project_title = body.get("projectTitle") or project_title or ""
    charity_name = body.get("charityName") or charity_name or ""

    missing = [k for k, v in (
        ("orderNo", order_no),
        ("amount", amount),
        ("encryptedData", encrypted_data),
        ("appId", app_id),
        ("skillId", skill_id),
    ) if not v]
    if missing:
        raise RuntimeError(f"订单创建响应缺少字段: {', '.join(missing)}")

    return order_no, amount, encrypted_data, app_id, skill_id, pay_env, project_title, charity_name


def save_order_info(order_no, amount_fen, project_id, encrypted_data, app_id, skill_id, pay_env,
                    project_title, charity_name):
    order_data = {
        "order_no": order_no,
        "amount": amount_fen,
        "app_id": app_id,
        "skill_id": skill_id,
        "pay_env": pay_env,
        "question": project_id,
        "encrypted_data": encrypted_data,
        "project_id": project_id,
        "project_title": project_title,
        "charity_name": charity_name,
    }
    return save_order(app_id, order_no, order_data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create charity donation order")
    parser.add_argument("project_id", help="公益项目 ID（projects.py 输出的 PROJECT_<i>_ID）")
    parser.add_argument("amount", help="捐赠金额，单位：元，如 10.50")
    parser.add_argument("--project-title", default="", help="项目标题（来自 projects.py，便于展示）")
    parser.add_argument("--charity-name", default="", help="机构名称（来自 projects.py）")
    parser.add_argument("--donor-name", default="", help="捐赠人真实姓名")
    parser.add_argument("--donor-nick-name", default="", help="捐赠人昵称")
    parser.add_argument("--comment", default="", help="留言")
    parser.add_argument("--donor-mobile", default="", help="捐赠人手机号")
    parser.add_argument("--donor-email", default="", help="捐赠人邮箱")
    args = parser.parse_args()

    try:
        amount_fen = to_fen(args.amount)
    except Exception as e:
        print(f"订单创建失败: 金额格式错误 {args.amount}: {e}")
        sys.exit(1)

    if amount_fen <= 0:
        print(f"订单创建失败: 金额必须大于 0")
        sys.exit(1)

    try:
        order_no, amount, encrypted_data, app_id, skill_id, pay_env, project_title, charity_name = \
            create_order(args.project_id, amount_fen, args.project_title, args.charity_name,
                         args.donor_name, args.donor_nick_name, args.comment,
                         args.donor_mobile, args.donor_email)
    except RuntimeError as e:
        print(f"订单创建失败: {e}")
        sys.exit(1)

    save_order_info(order_no, amount_fen, args.project_id, encrypted_data, app_id, skill_id, pay_env,
                    project_title, charity_name)

    print(f"ORDER_NO={order_no}")
    print(f"AMOUNT={amount}")
    print(f"APP_ID={app_id}")
    print(f"SKILL_ID={skill_id}")
    print(f"PAY_ENV={pay_env}")
    print(f"PROJECT_TITLE={project_title}")
    print(f"CHARITY_NAME={charity_name}")
