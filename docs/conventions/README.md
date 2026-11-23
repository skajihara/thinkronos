# 実装規約

<!-- 正本はこのファイル。企画書（Claude Docs）から 2026-11-23 に移した（K-01）。変更はPRで行う。 -->


## 1. 基本方針と適用範囲

この規約は、人が書くコードとAI（Claude Code、Kiro）が書くコードの両方に適用する。自動で検査できる規則は必ずツールで検査し（11章）、人の注意力に頼る規則は最小限にする。

- 規約の正はこの文書とする。開発開始時にリポジトリの `docs/conventions/` に移す。AIツール向けの指示の正はリポジトリ直下の `AGENTS.md` とし、中身は短くして `docs/conventions/` を指す。`CLAUDE.md` は `@AGENTS.md` を取り込み、Claude Code専用の指示だけを足す。`.kiro/steering/` には、Kiro専用の指示と `docs/` へのファイル参照だけを置く（G-10）。
- 迷ったときの優先順位は、安全性（セキュリティ、データの整合性）、読みやすさ、一貫性、性能の順。
- 規約を変えるときはIssueとPRで行い、変更の理由を残す。
- 要件定義書と矛盾する場合は、要件定義書を優先し、この規約を直す。

### 言語の使い分け（決定済み）

| 対象 | 言語 |
| --- | --- |
| 識別子（変数、関数、クラス、ファイル名など） | 英語 |
| コードのコメント、docstring | 英語 |
| コミットメッセージ、PRタイトル | 英語（Conventional Commits） |
| PR本文、Issue、ADR、設計文書 | 日本語 |
| UIの文言 | 日本語（A-07） |
| ログのメッセージ | 英語 |
| エラー応答のtitleとdetail | 英語。画面に出す文言は、フロントでエラーの種類から日本語に変換する |

## 2. 命名規則

言語やツールの標準の慣習に従い、Thinkronos独自の規則は最小限にする。同じ概念には、どの層でも同じ英単語を使う（例：作業枠は層を問わず scheduled block）。

### 2.1 ディレクトリ

- トップレベルは `backend/`、`frontend/`、`infra/`、`docs/`、`.github/`、`.kiro/` の6つ。
- ディレクトリ名は小文字とハイフン（kebab-case）。ただしPythonのパッケージは小文字とアンダースコア（snake\_case）。
- 文書は `docs/adr/`、`docs/conventions/`、`docs/requirements/` に分ける。

### 2.2 ファイル

| 種類 | 規則 | 例 |
| --- | --- | --- |
| Pythonのモジュール | snake\_case.py | map\_service.py |
| Pythonのテスト | test\_<対象>.py | test\_map\_service.py |
| Reactのコンポーネント | PascalCase.tsx。shadcn/ui の CLI が作る `src/shared/ui/` の部品は CLI の名前のまま（ADR 0036） | MapCanvas.tsx |
| Reactのフック | use<名前>.ts | useMapOperations.ts |
| そのほかのTypeScript | camelCase.ts | apiClient.ts |
| TypeScriptのテスト | <対象>.test.ts(x) | MapCanvas.test.tsx |
| E2Eテスト | <シナリオ>.spec.ts（kebab-case） | create-map.spec.ts |
| マイグレーション | <自動生成のID>\_\<snake\_caseの説明>.py | 3f2a\_add\_node\_links.py |
| ADR | NNNN-\<kebab-case>.md | 0008-authentication.md |
| プロンプト | prompts/<機能>/<名前>.v<版>.md | prompts/map/suggest\_children.v1.md |
| GitHub Actions | kebab-case.yml | branch-policy.yml |
| 環境変数のひな形 | .env.example（.env はコミットしない） | ― |

### 2.3 ブランチ（決定済み）

| 種類 | 規則 | 例 |
| --- | --- | --- |
| 機能・修正 | feature/\<Issue番号>-\<kebab-case> | feature/12-node-reorder |
| リリース | release/vX.Y.0 | release/v0.1.0 |
| 緊急修正 | hotfix/vX.Y.Z | hotfix/v0.1.1 |

### 2.4 コミットとPRタイトル

