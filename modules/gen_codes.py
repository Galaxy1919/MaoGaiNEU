"""
兑换码批量生成脚本
用法：
    python modules/gen_codes.py           # 生成 20 个码
    python modules/gen_codes.py 50        # 生成 50 个码
    python modules/gen_codes.py 50 VIP    # 生成 50 个 VIP 前缀的码

作用：
1. 生成随机兑换码明文
2. 用 base64 编码后的密文（用于填 VALID_CODES 数组）
3. 输出到 data/codes.txt（本地保存，不要传到 git）

发码流程：
1. 运行本脚本生成 codes.txt
2. 复制"密文"列到 index.html 的 VALID_CODES 数组
3. 复制"明文"列上传到爱发电后台"附赠"，让系统自动发码给付款用户
"""

import sys
import secrets
import string
import base64
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'


def random_code(prefix='MG'):
    """生成形如 MG-A8K3-P9X7 的兑换码"""
    chars = string.ascii_uppercase + string.digits
    seg1 = ''.join(secrets.choice(chars) for _ in range(4))
    seg2 = ''.join(secrets.choice(chars) for _ in range(4))
    return f'{prefix}-{seg1}-{seg2}'


def encode_code(plain):
    return base64.b64encode(plain.encode('utf-8')).decode('ascii')


def main():
    count = 20
    prefix = 'MG'

    if len(sys.argv) >= 2:
        count = int(sys.argv[1])
    if len(sys.argv) >= 3:
        prefix = sys.argv[2]

    codes = set()
    while len(codes) < count:
        codes.add(random_code(prefix))
    codes = sorted(codes)

    # 生成输出内容
    lines_plain = []
    lines_encoded = []
    lines_pretty = []
    for c in codes:
        e = encode_code(c)
        lines_plain.append(c)
        lines_encoded.append(f"        '{e}',  // {c}")
        lines_pretty.append(f'{c}\t{e}')

    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    out_path = DATA_DIR / f'codes-{ts}.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f'# 兑换码 - 生成时间 {ts}\n')
        f.write(f'# 共 {count} 个，前缀 {prefix}\n\n')

        f.write('=' * 60 + '\n')
        f.write('【第一部分】上传到爱发电的兑换码明文（一行一个）\n')
        f.write('=' * 60 + '\n')
        f.write('\n'.join(lines_plain))
        f.write('\n\n')

        f.write('=' * 60 + '\n')
        f.write('【第二部分】复制以下内容到 index.html 的 VALID_CODES 数组\n')
        f.write('=' * 60 + '\n')
        f.write('\n'.join(lines_encoded))
        f.write('\n\n')

        f.write('=' * 60 + '\n')
        f.write('【第三部分】明文-密文 对照表（便于核对）\n')
        f.write('=' * 60 + '\n')
        f.write('明文\t\t密文\n')
        f.write('\n'.join(lines_pretty))
        f.write('\n')

    print(f'✅ 已生成 {count} 个兑换码')
    print(f'   文件位置: {out_path}')
    print()
    print('📋 前 3 个示例：')
    for c in codes[:3]:
        print(f'   {c}   →   {encode_code(c)}')
    print()
    print('⚠️  下一步：')
    print(f'   1. 打开 {out_path}')
    print('   2. 【第一部分】明文列表 → 上传到爱发电"附赠 → 兑换码"')
    print('   3. 【第二部分】密文列表 → 追加到 index.html 的 VALID_CODES 数组')
    print('   4. 重新部署到 Vercel')


if __name__ == '__main__':
    main()
