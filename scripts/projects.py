"""
公益捐赠 Skill - 阶段一（项目浏览）：查询公益项目列表。

调用 yeeap 后端 /api/charity-donation/projects（代理调公益平台 findProjectInfoPage）。
后端固定查询第 1 页、10 条、月捐标识 N、筹款状态 PROGRESS，不对外暴露查询参数。
返回项目列表供用户选择。
"""

import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://qaap.yeepay.com/yeeap"
PROJECTS_URL = os.environ.get("YEEAP_DEMO_BASE_URL", DEFAULT_BASE_URL).rstrip("/") + \
    "/api/charity-donation/projects"


def query_projects():
    req = urllib.request.Request(
        PROJECTS_URL,
        data=b"",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            envelope = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"网络请求异常，请确认 yeeap 服务已在 {PROJECTS_URL} 上运行: {e}"
        ) from e

    body = envelope.get("resultData") if isinstance(envelope, dict) else None
    if body is None:
        raise RuntimeError(f"响应格式异常，无法解析 resultData：{envelope}")
    if body.get("responseCode") != "200":
        raise RuntimeError(
            f"项目查询失败: {body.get('responseMessage', 'unknown error')}"
        )
    return body


if __name__ == "__main__":
    try:
        body = query_projects()
    except RuntimeError as e:
        print(f"项目查询失败: {e}")
        sys.exit(1)

    page_data = body.get("pageData") or []
    print(f"TOTAL={body.get('total', len(page_data))}")
    print(f"PAGES={body.get('pages')}")
    for i, p in enumerate(page_data):
        print(f"PROJECT_{i}_ID={p.get('id')}")
        print(f"PROJECT_{i}_TITLE={p.get('projectTitle')}")
        print(f"PROJECT_{i}_DESC={p.get('description')}")
        print(f"PROJECT_{i}_COVER={p.get('cover')}")
        print(f"PROJECT_{i}_CHARITY={p.get('charityName')}")
        print(f"PROJECT_{i}_AMOUNT={p.get('allAmount')}")
        print(f"PROJECT_{i}_COUNT={p.get('allCount')}")
        print(f"PROJECT_{i}_REGISTERED_NO={p.get('registeredNo')}")
        print(f"PROJECT_{i}_DETAIL={p.get('detailUrl')}")
        print(f"PROJECT_{i}_DETAIL_QR_URL={PROJECTS_URL}/{p.get('id')}/qr")
        print(f"PROJECT_{i}_MONTH={p.get('monthDonateFlag')}")
