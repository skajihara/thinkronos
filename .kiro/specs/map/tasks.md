# Implementation Plan: マインドマップ編集（map）

## Overview

マインドマップ編集機能（MM-01〜MM-07、P1）の実装計画。バックエンド（マイグレーション → domain → ports → adapters → application → api）、フロントエンド（ストア・API → キュー・Undo → 描画 → IME → キーボード・組み立て）、テスト（性質テスト・E2E）の順に進める。

---

## Tasks

- [ ] 1. マイグレーション（mindmaps / nodes / map_operations / map_snapshots）
  - `mindmaps`、`nodes`、`map_operations`、`map_snapshots` テーブルを追加する Alembic マイグレーションファイルを `backend/migrations/versions/` に作成する
  - `mindmaps.root_node_id → nodes(map_id, id)` の外部キーを `DEFERRABLE INITIALLY DEFERRED` として定義する
  - 各テーブルに `ENABLE ROW LEVEL SECURITY` と `FORCE ROW LEVEL SECURITY` を設定し、`app_current_workspace_ids()` を使った USING / WITH CHECK ポリシーを付ける
  - `thinkronos_app` ロールへの必要な GRANT を付ける（`map_operations` は UPDATE 権限なし）
  - `map_operations` に `(map_id, seq)` の一意制約を追加する
  - `downgrade()` を実装し、`backend/tests/integration/` に適用 → 戻す → 再適用の結合テストを作成する
  - _要件: 1.2, 1.3, 1.5, 8.7, 8.9, 10.1_
  - _性質: Property 1, 3, 7, 8_
  - _依存: なし_

- [ ] 2. domain 層（エンティティ・ドメインルール）
  - [ ] 2.1 `Mindmap`、`Node`、`SortKey` のドメインエンティティ（frozen dataclass）を `backend/src/thinkronos/domain/` に作成する
    - `Node` にツリー先祖チェックによる循環検出ロジックを実装する
    - `SortKey` 値オブジェクトに形式バリデーション（非空文字列）を含める
    - ルートノードへの `delete_node` / `move_node` を検出したら `DomainError` を送出する関数を実装する
    - `seq` の単調増加チェック関数（`map_id` ごとに最後の `seq` より大きい値かを検証）を実装する
    - _要件: 2.8, 3.4, 3.6, 8.7_
  - [ ]* 2.2 Hypothesis を使った単体テストを `backend/tests/unit/` に作成する
    - **Property 2: 循環なし** — 任意の `move_node` 操作列を適用しても循環が生じないこと
    - **Property 3: ルート不変** — ルートノードへの操作が必ず `DomainError` を送出すること
    - **Property 8: seq 単調増加** — `seq` が必ず前の値より大きいことを検証すること
    - **Validates: Requirements 2.8, 3.4, 3.6, 8.7**
  - _性質: Property 2, 3, 8_
  - _依存: Task 1_

- [ ] 3. ports 層（リポジトリ・UoW の抽象）
  - `MapRepository`、`NodeRepository`、`MapOperationRepository`、`MapSnapshotRepository` のプロトコルを `backend/src/thinkronos/ports/` に作成する
  - `UnitOfWork` ポートに `begin()` で `set_config('app.user_id', ..., true)` と `set_config('app.workspace_ids', ..., true)` を呼ぶ抽象を定義する
  - `MapRepository.get_for_update(map_id)` のシグネチャに `SELECT FOR UPDATE` を使う旨を docstring で明記する
  - `MapOperationRepository.find_batch(map_id, batch_id)` のシグネチャを定義する（冪等性チェック用）
  - _要件: 8.5, 8.7, 10.3_
  - _性質: Property 1, 7, 8_
  - _依存: Task 2_

- [ ] 4. adapters 層（PostgreSQL 実装）
  - [ ] 4.1 `PgMapRepository`、`PgNodeRepository`、`PgMapOperationRepository`、`PgMapSnapshotRepository`、`PgUnitOfWork` を `backend/src/thinkronos/adapters/` に作成する
    - `PgUnitOfWork.begin()` で `set_config` を呼び RLS 文脈を設定する
    - `PgMapRepository.get_for_update()` は `SELECT ... FOR UPDATE` を発行する
    - _要件: 8.5, 8.7, 10.1, 10.3_
  - [ ]* 4.2 Testcontainers + `thinkronos/postgres:18` を使った結合テストを `backend/tests/integration/` に作成する
    - **Property 7: 認可** — 別ワークスペースのデータが見えないこと
    - **Property 1: 操作ログの冪等性** — 同じ `batch_id` を 2 回適用しても状態が変わらないこと
    - **Property 8: seq の一意性・単調増加** — `(map_id, seq)` の一意制約でシリアライズが保証されること
    - **Validates: Requirements 8.5, 8.7, 10.1, 10.3**
  - _性質: Property 1, 7, 8_
  - _依存: Task 3_

