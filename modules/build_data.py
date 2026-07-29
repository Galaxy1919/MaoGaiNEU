"""
题库打包加密脚本
用法：python modules/build_data.py

作用：
1. 读取 data/questions.json 和 data/disputed.json
2. 用 XOR + Base64 加密后写入 data/bundle.dat.js
3. 前端 index.html 只加载 bundle.dat.js，无法通过 URL 直接看到题库明文

注意：加密密钥 CRYPT_KEY 必须与 index.html 里的 CRYPT_KEY 一致
"""

import json
import base64
from pathlib import Path

# 加密密钥（改这里，index.html 里同步改）
CRYPT_KEY = 'mg-neu-2026-vault-key-9x7k3jz'

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'


def xor_encrypt(text: str, key: str) -> str:
    """XOR 加密 + Base64 编码"""
    text_bytes = text.encode('utf-8')
    key_bytes = key.encode('utf-8')
    encrypted = bytearray()
    for i, b in enumerate(text_bytes):
        encrypted.append(b ^ key_bytes[i % len(key_bytes)])
    return base64.b64encode(bytes(encrypted)).decode('ascii')


def build():
    # 读取题库
    q_path = DATA_DIR / 'questions.json'
    if not q_path.exists():
        print(f'❌ 未找到 {q_path}')
        return

    with open(q_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    print(f'✅ 读取题库：{len(questions)} 题')

    # 读取疑似错题（可选）
    disputed = []
    d_path = DATA_DIR / 'disputed.json'
    if d_path.exists():
        with open(d_path, 'r', encoding='utf-8') as f:
            disputed = json.load(f)
        print(f'✅ 读取疑似错题：{len(disputed)} 个ID')

    # 打包
    bundle = {
        'questions': questions,
        'disputed': disputed,
        'version': 1,
    }
    plain_json = json.dumps(bundle, ensure_ascii=False, separators=(',', ':'))
    encrypted = xor_encrypt(plain_json, CRYPT_KEY)

    # 输出为 JS 文件（用 window 变量，绕过静态 JSON 请求）
    output = f"window.__MG_DATA__ = '{encrypted}';\n"

    out_path = DATA_DIR / 'bundle.dat.js'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f'✅ 已生成 {out_path}')
    print(f'   原文大小: {len(plain_json)} 字符')
    print(f'   密文大小: {len(encrypted)} 字符')
    print()
    print('⚠️  发布前请从 vercel/git 移除以下文件（不要部署明文题库）：')
    print(f'   - {DATA_DIR / "questions.json"}')
    print(f'   - {DATA_DIR / "disputed.json"}')


if __name__ == '__main__':
    build()
