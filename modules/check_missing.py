# 保存为 modules/check_missing.py

import json

data = json.load(open('data/questions.json', 'r', encoding='utf-8'))

# 1. 找出未提取到答案的题
print("=" * 50)
print("未提取到答案的题目：")
print("=" * 50)
for q in data:
    if not q['answer']:
        print(f"  第{q['chapter']}章 第{q['id']}题: {q['question'][:50]}")

# 2. 各章题目数量
print("\n" + "=" * 50)
print("各章题目数量：")
print("=" * 50)
chapter_counts = {}
for q in data:
    ch = q['chapter']
    chapter_counts[ch] = chapter_counts.get(ch, 0) + 1

for ch, count in sorted(chapter_counts.items()):
    status = "  ⚠️ 缺题" if count < 80 else "  ✅"
    print(f"  第{ch}章: {count}题 {status}")