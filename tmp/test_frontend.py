import gradio as gr
orig_launch = gr.Blocks.launch

def patched_launch(self, server_name=None, server_port=None, **kwargs):
    return orig_launch(self, server_name="0.0.0.0", server_port=7861, **kwargs)

gr.Blocks.launch = patched_launch

exec(open('src/frontend/app.py').read())