- 形式は `<type>(<scope>): <summary>`。英語の命令形、小文字で始め、末尾にピリオドを付けず、72文字以内にする。
- typeは feat、fix、refactor、perf、docs、test、chore、ci、build、revert の10種類。
- scopeの案（G-04で確定する）：auth、map、node、task、calendar、schedule、sync、ai、notify、mcp、pwa、api、db、infra、ci、docs。
- 破壊的な変更は `feat(api)!: ...` のように `!` を付け、本文に `BREAKING CHANGE:` を書く。
- 例：`feat(map): add floating topics`、`fix(sync): retry on 429 from google calendar`

### 2.5 Python

| 対象 | 規則 | 例 |
| --- | --- | --- |
| 変数、関数、メソッド | snake\_case | find\_free\_slots |
| クラス | PascalCase。略語はPEP 8に従い大文字のまま | ScheduledBlock、LLMPort |
| 定数 | UPPER\_SNAKE\_CASE | MAX\_LOGIN\_ATTEMPTS |
| 非公開のもの | 先頭に \_ | \_build\_query |
| 真偽値 | is\_、has\_、can\_ で始める | is\_floating |
| ポート（抽象） | <役割>Port | CalendarPort、NotifierPort |
| アダプター | <実装><役割>Adapter | GoogleCalendarAdapter |
| ユースケース | <動詞><名詞>UseCase | ProposeScheduleUseCase |
| リポジトリ | <エンティティ>Repository | NodeRepository |
| APIの入出力スキーマ | <リソース><用途> | NodeCreateRequest、NodeResponse |
| 例外 | <内容>Error | IntegrationRequiredError |

### 2.6 TypeScriptとReact

| 対象 | 規則 | 例 |
| --- | --- | --- |
| 変数、関数 | camelCase | findFreeSlots |
| 型、コンポーネント | PascalCase。型にIやTの接頭辞を付けない | MapNode、MapCanvas |
| 略語 | 1つの単語として扱う | apiClient、HttpError、LlmCall |
| 定数（モジュール直下の不変の値） | UPPER\_SNAKE\_CASE | MAX\_NODE\_DEPTH |
| 真偽値 | is、has、can で始める | isFloating |
| イベント | 処理する関数は handle<事象>、propsは on<事象> | handleDrop、onDrop |
| propsの型 | <コンポーネント名>Props | MapCanvasProps |
| 列挙 | enumは使わず、文字列リテラルの合併型にする | type TaskStatus = 'todo' \| 'scheduled' \| 'done' |

### 2.7 DB

| 対象 | 規則 | 例 |
| --- | --- | --- |
| テーブル | snake\_caseの複数形 | scheduled\_blocks |
| 列 | snake\_caseの単数形 | external\_event\_id |
| 主キー | id（UUIDv7） | ― |
| 外部キー | <参照先の単数形>\_id | map\_id |
| 日時 | <過去分詞>\_at（timestamptz） | created\_at、deleted\_at |
| 日付だけの値 | <名詞>\_on（date） | due\_on |
| 真偽値 | is\_、has\_、can\_ で始める | can\_write |
| 暗号化した値、ハッシュ | \_enc、\_hash の接尾辞 | access\_token\_enc、token\_hash |
| 列挙の値 | snake\_caseの文字列＋CHECK制約。PostgreSQLのENUM型は使わない | 'needs\_reauth' |
| 制約、インデックス | pk\_<表>、fk\_<表>*<列>*<参照先>、uq\_<表>*<列>、ck*<表>*<名前>、ix*<表>\_<列> | SQLAlchemyのnaming\_conventionで自動で付ける。PostgreSQLの名前の上限は63文字 |

### 2.8 API

- パスは `/api/v1/<リソースの複数形>`。複数語のリソースはkebab-case（例：`/api/v1/scheduled-blocks`）。
- パスパラメータとクエリパラメータはcamelCase（例：`/api/v1/mindmaps/{mapId}/nodes?pageSize=50`）。
- OpenAPIはコードから生成する（コードファースト）。生成した `openapi.json` をコミットし、CIで実装との差分がないことを確かめる。画面側の型は同じ定義から生成し、手で書かない（C-28）。
- ワークスペースはパスに含めない。サーバーが利用者の所属するワークスペースの一覧を引き、RLSに設定する（D-19）。
- JSONのプロパティはcamelCase（決定済み）。Python側はsnake\_caseで書き、Pydanticの別名生成で自動変換する。
- 列挙の値はsnake\_caseの文字列で、DBと同じ値を使う。
- 日時はISO 8601のUTC（末尾にZ）、IDはUUIDの文字列。
- エラーの種類（type）は `/problems/<kebab-case>`（例：`/problems/integration-required`）。

