# Requirements Document

## Introduction

本文書は、マインドマップ編集機能（P1）の要件を定義する。対象は MM-01〜MM-07 で、マップの管理（MM-01）、ノードの編集（MM-02）、ノードの移動（MM-03）、折りたたみ（MM-04）、自動レイアウト・ズーム・パン（MM-05）、キーボード操作（MM-06）、Undo/Redo（MM-07）を含む。設計の詳細は `.kiro/specs/map/design.md` を参照する。機能要件の上流 ID（MM-xx）は `docs/requirements/01-features.md` に、データ設計の決定（D-xx）は `docs/decisions.md` に、テーブル定義は `docs/requirements/05a-tables.md` に定義されている。

変更履歴の保持（D-02）、共同編集への備え（A-02、D-13）、行レベルセキュリティ（D-14）はP1から有効にする。

---

## Glossary

- **System**：Thinkronos アプリケーション全体（バックエンド API とフロントエンド React アプリ）
- **MapEditor**：マップ編集機能のフロントエンドコンポーネント群
- **API**：バックエンドの FastAPI エンドポイント
- **Node**：マインドマップの各トピック。`nodes` テーブルの1行に対応する
- **RootNode**：マップに1つだけ存在する中心のトピック（`mindmaps.root_node_id` が指すノード）
- **Batch**：1回の操作送信単位。`batch_id`（UUIDv7）でまとめられた操作の集まり
- **UndoStack**：MapEditor がメモリ上で保持する Undo 操作のスタック
- **RedoStack**：MapEditor がメモリ上で保持する Redo 操作のスタック
- **OperationQueue**：MapEditor が保持する未送信バッチの列。先頭から順に1つずつ送信する
- **ViewTransform**：ズーム倍率（scale）と平行移動量（translateX、translateY）の組
- **SortKey**：兄弟ノードの並び順を表す文字列（COLLATE "C"、分数インデックス方式、D-01）
- **OptimisticUpdate**：サーバーの返事を待たずにクライアントの状態に即時反映すること
- **CatchUpAPI**：`GET /api/v1/mindmaps/{mapId}/operations?after={seq}` で他の操作を取り込む追いつき API

---

## Requirements

### Requirement 1: マップの管理

**User Story:** As a ユーザー、I want マップを作成・一覧・名前変更・削除できる、so that 自分のマインドマップを整理できる。（MM-01）

#### Acceptance Criteria

1. WHEN マップ一覧を取得するとき、THE System SHALL 未削除のマップを更新日時の新しい順に返す。
2. WHEN マップを新規作成するとき、THE System SHALL マップと RootNode を同一トランザクション内で作成し、`mindmaps.root_node_id` が有効なノード ID を指す状態でコミットする。
3. WHEN マップを削除するとき、THE System SHALL `mindmaps.deleted_at` を設定する論理削除を行い、マップを一覧から除外する。P1 では UI から復元できないが、データはDBに残る（MM-19 は PX）。
4. WHEN 認証済みユーザーが自分のワークスペースに属するマップへアクセスするとき、THE System SHALL そのマップのデータを返す。(AU-03)
5. IF マップが存在しない、または要求したユーザーが所属しないワークスペースのマップへアクセスするとき、THEN THE System SHALL 404 を返す。(AU-03、D-14)
6. WHEN ユーザーがマップの名前を変えるとき、THE MapEditor SHALL `update_map` 操作として OperationQueue から送信する。名前の変更専用のAPIは作らない（操作ログに残し、Undo できるようにする。D-15）。
7. THE System SHALL カーソルページング方式（`cursor`・`limit`）でマップ一覧を返す（`GET /api/v1/mindmaps`）。
8. WHEN マップを削除するとき、THE API SHALL `DELETE /api/v1/mindmaps/{mapId}` で受け付け、204 を返す。

---

### Requirement 2: ノードの編集

**User Story:** As a ユーザー、I want ノードを追加・編集・削除できる、so that マインドマップの内容を作成・更新できる。（MM-02）

#### Acceptance Criteria

