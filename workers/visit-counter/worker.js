/**
 * 访问统计 Cloudflare Worker
 * 
 * 部署步骤（5分钟）：
 * 1. 注册 Cloudflare 账号（https://dash.cloudflare.com）
 * 2. 创建 KV Namespace：Workers & Pages → KV → Create namespace → 名称填 "VISITS"
 * 3. 创建 Worker：Workers & Pages → Create → Create Worker → 名称随意
 * 4. 将本文件完整内容粘贴到 Worker 编辑器中，保存部署
 * 5. 绑定 KV：Worker Settings → Variables → KV Namespace Bindings → 添加 VISITS_KV → VISITS
 * 6. 复制 Worker URL（如 https://visit-counter.xxx.workers.dev）
 * 7. 在看板代码中找到 VISIT_API_URL，填入该 URL
 * 
 * API 说明：
 *   POST /visit     — 记录一次访问 { date, visitorId, ts }
 *   GET  /visits    — 获取最近N天数据 ?days=14
 *   GET  /health    — 健康检查
 */

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS },
  });
}

function todayStr() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
}

function dateStrOffset(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
}

export default {
  async fetch(request, env) {
    const KV = env.VISITS_KV;
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS });
    }

    const url = new URL(request.url);

    // 健康检查
    if (url.pathname === '/health') {
      return json({ ok: true, time: new Date().toISOString() });
    }

    // 记录访问
    if (url.pathname === '/visit' && request.method === 'POST') {
      try {
        const body = await request.json();
        const date = body.date || todayStr();
        const visitorId = body.visitorId || 'anonymous';

        // 读取当天计数
        const dayKey = 'day:' + date;
        const current = parseInt(await KV.get(dayKey) || '0', 10);

        // 检查该访客今天是否已记录（去重）
        const visitorDayKey = 'visitor:' + date + ':' + visitorId;
        const alreadyVisited = await KV.get(visitorDayKey);

        if (!alreadyVisited) {
          // 新访客
          await KV.put(dayKey, String(current + 1));
          await KV.put(visitorDayKey, '1', { expirationTtl: 86400 }); // 24小时过期

          // 更新总计数
          const totalKey = 'total';
          const total = parseInt(await KV.get(totalKey) || '0', 10);
          await KV.put(totalKey, String(total + 1));

          return json({ ok: true, count: current + 1, date, isNew: true });
        } else {
          // 同一访客当天重复访问，不计数
          return json({ ok: true, count: current, date, isNew: false });
        }
      } catch (e) {
        return json({ ok: false, error: e.message }, 500);
      }
    }

    // 获取最近N天数据
    if (url.pathname === '/visits' && request.method === 'GET') {
      try {
        const days = parseInt(url.searchParams.get('days') || '14', 10);
        const result = {};

        for (let i = 0; i < days; i++) {
          const ds = dateStrOffset(-i);
          const count = parseInt(await KV.get('day:' + ds) || '0', 10);
          result[ds] = count;
        }

        // 添加总计数
        const total = parseInt(await KV.get('total') || '0', 10);
        result['_total'] = total;

        return json(result);
      } catch (e) {
        return json({ ok: false, error: e.message }, 500);
      }
    }

    return json({ error: 'Not found' }, 404);
  },
};
