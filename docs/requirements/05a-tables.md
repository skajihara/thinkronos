<!-- 正本はこのファイル。企画書（Claude Docs）から 2026-11-23 に移した（K-01）。変更はPRで行う。 -->

# テーブル定義と操作ログの仕様

テーマ5（データ構造の詳細）の成果物。本体の「データ設計」を、列の型、制約、索引まで落とし込む。根拠はD-01、D-12〜D-17、D-19〜D-22、C-09。版は本体（要件定義書）の版に合わせる。

## 共通の約束

| 項目 | 約束 |
| --- | --- |
| 型 | 主キーはuuid（UUIDv7、C-08）。日時はtimestamptz（UTC、D-04）。列挙値はtextとCHECK制約で表す。形の決まっていない属性はjsonb |
| 時刻の列 | created\_atとupdated\_atは必須で、既定値はnow()。updated\_atはアプリで更新する |
| 論理削除 | deleted\_at（D-03）。論理削除するテーブルの一意制約は、deleted\_at IS NULLの部分一意索引にする |
| 同じ親の中に限る | 子は(workspace\_id, map\_id)や(map\_id, parent\_id)などの複合外部キーで親を指し、参照先には複合の一意制約を置く（D-17） |
| 索引 | 外部キーの列には索引を付ける（先頭の列が同じ索引で兼ねる場合を除く）。そのほかは下の「主なアクセスパターン」から決める |
| 並び順 | sort\_keyはCOLLATE "C"（D-17） |
| RLS | 表の「RLS」の列で、Wはworkspace\_idのポリシー（P1）、Uはuser\_idのポリシー（P2）、―は対象外（D-14）。ポリシーが行自身の値だけを見るよう、子テーブルにもworkspace\_idやuser\_idを持たせる。Wのポリシーは workspace\_id = ANY(所属の一覧) の形にする（D-19） |
| 権限 | 追記だけのテーブル（map\_operations、audit\_logs）は、アプリのロールにUPDATEの権限を与えない |
| 削除時の動作 | マップの完全削除（MM-19）では、子のテーブルも一緒に消す（ON DELETE CASCADE）。利用者の削除と連携の解除はD-10で確定する。複合外部キーで一部の列だけNULLにするときは、列を指定したON DELETE SET NULL（PostgreSQL 15以上）を使う |
| 名前 | 制約と索引の名前は実装規約2.7に従う |
| 保持期間 | job\_runsとllm\_callsは180日、audit\_logsは1年残し、定期ジョブで削除する（D-22） |

## 主なアクセスパターン

| 処理 | 条件 | 使う索引 |
| --- | --- | --- |
| マップ一覧 | workspace\_id、未削除、更新日時の新しい順 | mindmaps (workspace\_id, updated\_at)の部分索引 |
| マップを開く | map\_idの全ノードとつながり線 | nodes (map\_id, id)、node\_links (map\_id, source\_node\_id) |
| 操作に追いつく | map\_idで、seqがbaseSeqより大きい | map\_operations (map\_id, seq) |
| 再送されたまとまりの判定 | map\_idとbatch\_id | map\_operations (map\_id, batch\_id) |
| 版の一覧と復元 | map\_idで、seqの新しい順 | map\_snapshots (map\_id, seq) |
| マップ内の検索（MM-09） | textの部分一致 | nodes (text)のpg\_bigm（GIN） |
| 意味の近いトピック（AI-06） | model\_idごとの近傍検索 | node\_embeddingsのHNSW（モデルごと） |
| タスク一覧（TK-03） | workspace\_id、状態、期限 | tasks (workspace\_id, status, due\_at) |
| カレンダー表示と空き時間 | user\_idと期間 | scheduled\_blocks (user\_id, start\_at)、calendar\_events (user\_id, start\_at) |
| 同期の取り込み | calendar\_idと外部ID | calendar\_events (calendar\_id, external\_event\_id) |

