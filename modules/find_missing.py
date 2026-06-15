# 保存为 modules/find_missing.py

import re

# 读取原始文件
content = None
for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']:
    try:
        with open('data/questionBank.txt', 'r', encoding=encoding) as f:
            content = f.read()
        break
    except (UnicodeDecodeError, UnicodeError):
        continue

lines = content.split('\n')

current_chapter = 0
current_type = ""
chapter_pattern = r'第[一二三四五六七八九十百千\d]+章\s*(.+)'

# 找出所有看起来像题目但可能解析失败的行
problem_lines = []

for i, line in enumerate(lines):
    stripped = line.strip()

    if re.match(chapter_pattern, stripped):
        current_chapter += 1
        continue

    if re.search(r'单项选择|单选', stripped):
        current_type = "single"
        continue
    if re.search(r'多项选择|多选', stripped):
        current_type = "multi"
        continue

    # 检查缺题章节中的题目行
    if current_chapter in [3, 6, 7, 10, 11, 12]:
        # 看起来像题目但格式可能异常的行
        # 标准格式：数字、题干
        q_match = re.match(r'^(\d+)[、.．]\s*(.+)', stripped)
        if q_match:
            q_num = int(q_match.group(1))
            q_text = q_match.group(2)[:60]
            # 检查答案是否在括号中
            has_answer = bool(re.search(r'[（(]\s*[A-Za-z]+\s*[）)]', q_text))
            if not has_answer:
                # 往后看几行找答案
                context = lines[i:i + 8]
                problem_lines.append({
                    'chapter': current_chapter,
                    'line_num': i + 1,
                    'q_num': q_num,
                    'type': current_type,
                    'context': '\n'.join(l.strip() for l in context)
                })

# 输出缺题章节中没有括号答案的题目
print("=" * 60)
print("缺题章节中 答案格式可能异常 的题目：")
print("=" * 60)
for p in problem_lines[:30]:  # 只显示前30条
    print(f"\n第{p['chapter']}章 第{p['q_num']}题 (行{p['line_num']}, {p['type']}):")
    print(p['context'])
    print("-" * 40)

print(f"\n共找到 {len(problem_lines)} 条可疑题目")