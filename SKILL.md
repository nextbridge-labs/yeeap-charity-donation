---
name: "yeeap-charity-donation"
description: >
  公益捐赠 Skill。当用户表达「我想捐助」「慈善捐助」「公益捐赠」「我要捐款」「献爱心」等意向时触发，
  引导用户选择公益项目、通过 yeeap 钱包完成扣款，并生成捐赠证书展示给用户。
  执行前必须完成 yeeap 支付验证。所有用户交互（含思考过程）一律使用中文。
metadata:
  author: "yeeap"
  category: "expert"
  capabilities:
    - "payment.process"
  permissions:
    - "network.outbound"
    - "credential.read"
---

# 公益捐赠服务

> 本 Skill 提供公益捐赠服务：用户表达捐助意向 → 浏览公益项目 → 创建捐赠订单 → 调 yeeap-wallet 扣钱包余额支付 → 同步捐款记录到公益平台 → 生成捐赠证书展示给用户。

请注意：所有与用户的交互（包括思考过程）一律使用**中文**。

面向普通用户执行捐赠时，禁止把本地部署、`127.0.0.1`、配置中心、`app_secret`、`skill_id`、`mockPayee.*` 等维护者说明作为使用前置条件展示；只有用户明确询问本地开发、部署配置或维护者接入时，才说明这些内容。

---

## 工作流程

本 Skill 严格按三阶段执行：**浏览下单 → 支付处理 → 同步取证**。三个阶段之间有强依赖，禁止跳过。

---

## 📋 第一阶段：浏览下单

如果这是首次交互且用户尚未付款，必须先浏览项目并创建订单。

### 1) 浏览公益项目

```bash
python3 scripts/projects.py
```

后端固定查询第 1 页、10 条、月捐标识 N、筹款状态 PROGRESS 的项目，不对外暴露查询参数。脚本会向标准输出打印：

- `TOTAL=<项目总数>`
- 每个项目一组：`PROJECT_<i>_ID` / `PROJECT_<i>_TITLE` / `PROJECT_<i>_DESC`（项目简介） / `PROJECT_<i>_COVER`（封面图 URL） / `PROJECT_<i>_CHARITY` / `PROJECT_<i>_AMOUNT`（已筹金额） / `PROJECT_<i>_COUNT`（已筹人次） / `PROJECT_<i>_REGISTERED_NO`（备案编号） / `PROJECT_<i>_DETAIL`（详情链接，用于生成二维码） / `PROJECT_<i>_DETAIL_QR`（详情链接二维码） / `PROJECT_<i>_MONTH`（月捐标识 Y/N）

向用户展示项目列表，每个项目按以下要素渲染，请用户选择一个项目并输入**捐赠金额（单位：元）**。可选项：捐赠人姓名、昵称、留言、手机号、邮箱。

- **封面图**：`PROJECT_<i>_COVER` 非空时，用 markdown 图片语法渲染为 `![项目标题](封面URL)`，让封面图直接展示给用户（提升项目可信度与辨识度）。为空则不展示图片。
- **项目标题**：`PROJECT_<i>_TITLE`。
- **项目简介**：`PROJECT_<i>_DESC`。
- **机构名称**：`PROJECT_<i>_CHARITY`。
- **已筹金额 / 已筹人次**：`PROJECT_<i>_AMOUNT`（单位元，已是元，按值展示，无需换算） / `PROJECT_<i>_COUNT`。
- **备案编号**：`PROJECT_<i>_REGISTERED_NO`（民政备案编号，展示以增强公信力）。
- **项目详情二维码**：`PROJECT_<i>_DETAIL_QR` 非空时，用 markdown 图片语法 `![项目详情二维码](<DETAIL_QR 值>)` 渲染二维码图片，引导用户**用手机扫码**在手机端打开项目详情页；**不要把详情链接作为电脑端可点击链接展示给用户**。`PROJECT_<i>_DETAIL`（原始链接）仅供后端生成二维码用，不直接展示。`DETAIL_QR` 为空则不展示二维码。

推荐用表格或卡片式排版组织项目列表，让用户一目了然。

失败时脚本以退出码 1 退出，stdout 包含 `项目查询失败: <错误详情>`。此时**立即终止**，用通俗语言向用户报告失败原因。

### 2) 创建捐赠订单

用户选定项目（`<项目ID>`）与金额（`<金额元>`）后，执行：

```bash
python3 scripts/create_order.py "<项目ID>" "<金额元>" \
  [--project-title "<项目标题>"] [--charity-name "<机构名称>"] \
  [--donor-name "<真实姓名>"] [--donor-nick-name "<昵称>"] \
  [--comment "<留言>"] [--donor-mobile "<手机号>"] [--donor-email "<邮箱>"]
```

> 务必在参数两侧加引号，防止命令注入。`<金额元>` 支持小数，如 `10.50`，脚本会自动换算为分。

