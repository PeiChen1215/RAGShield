"""
RAGShield V2 批量评测脚本
读取测试用例文件，批量调用API进行评测
"""
import json
import re
import sys
import time
import requests
from collections import defaultdict

API_URL = "http://localhost:8000/api/v2/query/detect"


def parse_test_cases(filepath):
    """解析测试用例文件，返回 (test_id, query, category) 列表"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    tests = []
    for line in lines:
        line = line.rstrip('\n')
        m = re.match(r'^([A-G]-\d+)\s+\[[^\]]+\]\s+(.+)', line)
        if m:
            tid = m.group(1)
            query = m.group(2).strip()
            cat = tid[0]
            tests.append((tid, query, cat))
    return tests


def run_test(query, timeout=120):
    """调用API执行单条测试"""
    try:
        resp = requests.post(API_URL, json={"query": query}, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"error": str(e)}


def classify_result(result):
    """根据API返回结果分类"""
    if "error" in result:
        return "ERROR"
    
    final_action = result.get("final_action", "UNKNOWN")
    if final_action == "block":
        return "BLOCK"
    elif final_action == "review":
        return "REVIEW"
    elif final_action == "pass":
        return "PASS"
    else:
        return "UNKNOWN"


def run_evaluation(tests, delay=2):
    """批量运行评测"""
    results = []
    
    for i, (tid, query, cat) in enumerate(tests):
        print(f"\n[{i+1}/{len(tests)}] {tid} ({cat}类)")
        print(f"  Query: {query[:80]}...")
        
        result = run_test(query)
        action = classify_result(result)
        
        # 提取关键信息
        layer0 = result.get("layer0_scan", {})
        layer2 = result.get("layer2_analysis", {})
        fusion = result.get("fusion_result", {})
        
        l0_risk = layer0.get("overall_risk", 0) if isinstance(layer0, dict) else 0
        l2_risky = len(layer2.get("risky_docs", [])) if isinstance(layer2, dict) else 0
        fusion_score = fusion.get("final_score", 0) if isinstance(fusion, dict) else 0
        
        print(f"  Result: {action} | L0={l0_risk:.2f} L2risky={l2_risky} Fusion={fusion_score:.2f}")
        
        results.append({
            "tid": tid,
            "query": query,
            "category": cat,
            "action": action,
            "l0_risk": l0_risk,
            "l2_risky": l2_risky,
            "fusion_score": fusion_score,
            "raw": result
        })
        
        if delay > 0 and i < len(tests) - 1:
            time.sleep(delay)
    
    return results


def compute_metrics(results):
    """计算评测指标"""
    # 按分类统计
    by_cat = defaultdict(lambda: {"total": 0, "block": 0, "review": 0, "pass": 0, "error": 0})
    
    for r in results:
        cat = r["category"]
        by_cat[cat]["total"] += 1
        by_cat[cat][r["action"].lower()] += 1
    
    # 攻击查询 = B + C + D
    attack_block = by_cat["B"]["block"] + by_cat["C"]["block"] + by_cat["D"]["block"]
    attack_review = by_cat["B"]["review"] + by_cat["C"]["review"] + by_cat["D"]["review"]
    attack_total = by_cat["B"]["total"] + by_cat["C"]["total"] + by_cat["D"]["total"]
    
    # 正常查询 = A + E
    normal_block = by_cat["A"]["block"] + by_cat["E"]["block"]
    normal_review = by_cat["A"]["review"] + by_cat["E"]["review"]
    normal_total = by_cat["A"]["total"] + by_cat["E"]["total"]
    
    # 指标
    bdr = attack_block / attack_total if attack_total > 0 else 0
    fpr = (normal_block + normal_review) / normal_total if normal_total > 0 else 0
    
    print("\n" + "="*60)
    print("评测结果汇总")
    print("="*60)
    for cat in ['A','B','C','D','E','F','G']:
        if cat in by_cat:
            s = by_cat[cat]
            print(f"{cat}类: 总计={s['total']} BLOCK={s['block']} REVIEW={s['review']} PASS={s['pass']} ERROR={s['error']}")
    
    print("-"*60)
    print(f"攻击查询(B+C+D): 总计={attack_total} BLOCK={attack_block} REVIEW={attack_review}")
    print(f"  BDR (阻断检测率) = {bdr*100:.1f}%")
    print(f"正常查询(A+E): 总计={normal_total} BLOCK={normal_block} REVIEW={normal_review}")
    print(f"  FPR (误报率) = {fpr*100:.1f}%")
    print("="*60)
    
    return {"bdr": bdr, "fpr": fpr, "by_cat": dict(by_cat)}


def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_evaluate.py <test_cases_file> [limit]")
        sys.exit(1)
    
    test_file = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    print(f"加载测试用例: {test_file}")
    tests = parse_test_cases(test_file)
    print(f"共加载 {len(tests)} 条测试用例")
    
    if limit:
        tests = tests[:limit]
        print(f"限制运行前 {limit} 条")
    
    # 检查API可用性
    print(f"\n检查API: {API_URL}")
    try:
        resp = requests.get(API_URL.replace("/detect", "") + "/health", timeout=5)
        print(f"API状态: {resp.status_code}")
    except Exception as e:
        print(f"警告: API可能未启动 - {e}")
        print("请确保后端服务已启动: cd v2 && python -m uvicorn api:app --port 8000")
        return
    
    # 运行评测
    results = run_evaluation(tests)
    
    # 计算指标
    metrics = compute_metrics(results)
    
    # 保存结果
    output = {
        "metrics": metrics,
        "results": [{k: v for k, v in r.items() if k != "raw"} for r in results]
    }
    
    output_file = f"results/eval_{time.strftime('%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存至: {output_file}")


if __name__ == "__main__":
    main()