1. WHEN ノードを選択中に Tab キーを押すとき、THE MapEditor SHALL そのノードの子ノードを楽観的に追加し（OptimisticUpdate）、サーバーへの送信を待たずに EditableText にフォーカスする。(NF-02)
2. WHEN ノードを選択中に Enter キーを押すとき（IME 変換中でないとき）、THE MapEditor SHALL そのノードの下に兄弟ノードを楽観的に追加し EditableText にフォーカスする。
3. WHEN ノードを選択中に Shift+Enter を押すとき（IME 変換中でないとき）、THE MapEditor SHALL そのノードの上に兄弟ノードを楽観的に追加し EditableText にフォーカスする。
4. WHILE IME 変換中（`isComposing = true`）に Enter キーを受信するとき、THE MapEditor SHALL 変換確定として処理し、ノードを追加しない。
5. WHEN ノードのテキストをダブルクリックするか F2 キーを押すとき、THE MapEditor SHALL そのノードのインライン編集を開始する。また選択中に文字入力を始めた場合も、既存テキストを上書きして編集を開始する。
6. WHEN 編集中に Esc キーを押すとき、THE MapEditor SHALL 編集を取り消しテキストを変更前に戻す。
6a. WHEN 編集中（IME 変換中でないとき）に Enter を押すとき、THE MapEditor SHALL 入力を確定して編集を終える（兄弟は追加しない）。Shift+Enter はトピック内の改行とする。Tab は入力を確定し、子ノードを追加して編集を始める。
6b. WHILE IME 変換中（`isComposing = true`、または `keydown` の `keyCode` が 229）のとき、THE MapEditor SHALL Enter・Shift+Enter・Tab・Esc・矢印を含むすべてのショートカットを処理しない。
7. WHEN ノードを選択中に Delete キーを押すとき、THE MapEditor SHALL そのノードと子孫をすべて削除する（`delete_node` 操作を送信する）。
8. IF `delete_node` 操作の対象が RootNode であるとき、THEN THE API SHALL 409 `/problems/root-node-immutable` を返す。
9. IF `create_node` または `update_node` 操作においてテキストが 1,000 字を超えるとき、THEN THE API SHALL 422 `/problems/limit-exceeded` を返す。
10. IF マップのノード総数が 2,000 個を超えた状態で `create_node` 操作が来るとき、THEN THE API SHALL 422 `/problems/limit-exceeded` を返す。
11. WHEN `create_node` 操作が成功するとき、THE API SHALL そのノードの `inversePayload`（作成したノードの id）を `appliedOperations` に含めてレスポンスする。
12. WHEN `delete_node` 操作が成功するとき、THE API SHALL 削除した枝の全ノードとつながり線の削除前の全項目を `inversePayload` として `appliedOperations` に含めてレスポンスする。

---

### Requirement 3: ノードの移動

**User Story:** As a ユーザー、I want ノードをドラッグして親を付け替えたり兄弟の順番を変えたりできる、so that マインドマップの構造を整理できる。（MM-03）

#### Acceptance Criteria

1. WHEN ユーザーがノードをドラッグして別のノードの上で離すとき、THE MapEditor SHALL そのノードの `parent_id` を変更する `move_node` 操作を楽観的に適用してから OperationQueue に積む。
2. WHEN ユーザーがノードを兄弟間にドロップするとき、THE MapEditor SHALL `fractional-indexing-jittered`（CC0）ライブラリを使って新しい SortKey を生成し、`move_node` 操作に含める。
3. WHEN Ctrl+↑ または Ctrl+↓ キーを押すとき、THE MapEditor SHALL ノードを兄弟の中で1つ上または下に移動する `move_node` 操作を送信する。
4. IF `move_node` 操作が循環する移動（ノードを自分の子孫の下へ移動）であるとき、THEN THE API SHALL 409 `/problems/circular-reference` を返し、THE MapEditor SHALL 楽観的更新をロールバックして元の位置に戻す。
5. IF `move_node` 操作において新しい親が削除済みであるとき、THEN THE API SHALL 409 `/problems/invalid-parent` を返す。
6. IF `move_node` 操作の対象が RootNode であるとき、THEN THE API SHALL 409 `/problems/root-node-immutable` を返す。
7. IF `move_node` 操作における新しい SortKey が兄弟内で重複するとき、THEN THE API SHALL 409 `/problems/sort-key-conflict` を返し、THE MapEditor SHALL SortKey を作り直して自動的に再送する。
8. WHEN `move_node` 操作が成功するとき、THE API SHALL 元の `parent_id` と `sort_key` を `inversePayload` として `appliedOperations` に含めてレスポンスする。

---