- [ ] 5. `ApplyOperationsUseCase`（バッチ適用・seq 採番・スナップショット）
  - [ ] 5.1 `ApplyOperationsUseCase` を `backend/src/thinkronos/application/` に作成する
    - UoW で `SELECT FOR UPDATE` を取得し RLS 文脈を設定する処理を実装する（design.md のシーケンス図に準拠）
    - `batch_id` の冪等性チェック（既存の場合は前回の結果を返す）を実装する
    - スナップショット自動保存条件（前回から 30 分以上 or 200 操作以上）の判定と保存を実装する
    - `create_node`・`delete_node`・`move_node`・`update_node`・`update_map` の検証と `nodes` / `node_links` への適用を実装する
    - 循環検出、ルート保護、テキスト 1,000 字超・ノード 2,000 個超の limit チェック、sort_key 重複検出を実装する
    - `seq` を採番して `map_operations` に追記し `last_seq` を更新する処理を実装する
    - 各操作の `inversePayload` を組み立ててレスポンスに含める処理を実装する
    - _要件: 2.8, 2.9, 2.10, 2.11, 2.12, 3.4, 3.5, 3.6, 3.7, 3.8, 8.5, 8.7, 8.9, 8.10_
  - [ ]* 5.2 Hypothesis 単体テストを `backend/tests/unit/` に作成する
    - **Property 1: 操作ログの冪等性** — 同じ `batch_id` を 2 回送っても状態が変わらないこと
    - **Property 2: 循環なし** — 任意の `move_node` 操作列を適用しても循環が生じないこと
    - **Property 3: ルート不変** — ルートへの `delete_node` / `move_node` が必ず拒否されること
    - **Property 8: seq 単調増加** — 採番後の seq が前の値より常に大きいこと
    - **Validates: Requirements 2.8, 3.4, 3.6, 8.5, 8.7**
  - _性質: Property 1, 2, 3, 6, 8_
  - _依存: Task 4_

- [ ] 6. 残りのユースケース（CreateMap / GetMap / DeleteMap / GetOperationsAfter）
  - [ ] 6.1 各ユースケースを `backend/src/thinkronos/application/` に作成する
    - `CreateMapUseCase`：マップと root_node を同一トランザクションで作成する（DEFERRABLE 外部キーを活用）
    - `ListMapsUseCase`：未削除・更新日時降順・カーソルページングで返す
    - `GetMapUseCase`：全ノード・つながり線含む取得。RLS で所属確認し非所属なら 404 を返す
    - `DeleteMapUseCase`：`mindmaps.deleted_at` を設定する論理削除を実装する
    - `GetOperationsAfterUseCase`：`after` 以降の操作を返す（追いつき API 用）
    - 各ユースケースの冒頭で所属ワークスペースの認可チェックを実装する
    - _要件: 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 9.1_
  - [ ]* 6.2 Hypothesis 結合テストを `backend/tests/integration/` に作成する
    - **Property 7: 認可** — 別ワークスペースへのアクセスが 404 になること
    - **Validates: Requirements 1.4, 1.5, 9.1**
  - _性質: Property 7_
  - _依存: Task 5_

