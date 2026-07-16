// GET /api/health — health check

export async function onRequest() {
  return new Response(JSON.stringify({ ok: true, time: new Date().toISOString() }), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    }
  });
}
