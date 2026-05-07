"""
模块名: src/frontend/app.py
职责: Gradio 演示界面，纯 HTTP 调用 FastAPI，零业务逻辑。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import gradio as gr
import httpx

API_BASE = "http://localhost:8000/api/v1"


async def on_query_submit(query: str, kb_id: str = "default"):
    """Gradio 按钮回调——纯 HTTP 调用，零业务逻辑。

    Args:
        query: 用户查询。
        kb_id: 知识库 ID。

    Returns:
        格式化展示数据。
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/query",
            json={"query": query, "kb_id": kb_id, "top_k": 5, "generate_answer": True},
            timeout=60.0,
        )
        result = resp.json()

    risk_color = (
        "green"
        if result["is_safe"]
        else "red"
        if result["risk_level"] == "danger"
        else "orange"
    )
    status = "安全" if result["is_safe"] else "危险" if result["risk_level"] == "danger" else "警告"

    blocked_display = ""
    if result.get("blocked_answer"):
        blocked_display = f"\n\n⚠️ **模型原本想回答**：{result['blocked_answer']}\n→ 已被 RAGShield 拦截"

    return (
        result.get("answer", "[已阻断]") + blocked_display,
        f"**风险评分**: {result['final_risk_score']:.2f} | **状态**: <span style='color:{risk_color}'>{status}</span>",
        result.get("fusion"),
        {
            "Layer1 知识库层": f"评分: {result['layer1']['risk_score']:.2f} | 耗时: {result['layer1']['latency_ms']}ms | {result['layer1']['reason']}",
            "Layer2 检索层": f"评分: {result['layer2']['risk_score']:.2f} | 耗时: {result['layer2']['latency_ms']}ms | {result['layer2']['reason']}",
            "Layer3 生成层": f"评分: {result['layer3']['risk_score']:.2f} | 耗时: {result['layer3']['latency_ms']}ms | {result['layer3']['reason']}",
        },
        result.get("warning_message", ""),
    )


with gr.Blocks(title="RAGShield 防御演示") as demo:
    gr.Markdown("# RAGShield 知识库安全检测系统")
    gr.Markdown("### 三层全链路纵深防御演示")

    with gr.Row():
        with gr.Column(scale=1):
            query_input = gr.Textbox(label="输入查询", placeholder="例如：公司密码策略是什么")
            kb_input = gr.Textbox(label="知识库 ID", value="default")
            submit_btn = gr.Button("提交检测", variant="primary")

        with gr.Column(scale=2):
            answer_output = gr.Markdown(label="生成结果")
            risk_display = gr.Markdown(label="风险状态")
            fusion_json = gr.JSON(label="融合结果")
            layer_details = gr.JSON(label="三层检测详情")
            warning_box = gr.Textbox(label="系统提示", visible=False)

    submit_btn.click(
        on_query_submit,
        inputs=[query_input, kb_input],
        outputs=[answer_output, risk_display, fusion_json, layer_details, warning_box],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