- [ ] 7. API ルーター（maps_router）
  - [ ] 7.1 FastAPI ルーター `maps_router` と Pydantic スキーマを `backend/src/thinkronos/api/` に作成する
    - `MapResponse`、`MapCreateRequest`、`OperationBatchRequest`、`OperationBatchResponse` スキーマを定義する
    - `GET /api/v1/mindmaps`（カーソルページング）を実装する
    - `POST /api/v1/mindmaps`（冪等な作成）を実装する
    - `GET /api/v1/mindmaps/{mapId}`（ETag レスポンス付き）を実装する
    - `DELETE /api/v1/mindmaps/{mapId}`（204）を実装する
    - `POST /api/v1/mindmaps/{mapId}/operations`（バッチ適用、200）を実装する
    - `GET /api/v1/mindmaps/{mapId}/operations?after={seq}`（追いつき）を実装する
    - すべての 409 / 422 / 404 / 401 を RFC 9457 形式（`application/problem+json`）で返す
    - `make gen-openapi` で `openapi.json` を更新し差分を PR に含める
    - _要件: 1.1, 1.2, 1.3, 1.5, 1.7, 1.8, 2.8, 2.9, 2.10, 8.5, 8.7, 9.1, 10.2, 10.4_
  - [ ]* 7.2 Hypothesis 結合テストを `backend/tests/integration/` に作成する（Testcontainers）
    - **Property 1: 操作ログの冪等性** — API レベルで同じ `batch_id` を 2 回送っても状態が変わらないこと
    - **Property 3: ルート不変** — API がルートへの操作に必ず 409 を返すこと
    - **Property 7: 認可** — 別ワークスペースへのアクセスが 404 になること
    - **Property 8: seq 単調増加** — `(map_id, seq)` が一意で単調増加すること
    - **Validates: Requirements 1.5, 2.8, 3.6, 8.5, 8.7, 10.2**
  - _性質: Property 1, 3, 7, 8_
  - _依存: Task 6_

- [ ] 8. `mapEditorStore`（Zustand ストア）と `mapApi.ts`（TanStack Query）
  - [ ] 8.1 `src/features/map/store/mapEditorStore.ts` を作成する
    - `selectedNodeId`、`editingNodeId`、`isComposing`、`undoStack`、`redoStack`、`viewTransform`、`pendingOperations`、`isSending`、`lastAcknowledgedSeq` のフィールドを定義する
    - `selectNode`、`startEditing`、`stopEditing`、`setComposing`、`pushUndo`、`clearRedo`、`setViewTransform`、`enqueueBatch`、`acknowledgeBatch`、`rollbackBatch` のアクションを実装する
    - Zustand ストアはメモリのみ（永続化しない）
    - _要件: 7.1, 8.1_
  - [ ] 8.2 `src/features/map/api/mapApi.ts` を作成する
    - `useMapQuery`（`GET /mindmaps/{mapId}`）、`useMapListQuery`（`GET /mindmaps`）、`useCatchUpQuery`（`GET /mindmaps/{mapId}/operations`）を openapi-fetch で実装する
    - `openapi-typescript` で生成した型のみ使用し手書きの API 型は作らない
    - _要件: 1.1, 1.4, 9.1_
  - [ ]* 8.3 `src/features/map/store/mapEditorStore.test.ts` を作成する
    - **Property 5: Undo-Redo 可逆性（前提）** — `pushUndo`・`acknowledgeBatch`・`rollbackBatch` のスタック操作を fast-check で確認する
    - **Validates: Requirements 7.1, 7.2, 8.1**
  - _性質: Property 1, 5_
  - _依存: Task 7_

- [ ] 9. `useOperationQueue`（楽観的更新・キュー送信・rebase）
  - [ ] 9.1 `src/features/map/hooks/useOperationQueue.ts` を作成する
    - `isSending` フラグで1つずつ順に送信するキュー管理を実装する
    - 操作を TanStack Query のキャッシュに即時反映し成功時にキャッシュを確定する楽観的更新を実装する
    - `operationsAfter` の rebase（未送信バッチの操作の下に当て直す）を実装する
    - 409（sort-key-conflict）時に `fractional-indexing-jittered` で sort_key を作り直して自動再送する処理を実装する
    - 409（その他）/ 422 時にキューをすべてロールバックしサーバー状態を再取得する処理を実装する
    - 5xx / 通信失敗時に同じ `batch_id` で指数バックオフ再送する処理を実装する
    - `delete_node` の楽観的更新（枝全体のローカル削除と 409 時の復元）を実装する
    - _要件: 2.1, 2.2, 2.3, 7.2, 8.1, 8.2, 8.3, 8.3a, 8.5_
  - [ ]* 9.2 `src/features/map/hooks/useOperationQueue.test.ts` を fast-check で作成する
    - **Property 1: 操作ログの冪等性（前提）** — 送信列の順序保証・rebase・ロールバックの性質を確認する
    - **Property 4: sort_key 一意性** — sort_key 再生成後も兄弟内で重複しないことを確認する
    - **Validates: Requirements 3.7, 8.1, 8.2, 8.3, 8.5**
  - _性質: Property 1, 4, 5_
  - _依存: Task 8_