## テーブル定義

表の読み方：列は「列名 型」で書き、型の後ろの「?」はNULL可、PKは主キー、FKは外部キー。created\_at、updated\_atは型を省いた（timestamptz）。

### 認証・利用者

| テーブル | 列 | 制約と索引 | RLS |
| --- | --- | --- | --- |
| users | id uuid PK、email text、password\_hash text、display\_name text、timezone text、email\_verified\_at timestamptz?、status text、created\_at、updated\_at、deleted\_at timestamptz? | 一意索引：lower(email)。CHECK：statusはpending・active・suspended・deleted（suspendedは管理者による停止。一時的なロックはRedisで持つ、C-20）。timezoneはIANAの名前（例：Asia/Tokyo） | ― |
| user\_settings | user\_id uuid PK FK、work\_hours jsonb、buffer\_minutes integer、notify\_time time?、notify\_channels jsonb、default\_write\_calendar\_id uuid?、updated\_at | FK：(user\_id, default\_write\_calendar\_id)→calendars(user\_id, id)。削除時は default\_write\_calendar\_id だけをNULLにする。CHECK：buffer\_minutes ≥ 0 | ― |
| refresh\_tokens | id uuid PK、user\_id uuid FK、token\_hash text、family\_id uuid、expires\_at timestamptz、revoked\_at timestamptz?、created\_at | 一意：token\_hash。索引：user\_id、family\_id | ― |
| email\_tokens | id uuid PK、user\_id uuid FK、purpose text、token\_hash text、expires\_at timestamptz、used\_at timestamptz?、created\_at | 一意：token\_hash。CHECK：purposeはverify\_email・reset\_password。索引：user\_id | ― |
| api\_tokens | id uuid PK、user\_id uuid FK、name text、token\_hash text、scopes text\[]、last\_used\_at timestamptz?、expires\_at timestamptz?、revoked\_at timestamptz?、created\_at | 一意：token\_hash。索引：user\_id | ― |
| audit\_logs | id uuid PK、user\_id uuid?、workspace\_id uuid?、action text、target\_type text?、target\_id uuid?、metadata jsonb、created\_at | 対象が消えても記録を残すため、user\_idとworkspace\_idは外部キーにしない（扱いはD-10で確定）。索引：(user\_id, created\_at)、(workspace\_id, created\_at)。追記だけ | ― |

### ワークスペース

| テーブル | 列 | 制約と索引 | RLS |
| --- | --- | --- | --- |
| workspaces | id uuid PK、name text、kind text、created\_by uuid FK、created\_at、updated\_at | CHECK：kindはpersonal・shared。部分一意：created\_by（kind = personalのとき。個人用は1人に1つ） | ―（選ぶ前のワークスペースも一覧で読むため。所属の確認はworkspace\_membersで行う） |
| workspace\_members | workspace\_id uuid FK、user\_id uuid FK、role text、joined\_at timestamptz | PK：(workspace\_id, user\_id)。CHECK：roleはowner・editor・viewer。索引：user\_id | W（workspace\_idが今のワークスペース、またはuser\_idが自分） |

### マップ