### Requirement 4: 折りたたみ

**User Story:** As a ユーザー、I want 枝を折りたたんで展開できる、so that 大きなマップを見やすく整理できる。（MM-04）

#### Acceptance Criteria

1. WHEN ユーザーが CollapseToggle ボタンを押すか、ノード選択中に Space キーを押すとき、THE MapEditor SHALL `update_node` 操作（payload: `{ id, collapsed: !current_collapsed }`）を送信し、折りたたみ状態を反転させる。
2. WHEN `update_node` 操作が成功するとき、THE API SHALL `nodes.collapsed` を更新して永続化する。これにより折りたたみ状態は次回マップを開いたときにも維持される。(MM-04)
3. WHILE `collapsed = true` のノードを表示するとき、THE MapEditor SHALL そのノードの子孫を非表示にし、隠れている直接の子ノードの数をノード上に表示する。
4. THE MapEditor SHALL 子ノードが存在しないノードには CollapseToggle を表示しない。

---

### Requirement 5: 自動レイアウト・ズーム・パン

**User Story:** As a ユーザー、I want マップを自動で整列して表示し、ズームやパンで見る位置を変えられる、so that マップ全体を把握しやすい。（MM-05）

#### Acceptance Criteria

1. THE MapEditor SHALL `d3-hierarchy` ライブラリを使って左右展開（左右に均等）のツリーレイアウトを計算し、ノードの追加・移動・折りたたみのたびに再計算する。
2. WHEN 新しい第1階層ノードを追加するとき、THE MapEditor SHALL 左右の枝の数が均等になるように交互に割り振る（左右の枝数の差が 0 または 1）。同数のときは右優先とする。
3. WHEN ユーザーがマウスホイールを操作するか、ピンチ操作をするとき、THE MapEditor SHALL ズーム倍率を変更する。
4. WHEN ユーザーが何もないキャンバス上でドラッグするとき、THE MapEditor SHALL マップをパンする。
5. WHEN ViewTransform が変化するとき、THE MapEditor SHALL `thinkronos:map:{mapId}:view` のキーで `localStorage` に保存する。
6. WHEN マップを開くとき、THE MapEditor SHALL `localStorage` から ViewTransform を復元する。別の端末・別のブラウザで開く場合は中心位置・デフォルトスケールから表示する。
7. THE MapEditor SHALL pan/zoom を自前の Pointer Events で実装する（`d3-zoom` は使わない）。(ADR 0012)
8. THE MapEditor SHALL `+`/`-` キーでズームを変更し、F6 キーでマップを中心に戻す。

---

### Requirement 6: キーボード操作

**User Story:** As a ユーザー、I want キーボードだけでマップを操作できる、so that マウスなしでも効率的に編集できる。（MM-06）

#### Acceptance Criteria

1. THE MapEditor SHALL MindMeister 準拠（B-08）の以下のキーボードショートカットを実装する：

   | キー | 動作 |
   |------|------|
   | Tab / Insert | 選択ノードの子ノードを追加 |
   | Enter | 選択ノードの下に兄弟ノードを追加 |
   | Shift+Enter | 選択ノードの上に兄弟ノードを追加 |
   | F2、または文字入力 | 選択ノードの編集を開始 |
   | Esc | 編集取り消し／選択解除 |
   | Delete | 選択ノードと子孫を削除 |
   | Space | 選択ノードの折りたたみ切り替え |
   | ↑↓←→ | 隣のノードへ選択を移す（左右は親子、上下は兄弟） |
   | Ctrl+↑ / Ctrl+↓ | 兄弟の中の順番を入れ替え |
   | Ctrl+Z | Undo（元に戻す） |
   | Ctrl+Y / Ctrl+Shift+Z | Redo（やり直す） |
   | + / − | ズームイン / ズームアウト |
   | F6 | マップを中心に戻す |

2. WHILE `editingNodeId` が設定されているとき（編集中）、THE MapEditor SHALL 矢印キー・Delete・Space・Ctrl+Z/Y などのグローバルショートカットを無効化する。
3. WHILE `editingNodeId` が設定されているとき（編集中）、THE MapEditor SHALL Enter・Shift+Enter・Tab・Esc は `EditableText` 側でのみ処理する。

---

### Requirement 7: Undo / Redo

**User Story:** As a ユーザー、I want 操作を元に戻したりやり直したりできる、so that 誤操作から素早く回復できる。（MM-07）

