// Visit counter for Cloudflare Pages Functions
// POST /api/visit — record a visit

export async function onRequest(context) {
  const { request, env } = context;
  const KV = env.VISITS_KV;

  // CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      }
    });
  }

  if (request.method !== 'POST') {
    return json({ error: 'Method not allowed' }, 405);
  }

  try {
    const body = await request.json();
    const date = body.date || todayStr();
    const visitorId = body.visitorId || 'anonymous';

    const dayKey = `day:${date}`;
    const current = parseInt(await KV.get(dayKey) || '0', 10);

    const visitorDayKey = `visitor:${date}:${visitorId}`;
    const alreadyVisited = await KV.get(visitorDayKey);

    if (!alreadyVisited) {
      const next = current + 1;
      await KV.put(dayKey, String(next));
      await KV.put(visitorDayKey, '1', { expirationTtl: 86400 });

      const totalKey = 'total';
      const total = parseInt(await KV.get(totalKey) || '0', 10);
      await KV.put(totalKey, String(total + 1));

      return json({ ok: true, count: next, date, isNew: true });
    }

    return json({ ok: true, count: current, date, isNew: false });
  } catch (e) {
    return json({ ok: false, error: e.message }, 500);
  }
}

function todayStr() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    }
  });
}