- [ ] 10. `useUndoStack`（Undo/Redo・`delete_node` の復元）
  - [ ] 10.1 `src/features/map/hooks/useUndoStack.ts` を作成する
    - `appliedOperations[*].inversePayload` から逆操作を組み立てて `undoStack` に積む処理を実装する
    - Undo：`intent = "undo"` で逆操作を POST し成功後に `redoStack` に移す処理を実装する
    - Redo：`intent = "redo"` で元操作を POST し成功後に `undoStack` に移す処理を実装する
    - 追いつき API からの操作が来てもスタックを変更しない処理を実装する
    - `delete_node` の Undo：`inversePayload` をもとに **親から子の順に** `create_node` を送信する処理を実装する
    - 送信前バッチの Undo：Undo バッチをキューの末尾に積み先行バッチの `inversePayload` 受信後に送信する処理を実装する
    - _要件: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 8.8_
  - [ ]* 10.2 `src/features/map/hooks/useUndoStack.test.ts` を fast-check で作成する
    - **Property 5: Undo-Redo 可逆性** — 任意の操作列で 操作 → Undo → Redo 後に元の状態に戻ることを確認する
    - **Validates: Requirements 7.2, 7.3, 7.4**
  - _性質: Property 5_
  - _依存: Task 9_

- [ ] 11. `MapCanvas` / `NodeElement` / `EdgeLayer`（描画基盤）
  - [ ] 11.1 `src/features/map/hooks/usePanZoom.ts` を作成する
    - `pointerdown` / `pointermove` / `pointerup` と `wheel` イベントを処理して `viewTransform` を更新する
    - `viewTransform`（scale, translateX, translateY）を `localStorage`（キー `thinkronos:map:{mapId}:view`）に保存・復元する
    - _要件: 5.5, 5.6, 5.7_
  - [ ] 11.2 `src/features/map/hooks/useAutoLayout.ts` を作成する
    - `d3-hierarchy` で左右展開レイアウト（左右均等）を計算する
    - 第1階層ノードの左右振り分けルール（左右の枝数の差が 0 または 1、同数のとき右優先）を実装する
    - `canvas.measureText()` で文字幅を測定しノード幅を算出する
    - ノードの追加・移動・折りたたみのたびにレイアウトを再計算する
    - _要件: 5.1, 5.2_
  - [ ] 11.3 `src/features/map/components/MapCanvas.tsx` を作成する
    - CSS `transform: translate() scale()` による pan/zoom コンテナを実装する（d3-zoom は使わない）
    - `usePanZoom.ts` を呼び出して `viewTransform` を適用する
    - _要件: 5.3, 5.4, 5.7_
  - [ ] 11.4 `src/features/map/components/NodeElement.tsx` を作成する
    - `<div>` の絶対配置で `left` / `top` を CSS で設定する
    - 選択状態・編集状態のスタイルを実装する
    - _要件: 5.1_
  - [ ] 11.5 `src/features/map/components/EdgeLayer.tsx` を作成する
    - 1 枚の `<svg>` を重ねて親子接続線を `<path>` で描画する（P1 は親子のみ）
    - _要件: 5.1_
  - [ ] 11.6 `src/features/map/components/CollapseToggle.tsx` を作成する
    - 子ノードが存在するときだけ表示する
    - 押すと `update_node`（`collapsed: !current_collapsed`）を送信する
    - 折りたたんだときに隠れた直接の子の数を表示する
    - _要件: 4.1, 4.3, 4.4_
  - [ ]* 11.7 `src/features/map/components/MapCanvas.test.tsx` を作成する
    - CSS transform のスナップショットテストで描画方式が ADR 0012 に従っていることを確認する
    - _要件: 5.7_
  - _性質: なし_
  - _依存: Task 8_

