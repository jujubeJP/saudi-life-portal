/**
 * Netlify Serverless Function: /api/content
 * 環境変数からセクション別JSONデータを読み取り返す
 * （Notion API不要 - Coworkスケジュールタスクが環境変数を直接更新）
 */

export default async function handler(event) {
  const sections = ["security", "system", "news", "life", "community"];
  content = {};

  for (const key of sections) {
    const envKey = `PORTAL_${key.toUpperCase()}`;
    const raw = process.env[envKey];
    if (raw) {
      try {
        content[key] = JSON.parse(raw);
      } catch {
        content[key] = null;
      }
    } else {
      content[key] = null;
    }
  }

  return {
    statusCode: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "public, max-age=60",
      "Access-Control-Allow-Origin": "*",
    },
    body: JSON.stringify({
      data: content,
      timestamp: new Date().toISOString(),
    }),
  };
}
