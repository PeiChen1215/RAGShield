"""
Unicode 规范化模块 (Layer0/1/3 共用)
提供文本预处理、零宽字符去除、控制字符清理等功能。
"""
import unicodedata
import re


ZERO_WIDTH_CHARS = "\u200b\u200c\u200d\ufeff\u2060\u180e\u2061\u2062\u2063\u2064"


def normalize_text(text: str) -> str:
    """
    标准化文本：
    1. NFKC 规范化（合并兼容字符，全角→半角）
    2. 去除零宽字符（绕过字符串匹配的隐藏字符）
    3. 去除控制字符（保留换行、制表符）
    4. 去除多余空白
    """
    if not text:
        return ""
    
    # 1. NFKC 规范化
    text = unicodedata.normalize("NFKC", text)
    
    # 2. 去除零宽字符
    for c in ZERO_WIDTH_CHARS:
        text = text.replace(c, "")
    
    # 3. 去除控制字符（保留 \n, \t, \r）
    text = "".join(c for c in text if ord(c) >= 32 or c in "\n\t\r")
    
    # 4. 去除多余空白
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    
    return text


def remove_invisible_chars(text: str) -> str:
    """去除所有不可见字符（包括零宽、控制字符）"""
    return "".join(c for c in text if c.isprintable() or c in "\n\t\r")


def detect_obfuscation(text: str) -> dict:
    """
    检测文本是否使用了混淆手段。
    返回检测到的混淆类型和置信度。
    """
    results = {
        "has_zero_width": False,
        "has_homoglyphs": False,
        "has_mixed_scripts": False,
        "has_excessive_whitespace": False,
        "risk_score": 0.0,
    }
    
    # 零宽字符
    for c in ZERO_WIDTH_CHARS:
        if c in text:
            results["has_zero_width"] = True
            results["risk_score"] += 0.3
            break
    
    # 同形异义字（简单检测：拉丁字母和希腊字母混合）
    greek_lookalikes = "ΑΒΕΖΗΙΚΜΝΟΡΤΧ"  # 希腊字母看起来像拉丁字母
    latin_counterparts = "ABEZHIKMNOPTX"
    for g, l in zip(greek_lookalikes, latin_counterparts):
        if g in text:
            results["has_homoglyphs"] = True
            results["risk_score"] += 0.2
            break
    
    # 混合脚本
    scripts = set()
    for ch in text:
        if ch.isalpha():
            try:
                scripts.add(unicodedata.name(ch).split()[0])
            except:
                pass
    if len(scripts) > 2:
        results["has_mixed_scripts"] = True
        results["risk_score"] += 0.15
    
    # 异常空白
    if re.search(r"\s{5,}", text) or text.count("\n") > text.count("。") * 3:
        results["has_excessive_whitespace"] = True
        results["risk_score"] += 0.1
    
    results["risk_score"] = min(results["risk_score"], 1.0)
    return results


def test_unicode_norm():
    """自测"""
    # 测试零宽字符去除
    t1 = "密\u200b码\u200c是\u200d123456"
    assert normalize_text(t1) == "密码是123456", f"零宽字符去除失败: {normalize_text(t1)}"
    
    # 测试NFKC（全角转半角）
    t2 = "密码是１２３"
    assert normalize_text(t2) == "密码是123", f"NFKC失败: {normalize_text(t2)}"
    
    # 测试控制字符
    t3 = "hello\x00\x01world"
    assert normalize_text(t3) == "helloworld", f"控制字符去除失败: {normalize_text(t3)}"
    
    # 测试混淆检测
    t4 = "密\u200b码"
    obs = detect_obfuscation(t4)
    assert obs["has_zero_width"] == True
    assert obs["risk_score"] > 0
    
    print("[unicode_norm] 所有自测通过")


if __name__ == "__main__":
    test_unicode_norm()