| テーブル | 列 | 制約と索引 | RLS |
| --- | --- | --- | --- |
| mindmaps | id uuid PK、workspace\_id uuid FK、title text、layout text、root\_node\_id uuid、last\_seq bigint、created\_by uuid FK、created\_at、updated\_at、deleted\_at timestamptz? | 一意：(workspace\_id, id)。FK：(id, root\_node\_id)→nodes(map\_id, id)（マップとルートを同じトランザクションで作るため、検査はコミット時に遅らせる）。CHECK：layoutはmindmap・org\_chart・list、last\_seq ≥ 0。部分索引：(workspace\_id, updated\_at)（未削除） | W |
| nodes | id uuid PK、workspace\_id uuid、map\_id uuid、parent\_id uuid?、sort\_key text（COLLATE "C"）、text text、note text?、style jsonb、collapsed boolean、is\_floating boolean、position\_x double precision?、position\_y double precision?、created\_by uuid FK、updated\_by uuid FK、created\_at、updated\_at、deleted\_at timestamptz? | 一意：(map\_id, id)、(workspace\_id, id)。FK：(workspace\_id, map\_id)→mindmaps、(map\_id, parent\_id)→nodes(map\_id, id)。部分一意：ルートはマップに1つ（parent\_idがNULL、浮いていない、未削除）、兄弟のsort\_key（parent\_idがNULLでない、未削除）。CHECK：浮いたトピックは親を持たずに座標を持ち、それ以外は座標を持たない。索引：(map\_id, parent\_id)、textのpg\_bigm（GIN） | W |
| node\_links | id uuid PK、workspace\_id uuid、map\_id uuid、source\_node\_id uuid、target\_node\_id uuid、label text?、style jsonb、created\_by uuid FK、created\_at、updated\_at、deleted\_at timestamptz? | FK：(workspace\_id, map\_id)→mindmaps、(map\_id, source\_node\_id)と(map\_id, target\_node\_id)→nodes(map\_id, id)。CHECK：source\_node\_idとtarget\_node\_idは違う。部分一意：(map\_id, source\_node\_id, target\_node\_id)（未削除。向きの違う組は別とする）。索引：(map\_id, target\_node\_id) | W |
| attachments | id uuid PK、workspace\_id uuid、node\_id uuid、storage\_key text、content\_type text、size\_bytes bigint、created\_by uuid FK、created\_at、deleted\_at timestamptz? | 一意：storage\_key。FK：(workspace\_id, node\_id)→nodes(workspace\_id, id)。CHECK：size\_bytes > 0（上限はD-06） | W |
| map\_operations | id uuid PK（クライアントが生成）、workspace\_id uuid、map\_id uuid、seq bigint、batch\_id uuid、actor\_user\_id uuid FK、client\_id text、origin text、intent text?、op\_type text、op\_version smallint、llm\_call\_id uuid?、payload jsonb、inverse\_payload jsonb、created\_at | 一意：(map\_id, seq)。FK：(workspace\_id, map\_id)→mindmaps。CHECK：seq > 0、originはuser・ai・import・restore、op\_typeは下の8種類。索引：(map\_id, batch\_id)。追記だけ | W |
| map\_snapshots | id uuid PK、workspace\_id uuid、map\_id uuid、seq bigint、kind text、label text?、format\_version smallint、content jsonb、created\_by uuid?、created\_at | FK：(workspace\_id, map\_id)→mindmaps。CHECK：kindはauto・named、namedのときだけlabelを持つ。索引：(map\_id, seq) | W |
| node\_embeddings | node\_id uuid、model\_id text、workspace\_id uuid、dimension integer、embedding vector、source\_hash text、updated\_at | PK：(node\_id, model\_id)。FK：(workspace\_id, node\_id)→nodes(workspace\_id, id)。CHECK：vector\_dims(embedding) = dimension。HNSWの索引は、モデルごとに次元を指定した式索引と部分索引で作る | W |

### タスク・予定

