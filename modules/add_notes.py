"""
毛概题库解析/笔记管理工具

用法:
  # 查看所有有解析的题目
  python modules/add_notes.py list

  # 查看第5题的解析
  python modules/add_notes.py show 5

  # 为第5题添加/修改解析
  python modules/add_notes.py edit 5

  # 搜索解析（支持关键词）
  python modules/add_notes.py search 马克思主义

  # 统计解析完成情况
  python modules/add_notes.py stats
"""

import json
import sys
import os
import tempfile
import subprocess

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                         'data', 'questions.json')


def load():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save(questions):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)


def cmd_list():
    questions = load()
    has = [q for q in questions if q.get('explanation')]
    print(f"题库共 {len(questions)} 题")
    print(f"已有解析: {len(has)} 题 ({len(has)/len(questions)*100:.1f}%)\n")
    for q in has:
        exp = q['explanation']
        preview = exp[:50] + '...' if len(exp) > 50 else exp
        print(f"  #{q['id']:>3d}  第{q['chapter']}章  {preview}")
    if not has:
        print("  (暂无解析，用 python modules/add_notes.py edit <id> 添加)")


def cmd_show(qid):
    questions = load()
    for q in questions:
        if q['id'] == qid:
            exp = q.get('explanation') or '(空)'
            print(f"#{q['id']} 第{q['chapter']}章 [{q['type']}]")
            print(f"题目: {q['question']}")
            print(f"答案: {', '.join(q['answer'])}")
            print(f"\n解析:\n{exp}")
            return
    print(f"未找到 #{qid}")


def cmd_edit(qid):
    questions = load()
    q = None
    for item in questions:
        if item['id'] == qid:
            q = item
            break
    if not q:
        print(f"未找到 #{qid}")
        sys.exit(1)

    old = q.get('explanation') or ''
    # 用临时文件编辑
    suffix = '.txt'
    if sys.platform == 'win32':
        editor = os.environ.get('EDITOR', 'notepad')
    else:
        editor = os.environ.get('EDITOR', 'vim')

    tmpfile = tempfile.NamedTemporaryFile(
        mode='w', suffix=suffix, delete=False, encoding='utf-8')
    tmpfile.write(f"# 题目 #{q['id']}: {q['question']}\n")
    tmpfile.write(f"# 答案: {', '.join(q['answer'])}\n")
    tmpfile.write(f"# 请在上面写解析，以 # 开头的行会被忽略\n")
    tmpfile.write(f"# {'='*40}\n")
    if old:
        tmpfile.write(old)
    tmpfile.close()

    # 打开编辑器
    try:
        subprocess.call([editor, tmpfile.name])
    except FileNotFoundError:
        # fallback 到记事本
        subprocess.call(['notepad', tmpfile.name])

    with open(tmpfile.name, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    os.unlink(tmpfile.name)

    new_text = '\n'.join(
        line for line in lines
        if not line.startswith('#')
    ).strip()

    if new_text:
        q['explanation'] = new_text
        save(questions)
        print(f"✅ #{qid} 解析已保存 ({len(new_text)} 字)")
    else:
        print("⚠️  未写入内容，解析未变更")


def cmd_search(keyword):
    questions = load()
    results = []
    for q in questions:
        exp = q.get('explanation') or ''
        if keyword.lower() in q['question'].lower() or keyword in exp:
            results.append(q)
    print(f"找到 {len(results)} 条结果:\n")
    for q in results[:20]:
        exp = q.get('explanation') or '(无解析)'
        preview = exp[:60] + '...' if len(exp) > 60 else exp
        print(f"  #{q['id']:>3d}  第{q['chapter']}章  {q['question'][:50]}")
        print(f"         解析: {preview}\n")


def cmd_stats():
    questions = load()
    total = len(questions)
    has = [q for q in questions if q.get('explanation')]
    by_chapter = {}
    for q in questions:
        ch = f"第{q['chapter']}章"
        if ch not in by_chapter:
            by_chapter[ch] = {'total': 0, 'done': 0}
        by_chapter[ch]['total'] += 1
        if q.get('explanation'):
            by_chapter[ch]['done'] += 1

    print(f"{'='*40}")
    print(f"  毛概题库 — 解析完成情况")
    print(f"{'='*40}")
    print(f"  总题数:    {total}")
    print(f"  有解析:    {len(has)} ({len(has)/total*100:.1f}%)")
    print(f"  待完成:    {total - len(has)}")
    print(f"\n  各章节:")
    for ch, data in by_chapter.items():
        pct = data['done'] / data['total'] * 100 if data['total'] > 0 else 0
        bar_len = 20
        filled = int(bar_len * pct / 100)
        bar = '█' * filled + '░' * (bar_len - filled)
        print(f"    {ch:8s} {bar} {data['done']:>3d}/{data['total']:<3d} ({pct:.0f}%)")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == 'list':
        cmd_list()
    elif command == 'show' and len(sys.argv) > 2:
        cmd_show(int(sys.argv[2]))
    elif command == 'edit' and len(sys.argv) > 2:
        cmd_edit(int(sys.argv[2]))
    elif command == 'search' and len(sys.argv) > 2:
        cmd_search(' '.join(sys.argv[2:]))
    elif command == 'stats':
        cmd_stats()
    else:
        print(__doc__)
