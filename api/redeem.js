// Vercel Serverless Function: 兑换码激活接口
// POST /api/redeem  { code: "MG-XXXX-YYYY" }
// 返回: { ok: true, token, expiresAt } 或 { ok: false, error }

const crypto = require('crypto');

const UPSTASH_URL = process.env.UPSTASH_REDIS_REST_URL;
const UPSTASH_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN;
const SIGN_SECRET = process.env.SIGN_SECRET;

// 会员时长（毫秒），默认 30 天
const MEMBER_DURATION_MS = 30 * 24 * 60 * 60 * 1000;

// 调用 Upstash Redis REST API
async function redis(command) {
    const resp = await fetch(UPSTASH_URL, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${UPSTASH_TOKEN}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(command),
    });
    if (!resp.ok) throw new Error(`Upstash ${resp.status}`);
    const data = await resp.json();
    return data.result;
}

// 生成 HMAC 签名的 token（简易 JWT-like）
function signToken(payload) {
    const body = Buffer.from(JSON.stringify(payload)).toString('base64url');
    const sig = crypto.createHmac('sha256', SIGN_SECRET).update(body).digest('base64url');
    return `${body}.${sig}`;
}

module.exports = async (req, res) => {
    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') { res.status(200).end(); return; }
    if (req.method !== 'POST') {
        return res.status(405).json({ ok: false, error: 'Method not allowed' });
    }

    if (!UPSTASH_URL || !UPSTASH_TOKEN || !SIGN_SECRET) {
        return res.status(500).json({ ok: false, error: '服务端配置缺失' });
    }

    try {
        const { code } = req.body || {};
        if (!code || typeof code !== 'string' || code.length > 64) {
            return res.status(400).json({ ok: false, error: '兑换码格式无效' });
        }

        const normalized = code.trim();
        const codeKey = `code:${normalized}`;

        // 查询兑换码状态
        // 存储格式：{ status: 'unused' | 'used', usedAt?, usedBy? }
        const raw = await redis(['GET', codeKey]);
        if (!raw) {
            return res.status(404).json({ ok: false, error: '兑换码不存在' });
        }

        let record;
        try { record = JSON.parse(raw); } catch { record = { status: 'unused' }; }

        if (record.status === 'used') {
            return res.status(409).json({
                ok: false,
                error: '此兑换码已被使用',
                usedAt: record.usedAt || 0,
            });
        }

        // 生成用户 ID（匿名，用于区分不同激活者）
        const userId = crypto.randomBytes(8).toString('hex');
        const now = Date.now();
        const expiresAt = now + MEMBER_DURATION_MS;

        // 原子操作：标记为已用
        // 用 SET NX 保证并发安全（两个人同时兑换同一个码只能成功一个）
        const newRecord = {
            status: 'used',
            usedAt: now,
            usedBy: userId,
            expiresAt,
        };
        const setResult = await redis([
            'SET', codeKey, JSON.stringify(newRecord),
            'XX',  // 只在 key 存在时才 set（防止 code 被并发删除）
        ]);
        if (setResult !== 'OK') {
            return res.status(409).json({ ok: false, error: '激活失败，请重试' });
        }

        // 再存一份用户会员记录（用于 verify 时快速查询）
        await redis([
            'SET', `member:${userId}`, JSON.stringify({
                code: normalized,
                activatedAt: now,
                expiresAt,
            }),
            'EX', String(Math.ceil(MEMBER_DURATION_MS / 1000) + 86400),  // 多留 1 天用于查询
        ]);

        // 签发 token
        const token = signToken({ uid: userId, exp: expiresAt, iat: now });

        return res.status(200).json({
            ok: true,
            token,
            expiresAt,
            userId,
        });
    } catch (e) {
        console.error('redeem error:', e);
        return res.status(500).json({ ok: false, error: '服务器错误：' + e.message });
    }
};