| テーブル | 列 | 制約と索引 | RLS |
| --- | --- | --- | --- |
| tasks | id uuid PK、workspace\_id uuid FK、node\_id uuid?、title text、estimate\_minutes integer?、due\_on date?、priority text、status text、assignee\_user\_id uuid? FK、created\_by uuid FK、created\_at、updated\_at、completed\_at timestamptz?、deleted\_at timestamptz?、version integer | 一意：(workspace\_id, id)。FK：(workspace\_id, node\_id)→nodes(workspace\_id, id)（マップの完全削除時は node\_id だけをNULLにする）。部分一意：node\_id（NULLでなく未削除。ノードと1対1）。CHECK：estimate\_minutes > 0、priorityはhigh・medium・low、statusはtodo・scheduled・done（TK-02）、doneのときだけcompleted\_atを持つ。部分索引：(workspace\_id, status, due\_at)（未削除） | W |
| scheduled\_blocks | id uuid PK、workspace\_id uuid、task\_id uuid、user\_id uuid FK、calendar\_id uuid?、start\_at timestamptz、end\_at timestamptz、status text、proposal\_reason text?、external\_event\_id text?、created\_at、updated\_at、version integer | FK：(workspace\_id, task\_id)→tasks(workspace\_id, id)、(user\_id, calendar\_id)→calendars(user\_id, id)（連携の解除時は calendar\_id だけをNULLにする）。CHECK：end\_at > start\_at、statusはproposed・approved・synced・sync\_failed・cancelled・unlinked。部分一意：(calendar\_id, external\_event\_id)（external\_event\_idがあるとき）。索引：(user\_id, start\_at)、task\_id | W |

### 外部連携

| テーブル | 列 | 制約と索引 | RLS |
| --- | --- | --- | --- |
| integration\_accounts | id uuid PK、user\_id uuid FK、provider text、external\_account\_id text、account\_label text、granted\_scopes text\[]、access\_token\_enc bytea、refresh\_token\_enc bytea?、token\_key\_id text、expires\_at timestamptz?、status text、last\_error text?、settings jsonb、connected\_at timestamptz、updated\_at | 部分一意：(provider, external\_account\_id)（解除済みを除く）。一意：(user\_id, id)。CHECK：providerはgoogle・microsoft・slack・notion・github、statusはactive・reauth\_required・revoked。索引：user\_id | U |
| calendars | id uuid PK、user\_id uuid、integration\_account\_id uuid、external\_calendar\_id text、name text、color text?、is\_primary boolean、sync\_enabled boolean、include\_in\_free\_busy boolean、can\_write boolean、created\_at、updated\_at | 一意：(integration\_account\_id, external\_calendar\_id)、(user\_id, id)。FK：(user\_id, integration\_account\_id)→integration\_accounts(user\_id, id) | U |
| calendar\_events | id uuid PK、user\_id uuid、calendar\_id uuid、external\_event\_id text、etag text、start\_at timestamptz?、end\_at timestamptz?、start\_date date?、end\_date date?、all\_day boolean、summary text?、recurring\_event\_id text?、transparency text、status text、updated\_at | 一意：(calendar\_id, external\_event\_id)。FK：(user\_id, calendar\_id)→calendars(user\_id, id)。CHECK：終日の予定はstart\_dateとend\_dateを、それ以外はstart\_atとend\_atを持つ（D-20）。end\_at ≥ start\_at、transparencyはopaque・transparent、statusはconfirmed・tentative・cancelled。索引：(user\_id, start\_at)、(user\_id, start\_date) | U |
| sync\_states | calendar\_id uuid PK、user\_id uuid、cursor text?、last\_synced\_at timestamptz?、consecutive\_failures integer、last\_error text?、updated\_at | FK：(user\_id, calendar\_id)→calendars(user\_id, id) | U |
| push\_subscriptions | id uuid PK、user\_id uuid FK、endpoint text、p256dh text、auth\_enc bytea、created\_at | 一意：endpoint。索引：user\_id。authの値は暗号化して持つ（共通ルール） | U |

### 運用

| テーブル | 列 | 制約と索引 | RLS |
| --- | --- | --- | --- |
| job\_runs | id uuid PK、user\_id uuid?、type text、status text、attempts integer、last\_error text?、created\_at、started\_at timestamptz?、finished\_at timestamptz? | CHECK：statusはqueued・running・succeeded・failed。索引：(user\_id, created\_at)。部分索引：status（queued・runningのとき） | ― |
| llm\_calls | id uuid PK、user\_id uuid?、purpose text、provider text、model text、input\_tokens integer、output\_tokens integer、latency\_ms integer、result\_count integer?、created\_at | 索引：(user\_id, created\_at)、created\_at | ― |
| holidays | date date PK、name text、updated\_at | 内閣府の祝日CSVを定期取得して入れ替える（CL-06） | ―（全利用者で共有） |