- [ ] 12. `EditableText` / `useImeComposition`（インライン編集・IME）
  - [ ] 12.1 `src/features/map/hooks/useImeComposition.ts` を作成する
    - `compositionstart` → `isComposing = true`、`compositionend` → `isComposing = false` を処理する
    - `keydown` の `keyCode === 229` の場合も IME 変換中として扱う
    - _要件: 2.4, 2.6b_
  - [ ] 12.2 `src/features/map/components/EditableText.tsx` を作成する
    - `<textarea>` を使いインライン編集を実装する
    - `compositionstart` / `compositionend` / `keydown` を処理し `useImeComposition` を呼び出す
    - 編集中の Enter（IME 変換中でなければ確定、兄弟は追加しない）を実装する
    - 編集中の Shift+Enter（トピック内改行）を実装する
    - 編集中の Tab（確定して子ノードを追加）を実装する
    - 編集中の Esc（変更を取り消して元のテキストに戻す）を実装する
    - _要件: 2.4, 2.5, 2.6, 2.6a, 2.6b_
  - [ ]* 12.3 `src/features/map/components/EditableText.test.tsx` を fast-check で作成する
    - **Property 4: sort_key 一意性（前提）** — `isComposing = true` の間は Enter でノードが増えないことを確認する
    - **Validates: Requirements 2.4, 2.6b**
  - _性質: なし_
  - _依存: Task 11_

- [ ] 13. `useKeyboardShortcuts` / `MapEditor`（キーボード操作・全体組み立て）
  - [ ] 13.1 `src/features/map/hooks/useKeyboardShortcuts.ts` を作成する
    - 矢印キー（左右：親子移動、上下：兄弟移動）の選択ノード移動を実装する
    - Tab/Insert（子ノード追加）、Enter（下兄弟追加）、Shift+Enter（上兄弟追加）を実装する
    - F2・文字入力（編集開始）、Esc（選択解除）、Delete（削除）、Space（折りたたみ切り替え）を実装する
    - Ctrl+↑ / Ctrl+↓（`move_node` による兄弟並べ替え）を実装する
    - Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z（Undo / Redo）を実装する
    - + / − / F6（ズームイン/アウト・中心に戻す）を実装する
    - `editingNodeId` が設定されている間はグローバルショートカットを無効化する
    - _要件: 3.3, 4.1, 6.1, 6.2, 6.3_
  - [ ] 13.2 `src/features/map/hooks/useCatchUp.ts` を作成する
    - マップを開いたときおよびブラウザタブがフォアグラウンドに戻ったときに CatchUpAPI を呼び出す
    - 30 秒ごとに定期的に CatchUpAPI を呼び出す
    - 受け取った操作を TanStack Query のキャッシュに反映する
    - _要件: 9.1, 9.2, 9.3_
  - [ ] 13.3 `src/features/map/components/MapList.tsx` を作成する
    - マップ一覧を更新日時降順・カーソルページングで表示する
    - マップ作成・削除ボタンを含める
    - _要件: 1.1, 1.3, 1.7_
  - [ ] 13.4 `src/features/map/components/MapEditor.tsx` と `src/features/map/hooks/useMapEditor.ts` を作成する
    - `MapCanvas`・`NodeElement`・`EdgeLayer`・`MapList` を組み合わせたエディタ全体のレイアウトを実装する
    - `useMapEditor.ts` で初期データ取得・CatchUp 起動・ストア初期化を行う
    - _要件: 1.1, 1.2, 2.1_
  - _性質: なし_
  - _依存: Task 10, Task 12_

- [ ] 14. 性質ベースのテスト（Hypothesis / fast-check）
  - [ ]* 14.1 Hypothesis 結合テスト（`backend/tests/integration/`）を作成する
    - **Property 1: 操作ログの冪等性** — 任意の有効なバッチを生成し同じ `batch_id` を 2 回送っても状態が変わらないことを確認する
    - **Validates: Requirements 8.5**
  - [ ]* 14.2 Hypothesis 結合テスト（`backend/tests/integration/`）を作成する
    - **Property 2: 循環なし** — ランダムなツリー構造と `move_node` 操作列を生成し循環が生じないことを確認する
    - **Validates: Requirements 3.4**
  - [ ]* 14.3 Hypothesis 結合テスト（`backend/tests/integration/`）を作成する
    - **Property 3: ルート不変** — ルートに対する `delete_node` / `move_node` が必ず 409 を返すことを確認する
    - **Validates: Requirements 2.8, 3.6**
  - [ ]* 14.4 Hypothesis 結合テスト（`backend/tests/integration/`）を作成する
    - **Property 6: スナップショット整合性** — スナップショット + それ以降の操作を再生した結果が `nodes` テーブルと一致することを確認する
    - **Validates: Requirements 8.9, 8.10**
  - [ ]* 14.5 Hypothesis 結合テスト（`backend/tests/integration/`）を作成する
    - **Property 7: 認可** — 別ワークスペースへのアクセスが 404 になり データを変更しないことを確認する
    - **Validates: Requirements 10.1, 10.2**
  - [ ]* 14.6 Hypothesis 結合テスト（`backend/tests/integration/`）を作成する
    - **Property 8: seq の一意性・単調増加** — 同時並行リクエストを送っても `seq` が一意で単調増加することを確認する
    - **Validates: Requirements 8.7**
  - [ ]* 14.7 fast-check 単体テスト（`frontend/src/features/map/`）を作成する
    - **Property 4: sort_key 一意性** — 任意の挿入・並べ替え列で兄弟の sort_key が重複しないことを確認する
    - **Validates: Requirements 3.2, 3.7**
  - [ ]* 14.8 fast-check 単体テスト（`frontend/src/features/map/`）を作成する
    - **Property 5: Undo-Redo 可逆性** — 任意の操作列で 操作 → Undo → Redo 後に元の状態に戻ることを確認する
    - **Validates: Requirements 7.2, 7.3, 7.4**
  - _性質: Property 1, 2, 3, 4, 5, 6, 7, 8_
  - _依存: Task 7, Task 10_