### 2.9 環境変数と設定

- UPPER\_SNAKE\_CASE。アプリ独自の変数には `THINKRONOS_` を付ける（例：`THINKRONOS_LLM_PROVIDER`。要件定義書の `LLM_PROVIDER` はこの名前で実装する）。
- 外部ツールが決めている変数名はそのまま使う（例：`OTEL_EXPORTER_OTLP_ENDPOINT`）。
- 秘密情報は `.env` だけに書き、`.env.example` にはダミーの値を入れる。

### 2.10 Dockerとコンテナ

- Composeのサービス名はkebab-case：api、worker、scheduler、web、postgres、redis、ollama、mailpit、otel-lgtm。
- イメージ名は `ghcr.io/<owner>/thinkronos-<サービス名>:<タグ>`。
- ファイル名は `compose.yaml`、`compose.prod.yaml`。監視基盤は profile `observability`。

### 2.11 ログ、メトリクス、識別名

| 対象 | 規則 | 例 |
| --- | --- | --- |
| ログのイベント名 | <領域>.<対象>.<動作>（小文字、ドット区切り） | sync.calendar.completed、auth.login.failed |
| メトリクス名 | thinkronos.<領域>.<名前>。単位は名前に含めず属性で持つ | thinkronos.sync.duration |
| ケイパビリティ | <領域>.<操作> | calendar.write |
| 操作ログの種類 | <動詞>\_<名詞>（snake\_case） | create\_node、move\_node、update\_node |
| SSEのイベント名 | kebab-case | message-delta、done、error |

### 2.12 テスト

- Python：`test_<対象>_<条件>_<期待する結果>`（例：`test_find_free_slots_with_overlapping_events_excludes_busy_time`）。
- TypeScript：`describe('<対象>')` と `it('<振る舞いを英語の文で>')`。
- E2E：ファイル名はシナリオ名、テスト名は `user can ...` の形。

## 3. アーキテクチャ規約

バックエンドはポート＆アダプターで作り、依存は必ず内側（domain）に向ける。この規則はimport-linterでCIが検査し、違反したPRはマージできない。

### 3.1 レイヤーとimportの規則

| レイヤー | importしてよいもの | importしてはいけないもの |
| --- | --- | --- |
| domain | 標準ライブラリ、domainの中 | FastAPI、SQLAlchemy、Pydantic、Strands、各種SDK、ほかのすべてのレイヤー |
| application | domain、ports | adapters、api、worker、フレームワーク |
| ports | domain | adapters、フレームワーク |
| adapters | ports、domain、外部のライブラリ | api、application、worker |
| api | application、自分のスキーマ | adapters（組み立て場所を除く） |
| worker | application | adapters（組み立て場所を除く） |
| mcp | 自分のAPIクライアントと設定 | application、adapters、domain（APIを経由して操作する。C-22） |

- 組み立て場所（`app/bootstrap.py`）だけは、すべてのレイヤーをimportしてよい。環境変数を読み、ポートにアダプターを結び付ける役割に限る。
- domainのエンティティと値オブジェクトは、標準の `dataclasses`（frozen）で書く。Pydanticはapiの入出力にだけ使う。

### 3.2 ユースケース

- 1つのユースケースを1つのクラスにし、`execute()` だけを公開する。入力は `<名前>Command`、出力は `<名前>Result` のdataclassにする。
- トランザクションの境界はユースケースにする（Unit of Workをポートとして渡す）。
- Unit of Workは、トランザクションを始めるときに `set_config` で `app.user_id` と `app.workspace_ids`（所属するワークスペースの一覧）を設定する。トランザクションの外でDBを読まない（D-19）。
- ノードとタスクのように集約をまたぐ操作は、1つのユースケース・1つのトランザクションにまとめる（D-21）。
- 認可（ワークスペースへの所属、ケイパビリティ）は、ユースケースの最初で判定する。
- 現在時刻は直接取らず、`ClockPort` から受け取る。テストで時刻を固定するため。

### 3.3 フロントエンドの構成

- `src/features/<機能>/` に機能ごとのコンポーネント、フック、APIの呼び出しをまとめる（例：features/map、features/calendar）。
- 機能をまたいで使うものだけを `src/shared/` に置く。features同士は直接importせず、sharedを経由する。この規則はdependency-cruiserで検査する。
- APIの型は、OpenAPI定義から生成したもの（openapi-typescript）だけを使い、手で書かない。

