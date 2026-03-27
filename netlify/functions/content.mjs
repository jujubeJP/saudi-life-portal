export default async function handler(request, context) {
  const sections = ["security", "system", "news", "life", "community"];
  const result = {};
  for (const key of sections) {
    const envKey = "PORTAL_" + key.toUpperCase();
    const raw = Netlify.env.get(envKey);
    if (raw) {
      try { result[key] = JSON.parse(raw); } catch(e) { result[key] = null; }
    } else { result[key] = null; }
  }
  return new Response(
    JSON.stringify({ data: result, timestamp: new Date().toISOString() }),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "public, max-age=60",
        "Access-Control-Allow-Origin": "*",
      },
    }
  );
}
