# 監視（ログ・メトリクス・トレース）の設計メモ

NF-19、ADR 0015（正式な記録は Issue「設計の記録を残す」で書く）。

## 方針
- 計装は **OpenTelemetry**。送信は **OTLP/HTTP**（`http/protobuf`）。
- ローカルの受け側は `grafana/otel-lgtm`（compose の `lgtm`）。会社のAWSでは ADOT に置き換える。
- **アプリのコードにバックエンド固有の設定を書かない。** 送信先は `OTEL_*` 環境変数だけで切り替える。

## 共通の設定（本物のAPI・worker・schedulerでもそのまま使う）
- 実装：`docker/stub/telemetry.py`（`setup(service)` が logger・tracer・meter を返す）。
- 依存：`opentelemetry-sdk` と `opentelemetry-exporter-otlp-proto-http`（`docker/stub/requirements.txt` で固定）。
- 環境変数（compose の `x-otel` で全サービスに共通で渡す）：

| 変数 | 値（ローカル） |
|---|---|
| `OTEL_SERVICE_NAME` | `api` / `worker` / `scheduler` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://lgtm:4318` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` |
| `OTEL_RESOURCE_ATTRIBUTES` | `deployment.environment.name=local` |
| `OTEL_METRIC_EXPORT_INTERVAL` | `10000`（ms） |

## ログ（構造化JSON）
標準出力に1行1JSON。同じ内容をOTLPでも送る（トレースIDはSDKが自動で付ける）。
```json
{"timestamp":"2026-11-23T10:00:00.123+00:00","level":"INFO","service":"api",
 "message":"request finished","request_id":"…","trace_id":"…","span_id":"…",
 "http":{"method":"GET","path":"/healthz","status":200,"duration_ms":1.2}}
```
- `request_id`：リクエストの `X-Request-ID` を使う。無ければ UUIDv4 を作る。レスポンスヘッダ `X-Request-ID` にも返す。
- `trace_id` / `span_id`：有効なスパンがあるときだけ入る（W3C Trace Context、16進）。
- コンテナのヘルスチェック（`X-Healthcheck` ヘッダ付き）は、テレメトリを送らない。

## データの扱い
- `lgtm` のデータは名前付きボリューム `lgtmdata`（`/data`）に残す。`make down` では消えない。消すときは `docker compose down -v`。
- 実測：`down` → `up` の後も、ログ（Loki）とメトリクス（Prometheus）は残った。**トレース（Tempo）は、再起動前の分が見えなかった**（停止の猶予を30秒に延ばしても未確認）。トレースは消える前提で使う。
- 公式は「開発・デモ・テスト用」としている。本番の保存先ではない。

## 安全
- Grafana は匿名で **Admin** になる（既定）。ポートは必ず `127.0.0.1` にだけ公開する。
- メモリ：`mem_limit: 3g`。起動直後の実測は約 0.8 GiB（負荷が増えると増える）。
