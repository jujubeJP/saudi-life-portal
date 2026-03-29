// Site-wide search index for Saudi Navi
const SITE_SEARCH_INDEX = [
  // index.html - ホーム（ダッシュボード）
  {page: 'index.html', pageTitle: '🏠 ホーム', title: 'サウジナビ', desc: 'サウジアラビア日本語生活情報ポータル'},
  {page: 'index.html', pageTitle: '🏠 ホーム', title: 'ダッシュボード', desc: '各ページへのナビゲーション、お知らせ'},

  // news.html - 治安・ニュース
  {page: 'news.html', pageTitle: '📰 治安・ニュース', title: 'ニュース', desc: 'サウジアラビアの最新ニュース（英語・アラビア語・日本語）'},
  {page: 'news.html', pageTitle: '📰 治安・ニュース', title: '治安情報', desc: '安全対策、犯罪、注意事項'},
  {page: 'news.html', pageTitle: '📰 治安・ニュース', title: '危険情報', desc: '外務省海外安全HP、危険レベル'},
  {page: 'news.html', pageTitle: '📰 治安・ニュース', title: '大使館ニュース', desc: '在サウジ日本大使館からのお知らせ'},

  // saudi-time.html - サウジ時間
  {page: 'saudi-time.html', pageTitle: '🕐 サウジ時間', title: '時差・タイムゾーン', desc: 'UTC+3、日本との時差マイナス6時間'},
  {page: 'saudi-time.html', pageTitle: '🕐 サウジ時間', title: '週末', desc: '金曜・土曜が休み。日曜が週の始まり'},
  {page: 'saudi-time.html', pageTitle: '🕐 サウジ時間', title: '就業時間（通常）', desc: '官公庁7:30-14:30、民間8:00-17:00'},
  {page: 'saudi-time.html', pageTitle: '🕐 サウジ時間', title: '就業時間（ラマダン）', desc: '官公庁10:00-15:00、民間6時間/日'},
  {page: 'saudi-time.html', pageTitle: '🕐 サウジ時間', title: '礼拝時間', desc: '1日5回。店舗が15-30分閉店'},
  {page: 'saudi-time.html', pageTitle: '🕐 サウジ時間', title: '食事の時間帯', desc: '昼食13-15時、夕食21-23時'},
  {page: 'saudi-time.html', pageTitle: '🕐 サウジ時間', title: '月別気温', desc: 'リヤド夏44℃、冬9-22℃。ジェッダは年中温暖'},
  {page: 'saudi-time.html', pageTitle: '🕐 サウジ時間', title: '夏の生活', desc: '夜型。モールが涼みスポット。ディナーは22時以降'},
  {page: 'saudi-time.html', pageTitle: '🕐 サウジ時間', title: '冬の生活', desc: '砂漠キャンプ、屋外バーベキュー、デューンバッシング'},

  // travel-info.html - 渡航情報
  {page: 'travel-info.html', pageTitle: '✈️ 渡航情報', title: 'パスポート', desc: '残存期間6ヶ月以上、空白ページ必要'},
  {page: 'travel-info.html', pageTitle: '✈️ 渡航情報', title: '観光ビザ（eVisa）', desc: 'オンライン申請、1年有効、90日滞在、535SAR'},
  {page: 'travel-info.html', pageTitle: '✈️ 渡航情報', title: '就労ビザ・イカマ', desc: '雇用主スポンサー、在留許可証'},
  {page: 'travel-info.html', pageTitle: '✈️ 渡航情報', title: 'プレミアムレジデンシー', desc: '永住権に近い、年10万SAR or 一括80万SAR'},
  {page: 'travel-info.html', pageTitle: '✈️ 渡航情報', title: '入国手続き', desc: '入国審査、指紋・顔認証、税関'},
  {page: 'travel-info.html', pageTitle: '✈️ 渡航情報', title: '持ち込み禁止品', desc: '酒類、豚肉製品、薬物は厳禁'},
  {page: 'travel-info.html', pageTitle: '✈️ 渡航情報', title: 'SIM購入', desc: 'STC、Mobily、Zain。空港で購入可'},
  {page: 'travel-info.html', pageTitle: '✈️ 渡航情報', title: 'Absher', desc: 'ビザ・在留許可のオンラインポータル'},

  // vision2030.html - VISION 2030
  {page: 'vision2030.html', pageTitle: '🏗️ VISION 2030', title: 'VISION 2030', desc: '2016年発表の国家変革計画。石油依存脱却'},
  {page: 'vision2030.html', pageTitle: '🏗️ VISION 2030', title: 'NEOM', desc: '未来都市。THE LINE（直線都市170km）'},
  {page: 'vision2030.html', pageTitle: '🏗️ VISION 2030', title: '紅海プロジェクト', desc: '高級リゾート開発。50の島'},
  {page: 'vision2030.html', pageTitle: '🏗️ VISION 2030', title: 'Qiddiya', desc: 'エンタメ都市。Six Flagsテーマパーク'},
  {page: 'vision2030.html', pageTitle: '🏗️ VISION 2030', title: '女性の社会進出', desc: '2018年運転解禁、労働参加率向上'},
  {page: 'vision2030.html', pageTitle: '🏗️ VISION 2030', title: 'サウジ化（Nitaqat）', desc: 'サウジ人雇用義務化政策'},

  // money.html - 通貨・銀行
  {page: 'money.html', pageTitle: '💰 通貨・銀行', title: 'サウジリヤル', desc: '通貨SAR。1USD=3.75SAR（固定）。1SAR≈40円'},
  {page: 'money.html', pageTitle: '💰 通貨・銀行', title: '両替', desc: '市中の両替所がレート良い。Enjaz、Al Rajhi Exchange'},
  {page: 'money.html', pageTitle: '💰 通貨・銀行', title: 'ATM', desc: '街中に多数。国際カード対応。引出上限5000SAR'},
  {page: 'money.html', pageTitle: '💰 通貨・銀行', title: 'クレジットカード', desc: 'VISA/Mastercard可。AMEXは使えない場合多い'},
  {page: 'money.html', pageTitle: '💰 通貨・銀行', title: 'STCpay', desc: '最大手の支払アプリ。送金・決済・チャージ'},
  {page: 'money.html', pageTitle: '💰 通貨・銀行', title: 'Al Rajhi Bank', desc: '最大のイスラム銀行'},
  {page: 'money.html', pageTitle: '💰 通貨・銀行', title: 'VAT', desc: '付加価値税15%。2018年導入'},
  {page: 'money.html', pageTitle: '💰 通貨・銀行', title: '国際送金', desc: 'Wise、Western Union、銀行送金'},
  {page: 'money.html', pageTitle: '💰 通貨・銀行', title: 'チップ', desc: 'レストラン10-15%、ホテルポーター5-10SAR'},

  // history-culture.html - 歴史・文化
  {page: 'history-culture.html', pageTitle: '🕌 歴史・文化', title: 'サウジ建国', desc: '1932年アブドゥルアジーズ王が統一'},
  {page: 'history-culture.html', pageTitle: '🕌 歴史・文化', title: '石油発見', desc: '1938年ダンマーム油田。ARAMCO'},
  {page: 'history-culture.html', pageTitle: '🕌 歴史・文化', title: 'マッカ', desc: 'イスラム最大の聖地。カアバ神殿。非ムスリム入域不可'},
  {page: 'history-culture.html', pageTitle: '🕌 歴史・文化', title: 'メディナ', desc: '預言者のモスク。イスラム第二の聖地'},
  {page: 'history-culture.html', pageTitle: '🕌 歴史・文化', title: '世界遺産', desc: 'マダインサーレハ、ディルイーヤ、ジェッダ他6件'},
  {page: 'history-culture.html', pageTitle: '🕌 歴史・文化', title: 'アバヤ', desc: '女性の外衣。外国人は義務ではないが控えめな服装推奨'},
  {page: 'history-culture.html', pageTitle: '🕌 歴史・文化', title: 'ラマダン', desc: '断食月。公共の場での飲食を控える'},
  {page: 'history-culture.html', pageTitle: '🕌 歴史・文化', title: 'アラビアコーヒー', desc: 'カフワ。おもてなしの象徴'},

  // emergency.html - 緊急連絡先
  {page: 'emergency.html', pageTitle: '🚨 緊急連絡先', title: '警察', desc: '999'},
  {page: 'emergency.html', pageTitle: '🚨 緊急連絡先', title: '救急車', desc: '997'},
  {page: 'emergency.html', pageTitle: '🚨 緊急連絡先', title: '消防', desc: '998'},
  {page: 'emergency.html', pageTitle: '🚨 緊急連絡先', title: '総合緊急番号', desc: '911（全土対応）'},
  {page: 'emergency.html', pageTitle: '🚨 緊急連絡先', title: '日本大使館', desc: '+966-11-488-1100（リヤド）'},
  {page: 'emergency.html', pageTitle: '🚨 緊急連絡先', title: '病院', desc: 'King Faisal、Dr. Sulaiman Al Habib等'},

  // events.html - イベント
  {page: 'events.html', pageTitle: '📅 イベント', title: '2026年イベント', desc: 'サウジアラビアの祝日・スポーツ・文化イベント'},
  {page: 'events.html', pageTitle: '📅 イベント', title: 'ラマダン', desc: '2026年は2月中旬〜3月中旬頃'},
  {page: 'events.html', pageTitle: '📅 イベント', title: 'リヤドシーズン', desc: '冬の大型エンタメイベント'},
  {page: 'events.html', pageTitle: '📅 イベント', title: '建国記念日', desc: '9月23日'},

  // life.html - 生活
  {page: 'life.html', pageTitle: '🏠 生活ガイド', title: '生活情報', desc: '住居、交通、買い物、医療'},

  // glossary.html - 用語集
  {page: 'glossary.html', pageTitle: '📖 用語集', title: 'アラビア語用語集', desc: 'サウジ生活で使う基本用語'},

  // about.html
  {page: 'about.html', pageTitle: '運営者情報', title: '運営者情報', desc: 'このサイトについて'},

  // links.html
  {page: 'links.html', pageTitle: '🔗 リンク集', title: '便利リンク', desc: '大使館、官公庁、生活情報'},

  // disclaimer.html
  {page: 'disclaimer.html', pageTitle: '免責事項', title: '免責事項', desc: '利用規約と免責について'},

  // telecom.html - 通信・アプリ
  {page: 'telecom.html', pageTitle: '📱 通信・アプリ', title: 'SIMカード', desc: 'STC、Mobily、Zain。購入方法とプラン'},
  {page: 'telecom.html', pageTitle: '📱 通信・アプリ', title: 'Absher', desc: '政府サービスポータル。ビザ・在留許可管理'},
  {page: 'telecom.html', pageTitle: '📱 通信・アプリ', title: 'Tawakkalna', desc: '健康・身分証明アプリ'},
  {page: 'telecom.html', pageTitle: '📱 通信・アプリ', title: 'Nafath', desc: '国家デジタル認証システム'},
  {page: 'telecom.html', pageTitle: '📱 通信・アプリ', title: 'VPN', desc: 'VPN利用の注意点'},

  // transport.html - 国内交通
  {page: 'transport.html', pageTitle: '🚗 国内交通', title: '国内線フライト', desc: 'Saudia、flynas、flyadeal'},
  {page: 'transport.html', pageTitle: '🚗 国内交通', title: 'ハラマイン高速鉄道', desc: 'マッカ〜マディーナ間の高速鉄道'},
  {page: 'transport.html', pageTitle: '🚗 国内交通', title: 'リヤドメトロ', desc: '6路線の新都市鉄道'},
  {page: 'transport.html', pageTitle: '🚗 国内交通', title: 'Uber・Careem', desc: 'ライドシェアアプリ'},
  {page: 'transport.html', pageTitle: '🚗 国内交通', title: 'レンタカー', desc: '国際免許・サウジ免許・主要レンタカー会社'},
  {page: 'transport.html', pageTitle: '🚗 国内交通', title: '運転文化', desc: 'スピード違反カメラ、交通ルール'},

  // food.html - サウジ料理
  {page: 'food.html', pageTitle: '🍽️ サウジ料理', title: 'カブサ', desc: 'サウジの国民食。スパイス米と肉'},
  {page: 'food.html', pageTitle: '🍽️ サウジ料理', title: 'マンディ', desc: '燻製風炊き込みご飯'},
  {page: 'food.html', pageTitle: '🍽️ サウジ料理', title: 'シャワルマ', desc: '人気のストリートフード'},
  {page: 'food.html', pageTitle: '🍽️ サウジ料理', title: 'アラビアコーヒー', desc: 'カフワとデーツ。おもてなしの文化'},
  {page: 'food.html', pageTitle: '🍽️ サウジ料理', title: 'スーパーマーケット', desc: 'Tamimi、Danube、Panda、LuLu'},
  {page: 'food.html', pageTitle: '🍽️ サウジ料理', title: 'フードデリバリー', desc: 'HungerStation、Jahez、Careem Food'},

  // city-guide.html - 都市ガイド
  {page: 'city-guide.html', pageTitle: '🏙️ 都市ガイド', title: 'リヤド', desc: '首都。人口約800万。ビジネスの中心'},
  {page: 'city-guide.html', pageTitle: '🏙️ 都市ガイド', title: 'ジェッダ', desc: '紅海沿い。マッカへの玄関口。アルバラド旧市街'},
  {page: 'city-guide.html', pageTitle: '🏙️ 都市ガイド', title: 'ダンマーム・東部州', desc: 'アラムコ本社。石油産業の中心'},
  {page: 'city-guide.html', pageTitle: '🏙️ 都市ガイド', title: 'メディナ', desc: '預言者のモスク。イスラム第二の聖地'},
  {page: 'city-guide.html', pageTitle: '🏙️ 都市ガイド', title: 'NEOM', desc: 'Vision 2030の未来都市プロジェクト'},

  // medical.html - 医療
  {page: 'medical.html', pageTitle: '🏥 医療', title: '病院の探し方', desc: '公立・私立病院、英語対応医師'},
  {page: 'medical.html', pageTitle: '🏥 医療', title: '健康保険', desc: 'CCHI、雇用主提供保険、カバー範囲'},
  {page: 'medical.html', pageTitle: '🏥 医療', title: '救急医療', desc: '997番。救急車の呼び方'},
  {page: 'medical.html', pageTitle: '🏥 医療', title: '薬局', desc: 'Al Nahdi、Whites。処方箋ルール'},
  {page: 'medical.html', pageTitle: '🏥 医療', title: '予防接種', desc: '必須・推奨ワクチン'},
  {page: 'medical.html', pageTitle: '🏥 医療', title: '医療費', desc: '保険あり・なしの費用目安'},

  // entertainment.html - 娯楽
  {page: 'entertainment.html', pageTitle: '🎡 娯楽', title: 'テーマパーク', desc: 'Boulevard Riyadh、Winter Wonderland、Qiddiya'},
  {page: 'entertainment.html', pageTitle: '🎡 娯楽', title: '映画館', desc: 'AMC、VOX、Muvi。2018年解禁'},
  {page: 'entertainment.html', pageTitle: '🎡 娯楽', title: 'スポーツ', desc: 'F1サウジGP、サッカー、WWE'},
  {page: 'entertainment.html', pageTitle: '🎡 娯楽', title: 'リヤドシーズン', desc: '冬の大型エンタメイベント'},
  {page: 'entertainment.html', pageTitle: '🎡 娯楽', title: '砂漠体験', desc: 'デューンバッシング、キャンプ、星空観賞'},
  {page: 'entertainment.html', pageTitle: '🎡 娯楽', title: '紅海ダイビング', desc: '世界クラスのサンゴ礁'},
  {page: 'entertainment.html', pageTitle: '🎡 娯楽', title: 'アルウラ', desc: 'ヘグラ遺跡（UNESCO）、マラヤコンサートホール'},

  // business.html - ビジネスマナー
  {page: 'business.html', pageTitle: '💼 ビジネスマナー', title: '挨拶・名刺交換', desc: '握手の作法、右手の使用'},
  {page: 'business.html', pageTitle: '💼 ビジネスマナー', title: '会議の文化', desc: '関係構築重視、コーヒー儀礼'},
  {page: 'business.html', pageTitle: '💼 ビジネスマナー', title: 'ラマダン中のビジネス', desc: '短縮営業、公共での飲食禁止'},
  {page: 'business.html', pageTitle: '💼 ビジネスマナー', title: 'ワスタ', desc: '人脈・コネクションの重要性'},
  {page: 'business.html', pageTitle: '💼 ビジネスマナー', title: 'サウジ化（Nitaqat）', desc: 'サウジ人雇用義務化政策'},
  {page: 'business.html', pageTitle: '💼 ビジネスマナー', title: 'JETRO', desc: '日本貿易振興機構のサポート'},
];
