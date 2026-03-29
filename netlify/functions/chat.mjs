/**
 * サウジナビ RAG チャットボット API
 *
 * POST /api/chat  { "message": "ビザの取り方を教えて" }
 * → KBインデックスからTF-IDF的に関連チャンクを検索
 * → Claude Haiku で回答生成
 * → { "answer": "...", "sources": [...] }
 */

const ANTHROPIC_API_KEY = Netlify.env.get("ANTHROPIC_API_KEY") || "";
const MODEL = "claude-haiku-4-5-20251001";
const MAX_CHUNKS = 5;
const MAX_TOKENS = 1024;

// ─── TF-IDF 簡易検索 ─────────────────────────────────────────

function tokenize(text) {
  // 日本語: 2-3文字のN-gram + 英数字単語
  const tokens = [];
  // 英数字単語
  for (const m of text.toLowerCase().matchAll(/[a-z0-9]+/g)) {
    tokens.push(m[0]);
  }
  // 日本語 bigram
  const jpText = text.replace(/[a-zA-Z0-9\s\p{P}]/gu, "");
  for (let i = 0; i < jpText.length - 1; i++) {
    tokens.push(jpText.slice(i, i + 2));
  }
  return tokens;
}

function searchChunks(query, chunks) {
  const queryTokens = new Set(tokenize(query));
  if (queryTokens.size === 0) return [];

  const scored = chunks.map((chunk) => {
    const chunkText = `${chunk.title} ${chunk.content} ${(chunk.tags || []).join(" ")}`;
    const chunkTokens = tokenize(chunkText);
    let score = 0;
    for (const token of chunkTokens) {
      if (queryTokens.has(token)) score++;
    }
    // タイトル完全一致ボーナス
    if (chunk.title && query.includes(chunk.title)) score += 10;
    // タグ一致ボーナス
    for (const tag of chunk.tags || []) {
      if (query.includes(tag)) score += 5;
    }
    return { ...chunk, score };
  });

  return scored
    .filter((c) => c.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, MAX_CHUNKS);
}

// ─── Claude API 呼び出し ─────────────────────────────────────

async function callClaude(systemPrompt, userMessage) {
  const resp = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: MAX_TOKENS,
      system: systemPrompt,
      messages: [{ role: "user", content: userMessage }],
    }),
  });
  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`Claude API error ${resp.status}: ${err}`);
  }
  const data = await resp.json();
  return data.content[0].text;
}

// ─── Handler ─────────────────────────────────────────────────

const SYSTEM_PROMPT = `あなたは「サウジナビ」のAIアシスタントです。
サウジアラビアで暮らす日本人のための情報ポータルサイトのチャットボットとして回答してください。

ルール:
- 提供されたコンテキスト（KB情報）に基づいて回答してください
- コンテキストにない情報は「現在の情報では分かりかねます」と正直に伝えてください
- 回答は簡潔に、日本語で答えてください
- 安全に関わる情報は慎重に、公式情報源の確認を促してください
- 出典があれば「詳しくは○○をご覧ください」と案内してください`;

export default async function handler(request, context) {
  // CORS preflight
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }

  if (request.method !== "POST") {
    return new Response(JSON.stringify({ error: "POST only" }), {
      status: 405,
      headers: { "Content-Type": "application/json" },
    });
  }

  try {
    const body = await request.json();
    const message = (body.message || "").trim();

    if (!message) {
      return new Response(
        JSON.stringify({ error: "message is required" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    if (!ANTHROPIC_API_KEY) {
      return new Response(
        JSON.stringify({ error: "API key not configured" }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      );
    }

    // RAG インデックスを取得（ビルド時に public/data/rag-index.json に配置済み）
    const siteUrl = new URL(request.url).origin;
    let chunks = [];
    try {
      const indexResp = await fetch(`${siteUrl}/data/rag-index.json`);
      if (indexResp.ok) {
        chunks = await indexResp.json();
      }
    } catch (e) {
      // フォールバック: インデックスなしで回答
      console.error("RAG index fetch failed:", e);
    }

    // 関連チャンク検索
    const relevant = searchChunks(message, chunks);

    // コンテキスト構築
    let contextText = "";
    const sources = [];
    if (relevant.length > 0) {
      contextText = relevant
        .map((c, i) => `[${i + 1}] ${c.title} (${c.category})\n${c.content}`)
        .join("\n\n---\n\n");
      for (const c of relevant) {
        if (c.source_url && !sources.includes(c.source_url)) {
          sources.push(c.source_url);
        }
      }
    }

    const userMsg = contextText
      ? `以下の情報を参考に質問に回答してください。\n\n【参考情報】\n${contextText}\n\n【質問】\n${message}`
      : `以下の質問に回答してください。情報が不足している場合はその旨伝えてください。\n\n【質問】\n${message}`;

    const answer = await callClaude(SYSTEM_PROMPT, userMsg);

    return new Response(
      JSON.stringify({
        answer,
        sources,
        chunks_used: relevant.length,
      }),
      {
        status: 200,
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "no-cache",
        },
      }
    );
  } catch (e) {
    console.error("Chat error:", e);
    return new Response(
      JSON.stringify({ error: "内部エラーが発生しました" }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      }
    );
  }
}
