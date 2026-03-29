# Knowledge Base — サウジナビ一次情報データベース

このディレクトリは、サウジナビのコンテンツを支える **一次情報・検証データ** を蓄積する場所です。
サイト（`public/`）には直接公開されませんが、以下の目的で使用します。

## 目的

1. **コンテンツの根拠管理** — 各ページの記述がどの一次情報に基づいているかを追跡
2. **AI自動更新の検証ベース** — `collect_content.py` が取得した情報の正誤チェック用
3. **将来のQ&A機能のRAGソース** — 自然言語質問への回答生成時の参照データ
4. **コミュニティからの情報蓄積** — 協力者からの現地情報・修正提案の記録

## ディレクトリ構造

```
knowledge-base/
├── README.md          # このファイル
├── visa/              # ビザ・入国要件の一次情報
├── living/            # 生活全般（住居、学校、日常）
├── business/          # ビジネスマナー・商習慣
├── safety/            # 治安・安全情報
├── culture/           # 歴史・文化・宗教
├── transport/         # 交通（国内線、鉄道、タクシー）
├── finance/           # 通貨・銀行・送金
├── telecom/           # 通信・アプリ
├── medical/           # 医療・保険
└── community/         # コミュニティ情報・協力者メモ
```

## ファイル形式

- **Markdown (.md)** — テキスト情報、ガイドライン、手順書
- **JSON (.json)** — 構造化データ（料金表、連絡先リスト等）
- **ソースURL付き** — 各ファイルには情報ソースのURLと確認日を必ず記載

## ファイル命名規則

```
[カテゴリ]/[トピック]_[YYYYMMDD].md
例: visa/evisa-requirements_20260329.md
    finance/bank-comparison_20260329.json
    community/jeddah-resident-notes_20260329.md
```

## 情報の信頼度ラベル

各ファイルの冒頭に以下のメタデータを記載：

```yaml
---
source: "https://visa.visitsaudi.com/"   # 情報ソースURL
verified_date: "2026-03-29"               # 最終確認日
confidence: "high"                         # high / medium / low
verified_by: "auto"                        # auto / yoshi / collaborator名
notes: "eVisa公式サイトから直接確認"       # 補足メモ
---
```

## 更新フロー

1. AI自動収集 → `knowledge-base/` に下書き保存（confidence: low）
2. 管理者（YOSHI）がレビュー → confidence を更新
3. 協力者の現地確認 → confidence: high に昇格
4. 確認済みデータを `public/` のページに反映

## 協力者

- YOSHI（管理者）
- ジェッダ在住者（40年在住・女性）
- エンタメ関係者（男性）
- リヤド在住サウジ人友人
- ジェッダ在住サウジ人友人