#### Acceptance Criteria

1. THE MapEditor SHALL UndoStack と RedoStack をブラウザのメモリ上にのみ保持する（`localStorage` やサーバーへの保存は行わない）。ページを再読み込みするとスタックが消える。(D-15)
2. WHEN 操作バッチが成功するとき、THE MapEditor SHALL サーバーが返した `appliedOperations[*].inversePayload` を使って UndoStack にバッチを積み、RedoStack をクリアする。
3. WHEN ユーザーが Ctrl+Z を押すとき（UndoStack が空でないとき）、THE MapEditor SHALL UndoStack の先頭バッチの逆操作を `intent = "undo"` として POST し、成功後にそのバッチを RedoStack に移す。
4. WHEN ユーザーが Ctrl+Y（または Ctrl+Shift+Z）を押すとき（RedoStack が空でないとき）、THE MapEditor SHALL RedoStack の先頭バッチの操作を `intent = "redo"` として POST し、成功後にそのバッチを UndoStack に移す。
5. WHEN CatchUpAPI から他ユーザーの操作が届くとき、THE MapEditor SHALL UndoStack と RedoStack を変更しない。(D-15)
6. WHEN `delete_node` を Undo するとき、THE MapEditor SHALL サーバーから受け取った `inversePayload` をもとに、**親から子の順に** `create_node` 操作（同一 id で論理削除ノードを復活）を送信する。(D-15)

---

### Requirement 8: 操作送信の共通動作

**User Story:** As a ユーザー、I want マップへの変更が確実にサーバーに保存される、so that データを失わずに編集できる。

#### Acceptance Criteria

1. THE MapEditor SHALL OperationQueue に積まれたバッチを先頭から1つずつ順に送信する。前のバッチの返事を受け取るまで次のバッチを送信しない。
2. WHEN バッチ送信が成功（200）するとき、THE MapEditor SHALL レスポンスの `operationsAfter` を受け取り、未送信バッチの操作の下に当て直す（rebase）。
3. IF バッチ送信が 409（`/problems/sort-key-conflict` を除く）または 422 で拒否されるとき、THEN THE MapEditor SHALL そのバッチ以降のキューをすべてロールバックし、`GET /api/v1/mindmaps/{mapId}` でサーバーの状態を再取得し、拒否の理由を知らせる。
3a. IF バッチ送信が通信の失敗または 5xx で失敗するとき、THEN THE MapEditor SHALL 画面の状態を戻さず、同じ `batch_id` で間隔を延ばしながら再送する（8.5 の冪等性により二重に適用されない）。再送を続けている間は、保存できていないことを画面に示す。
4. THE MapEditor SHALL オフライン時に操作をサーバーへ送信しない（通信が切れている間は操作が保存されない。ADR 0016）。
5. WHEN 同一の `batch_id` のバッチが再送されるとき、THE API SHALL そのバッチを再適用せず、前回の結果を返す（冪等性）。(D-15)
6. IF 1 バッチの操作数が 1,000 件を超えるとき、THEN THE API SHALL 422 `/problems/batch-too-large` を返す。
7. THE API SHALL `seq` をマップ内で一意かつ単調増加の整数として採番する。サーバーは `mindmaps` の行を `SELECT FOR UPDATE` でロックしてから `seq` を採番し、`(map_id, seq)` の一意制約で保証する（`docs/requirements/05a-tables.md` の適用の手順）。
8. WHEN 送信前のバッチの Undo が押されるとき、THE MapEditor SHALL Undo のバッチを OperationQueue の後ろに積み、前のバッチの返事（inversePayload）を受け取ってから送信する。
9. WHEN 前回のスナップショットから200操作以上、または前回の操作から30分以上空いて操作を適用するとき、THE API SHALL 適用の前の状態を自動のスナップショット（kind = auto）として同じトランザクションで保存する。(D-16)
10. THE API SHALL スナップショットとそれ以降の操作を順に再生すると、状態テーブル（nodes）と一致する形で操作ログを記録する。(D-02、D-12)

---

### Requirement 9: 追いつき API

**User Story:** As a ユーザー、I want 別のタブや将来の別ユーザーの変更を取り込める、so that 最新のマップ状態を見られる。(A-02、D-13)

#### Acceptance Criteria