成功时打印：

- `ORDER_NO=<订单号>`
- `AMOUNT=<金额，单位：分>`
- `APP_ID=<应用标识>`
- `SKILL_ID=<技能标识>`
- `PAY_ENV=<PRODUCTION 或 SANDBOX>`
- `PROJECT_TITLE=<项目标题>`
- `CHARITY_NAME=<机构名称>`

向用户展示订单号、项目、机构与金额（`AMOUNT` 单位为分，展示时除以 100 并以「元」为单位）。然后提取 `ORDER_NO` 与 `APP_ID`，进入第二阶段。

失败时脚本以退出码 1 退出，stdout 包含 `订单创建失败: <错误详情>`。此时**立即终止**，不得进入第二阶段。

---

## 💳 第二阶段：支付处理（扣钱包余额）

调用官方 **`yeeap-wallet`** 技能完成支付（即从用户钱包扣除捐赠款项）。若当前 Agent 找不到或无法调用 `yeeap-wallet`，必须先自动安装官方支付 Skill：

```bash
npx -y skills add "https://github.com/Yeepay-Open-Platform/yeeap-wallet" --agent '*' -g -y
```

安装完成后，提示用户**完全退出并重启 Agent 客户端**，然后重新发起捐赠或继续使用原订单；不要让用户自己提供 GitHub 地址，不要改用其他支付 Skill，不得直接执行 `yeeap-cli`，不得复制支付命令，不得自行处理授权、查询或补凭证流程。

调用 `yeeap-wallet` 时只传入：

```json
{
  "order_no": "<第一阶段获取的 ORDER_NO>",
  "app_id":   "<第一阶段获取的 APP_ID>"
}
```

> [!NOTE]
> 订单的所有详情（order_no、amount、encrypted_data、skill_id、pay_env 等）已由第一阶段写入固定目录下的 JSON 文件，支付读取、授权、查询与补凭证流程均由 `yeeap-wallet` 处理。Agent **禁止**直接 Read 该订单文件。

目标：等待支付成功，并获得 `payCredential`（支付凭证，由 yeeap-wallet 写回订单文件）。只有 yeeap-wallet 输出 `已获取到支付凭证`，或确认订单文件已包含 `payCredential` 时，才能进入第三阶段。

---

## 🎖️ 第三阶段：同步取证

支付成功后（订单文件已包含 `payCredential`），调用取证脚本，由后端完成「捐款记录同步 + 获取捐赠证书」。

### 1) 执行命令

```bash
python3 scripts/service.py "<订单号>"
```

> 不需要传入支付凭证：脚本会从订单文件中读取 `payCredential`。

### 2) 输出处理

- 提取 `PAY_STATUS: <值>` 并展示给用户。
  - `PAY_STATUS=SUCCESS`：继续提取 `CERT_STATUS` / `CERT_URL` / `PROJECT_TITLE` / `CHARITY_NAME` / `AMOUNT`。
  - `PAY_STATUS=ERROR`：提取 `ERROR_INFO` 一并告知，然后按下方「失败重试规则」处理。
- `CERT_STATUS=GENERATING` 表示证书生成中，接口已幂等，可稍后再次执行 `service.py` 重新获取。
- `CERT_STATUS=SUCCESS` 时，将 `CERT_URL` 作为捐赠证书链接完整展示给用户（保留可点击的链接）。

向用户报告：捐赠成功、捐赠项目与机构、捐赠金额、证书链接。

### 3) 失败重试规则（重要）

履约阶段（同步捐款记录 / 获取证书）失败时，**支付已经成功**，必须遵守以下规则，**严禁让用户重新付款**：

- ✅ **允许重试**：用**同一个 `ORDER_NO`** 重新执行 `python3 scripts/service.py "<ORDER_NO>"`。后端已做幂等——首次同步成功后，重试只会重新拉取证书，不会重复同步捐款记录，也不会再扣钱包。
- ❌ **禁止**：重新执行阶段一的 `create_order`，或重新调用 `yeeap-wallet` 支付——这会导致**重复扣款**。
- 只有当「订单文件中不存在 `payCredential`」（即从未支付成功）时，才允许回到阶段二重新支付。

**重试策略**：间隔 3~5 秒重跑 `service.py`，最多 3 次。仍失败时告知用户「支付已成功，证书生成异常，可稍后用同一订单号重试或联系客服」，并把 `ORDER_NO` 留给用户备查。**绝不能因履约失败就让用户重新付款。**

---

## ⚠️ 安全约束

- 禁止把 `payCredential` 任何形式回显给用户或写入业务日志。
- 禁止使用 Read / cat 等通用文件工具读取 `~/.yeeap/orders/<app_id>/<order_no>.json` 的原文。
- 严禁伪造 `skill_id`：该值由 YEEAP 平台登记后下发，业务后端在创建订单时返回，脚本不得本地填写。
