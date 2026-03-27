export default async function handler(event) {
  const sections = ["security", "system", "news", "life", "community"];
  const result = {};
  for (const key of sections) {
    const envKey = "PORTAL_" + key.toUpperCase();
    const raw = process.env[envKey];
    if (raw) {
      try { result[key] = JSON.parse(raw); } catch(e) { result[key] = null; }
    } else { result[key] = null; }
  }
  return {
    statusCode: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "public, max-age=60",
      "Access-Control-Allow-Origin": "*",
    },
    body: JSON.stringify({ data: result, timestamp: new Date().toISOString() }),
  };
}
