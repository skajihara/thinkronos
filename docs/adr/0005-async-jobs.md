# 0005 非同期ジョブの基盤（Celery＋Redis と、async のユースケースの動かし方）

## 状態

承認済み、2026-11-23

## 背景

LLM の呼び出しや、カレンダーとの同期など、時間のかかる処理を API の外で動かす基盤が要る（G-22）。アプリのユースケースは `async def` で書く（SQLAlchemy の async、asyncpg、Strands の `invoke_async`）。決める必要があったのは次の2点。

- ジョブの基盤（キューとワーカー、定期実行）
- Celery の同期のタスクから、async のユースケースをどう実行するか

## 比べた選択肢

**基盤**：Celery＋Redis ／ 別のキュー（arq、Taskiq、Dramatiq）。

**async のユースケースの動かし方**

| 案 | 内容 |
|---|---|
| A | 同期のタスクの中で `asyncio.run(...)` を呼ぶ。タスクごとに新しいイベントループを作って閉じる。DB の接続は使い回さない（NullPool） |
| B | ワーカーのプロセスごとに `asyncio.Runner` を1つ持ち、ループを使い回す。DB の接続はプールで使い回す |
| C | 非公式の拡張（celery-pool-asyncio、acelery、aio-celery、celery-asyncio）で `async def` のタスクを書く |
| D | async に対応した別のキューにする |

## 決定

- 基盤は **Celery＋Redis**（ブローカーと結果の保存先）。定期実行は **celery beat**（compose の `scheduler`）。
- async のユースケースは **A 案**で動かす（`WORKER_ASYNC_MODE=run`、既定）。B 案もコードに残し、環境変数で切り替えられる（`runner`）。
- タスクは薄いアダプターにする。引数（JSON）を application のコマンドに直し、ユースケースを実行するだけにする（`thinkronos/worker/app.py`）。

## 理由

- Celery 5.7.0（2026-11-05）の公式の文書（タスクのページ、FAQ、5.7 の What's new）には、`async def` のタスクや asyncio についての記述が**見つからなかった**。公式が示す async への対応方法も無い（[Tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html)、[FAQ](https://docs.celeryq.dev/en/stable/faq.html)、[What's new in 5.7](https://docs.celeryq.dev/en/stable/history/whatsnew-5.7.html)）。そのため、Celery の標準の機能だけで済む A・B を比べ、C は採らなかった（Celery 本体の更新に追従し続けるかを確認できない）。
- Celery＋Redis：Redis は compose に既にあり、会社の AWS では ElastiCache で置き換えられる見込み（AWS 側は未確認）。定期実行（beat）、再試行、遅延実行を標準で持つ。D は Celery を前提にした要件（G-22）から外れるので、A・B で足りないときの代替として記録だけする（D の各ライブラリは評価していない）。
- A と B を、同じユースケース（ワークスペースの名前を変える）で試した（`backend/tests/unit/test_worker.py`、`backend/tests/integration/test_worker_db.py`）。

| 確認 | A（run） | B（runner） |
|---|---|---|
| タスク10件を続けて流して、すべて成功し、DB に反映される | 通過 | 通過 |
| イベントループ | タスクごとに別のループ（10個）で、終わると閉じる | 1つのループを使い回す |
| DB の接続（タスクの実行中の数の増え方） | 増えない（NullPool。タスクが終わると閉じる） | 1本まで（プールで使い回す） |
| 接続の失敗（`ConnectionError`）は再試行し、3回目に成功する | 通過 | （同じタスクの定義なので同じ） |
| 見えない行（`WorkspaceNotFound`）・入力の誤りは再試行しない | 通過 | （同じ） |
| API の `X-Request-ID` がタスクのログの `request_id` に引き継がれる | 通過 | 通過 |

- A を選んだ理由：
  - タスクの間で、ループや接続の状態が残らない。asyncpg の接続はそれを作ったイベントループに結び付くので、B ではループと接続の寿命をプロセスと揃える必要がある。prefork の fork の前に作ったものを子に持ち込まない、などの注意が要る（今の実装は、最初のタスクで作るので避けている）。
  - B のループは同時に1つの `run` しか受け付けないので、スレッドのプール（`--pool threads`）ではロックで直列になる。A にはこの制約が無い。
  - A のコストは、タスクごとのループの作成と DB への接続。このアプリのタスクは LLM の呼び出しなど秒単位のものが中心なので、無視できると見込んだ（**計測はしていない**）。
- B に切り替える目安：短いタスクが大量に流れ、接続の作成が目立つようになったとき。切り替えは `WORKER_ASYNC_MODE=runner` で、bootstrap がプールありのエンジンに変える。

## 影響

- ワーカーのエンジンは A では NullPool。DB の接続数は、同時に動くタスクの数まで増える（`--concurrency` で上限を決める）。
- 監視は、プロセスごとに1回設定する（prefork の子は fork の後の `worker_process_init`、beat は `beat_init`）。タスクのスパン（トレース）はまだ出していない。ログ（`task started`／`task finished`）と `request_id` だけ。Celery 自身のログは JSON ではない。
- `@app.task(shared=False)` にしている。既定ではプロセスの中のすべての Celery アプリにタスクが共有され、同じ名前の2つ目が無視される（テストで2つのアプリを作ったときに起きた）。
- ワーカーの死活確認は `celery inspect ping`。beat は HTTP を持たないので、PID 1 が beat であることだけを見る。
- 実際の Redis を使った確認は compose（`make up` の後に `python -m thinkronos.cli rename …`）で行う。CI のテストはブローカーに `memory://` を使う。
- タスクの冪等性（同じタスクが2回届いたとき）は、`task_acks_late` を有効にしているので必要になる。各タスクで考える（名前を変えるタスクは、同じ名前に2回変えても同じ結果になる）。

## 参照

- Issue #13
- [0035](0035-backend-foundation.md)（層、Unit of Work、RLS）
- [0032](0032-local-llm-and-embedding.md)（Strands Agents、qwen3:8b）