- [ ] 15. E2E テスト（スモーク・キーボード・Undo）
  - [ ]* 15.1 `frontend/e2e/create-map.spec.ts`（スモーク E2E）を作成する
    - ログイン → マップ作成 → 中心ノードの確認 → Tab でノード追加 → テキスト入力のフローを実装する
    - ページ再読み込み後にノードが残っていることを確認する
    - _要件: 1.1, 1.2, 2.1_
  - [ ]* 15.2 `frontend/e2e/keyboard-operations.spec.ts`（MM-06）を作成する
    - Tab / Enter / Shift+Enter でノードを追加できることを確認する
    - Delete でノードと子孫が消えることを確認する
    - Ctrl+↑ / Ctrl+↓ で兄弟の順番が変わることを確認する
    - 矢印キーで選択が移動することを確認する
    - _要件: 2.7, 6.1_
  - [ ]* 15.3 `frontend/e2e/undo-redo.spec.ts`（MM-07）を作成する
    - 操作後に Ctrl+Z でノードが消えることを確認する（Property 5）
    - Ctrl+Y で戻ることを確認する（Property 5）
    - `delete_node` → Undo で枝が復元されることを確認する（Property 3）
    - ページ再読み込み後に Undo スタックが消えていることを確認する
    - _要件: 7.1, 7.3, 7.4_
  - _性質: Property 3, 5_
  - _依存: Task 13, Task 14_

---

## Notes

- `*` が付いたサブタスクはオプション扱いであり MVP のためスキップ可能
- 各タスクは 1 PR に収まる大きさ（目安 3〜6 時間）を想定している
- バックエンドのテストは `thinkronos_app` ロールで接続し RLS が有効な状態で実行する（ADR 0035、I-01）
- `openapi.json` の更新（Task 7）は、`make gen-openapi` と `make gen-types` を同じ PR でコミットする（C-28）
- Property テストは結合テストで Testcontainers を使い本物の PostgreSQL 18 に対して実行する
- E2E テストの LLM 呼び出しはモックにする（I-07）

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2", "3"] },
    { "id": 3, "tasks": ["4.1"] },
    { "id": 4, "tasks": ["4.2", "5.1"] },
    { "id": 5, "tasks": ["5.2", "6.1"] },
    { "id": 6, "tasks": ["6.2", "7.1"] },
    { "id": 7, "tasks": ["7.2", "8.1", "8.2"] },
    { "id": 8, "tasks": ["8.3", "9.1", "11.1", "11.2"] },
    { "id": 9, "tasks": ["9.2", "10.1", "11.3", "11.4", "11.5", "11.6"] },
    { "id": 10, "tasks": ["10.2", "11.7", "12.1"] },
    { "id": 11, "tasks": ["12.2"] },
    { "id": 12, "tasks": ["12.3", "13.1", "13.2", "13.3", "13.4"] },
    { "id": 13, "tasks": ["14.1", "14.2", "14.3", "14.4", "14.5", "14.6", "14.7", "14.8"] },
    { "id": 14, "tasks": ["15.1", "15.2", "15.3"] }
  ]
}
```
