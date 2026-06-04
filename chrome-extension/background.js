const NATIVE_HOST = "com.clipmind.host";

const YOUTUBE_PATTERNS = [
  "https://www.youtube.com/*",
  "https://youtube.com/*",
  "https://m.youtube.com/*",
];

function isYouTubeUrl(url) {
  try {
    const u = new URL(url);
    return (
      ["www.youtube.com", "youtube.com", "m.youtube.com"].includes(u.hostname) &&
      (u.pathname === "/watch" || u.pathname.startsWith("/shorts/"))
    );
  } catch {
    return false;
  }
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "clipmind-summarize",
    title: "clipmindで要約",
    documentUrlPatterns: YOUTUBE_PATTERNS,
    contexts: ["page", "link"],
  });
});

chrome.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId !== "clipmind-summarize") return;

  const url = info.linkUrl || info.pageUrl;
  if (!url || !isYouTubeUrl(url)) {
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon48.png",
      title: "clipmind",
      message: "YouTube動画のURLではありません",
    });
    return;
  }

  chrome.runtime.sendNativeMessage(
    NATIVE_HOST,
    { action: "summarize", url },
    (response) => {
      if (chrome.runtime.lastError) {
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icons/icon48.png",
          title: "clipmind - エラー",
          message: chrome.runtime.lastError.message,
        });
        return;
      }

      if (response && response.status === "started") {
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icons/icon48.png",
          title: "clipmind",
          message: "処理を開始しました",
        });
      } else {
        const msg = (response && response.error) || "不明なエラー";
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icons/icon48.png",
          title: "clipmind - エラー",
          message: msg,
        });
      }
    }
  );
});
