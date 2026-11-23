<!-- 正本はこのファイル。企画書（Claude Docs）から 2026-11-23 に移した（K-01）。変更はPRで行う。 -->

# ロギング・モニタリング基盤

ログ・メトリクス・トレースはすべてOpenTelemetryで出し、ローカルではGrafanaの `grafana/otel-lgtm` イメージ1つで見られるようにする。AWS環境では、アプリのコードは変えずに送り先だけをCloudWatchとX-Rayに変える。

## 構成

- アプリ（API、ワーカー）→ OpenTelemetry SDK → otel-lgtm（OTLPで受信）→ Grafanaで表示。
- otel-lgtmは、OpenTelemetry Collector、Prometheus（メトリクス）、Tempo（トレース）、Loki（ログ）、Pyroscope（プロファイル）、Grafanaを1つのコンテナにまとめた、開発・検証向けのイメージ（[grafana/docker-otel-lgtm](https://github.com/grafana/docker-otel-lgtm)）。
- Docker Composeのprofile `observability` で起動し、必要なときだけ立ち上げる。
- Strandsのエージェント実行（ツール呼び出しを含む）も、OpenTelemetryのトレースに含める。

## ログの方針

| 項目 | 方針 |
| --- | --- |
| 形式 | JSON（structlog）。標準出力に出し、収集は基盤側に任せる |
| 共通項目 | 時刻（UTC）、レベル、サービス名、バージョン、trace\_id、span\_id、request\_id、ユーザーの内部ID |
| ERROR | 利用者に影響する失敗（処理の中断、同期の失敗） |
| WARNING | リトライで回復した失敗、想定外の入力、外部APIの429 |
| INFO | リクエストの完了、ジョブの開始と終了、外部連携の結果 |
| DEBUG | 開発環境でのみ出す |
| 出さないもの | パスワード、トークン、メールアドレス、予定の本文、LLMへの入力の全文（長さとハッシュだけを残す） |

## メトリクス

| 対象 | メトリクス | 何に使うか |
| --- | --- | --- |
| API | リクエスト数、エラー率、レイテンシ（p50、p95、p99） | NF-01の確認と、異常の検知 |
| ワーカー | キューの長さ、ジョブの成功数と失敗数、処理時間、リトライ回数 | 同期の詰まりの検知 |
| 外部連携 | API呼び出し数、429と5xxの回数、トークン更新の失敗数、要再連携のアカウント数 | 連携の健全性の確認 |
| LLM | 呼び出し数、入出力トークン数、レイテンシ、構造化出力の検証失敗率 | 品質とコストの確認 |
| DB | 接続数、遅いクエリ | 性能の確認 |
| 利用状況 | 作られたノード数、AI提案の採用率、承認された枠の数 | 機能が使われているかの確認 |

## トレース

HTTPリクエストから、ユースケース、DB、外部API、LLMの呼び出しまでを1本のトレースでつなぐ。Celeryのジョブにもトレースの文脈を引き継ぎ、APIで受けた操作が非同期処理のどこで遅れたかを追えるようにする。

## ダッシュボード、アラート、ヘルスチェック

- ダッシュボードはJSONでリポジトリに置き、起動時に自動で読み込む。最初に作るのは「API概要」「ジョブと同期」「LLM」の3枚。
- アラートはGrafanaからSlackへ通知する。条件の初期案は、エラー率が5分間5%を超える、同期ジョブが3回続けて失敗する、要再連携のアカウントが出る、LLMのp95レイテンシが通常の2倍を超える、の4つ。
- ヘルスチェックは、プロセスの生存を見る `/healthz` と、DB・Redis・Ollamaへの接続を見る `/readyz` に分ける。Docker Composeのhealthcheckに使い、AWS環境ではロードバランサーとECSのヘルスチェックに使う。
- ブラウザで起きたエラーは、最小限の情報だけをAPI経由でログに送る。

AWS環境では、AWS Distro for OpenTelemetry（ADOT）のCollectorを使い、送り先をCloudWatch LogsとX-Rayに変える。