## 4. Pythonの規約

型を必ず書き、フォーマットと静的解析はツールに任せる。人が判断するのは、設計とエラー処理の書き方だけにする。

| 項目 | 規則 |
| --- | --- |
| バージョン | P0の時点の最新の安定版に固定し、`.python-version` と `pyproject.toml` で管理する。パッケージはuvで管理する |
| フォーマットとLint | Ruff（formatとlint）。1行は100文字まで |
| 型 | すべての関数に型注釈を書く。domainとapplicationはmypyのstrictモード、それ以外は標準の設定。`Any` は使わない |
| 例外 | 業務ルールの違反は `DomainError` を基底にした例外で表す。api層でRFC 9457のエラー応答に変換する。`except:` だけの捕捉と、例外の握りつぶしは禁止 |
| 非同期 | I/Oはasyncで書く。async関数の中でブロッキングI/Oを呼ばない。重い計算はワーカーに回す |
| 依存の受け取り方 | コンストラクタで受け取る。グローバル変数やシングルトンを直接参照しない。設定はpydantic-settingsの `Settings` を経由する |
| 日時 | タイムゾーン付きの日時だけを使う（UTC）。タイムゾーンなしの日時は禁止。日付だけの値（期限、終日の予定）はdate型で持ち、利用者のタイムゾーンで解釈する（D-20） |
| ID | UUIDv7の生成は共通の関数を使う |
| ログ | structlogを使い、`print` は禁止 |
| docstring | 公開する関数とクラスに英語で書く（Googleスタイル） |
| 1ファイルの大きさ | 400行を超えたら分割を検討する |

## 5. TypeScript・Reactの規約

型の抜け道（any、無理な型アサーション）を作らないことと、状態の置き場所を決めておくことの2つを特に重視する。

| 項目 | 規則 |
| --- | --- |
| 型の設定 | tsconfigで `strict` と `noUncheckedIndexedAccess` を有効にする |
| any | 禁止。型が分からない値は `unknown` で受けて絞り込む。型アサーション（as）は最小限にし、使う理由をコメントに書く |
| コンポーネント | 関数コンポーネントだけを使う。1ファイルに1コンポーネント。名前付きexportにし、default exportは使わない（フレームワークが求める場合を除く） |
| 状態の置き場所 | サーバーのデータはTanStack Query、エディタの中の状態はZustand（C-11、ADR 0036）。グローバルな状態は増やさない |
| useEffect | データの取得には使わない（TanStack Queryを使う）。外部との同期だけに使う |
| スタイル | Tailwind CSSのユーティリティとデザイントークンを使う。任意の値（例：`w-[137px]`）は多用しない |
| UIの文言 | コンポーネントに直接書かず、`src/shared/messages/ja.ts` に集める |
| アクセシビリティ | 押せる要素にはbuttonかaを使い、divにクリックを付けない。キーボードだけで操作できるようにする |
| フォーム | 入力の検証はスキーマ（Zod）で書き、APIの型と揃える |
| フォーマットとLint | Prettier、ESLint（typescript-eslint、react-hooks、jsx-a11y） |

## 6. APIの規約

APIはリソース指向のRESTで設計し、FastAPIが出力するOpenAPI定義を契約の正とする。OpenAPI定義はリポジトリにコミットし、変更はPRで差分としてレビューする。

### 6.1 メソッドとステータスコード

| 操作 | メソッド | 成功時 |
| --- | --- | --- |
| 取得 | GET | 200 |
| 作成 | POST | 201（Locationヘッダー付き） |
| 部分更新 | PATCH | 200 |
| 削除 | DELETE | 204 |
| 動詞的な操作（例：作業枠の提案） | POST /<リソース>/{id}/<名詞の複数形> | 201 または 202 |

全体を置き換えるPUTは使わない。

| 状況 | ステータス |
| --- | --- |
| 入力の検証エラー | 422（FastAPIの既定） |
| 未認証 | 401 |
| 権限なし | 403 |
| 存在しない、または見る権限がない | 404 |
| 状態の競合、連携が必要（integration-required） | 409 |
| If-Matchのバージョン不一致 | 412 |
| 試行回数の超過 | 429（Retry-After付き） |

### 6.2 エラー応答

- RFC 9457の形式（C-04）（`application/problem+json`）で、`type`、`title`、`status`、`detail`、`instance` を返す。
- 検証エラーは `errors` に、項目ごとの内容を入れる。連携が必要なときは `capability`、`providers`、`reason` を入れる。
- 内部の例外のメッセージやスタックトレースは返さない。

