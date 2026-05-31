"""
v2/start_servers.py
一键启动 RAGShield V2 前后端服务
"""
import subprocess
import sys
import time
import os


def start_backend():
    """启动 FastAPI 后端"""
    print("[1/2] 启动 FastAPI 后端 (端口 8000)...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "v2.api.main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    # 等待后端就绪
    for _ in range(30):
        import socket
        if socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex(("127.0.0.1", 8000)) == 0:
            print("[OK] 后端已就绪: http://localhost:8000")
            print("[OK] API 文档: http://localhost:8000/docs")
            return proc
        time.sleep(0.5)
    print("[WARN] 后端启动超时，可能仍在加载中...")
    return proc


def start_frontend():
    """启动 Gradio 前端"""
    print("[2/2] 启动 Gradio 前端 (端口 7860)...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "v2.frontend.app"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    time.sleep(3)
    print("[OK] 前端已就绪: http://localhost:7860")
    return proc


def main():
    print("=" * 50)
    print("RAGShield V2 服务启动器")
    print("=" * 50)
    
    backend_proc = start_backend()
    frontend_proc = start_frontend()
    
    print("\n" + "=" * 50)
    print("所有服务已启动")
    print("- 前端界面: http://localhost:7860")
    print("- 后端 API: http://localhost:8000")
    print("- API 文档: http://localhost:8000/docs")
    print("- 健康检查: http://localhost:8000/health")
    print("=" * 50)
    print("按 Ctrl+C 停止所有服务\n")
    
    try:
        while True:
            # 轮询子进程输出，避免缓冲区满阻塞
            if backend_proc.poll() is not None:
                print("[ERR] 后端进程已退出")
                break
            if frontend_proc.poll() is not None:
                print("[ERR] 前端进程已退出")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[STOP] 收到中断信号，正在停止服务...")
    finally:
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait(timeout=5)
        frontend_proc.wait(timeout=5)
        print("[STOP] 所有服务已停止")


if __name__ == "__main__":
    main()
