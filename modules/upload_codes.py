"""
把兑换码批量上传到 Upstash Redis
用法：
    # 先设置环境变量
    set UPSTASH_REDIS_REST_URL=https://xxxxx.upstash.io
    set UPSTASH_REDIS_REST_TOKEN=AXXXAA...

    # 然后运行（读取 data/codes-YYYYMMDD-HHMMSS.txt）
    python modules/upload_codes.py data/codes-20260729-143627.txt

作用：把 codes 文件中的明文兑换码全部标记为 "unused" 状态存入 Redis
存储格式：
    key:   code:MG-XXXX-YYYY
    value: {"status":"unused"}
"""

import os
import sys
import json
import re
import urllib.request
from pathlib import Path

UPSTASH_URL = os.environ.get('UPSTASH_REDIS_REST_URL', '').rstrip('/')
UPSTASH_TOKEN = os.environ.get('UPSTASH_REDIS_REST_TOKEN', '')


def redis_command(command_array):
    """调用 Upstash REST API 执行 Redis 命令"""
    req = urllib.request.Request(
        UPSTASH_URL,
        data=json.dumps(command_array).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {UPSTASH_TOKEN}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))


def parse_codes(file_path):
    """从生成的 codes-*.txt 里解析出明文兑换码列表"""
    codes = []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 只取"第一部分"的明文列表
    section = re.search(
        r'【第一部分】.*?\n=+\n(.*?)\n\n',
        content, re.DOTALL,
    )
    if not section:
        # 兜底：直接匹配 MG-XXXX-XXXX 格式
        codes = re.findall(r'\b[A-Z]{2,4}-[A-Z0-9]{4}-[A-Z0-9]{4}\b', content)
    else:
        for line in section.group(1).splitlines():
            line = line.strip()
            if line and re.match(r'^[A-Z]{2,4}-[A-Z0-9]{4}-[A-Z0-9]{4}$', line):
                codes.append(line)

    return codes


def main():
    if len(sys.argv) < 2:
        print('❌ 用法: python modules/upload_codes.py <codes文件路径>')
        sys.exit(1)

    if not UPSTASH_URL or not UPSTASH_TOKEN:
        print('❌ 请先设置环境变量 UPSTASH_REDIS_REST_URL 和 UPSTASH_REDIS_REST_TOKEN')
        print('   Windows CMD:')
        print('     set UPSTASH_REDIS_REST_URL=https://xxx.upstash.io')
        print('     set UPSTASH_REDIS_REST_TOKEN=AXXX...')
        print('   PowerShell:')
        print('     $env:UPSTASH_REDIS_REST_URL="https://xxx.upstash.io"')
        print('     $env:UPSTASH_REDIS_REST_TOKEN="AXXX..."')
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f'❌ 文件不存在: {file_path}')
        sys.exit(1)

    codes = parse_codes(file_path)
    if not codes:
        print(f'❌ 未从 {file_path} 中解析出任何兑换码')
        sys.exit(1)

    print(f'📋 从 {file_path.name} 解析出 {len(codes)} 个兑换码')
    print(f'   前 3 个: {codes[:3]}')

    # 试连接
    try:
        pong = redis_command(['PING'])
        print(f'✅ Redis 连接成功: {pong}')
    except Exception as e:
        print(f'❌ Redis 连接失败: {e}')
        sys.exit(1)

    # 批量上传
    success, skipped, failed = 0, 0, 0
    for i, code in enumerate(codes, 1):
        key = f'code:{code}'
        value = json.dumps({'status': 'unused'})
        try:
            # SET NX：只在不存在时创建，避免覆盖已使用的码
            result = redis_command(['SET', key, value, 'NX'])
            if result.get('result') == 'OK':
                success += 1
            else:
                skipped += 1
            if i % 10 == 0 or i == len(codes):
                print(f'   进度 {i}/{len(codes)} (新增 {success} · 跳过 {skipped} · 失败 {failed})')
        except Exception as e:
            failed += 1
            print(f'   ⚠️  {code} 失败: {e}')

    print()
    print('✅ 上传完成')
    print(f'   新增: {success} 个')
    print(f'   已存在跳过: {skipped} 个（可能之前已上传或已被使用）')
    print(f'   失败: {failed} 个')
    print()
    print('📤 下一步：把明文列表复制到爱发电"方案 → 附赠 → 兑换码"')


if __name__ == '__main__':
    main()
