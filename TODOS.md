# TODOS

## Podcast Source Adapter
**What:** yt-dlp対応サイトの音声コンテンツをsource adapterで取り込めるようにする
**Why:** 「動画もPodcastもいける」がマルチソースの「うわ」感の核。現在YouTube単独。
**Pros:** マルチソースのデモが可能に。差別化の第2の柱。
**Cons:** source adapter Protocol層の設計が必要。yt-dlp対応範囲の明確化も必要。
**Context:** Codex outside voiceが「Podcastソースはフェイク」と指摘。RSS/Apple Podcasts/Spotifyなしでは
生メディアURLしか受け付けない。実装時は `yt-dlp --list-extractors` で対応サイトを確認し、
サポート範囲をドキュメント化すること。requestsフォールバックではなくyt-dlp一本で行く設計が推奨。
**Depends on:** Clip Object + destination adapter実装完了後
