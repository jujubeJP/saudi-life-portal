/**
 * サウジナビ チャットボットウィジェット
 * 全ページに読み込み、右下にフローティングチャットを表示
 */
(function () {
  "use strict";

  const API_URL = "https://saudi-navi-chat.ejanjan.workers.dev";

  // ── UI 生成 ──────────────────────────────────────────────
  function createWidget() {
    // スタイル注入
    const style = document.createElement("style");
    style.textContent = `
      #sn-chat-btn, #sn-chat-panel, #sn-chat-panel * {
        box-sizing: border-box;
      }
      #sn-chat-btn {
        position: fixed; bottom: 24px; right: 24px; z-index: 9999;
        width: 56px; height: 56px; border-radius: 50%;
        background: linear-gradient(135deg, #006c35, #009a4e);
        color: #fff; border: none; cursor: pointer;
        box-shadow: 0 4px 16px rgba(0,0,0,.25);
        font-size: 24px; display: flex; align-items: center; justify-content: center;
        transition: transform .2s;
      }
      #sn-chat-btn:hover { transform: scale(1.1); }
      #sn-chat-btn.sn-hidden { display: none !important; }
      #sn-chat-panel {
        position: fixed; bottom: 92px; right: 24px; z-index: 9998;
        width: 360px; max-width: calc(100vw - 32px);
        max-height: 520px; border-radius: 16px;
        background: #fff; box-shadow: 0 8px 32px rgba(0,0,0,.2);
        display: none; flex-direction: column; overflow: hidden;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      }
      #sn-chat-panel.open { display: flex; }
      #sn-chat-header {
        background: linear-gradient(135deg, #006c35, #009a4e);
        color: #fff; padding: 14px 16px; font-weight: bold; font-size: 15px;
        display: flex; justify-content: space-between; align-items: center;
        flex-shrink: 0;
      }
      #sn-chat-close {
        background: none; border: none; color: #fff; font-size: 22px;
        cursor: pointer; padding: 4px 8px; min-width: 36px; min-height: 36px;
        display: flex; align-items: center; justify-content: center;
      }
      #sn-chat-messages {
        flex: 1; overflow-y: auto; overflow-x: hidden; padding: 12px 14px;
        min-height: 200px; max-height: 360px;
        font-size: 14px; line-height: 1.6;
      }
      .sn-msg { margin-bottom: 10px; max-width: 85%; word-break: break-word; }
      .sn-msg-bot {
        background: #f0f4f0; border-radius: 12px 12px 12px 2px;
        padding: 10px 14px; margin-right: auto;
      }
      .sn-msg-user {
        background: #006c35; color: #fff; border-radius: 12px 12px 2px 12px;
        padding: 10px 14px; margin-left: auto; text-align: right;
      }
      .sn-msg-sources {
        font-size: 12px; color: #666; margin-top: 4px;
      }
      .sn-msg-sources a { color: #006c35; }
      #sn-chat-input-area {
        display: flex; border-top: 1px solid #e0e0e0; padding: 8px;
        flex-shrink: 0;
      }
      #sn-chat-input {
        flex: 1; min-width: 0; border: 1px solid #ccc; border-radius: 8px;
        padding: 8px 12px; font-size: 16px; outline: none;
      }
      #sn-chat-input:focus { border-color: #006c35; }
      #sn-chat-send {
        margin-left: 6px; background: #006c35; color: #fff;
        border: none; border-radius: 8px; padding: 8px 14px;
        cursor: pointer; font-size: 14px; flex-shrink: 0;
      }
      #sn-chat-send:disabled { opacity: .5; cursor: default; }
      .sn-msg-bot strong { color: #005a2b; }
      .sn-msg-bot hr { border: none; border-top: 1px solid #ddd; margin: 8px 0; }
      .sn-typing { color: #999; font-style: italic; }

      @media (max-width: 768px) {
        #sn-chat-panel {
          position: fixed; top: 0; left: 0; right: 0; bottom: 0;
          width: 100vw; max-width: 100vw;
          height: 100vh; height: 100dvh;
          max-height: none;
          border-radius: 0;
          z-index: 10000;
          margin: 0; padding: 0;
        }
        #sn-chat-panel #sn-chat-messages {
          flex: 1; min-height: 0; max-height: none;
        }
        #sn-chat-panel #sn-chat-input-area {
          padding: 8px; padding-bottom: max(8px, env(safe-area-inset-bottom));
        }
        #sn-chat-btn { bottom: 16px; right: 16px; width: 50px; height: 50px; font-size: 22px; }
      }
    `;
    document.head.appendChild(style);

    // チャットボタン
    const btn = document.createElement("button");
    btn.id = "sn-chat-btn";
    btn.innerHTML = "💬";
    btn.title = "サウジナビに質問する";
    btn.setAttribute("aria-label", "チャットを開く");
    document.body.appendChild(btn);

    // チャットパネル
    const panel = document.createElement("div");
    panel.id = "sn-chat-panel";
    panel.innerHTML = `
      <div id="sn-chat-header">
        <span>🤖 サウジナビ AI</span>
        <button id="sn-chat-close" aria-label="閉じる">✕ 閉じる</button>
      </div>
      <div id="sn-chat-messages">
        <div class="sn-msg sn-msg-bot">
          こんにちは！サウジアラビアの生活について何でも聞いてください。<br>
          <small style="color:#888">例: 「eVisaの申請方法は？」「緊急時の連絡先」</small>
        </div>
      </div>
      <div id="sn-chat-input-area">
        <input id="sn-chat-input" type="text" placeholder="質問を入力..." autocomplete="off">
        <button id="sn-chat-send">送信</button>
      </div>
    `;
    document.body.appendChild(panel);

    return { btn, panel };
  }

  // ── 簡易Markdown→HTML変換 ──────────────────────────────────
  function mdToHtml(text) {
    // XSS対策: HTMLタグをエスケープ
    let html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // 見出し: ## → 太字テキスト
    html = html.replace(/^### (.+)$/gm, '<strong>$1</strong>');
    html = html.replace(/^## (.+)$/gm, '<strong>$1</strong>');
    html = html.replace(/^# (.+)$/gm, '<strong style="font-size:1.1em">$1</strong>');

    // 太字: **text**
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // 区切り線: ---
    html = html.replace(/^---$/gm, '<hr style="border:none;border-top:1px solid #ddd;margin:8px 0">');

    // リスト: - item
    html = html.replace(/^- (.+)$/gm, '• $1');

    // テーブル行を簡易変換（| col | col |）
    html = html.replace(/^\|(.+)\|$/gm, (match, inner) => {
      if (inner.match(/^[\s\-|]+$/)) return ''; // ヘッダー区切り行を削除
      return inner.split('|').map(c => c.trim()).filter(Boolean).join('　│　');
    });

    // 連続改行 → 段落区切り
    html = html.replace(/\n\n+/g, '<br><br>');
    // 単一改行 → 改行
    html = html.replace(/\n/g, '<br>');

    return html;
  }

  // ── メッセージ追加 ────────────────────────────────────────
  function addMessage(container, text, type, sources) {
    const div = document.createElement("div");
    div.className = `sn-msg sn-msg-${type}`;
    if (type === "bot") {
      div.innerHTML = mdToHtml(text);
    } else {
      div.textContent = text;
    }

    if (sources && sources.length > 0) {
      const srcDiv = document.createElement("div");
      srcDiv.className = "sn-msg-sources";
      const links = sources
        .filter((s) => s.startsWith("http"))
        .slice(0, 3)
        .map((s) => {
          try {
            const host = new URL(s).hostname;
            return `<a href="${s}" target="_blank" rel="noopener">${host}</a>`;
          } catch {
            return "";
          }
        })
        .filter(Boolean);
      if (links.length) {
        srcDiv.innerHTML = "出典: " + links.join(", ");
        div.appendChild(srcDiv);
      }
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
  }

  // ── API 呼び出し ──────────────────────────────────────────
  async function sendMessage(message) {
    try {
      const resp = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (e) {
      return {
        answer: "申し訳ありません、通信エラーが発生しました。しばらくしてからお試しください。",
        sources: [],
      };
    }
  }

  // ── 初期化 ────────────────────────────────────────────────
  function init() {
    const { btn, panel } = createWidget();
    const messages = panel.querySelector("#sn-chat-messages");
    const input = panel.querySelector("#sn-chat-input");
    const sendBtn = panel.querySelector("#sn-chat-send");
    const closeBtn = panel.querySelector("#sn-chat-close");

    let isOpen = false;

    // モバイル判定
    const isMobile = () => window.innerWidth <= 768;

    btn.addEventListener("click", () => {
      isOpen = !isOpen;
      panel.classList.toggle("open", isOpen);
      if (isMobile()) btn.classList.toggle("sn-hidden", isOpen);
      if (isOpen) input.focus();
    });

    closeBtn.addEventListener("click", () => {
      isOpen = false;
      panel.classList.remove("open");
      btn.classList.remove("sn-hidden");
    });

    // モバイルでキーボード表示時にスクロールを調整
    if ("visualViewport" in window) {
      window.visualViewport.addEventListener("resize", () => {
        if (isOpen && isMobile()) {
          panel.style.height = window.visualViewport.height + "px";
          messages.scrollTop = messages.scrollHeight;
        }
      });
      window.visualViewport.addEventListener("scroll", () => {
        if (isOpen && isMobile()) {
          panel.style.top = window.visualViewport.offsetTop + "px";
        }
      });
    }

    async function handleSend() {
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      sendBtn.disabled = true;

      addMessage(messages, text, "user");

      const typing = document.createElement("div");
      typing.className = "sn-msg sn-msg-bot sn-typing";
      typing.textContent = "考え中...";
      messages.appendChild(typing);
      messages.scrollTop = messages.scrollHeight;

      const result = await sendMessage(text);

      typing.remove();
      addMessage(messages, result.answer, "bot", result.sources);
      sendBtn.disabled = false;
      input.focus();
    }

    sendBtn.addEventListener("click", handleSend);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.isComposing) handleSend();
    });
  }

  // DOM ready で起動
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
