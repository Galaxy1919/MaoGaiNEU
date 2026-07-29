// Vercel Serverless Function: 会员 token 验证接口
// POST /api/verify  { token: "xxx.yyy" }
// 返回: { ok: true, expiresAt, remainDays } 或 { ok: false, error }

const crypto = require('crypto');

const UPSTASH_URL = process.env.UPSTASH_REDIS_REST_URL;
const UPSTASH_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN;
const SIGN_SECRET = process.env.SIGN_SECRET;

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

function verifyToken(token) {
    if (!token || typeof token !== 'string' || !token.includes('.')) return null;
    const [body, sig] = token.split('.');
    const expected = crypto.createHmac('sha256', SIGN_SECRET).update(body).digest('base64url');
    if (sig !== expected) return null;
    try {
        return JSON.parse(Buffer.from(body, 'base64url').toString('utf-8'));
    } catch {
        return null;
    }
}

module.exports = async (req, res) => {
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
        const { token } = req.body || {};
        const payload = verifyToken(token);
        if (!payload) {
            return res.status(401).json({ ok: false, error: 'token 无效' });
        }

        const now = Date.now();
        if (!payload.exp || payload.exp < now) {
            return res.status(401).json({ ok: false, error: '会员已过期' });
        }

        // 查 Redis 确认这个 uid 仍然有效（可选强校验，方便你后台封号）
        const memberRaw = await redis(['GET', `member:${payload.uid}`]);
        if (!memberRaw) {
            return res.status(401).json({ ok: false, error: '会员记录已失效' });
        }

        let member;
        try { member = JSON.parse(memberRaw); } catch { member = null; }
        if (!member || member.expiresAt < now) {
            return res.status(401).json({ ok: false, error: '会员已过期' });
        }

        const remainDays = Math.max(0, Math.ceil((member.expiresAt - now) / 86400000));

        return res.status(200).json({
            ok: true,
            expiresAt: member.expiresAt,
            activatedAt: member.activatedAt,
            remainDays,
        });
    } catch (e) {
        console.error('verify error:', e);
        return res.status(500).json({ ok: false, error: '服务器错误：' + e.message });
    }
};
