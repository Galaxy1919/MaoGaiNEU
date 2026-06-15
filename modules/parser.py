import re
import json
import sys
import argparse


def normalize_text(text):
    """全角字母/数字/标点转半角"""
    result = []
    for char in text:
        code = ord(char)
        if 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        elif code == 0x3000:
            result.append(' ')
        else:
            result.append(char)
    return ''.join(result)


def parse_questions(text):
    """解析完整题库文本，返回题目列表"""
    text = normalize_text(text)

    questions = []
    chapter_pattern = r'第[一二三四五六七八九十百千\d]+章\s*(.+)'

    current_chapter = 0
    current_chapter_name = ""
    current_type = "single"
    global_id = 0

    lines = text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # 检测章节标题
        chapter_match = re.match(chapter_pattern, line)
        if chapter_match:
            current_chapter += 1
            current_chapter_name = chapter_match.group(1).strip()
            i += 1
            continue

        # 检测题型切换
        if re.search(r'单项选择|单选', line):
            current_type = "single"
            i += 1
            continue
        if re.search(r'多项选择|多选', line):
            current_type = "multi"
            i += 1
            continue
        if re.match(r'^[一二三四五六七八九十]+[、.．]\s*\S+题', line):
            i += 1
            continue

        # 检测题目
        question_match = re.match(r'^(\d+)[、.．]\s*(.+)', line)
        if question_match:
            global_id += 1
            q_text = question_match.group(2).strip()

            # 题干可能跨多行
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if not next_line:
                    i += 1
                    continue
                # 选项行
                if re.match(r'^[A-Z][、.．\u4e00-\u9fff《(（]', next_line):
                    break
                if re.match(r'^\d+[、.．]', next_line):
                    break
                if re.match(chapter_pattern, next_line):
                    break
                if re.search(r'[单多]项选择|[单多]选', next_line):
                    break
                q_text += next_line
                i += 1

            # 提取答案 - 支持字母间有空格
            answer_match = re.search(r'[（(]\s*([A-Za-z](?:\s*[A-Za-z])*)\s*[）)]', q_text)
            answer = []
            if answer_match:
                answer_str = answer_match.group(1).upper()
                answer = [ch for ch in answer_str if ch.isalpha()]
                q_text = re.sub(r'[（(]\s*[A-Za-z](?:\s*[A-Za-z])*\s*[）)]', '(    )', q_text)

            q_text = q_text.rstrip('。.．')

            # 读取选项
            options = {}
            while i < len(lines):
                opt_line = lines[i].strip()
                if not opt_line:
                    i += 1
                    continue

                # 是否包含选项标记
                has_option = bool(re.search(r'[A-Z][、.．]', opt_line)) or \
                             bool(re.match(r'^[A-Z][\u4e00-\u9fff《(（]', opt_line))

                if not has_option:
                    break
                if re.match(r'^\d+[、.．]', opt_line):
                    break
                if re.match(chapter_pattern, opt_line):
                    break
                if re.search(r'[单多]项选择|[单多]选', opt_line):
                    break

                # 解析本行选项
                line_options = {}
                opt_markers = list(re.finditer(r'([A-Z])(?=[、.．\u4e00-\u9fff《(（])', opt_line))

                if opt_markers:
                    for idx, m in enumerate(opt_markers):
                        key = m.group(1)
                        val_start = m.end()
                        # 跳过分隔符
                        if val_start < len(opt_line) and opt_line[val_start] in '、.．':
                            val_start += 1
                        # 结束位置
                        if idx + 1 < len(opt_markers):
                            val_end = opt_markers[idx + 1].start()
                        else:
                            val_end = len(opt_line)
                        value = opt_line[val_start:val_end].strip()
                        if value:
                            line_options[key] = value

                options.update(line_options)
                i += 1

                # 选项续行
                while i < len(lines):
                    next_l = lines[i].strip()
                    if not next_l:
                        break
                    if re.search(r'[A-Z][、.．]', next_l) or re.match(r'^[A-Z][\u4e00-\u9fff《(（]', next_l):
                        break
                    if re.match(r'^\d+[、.．]', next_l):
                        break
                    if re.match(chapter_pattern, next_l):
                        break
                    if re.search(r'[单多]项选择|[单多]选', next_l):
                        break
                    # 追加到最后一个选项
                    if line_options:
                        last_key = list(line_options.keys())[-1]
                        options[last_key] = options[last_key] + next_l
                    i += 1

            # 题型判定
            q_type = current_type
            if len(answer) > 1:
                q_type = "multi"

            questions.append({
                "id": global_id,
                "chapter": current_chapter,
                "chapterName": current_chapter_name,
                "type": q_type,
                "question": q_text,
                "options": options,
                "answer": answer
            })
        else:
            i += 1

    return questions


def main():
    parser = argparse.ArgumentParser(description='题库文本转JSON解析器')
    parser.add_argument('input', help='输入文本文件路径')
    parser.add_argument('-o', '--output', default='questions.json', help='输出JSON文件路径')
    parser.add_argument('--indent', type=int, default=2, help='JSON缩进空格数')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')

    args = parser.parse_args()

    content = None
    for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']:
        try:
            with open(args.input, 'r', encoding=encoding) as f:
                content = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if content is None:
        print("错误：无法读取文件，请检查文件编码", file=sys.stderr)
        sys.exit(1)

    questions = parse_questions(content)

    if not questions:
        print("警告：未解析到任何题目，请检查文本格式", file=sys.stderr)
        sys.exit(1)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=args.indent)

    print(f"成功解析 {len(questions)} 道题目 -> {args.output}")

    if args.stats:
        chapters = {}
        single_count = 0
        multi_count = 0
        no_answer = 0

        for q in questions:
            ch = q['chapterName']
            chapters[ch] = chapters.get(ch, 0) + 1
            if q['type'] == 'single':
                single_count += 1
            else:
                multi_count += 1
            if not q['answer']:
                no_answer += 1

        print(f"\n统计信息：")
        print(f"  总题数：{len(questions)}")
        print(f"  单选题：{single_count}")
        print(f"  多选题：{multi_count}")
        if no_answer:
            print(f"  未提取到答案：{no_answer} 题")
        print(f"\n  各章节：")
        for ch_name, count in chapters.items():
            print(f"  - {ch_name}：{count} 题")


if __name__ == '__main__':
    main()