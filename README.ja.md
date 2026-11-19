# ⚽ nexpitch

[한국어](README.md) · **日本語**

> 本 README は韓国語版 [README.md](README.md) を Gemini で自動翻訳したものです（数値・リンクは原文と一致することを自動検査しています）。設計記録（ADR）・開発ノート・コードコメントは韓国語です。

プレミアリーグの試合を統計モデルとLLMが分析し、**その分析が正しいかを直接測定する**AIサッカーアプリ。

[![Next.js](https://img.shields.io/badge/Next.js_16-000?logo=nextdotjs&logoColor=fff)](frontend)
[![Python](https://img.shields.io/badge/Python_3.13-3776AB?logo=python&logoColor=fff)](backend)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=fff)](docs/adr/0014-선수-팀-임베딩-모델.md)
[![Gemini](https://img.shields.io/badge/Gemini-8E75B2?logo=googlegemini&logoColor=fff)](docs/adr/0009-LLM-분석가-같은-숫자-같은-지표.md)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=fff)](docs/adr/0003-뉴스-저장소는-Neon-PostgreSQL.md)
[![analysis-batch](https://github.com/jjoonii34/nexpitch/actions/workflows/analysis-batch.yml/badge.svg)](https://github.com/jjoonii34/nexpitch/actions/workflows/analysis-batch.yml)

**デモ** → https://nexpitch-pi.vercel.app

## コア

- **同じ入力** — 統計モデルとLLMに同じ試合前の数値を与える。
- **同じ採点** — 実際の試合結果でブライアースコア（Brier score）を測定し、その差が偶然によるものかをブートストラップ法で判定する。
- **記憶の制御** — チーム名を伏せた入力と比較し、LLMが結果を記憶していないかを確認する。
- **仮説はLLM、検証は統計** — LLMの仮説を過去の試合で逆検証する。
- **直接学習** — 自前で収集した選手の記録で埋め込みモデルを学習する。

## 測定結果

学習 2022・2023シーズン → 評価 2024シーズン 380試合。ブライアースコア・対数損失は低いほど良い。

| モデル | Brier | 対数損失 | 正解率 |
|---|---|---|---|
| 定数（勝・分・敗の割合） | 0.6595 | 1.0860 | 40.8% |
| Elo | 0.6021 | 1.0048 | 53.2% |
| 特徴量モデル | 0.6071 | 1.0540 | 51.8% |
| LLM (Gemini) | 0.5938 | 0.9945 | 51.6% |
| **LLM + Elo 平均** | **0.5937** | **0.9924** | 52.4% |

同じ試合同士でペアにしたBrier差（95%区間）：

| 比較 | 差 | 95%区間 | 判定 |
|---|---|---|---|
| LLM − Elo | −0.0083 | −0.0226 〜 +0.0057 | 差なし |
| LLM+Elo − Elo | −0.0083 | −0.0155 〜 −0.0013 | **組み合わせの方が良い** |
| 名前を伏せた − 伏せていない（54試合） | +0.0047 | −0.0097 〜 +0.0187 | 記憶効果の根拠なし |

プロンプトバージョン比較：

| 指標 | v1 (380試合) | v2 (97試合) |
|---|---|---|
| 検証可能な仮説 | 0% | 100% |
| 異なる仮説の数 / 使用された特徴量 | — | 21個 / 1種類 |
| 自明ではない仮説（Elo単独を除く） | — | **0%** |
| 根拠の数値が入力に存在する割合 | 99% | 100% |

- 仮説97件の逆検証：根拠あり 83件 ・ サンプル不足 12件 ・ 根拠なし 2件。すべてElo単独の仮説であるため、成果としては見なさない。
- 戦術スタッツの半期安定性（83試合）：パス数 0.65 ・ ポゼッション 0.62 ・ xG 0.30。
- 戦術特徴量・埋め込みモデルの予測性能は**未測定**（データ収集中、11月末に暫定測定予定）。

## 機能

| 領域 | 内容 |
|---|---|
| 試合・リーグ | 日付別の試合、試合詳細、順位表、得点ランキング |
| ニュース | 20クラブのガーディアン記事（原文のまま、直近24時間） |
| 収集 | ラインアップ・チームスタッツ・選手スタッツ、毎日自動実行 |
| 予測 | 定数・Elo・特徴量モデル、LLMアナリスト、結合モデル |
| 評価 | シーズン単位の時間順分割、ペアにしたブートストラップ法、プロンプト評価ハーネス、仮説逆検証 |
| 学習 | 選手・チーム埋め込みモデル (PyTorch) |

## 構造

```
Guardian ─────► 収集バッチ ──► Neon PostgreSQL ◄── 収集バッチ ◄── API-Football
                (GitHub Actions)     │
                                     ├──► 分析 (Elo · ロジスティック · Gemini · PyTorch)
football-data.org ──► Next.js (Vercel) ◄── ユーザー
```

- `frontend/` — Next.js 16。API失敗時はサンプルデータ＋表示帯を表示。
- `backend/` — Python。収集器、分析モデル、Alembicマイグレーション。
- テスト — フロントエンド16、バックエンド76。ネットワークなしで実行可能。
- 常駐サーバーなし。コスト0円。

## データソース

| ソース | 用途 | 規約上の制限 |
|---|---|---|
| football-data.org | 結果・順位 | 1分間に10回 |
| The Guardian Open Platform | ニュース | 翻訳・加工の禁止、24時間保管 ([ADR 0006](docs/adr/0006-가디언-약관-준수-번역과-LLM-가공-중지.md)) |
| API-Football | ラインアップ・スタッツ | 1日100回、元のデータの再配布禁止 ([ADR 0007](docs/adr/0007-경기-분석-데이터는-API-Football-무료-플랜.md)) |
| コミュニティサイト | 収集しない | — |

## ロードマップ

- [x] 試合・リーグ・ニュースタブ、デプロイ
- [x] 第1段階 データ収集
- [x] 第2段階 統計ベースライン
- [x] 第3段階 LLMアナリスト
- [x] 第4段階 仮説逆検証
- [ ] 第4.5段階 AIアナリスト高度化
  - [x] 評価ハーネス
  - [x] 戦術特徴量（コード）
  - [x] 埋め込みモデル（コード）
  - [ ] プロンプト v3
  - [ ] 人間によるラベル付き評価セット100件
  - [ ] 実データ測定（11月末暫定測定、12月末最終測定）
- [ ] 第5段階 分析画面
- [ ] 第6段階 移籍トラッカー ＋ 選手獲得推薦
- [ ] フォロータブ

詳細はこちら: [docs/roadmap.md](docs/roadmap.md)

## 実行

```bash
# フロントエンド
cd frontend
npm install && npm run dev
npm test

# バックエンド
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest
python -m alembic upgrade head
python -m app.analysis.run 2024           # 統計モデル採点
python -m app.analysis.llm_run 2024       # LLMアナリスト実行・採点
python -m app.analysis.prompt_eval 2024   # プロンプトバージョン比較
python -m app.analysis.tactical_run 2024  # 戦術特徴量点検
pip install -r requirements-ml.txt
python -m app.analysis.embed_model 2024   # 埋め込みモデル学習
```

環境変数については `frontend/.env.example`、`backend/.env.example` を参照してください。

## ドキュメント

- 設計決定 14件: [docs/adr/](docs/adr)
- 作業記録: [docs/notes.md](docs/notes.md)

---

試合データ: football-data.org · API-Football &nbsp;|&nbsp; ニュース: Powered by The Guardian

<!-- readme-ja source-sha256: 276cc79f11f0fea2393f23619e54243f8b38bdcc6affb183f6b5dc02c3541841 -->
