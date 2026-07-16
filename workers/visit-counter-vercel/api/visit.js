const { kv } = require('@vercel/kv');

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { date, visitorId, ts } = req.body || {};
    const d = date || new Date().toISOString().slice(0, 10);
    const vid = visitorId || 'anonymous';

    // 当天计数
    const dayKey = `day:${d}`;
    const current = parseInt(await kv.get(dayKey) || '0', 10);

    // 检查同访客同天是否已记录
    const visitorDayKey = `visitor:${d}:${vid}`;
    const alreadyVisited = await kv.get(visitorDayKey);

    if (!alreadyVisited) {
      const next = current + 1;
      await kv.set(dayKey, next);
      // 24小时过期
      await kv.set(visitorDayKey, '1', { ex: 86400 });

      // 更新总计
      const total = parseInt(await kv.get('total') || '0', 10);
      await kv.set('total', total + 1);

      return res.status(200).json({ ok: true, count: next, date: d, isNew: true });
    }

    return res.status(200).json({ ok: true, count: current, date: d, isNew: false });
  } catch (e) {
    return res.status(500).json({ ok: false, error: e.message });
  }
};