1. THE MapEditor SHALL マップを開いたときおよびブラウザタブがフォアグラウンドに戻ったとき、CatchUpAPI（`GET /api/v1/mindmaps/{mapId}/operations?after={lastAcknowledgedSeq}`）を呼び出す。
2. THE MapEditor SHALL 30 秒ごとに定期的に CatchUpAPI を呼び出す。
3. WHEN CatchUpAPI が他のタブや利用者の操作を返すとき、THE MapEditor SHALL 受け取った操作を TanStack Query のキャッシュに反映し、未送信の自分の操作をその上に当て直す（8.2 と同じ）。
4. WHEN 同一のプロパティ（例：ノードのテキスト）を複数の場所から変更したとき、THE System SHALL `seq` の大きいほうの値を残す（項目単位の後勝ち、D-13）。

---

### Requirement 10: セキュリティ・認可

**User Story:** As a ユーザー、I want 自分のワークスペースのマップだけにアクセスできる、so that 他人のデータにアクセスされない。(AU-03)

#### Acceptance Criteria

1. THE API SHALL すべてのリクエストに対し、RLS（`workspace_id = ANY(app_current_workspace_ids())`）で所属確認を行う。(D-14、D-19)
2. IF 要求したユーザーが所属しないワークスペースのマップへアクセスするとき、THEN THE API SHALL マップの存在を知らせないため 404 を返す。(AU-03)
3. WHEN `PgUnitOfWork.begin()` を呼び出すとき、THE API SHALL `set_config('app.user_id', ..., true)` と `set_config('app.workspace_ids', ..., true)` をトランザクション内で設定する（`is_local = true`、D-19）。
4. THE API SHALL 未認証のリクエストに対して 401 を返す。

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

テストツール：
- バックエンド（Python）：**Hypothesis**
- フロントエンド（TypeScript）：**fast-check**

### Property 1：操作ログの冪等性

*For any* 操作バッチと `batch_id`、同じ `batch_id` を持つバッチを 2 回送信した場合、2 回目の送信後の `nodes` テーブルと `map_operations` テーブルの状態が、1 回目の送信後と同一である。

**Validates: Requirements 8.5**

**テストツール**：Hypothesis（結合テスト）

### Property 2：循環なし

*For any* ノードのツリー構造と `move_node` 操作の列、任意の順序でその操作列を適用しても、いかなるノードも自分の子孫の下に移動されない（循環が生じない）。

**Validates: Requirements 3.4**

**テストツール**：Hypothesis（単体テスト：domain 層の循環検出）

### Property 3：ルート不変

*For any* マップの RootNode に対して `delete_node` または `move_node` 操作を送信したとき、THE API は必ず 409 を返す。

**Validates: Requirements 2.8, 3.6**

**テストツール**：Hypothesis（結合テスト）

### Property 4：sort_key 一意性

*For any* ノードの挿入・並べ替え操作の列を適用した後、同じ親を持つ兄弟ノードの間で `sort_key` が重複しない。

**Validates: Requirements 3.2, 3.7**

**テストツール**：fast-check（フロントエンド単体テスト）

### Property 5：Undo-Redo 可逆性

*For any* 操作列（同一タブ、外部割り込みなし）に対して、操作 → Undo → Redo の順に実行すると、Redo 後の状態が操作後の状態と一致する。

**Validates: Requirements 7.2, 7.3, 7.4**

**テストツール**：fast-check（フロントエンド）+ Hypothesis（バックエンド結合テスト）

### Property 6：スナップショット整合性

*For any* スナップショットとそれ以降の操作列を組み合わせて再生した結果が、現在の `nodes` テーブルの状態と一致する。

**Validates: Requirements 8.9, 8.10**

**テストツール**：Hypothesis（結合テスト）

### Property 7：認可

*For any* ユーザーと、そのユーザーが所属しないワークスペースのマップへの操作リクエスト、THE API は RLS により 404 を返し、データを変更しない。

**Validates: Requirements 10.1, 10.2**

**テストツール**：Hypothesis（結合テスト）

### Property 8：seq の一意性・単調増加

*For any* マップへの操作バッチ列において、`map_operations` テーブルに記録された `(map_id, seq)` の組はすべて一意であり、同じマップ内での `seq` は単調増加する。

**Validates: Requirements 8.7**

**テストツール**：Hypothesis（結合テスト）