### 6.3 そのほかの決まり

- 楽観ロック（C-09）：マップ以外のリソース（タスク、作業枠など）は、取得時に `ETag` を返し、更新時は `If-Match` を必須にする。
- マップの編集（D-13、D-15、C-09）：`POST /api/v1/mindmaps/{mapId}/operations` に操作のまとまりを送る。リクエストは `baseSeq` と `operations`、レスポンスは採番した `seq` と、`baseSeq` より後のほかの操作。サーバーが順序を決めて項目単位で後勝ちにし、循環ができる移動など不正な操作だけを409で拒否する。画面に戻ったときと一定の間隔（例：30秒）で、追いつきのAPIを呼ぶ。
- ページング：カーソル方式。リクエストは `cursor` と `limit`、レスポンスは `items` と `nextCursor`。
- 冪等性：作成のPOSTはクライアントが生成したID（C-08）を受け付け、同じIDでの再送は既存のものを返す。
- LLMには相対的な日付（来週、明後日など）を計算させない。LLMは表現の抜き出しだけを担い、日付はコードで利用者のタイムゾーンに沿って計算する（E-01、ADR 0006）。
- ローカルのOllamaには `127.0.0.1` で接続する（Windowsでは `localhost` だと毎回約2秒遅れるため、E-01）。
- 外部サービスへの書き込みの冪等性：外部に作るものには、こちらで決めたID（作業枠のIDなど）を使い、再試行しても二重にできないようにする（F-10）。
- バージョン（C-03）：URLの `/api/v1`。破壊的な変更をするときだけv2を作る。
- SSE：イベント名はkebab-case。最後に `done`、失敗時は `error` を送る。
- UIの表現の原則：不要な補足ラベルや説明文を足さず、レイアウトに説明させる。テキストを足す前に、配置、グループ化、階層、余白、強調で表現できないかを必ず検討し、それでも伝わらない場合だけ足す。PRのレビューでも確かめる（B-11）。
- ブラウザでSSEを受けるときは、EventSourceを使わず、fetchで応答を読み続ける（Authorizationヘッダーを付けるため、C-19）。

## 7. DBの規約

スキーマの変更はすべてマイグレーションで行い、アプリを止めずに前後のバージョンが動く順番（追加→移行→削除）で進める。

- **マイグレーション**：Alembicで書き、1つのPRには1つのマイグレーションにする。ダウングレードも必ず書き、CIで「適用→戻す→再適用」を試す。
- **破壊的な変更**：列の削除や名前の変更は、追加、データの移行、古い列の削除を別々のリリースに分ける（D-07）。
- **共通の列**：業務のテーブルには `created_at` と `updated_at` を持たせる。論理削除するテーブルには `deleted_at` を持たせる。
- **外部キー**：必ず張り、削除時の動き（ON DELETE）を明示する。複合外部キーで一部の列だけNULLにするときは、列を指定した ON DELETE SET NULL を使う（PostgreSQL 15以上）。
- **列挙**：snake\_caseの文字列とCHECK制約で表す。
- **楽観ロック**：画面と同期ジョブの両方から更新されうるテーブル（tasks、scheduled\_blocks）には `version` の列を持たせる（C-09。マップのテーブルは持たず、mindmaps.last\_seqで版を表す）。
- **制約**：不変条件はDBでも守る（D-17）。子のテーブルは複合外部キーで同じマップ・同じワークスペースの親を指し、CHECK制約と部分一意索引を使う。外部キーの列には索引を付ける。`sort_key` は `COLLATE "C"` にする。詳細は[テーブル定義と操作ログ](../requirements/05a-tables.md)。
- **クエリ**：DBへのアクセスはリポジトリの中に閉じ込める。N+1は禁止。生のSQLは原則として書かず、必要な場合はバインド変数を使う。
- **インデックス**：外部キーと、検索や並べ替えの条件に張る。インデックスを追加するPRには、EXPLAINの結果を貼る。
- **データの所属**：ワークスペースに属するデータには、必ず `workspace_id` を持たせ、すべての検索で所属を条件に入れる。あわせてPostgreSQLの行レベルセキュリティ（RLS）で二重に守る（D-14）。アプリはテーブルの所有者ではない専用ロールで接続し、トランザクションの最初に、所属するワークスペースの一覧とuser\_idを設定する（D-19）。ポリシーは行自身の値だけを見る形にする。