## 操作ログの仕様

根拠はD-13（サーバーが順序を決め、項目単位で後勝ち）、D-15（操作の形とUndo）、C-09（マップは操作API）。

### 操作の種類

| op\_type | payload | inverse\_payload | 拒否する条件（409） |
| --- | --- | --- | --- |
| create\_node | 新しいノードの全項目（id、親、sort\_key、text、note、style、collapsed、is\_floating、座標） | 作ったノードのid | 親が存在しない、削除済み、別のマップにある。同じidの削除されていないノードがある |
| delete\_node | id | 適用の時点で消した枝のすべてのノードとつながり線の、削除前の全項目 | ルートを消そうとした |
| move\_node | id、新しい親、新しいsort\_key（必ず一緒に送る） | 元の親とsort\_key | 循環ができる。親が削除済み。ルートを動かそうとした |
| update\_node | id、変わった項目と新しい値 | 同じ項目の元の値 | ノードが存在しない、削除済み |
| create\_link | つながり線の全項目 | 作ったつながり線のid | 両端が同じ。端のノードが存在しない、削除済み |
| delete\_link | id | 削除前の全項目 | ― |
| update\_link | id、変わった項目と新しい値 | 同じ項目の元の値 | つながり線が存在しない、削除済み |
| update\_map | 変わった項目（title、layout） | 同じ項目の元の値 | ― |

### 規則

- delete\_nodeは枝ごと消す。サーバーは、適用の時点の子孫をクライアントが知らないものも含めてすべて論理削除し、端のノードが消えるつながり線も一緒に論理削除する。
- create\_nodeで、論理削除されたノードと同じidを指定したときは、復活として扱う（UndoとRedoで使う）。
- update\_node、update\_link、move\_nodeは項目単位で後勝ち（D-13）。同じ項目への変更は、seqの大きいほうが残る。
- 1つのまとまり（batch）は、すべて適用するか、1つも適用しないかのどちらかにする。1つのまとまりの上限は1,000操作。
- 同じbatch\_idのまとまりが再送されたら、適用せずに前回の結果を返す。

### 適用の手順

1. トランザクションを始め、RLSのために、所属するワークスペースの一覧とuser\_idを設定する（D-19）。
2. mindmapsの行をロックし（SELECT … FOR UPDATE）、last\_seqを読む。
3. 自動の版の条件（前回の操作から30分以上空いた、または前回の版から200操作）を満たしていれば、今の状態をmap\_snapshotsに保存する（D-16）。
4. まとまりの操作を順に検証してnodesとnode\_linksに適用し、seqを採番してmap\_operationsに追記する。
5. mindmaps.last\_seqを更新してコミットする。
6. 採番したseqと、baseSeqより後のほかの操作を返す。

### スナップショットと復元（D-16）

- contentは、その時点の未削除のノードとつながり線の全項目と、マップの項目（title、layout）を持つJSON。形式の版はformat\_versionで表す。
- seqは、その版が反映している最後の操作の番号。
- 版は自動（auto）と名前付き（named）の2種類で、すべて残す。操作ログも消さない。
- 復元は、選んだ版と今の状態の差分を、origin = restoreのまとまりとして追記する。復元そのものもUndoできる。

### Undoの約束（D-15）

- クライアントは、送ったまとまりの逆の操作をUndoのスタックに積む。Undoはそれを新しいまとまり（intent = undo）として送る。Redoも同じ（intent = redo）。
- ほかのタブや利用者の操作を受け取っても、自分のスタックは消さない。項目単位の後勝ちなので、Undoで戻るのは自分が変えた項目だけになる。
- ページを再読み込みするとスタックは消える。それより前に戻すときは、版の復元を使う。
