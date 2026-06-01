const NATIVE_HOST = "com.clipmind.host";

const statusEl = document.getElementById("status");
const runBtn = document.getElementById("run-btn");
const discordCb = document.getElementById("dest-discord");
const slackCb = document.getElementById("dest-slack");

function setStatus(msg, type) {
  statusEl.textContent = msg;
  statusEl.className = "status" + (type ? " " + type : "");
}

// Fetch available destinations from native host on popup open.
chrome.runtime.sendNativeMessage(NATIVE_HOST, { action: "get_config" }, (resp) => {
  if (chrome.runtime.lastError || !resp) {
    // Fallback: enable both.
    return;
  }
  const avail = resp.destinations || [];
  if (!avail.includes("discord")) {
    discordCb.checked = false;
    discordCb.disabled = true;
    document.getElementById("label-discord").classList.add("disabled");
  }
  if (!avail.includes("slack")) {
    slackCb.checked = false;
    slackCb.disabled = true;
    document.getElementById("label-slack").classList.add("disabled");
  }
});

runBtn.addEventListener("click", async () => {
  console.log("[clipmind popup] button clicked");
  const destinations = [];
  if (discordCb.checked) destinations.push("discord");
  if (slackCb.checked) destinations.push("slack");

  if (destinations.length === 0) {
    setStatus("送り先を1つ以上選択してください", "error");
    return;
  }

  runBtn.disabled = true;
  setStatus("タブのURLを取得中...");

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    console.log("[clipmind popup] tabs:", JSON.stringify(tabs));
    if (!tabs || !tabs[0] || !tabs[0].url) {
      setStatus("タブのURLを取得できませんでした", "error");
      runBtn.disabled = false;
      return;
    }

    // Strip playlist/radio params to avoid yt-dlp playlist errors.
    const rawUrl = new URL(tabs[0].url);
    rawUrl.searchParams.delete("list");
    rawUrl.searchParams.delete("start_radio");
    rawUrl.searchParams.delete("index");
    const url = rawUrl.toString();

    // Simple YouTube check.
    try {
      const u = new URL(url);
      const ytHosts = ["www.youtube.com", "youtube.com", "m.youtube.com"];
      if (!ytHosts.includes(u.hostname)) {
        setStatus("YouTube動画のURLではありません", "error");
        runBtn.disabled = false;
        return;
      }
    } catch {
      setStatus("無効なURLです", "error");
      runBtn.disabled = false;
      return;
    }

    setStatus("処理を開始しています...");

    chrome.runtime.sendNativeMessage(
      NATIVE_HOST,
      { action: "summarize", url, destinations },
      (response) => {
        if (chrome.runtime.lastError) {
          setStatus(chrome.runtime.lastError.message, "error");
          runBtn.disabled = false;
          return;
        }

        if (response && response.status === "started") {
          setStatus(`処理開始 (${destinations.join(", ")})`, "ok");
        } else {
          const msg = (response && response.error) || "不明なエラー";
          setStatus(msg, "error");
          runBtn.disabled = false;
        }
      }
    );
  });
});
