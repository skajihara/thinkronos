# 0015 可観測性の基盤

## 状態

承認済み、2026-11-23（企画書の決定 J-01 を記録したもの）

## 背景

API とワーカーのログ・メトリクス・トレースを、ローカルで見たい。ジョブの失敗（Googleの同期、通知）を追い、LLMの呼び出しの時間を測りたい。P4 では AWS に移すので、計装はそのまま使いたい（移植性）。

## 比べた選択肢

| 案 | 特徴 |
|---|---|
| ベンダーのSDK（Datadog、New Relic など） | 機能が多い。有料で、ローカルで完結しない。AWSへの移行で計装を替える |
| Prometheus＋Grafana＋Loki＋Tempo を個別に構成 | 柔軟。コンテナと設定が多い |
| OpenTelemetry＋grafana/otel-lgtm（1つのコンテナ） | 計装は標準の OpenTelemetry。ローカルは1つのコンテナで、ログ・メトリクス・トレースを Grafana で見られる |

## 決定

OpenTelemetry で計装し、ローカルは `grafana/otel-lgtm`（0.41.1）に OTLP で送る。AWS環境では、AWS Distro for OpenTelemetry（ADOT）の Collector で CloudWatch Logs と X-Ray に送る。

## 理由

- 計装のコードは OpenTelemetry の標準だけに依存し、送り先は環境変数で替えられる。
- ローカルは `make up` と `make grafana` で、追加の設定なしに見られる。
- 無料で、個人開発の費用が増えない。

## 影響

- ログは構造化（JSON）し、トレースのIDを入れる。運用の手順は `docs/observability.md`。
- `otel-lgtm` は開発用で、データの保存と性能は本番向けではない。
- ダッシュボード（「API概要」、REDメトリクス）は P1 の実装計画 5-1 で作る。

## 参照

- J-01、`docs/observability.md`、`docs/requirements/09-observability.md`、Issue「監視の最小構成を作る」
