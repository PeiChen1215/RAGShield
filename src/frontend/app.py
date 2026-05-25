"""
模块名: src/frontend/app.py
职责: Gradio 演示界面，纯 HTTP 调用 FastAPI，零业务逻辑。
作者: RAGShield Team
创建日期: 2026-05-07
更新日期: 2026-05-25 — 修复前后端接口不一致 bug
"""

import gradio as gr
import httpx

API_BASE = "http://localhost:8000/api/v1"


async def on_query_submit(query: str, kb_id: str = "demo_safe"):
    """Gradio 按钮回调——纯 HTTP 调用，零业务逻辑。

    Args:
        query: 用户查询。
        kb_id: 知识库 ID。

    Returns:
        格式化展示数据。
    """
    if not query or not query.strip():
        return (
            "请输入查询内容",
            "**风险评分**: -- | **状态**: <span style='color:gray'>等待输入</span>",
            {},
            {},
            "",
        )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/query",
                json={"query": query.strip(), "kb_id": kb_id.strip(), "top_k": 5, "generate_answer": True},
                timeout=120.0,
            )
            # 检查 HTTP 状态码
            if resp.status_code != 200:
                error_detail = resp.text[:500]
                return (
                    f"❌ 后端错误 (HTTP {resp.status_code}):\n{error_detail}",
                    "**风险评分**: -- | **状态**: <span style='color:red'>请求失败</span>",
                    {},
                    {},
                    "",
                )
            result = resp.json()
    except httpx.ConnectError:
        return (
            "❌ 无法连接后端服务。请确认:\n1. FastAPI 已启动 (python -m src.api.main)\n2. 端口 8000 未被占用",
            "**风险评分**: -- | **状态**: <span style='color:red'>连接失败</span>",
            {},
            {},
            "",
        )
    except Exception as e:
        return (
            f"❌ 请求异常: {type(e).__name__}: {str(e)}",
            "**风险评分**: -- | **状态**: <span style='color:red'>异常</span>",
            {},
            {},
            "",
        )

    # 颜色与状态根据 risk_level 判定（与后端一致）
    risk_level = result.get("risk_level", "safe")
    risk_color = (
        "green"
        if risk_level == "safe"
        else "red"
        if risk_level == "danger"
        else "orange"
    )
    status = "安全" if risk_level == "safe" else "危险" if risk_level == "danger" else "警告"

    # Bug 修复: answer 可能为 null，用 or 而非 .get default
    answer = result.get("answer") or "[已阻断]"
    blocked_display = ""
    if result.get("blocked_answer"):
        blocked_display = f"\n\n⚠️ **模型原本想回答**：{result['blocked_answer']}\n→ 已被 RAGShield 拦截"

    # warning 时显示系统提示
    warning_msg = result.get("warning_message") or ""
    if risk_level == "warning" and not warning_msg:
        warning_msg = "⚠️ 本回答可能包含未核实的信息，请谨慎使用。"

    # 安全获取各层数据（防御性编程）
    layer1 = result.get("layer1") or {}
    layer2 = result.get("layer2") or {}
    layer3 = result.get("layer3") or {}

    layer_details = {
        "Layer1 知识库层": (
            f"评分: {layer1.get('risk_score', 0):.2f} | "
            f"耗时: {layer1.get('latency_ms', 0)}ms | {layer1.get('reason', 'N/A')}"
        ),
        "Layer2 检索层": (
            f"评分: {layer2.get('risk_score', 0):.2f} | "
            f"耗时: {layer2.get('latency_ms', 0)}ms | {layer2.get('reason', 'N/A')}"
        ),
        "Layer3 生成层": (
            f"评分: {layer3.get('risk_score', 0):.2f} | "
            f"耗时: {layer3.get('latency_ms', 0)}ms | {layer3.get('reason', 'N/A')}"
        ),
    }

    return (
        answer + blocked_display,
        f"**风险评分**: {result.get('final_risk_score', 0):.2f} | **状态**: <span style='color:{risk_color}'>{status}</span>",
        result.get("fusion", {}),
        layer_details,
        warning_msg,
    )


with gr.Blocks(title="RAGShield 防御演示") as demo:
    gr.Markdown("# RAGShield 知识库安全检测系统")
    gr.Markdown("### 三层全链路纵深防御演示")
    gr.Markdown(
        "**提示**: 知识库 `demo_safe`（100篇正常文档）用于演示安全通过；"
        "`demo_attack`（100正常+25篇攻击）用于演示检测拦截。"
    )

    with gr.Row():
        with gr.Column(scale=1):
            query_input = gr.Textbox(
                label="输入查询",
                placeholder="例如：公司密码策略是什么",
            )
            # Bug 修复: 默认值改为实际存在的知识库
            kb_input = gr.Textbox(label="知识库 ID", value="demo_safe")
            submit_btn = gr.Button("提交检测", variant="primary")

            with gr.Accordion("快速 Demo", open=False):
                gr.Markdown(
                    """
                    | Demo | 查询 | 知识库 | 预期 |
                    |------|------|--------|------|
                    | 1 绿色通过 | 公司年假有多少天？ | demo_safe | 🟢 Safe |
                    | 2 黄色警告 | 公司年假有多少天？ | demo_attack | 🟡 Warning |
                    | 3 红色阻断 | API密钥是什么？ | demo_attack | 🔴 Block |
                    """
                )

        with gr.Column(scale=2):
            answer_output = gr.Markdown(label="生成结果")
            risk_display = gr.Markdown(label="风险状态")
            fusion_json = gr.JSON(label="融合结果")
            layer_details = gr.JSON(label="三层检测详情")
            # Bug 修复: 改为可见，warning 消息独立显示
            warning_box = gr.Textbox(label="系统提示", visible=True)

    submit_btn.click(
        on_query_submit,
        inputs=[query_input, kb_input],
        outputs=[answer_output, risk_display, fusion_json, layer_details, warning_box],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
