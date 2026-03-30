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
      }
      #sn-chat-header button {
        background: none; border: none; color: #fff; font-size: 20px; cursor: pointer;
      }
      #sn-chat-messages {
        flex: 1; overflow-y: auto; padding: 12px 14px;
        min-height: 200px; max-height: 360px;
        font-size: 14px; line-height: 1.6;
      }
      .sn-msg { margin-bottom: 10px; max-width: 85%; }
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
      }
      #sn-chat-input {
        flex: 1; border: 1px solid #ccc; border-radius: 8px;
        padding: 8px 12px; font-size: 14px; outline: none;
      }
      #sn-chat-input:focus { border-color: #006c35; }
      #sn-chat-send {
        margin-left: 6px; background: #006c35; color: #fff;
        border: none; border-radius: 8px; padding: 8px 14px;
        cursor: pointer; font-size: 14px;
      }
      #sn-chat-send:disabled { opacity: .5; cursor: default; }
      .sn-typing { color: #999; font-style: italic; }
      @media (max-width: 480px) {
        #sn-chat-panel { bottom: 0; right: 0; width: 100%; max-width: 100%;
          max-height: 75vh; border-radius: 16px 16px 0 0; }
        #sn-chat-btn { bottom: 16px; right: 16px; }
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
        <button id="sn-chat-close" aria-label="閉じる">✕</button>
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

  // ── メッセージ追加 ────────────────────────────────────────
  function addMessage(container, text, type, sources) {
    const div = document.createElement("div");
    div.className = `sn-msg sn-msg-${type}`;
    div.textContent = text;

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

    btn.addEventListener("click", () => {
      isOpen = !isOpen;
      panel.classList.toggle("open", isOpen);
      if (isOpen) input.focus();
    });

    closeBtn.addEventListener("click", () => {
      isOpen = false;
      panel.classList.remove("open");
    });

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
