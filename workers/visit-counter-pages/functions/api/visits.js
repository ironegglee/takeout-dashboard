// GET /api/visits?days=14 — fetch recent visit data

export async function onRequest(context) {
  const { request, env } = context;
  const KV = env.VISITS_KV;
  const url = new URL(request.url);

  try {
    const days = parseInt(url.searchParams.get('days') || '14', 10);
    const result = {};

    const today = new Date();
    for (let i = 0; i < days; i++) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      const ds = d.toISOString().slice(0, 10);
      const count = parseInt(await KV.get(`day:${ds}`) || '0', 10);
      result[ds] = count;
    }

    const total = parseInt(await KV.get('total') || '0', 10);
    result['_total'] = total;

    return new Response(JSON.stringify(result), {
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      }
    });
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: e.message }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      }
    });
  }
}
