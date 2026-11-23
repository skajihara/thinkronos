# 文書の索引

Thinkronos の設計・運用の文書。正本はこの `docs/` のMarkdownで、変更はPRで行う（K-01、K-06）。企画書（背景・目的・企画・スコープ・意思決定ログ）は非公開で、2026-11-23 に凍結した。

## 要件定義書（`requirements/`）

| ファイル | 内容 |
|---|---|
| [01-features.md](requirements/01-features.md) | 機能一覧、機能要件（要件ID） |
| [02-screens.md](requirements/02-screens.md) | 画面一覧と画面遷移 |
| [03-non-functional.md](requirements/03-non-functional.md) | 非機能要件 |
| [04-architecture.md](requirements/04-architecture.md) | システムアーキテクチャ、技術スタック |
| [05-data.md](requirements/05-data.md) | データ設計（ER図） |
| [05a-tables.md](requirements/05a-tables.md) | テーブル定義と操作ログの仕様 |
| [06-integrations.md](requirements/06-integrations.md) | 外部API連携設計、連携先アカウント |
| [07-ai.md](requirements/07-ai.md) | AI機能設計 |
| [08-process.md](requirements/08-process.md) | 開発プロセス、AI開発ツール、ブランチ戦略、CI/CD |
| [09-observability.md](requirements/09-observability.md) | ロギング・モニタリング（運用は [observability.md](observability.md)） |
| [10-pwa.md](requirements/10-pwa.md) | PWA |
| [11-plan.md](requirements/11-plan.md) | 開発計画（フェーズと完了条件） |
| [11a-implementation-plan.md](requirements/11a-implementation-plan.md) | 実装計画（日程、依存関係、リリース） |
| [12-test-plan.md](requirements/12-test-plan.md) | テスト計画（E2Eシナリオ、品質ゲート） |

## そのほか

| 場所 | 内容 |
|---|---|
| [conventions/](conventions/README.md) | 実装規約 |
| [decisions.md](decisions.md) | 決定事項一覧（状態の表） |
| [adr/](adr/README.md) | 設計判断の記録（ADR） |
| [architecture/](architecture/README.md) | C4の図、主要な処理の図、脅威モデリング |
| [guide/](guide/README.md) | 機能ごとの使い方（操作マニュアルの元） |
| [tool-notes.md](tool-notes.md) | ツールごとの使い方の記録 |

## 工程ごとの成果物（K-08）

| 工程 | 一般的な成果物 | この開発での成果物 |
| --- | --- | --- |
| 企画・構想 | 企画書、システム化計画書、見積書、プロジェクト計画書 | 企画書（非公開）、[実装計画](requirements/11a-implementation-plan.md) |
| 要件定義 | 要件定義書、業務フロー図、機能一覧、非機能要件定義書 | [機能一覧・機能要件](requirements/01-features.md)、[非機能要件](requirements/03-non-functional.md)、主要ユースケースと利用シナリオ、主な処理の流れ |
| 基本設計 | 基本設計書、画面レイアウト図、画面遷移図、帳票設計書、ER図、テーブル定義書、外部インターフェース設計書 | [システムアーキテクチャ](requirements/04-architecture.md)、[画面一覧と画面遷移](requirements/02-screens.md)、ワイヤーフレーム、[ER図](requirements/05-data.md)、[テーブル定義と操作ログ](requirements/05a-tables.md)、[外部API連携設計](requirements/06-integrations.md)、ジョブ一覧、C4の図（K-02）。帳票はないので対象外 |
| 詳細設計 | 詳細設計書、クラス図、シーケンス図、モジュール構成図、API仕様書 | 機能ごとのKiroの仕様（design.md）、[ADR](adr/README.md)、ディレクトリ構成、`openapi.json`（C-28） |
| 実装・開発 | ソースコード、単体テスト仕様書 | ソースコード、テストコード（テスト名が仕様になる）、機能ごとの「使い方」ページ（`guide/`、K-07） |
| テスト | 結合・総合・受入テスト仕様書、テスト結果報告書、バグ管理表 | [テスト計画](requirements/12-test-plan.md)、CIの結果、リリースノート（性能の計測結果を含む）、Issue（ラベル `bug`） |
| リリース・移行 | リリース計画書、移行計画書、移行手順書 | 実装計画のリリースの表、CHANGELOG。移行計画と手順はAWS環境に移すP4で作る |
| 運用・保守 | 運用設計書、操作マニュアル、障害対応手順書 | [ロギング・モニタリング](observability.md)、操作マニュアル（「使い方」ページの集まり）、障害対応の手順（runbook、P3までに作る） |

## 決定の残し方

- 大きな決定はADR、小さな決定はIssueとPRに残す。未決・保留の論点はラベル `decision` のIssueで扱う。
- 決定したら [decisions.md](decisions.md) の状態を同じPRで更新する。
- 図はMermaidで書き、同じPRで管理する（K-02）。