## 8. ログ・エラー処理・セキュリティ

例外は境界で1回だけ記録し、秘密情報はどの経路からも外に出さない。ログの形式と出さないものの一覧は、要件定義書の「ロギング・モニタリング基盤」に従う。

### 8.1 ログとエラー処理

- 例外は、起きた場所ではログに書かず、境界（APIのリクエスト、ジョブ）で1回だけ記録する。二重に記録しない。
- 想定内のエラー（検証エラー、連携が必要など）はWARNING以下、利用者に影響する想定外のエラーはERRORにする。
- ログには、パスワード、トークン、メールアドレス、予定の本文、LLMへの入力の全文を出さない。マスキングは共通の処理で行い、各所で個別に書かない。
- 外部APIの失敗は、再試行できるもの、再連携が必要なもの、恒久的なものに分類してから扱う（要件定義書の「外部API連携設計」）。

### 8.2 セキュリティ

- 外部からの入力は、必ずスキーマで検証してから使う。
- 認可はユースケースの最初で判定する（ワークスペースへの所属、ケイパビリティ）。画面での非表示に頼らない。
- 利用者の停止と許可リストの更新は、運用者だけが使う管理用のコマンドで行い、監査ログに残す。管理画面は作らず、DBを直接書き換えない（C-27）。
- 秘密情報は設定（Settings）経由でだけ読み、コードや設定ファイルに書かない。
- 連携先の予定の本文など外部から来たテキストは、データとして扱い、LLMへの指示として扱わない。
- 画面とAPIは同じオリジンで配信する（開発中はViteのプロキシ、C-19）。CORSは許可リスト方式にし、リフレッシュトークンのCookieはSameSite=Strictにする。
- 依存ライブラリを追加するときは、PRに理由と代わりの候補を書く。
- AIが書いたコードも、差分を全行読んでからマージする。

## 9. テストの規約

テストの全体戦略（層ごとの責務、範囲、品質ゲート）は、要件定義書の[テスト計画](../requirements/12-test-plan.md)に従う。ここでは、テストを書くときの決まりだけを定める。

| 項目 | 規則 |
| --- | --- |
| 置き場所 | `backend/tests/unit/`、`backend/tests/integration/`、`backend/tests/eval/`、`frontend/src/**/*.test.ts(x)`、`frontend/e2e/` |
| 単体テスト | 外部（DB、ネットワーク、時計）に触れない。ポートを偽物に差し替える |
| 結合テスト | PostgreSQLとRedisはTestcontainersで本物を使う。DBへは、テーブルの所有者ではないアプリのロールで接続し、RLSが効いた状態で確かめる（I-01、D-14）。外部APIは記録しておいた応答を再生する |
| 書き方 | 1つのテストで確かめることは1つ。準備、実行、確認（Arrange-Act-Assert）の順に書く |
| テストデータ | ファクトリ（factory\_boy、TypeScriptはファクトリ関数）で作る。テスト間でデータを共有しない |
| 時刻 | `ClockPort` で時刻を固定する。現在時刻に依存するテストは書かない |
| LLM | 単体・結合テストでは応答をモックにする。品質の確認は `tests/eval/` の評価セットで行う |
| カバレッジ | domainとapplicationは80%以上。PRで変更した行も80%以上にする。全体の数字は追わない（I-02） |
| 不安定なテスト | 放置しない。見つけたらIssueにし、直すまでの間はスキップ理由をコードに書く |
| 認可のテスト | ワークスペースのデータを扱うAPIごとに、別のワークスペースのデータを読めず、書き換えられないことを結合テストで確かめる（I-01、AU-03） |
| E2E | PRでは、スモークE2E（ログイン→マップ作成→ノード追加。LLMはモック）を必須にする。残りのE2Eは毎晩流す（I-07） |

## 10. Gitとレビューの規約

ここまでに決めた運用を、日々の作業の決まりとしてまとめる。詳しい理由は要件定義書の「ブランチ戦略・PR・レビュー・リリース管理」を参照する。

- すべての作業はIssueから始め、`feature/<Issue番号>-<kebab-case>` のブランチで行う。
- 1つのPRは1つのIssueに対応させ、差分は400行以内を目安にする（テストとマイグレーションの行は数えない、G-15）。超えそうならtasks.mdの段階で分ける。作業中はDraft PRにする。
- PRタイトルはConventional Commitsの英語で書く（Squash mergeでコミットメッセージになるため）。PR本文は日本語で、テンプレートに沿って書く。
- マージ方式は、featureからdevelopへはSquash merge、releaseとhotfixはMerge commit。
- PRを出す前に、ローカルのClaude Codeで差分をレビューし、結果をPRに貼る。指摘ごとに「対応した」「対応しない（理由）」を返信する。
- セルフレビューは時間を置いて（目安は翌日）、差分を全行読む。
- レビューコメントには must、should、imo、nits、q のいずれかを先頭に付ける。
- Squash mergeのコミットメッセージは、タイトルだけを残し、本文の自動生成された一覧は消す。

## 11. 規約を自動で守らせる仕組み

規約のうち機械で判定できるものは、すべてpre-commitとCIで検査する。CIで失敗するものはマージできない（必須チェック）。

| 規則 | ツール | 実行するタイミング |
| --- | --- | --- |
| Pythonのフォーマットとlint | Ruff | pre-commit、CI |
| Pythonの型 | mypy | CI |
| レイヤーの依存（Python） | import-linter | CI |
| TypeScriptのフォーマット | Prettier | pre-commit、CI |
| TypeScriptのlint | ESLint | pre-commit、CI |
| TypeScriptの型 | tsc | CI |
| 機能をまたぐimport（フロント） | dependency-cruiser | CI |
| コミットメッセージの形式 | commitlint | pre-commit（commit-msg）、CI |
| PRタイトルとブランチ名 | pr-title.yml、branch-policy.yml | CI |
| 秘密情報の混入 | gitleaks | pre-commit、CI |
| OpenAPI定義の差分 | 生成した定義とコミット済みの定義を比べるスクリプト | CI |
| マイグレーション | 適用→戻す→再適用のテスト | CI |
| エディタの基本設定 | EditorConfig（改行コード、インデント、末尾の空白） | エディタ |
| 共通コマンド（起動、テスト、Lint、マイグレーション、型の生成） | タスクランナー（Makefileなど）。AGENTS.mdにも書く | 手元、CI、AIツールで同じコマンドを使う |

DBの命名（制約とインデックス）は、SQLAlchemyの命名規則の設定で自動的に揃える。機械で判定できない規則（ユースケースの分け方、エラーの分類など）は、PRテンプレートのチェックリストとレビューで確認する。

## 改訂履歴

| 版数 | 日付 | 変更内容 |
| --- | --- | --- |
| v0.1 | 2026-11-13 | 初版作成 |
| v0.2 | 2026-11-13 | 未決のC-03、C-04、C-09に基づく規則を「仮置き」と明記。データの所属に行レベルセキュリティ（D-14）の規則を追加 |
| v0.3 | 2026-11-13 | C-09（同時更新の制御）とD-15（操作の形）の決定を反映。楽観ロックの対象をマップ以外に絞り、マップの操作APIの規則を追加。操作ログの種類の例を直した |
| v0.4 | 2026-11-13 | C-03、C-04の決定で「仮置き」を外した。DB規約に制約の規則（D-17）を追加 |
| v0.5 | 2026-11-13 | PRの差分の数え方（テストとマイグレーションを除く、G-15）を追記 |
| v0.6 | 2026-11-13 | テストの規約に、結合テストのDBロール、変更行のカバレッジ、認可のテスト、E2Eの扱い（I-01、I-02、I-07）を追加 |
| v0.7 | 2026-11-13 | AIツール向けの指示の正をAGENTS.mdにした（G-10） |
| v0.8 | 2026-11-13 | アーキテクトのレビューを反映。ワークスペースの文脈とUnit of Work（D-19）、集約をまたぐ操作（D-21）、日付の扱い（D-20）、MCPの置き場所（C-22）、同一オリジンとSSEの受け方（C-19）、外部への書き込みの冪等性（F-10）、削除時の動き、共通コマンドの規則を追加。テストの章の参照先を[テスト計画](../requirements/12-test-plan.md)に直した |
| v0.9 | 2026-11-13 | 利用者の停止と許可リストの管理を、管理用のコマンドで行う規則を追加（C-27） |
| v0.10 | 2026-11-22 | OpenAPIの運用（C-28）とUIの表現の原則（B-11）を追加 |
| v0.11 | 2026-11-23 | LLMと日付の計算、Ollamaへの接続先の規則を追加（E-01） |
