# 主要な処理の図

文章での説明は [04-architecture.md の「主な処理の流れ」](../requirements/04-architecture.md)。

## 作業枠の状態遷移（scheduled_blocks.status）

```mermaid
stateDiagram-v2
  [*] --> 提案: AIが propose_blocks で保存（AI-07、AI-08）
  提案 --> 承認済み: 利用者が承認（空き時間を計算し直し、重なれば409）
  提案 --> [*]: 利用者が却下（行を消す）
  承認済み --> 同期済み: ワーカーがGoogleに書き込む（予定のID＝作業枠のID、F-10）
  承認済み --> 承認済み: 書き込みに失敗（バックオフして再試行）
  承認済み --> 同期失敗: 再試行の上限を超えた
  同期失敗 --> 承認済み: 利用者が再試行を選ぶ
  同期済み --> 同期済み: 時間の変更（アプリまたはGoogle。正はGoogle）
  同期済み --> 取消: Google側で予定が消された
  同期済み --> 同期解除: 連携を解除した（予定はGoogleに残す、F-08）
  取消 --> [*]
  同期解除 --> [*]
```

- 状態を変える更新は `version` で楽観ロックする（C-09）。画面とワーカーの更新がぶつかったら、後から来たほうが 409 になる。
- 「同期解除」のときの扱い（作業枠を残すか消すか）は F-08 で決める（Issue「[decide] 連携解除時の作業枠の扱い（F-08）」）。

## 自動スケジューリング（フロー3）

```mermaid
sequenceDiagram
  autonumber
  actor U as 利用者
  participant W as 画面
  participant A as API（application）
  participant G as エージェント（Strands）
  participant L as LLM（Ollama）
  participant D as PostgreSQL
  participant Q as ワーカー
  participant C as Googleカレンダー

  U->>W: タスクを選んで「枠を提案」
  W->>A: POST 提案
  A->>G: タスク、期限、優先度
  G->>A: find_free_slots（コード）
  A->>D: 予定、作業枠、稼働時間帯
  A-->>G: 空き時間の一覧
  G->>L: 空き時間の中から選び、理由を書く
  L-->>G: 枠と理由（構造化出力）
  G->>A: propose_blocks
  A->>A: 空き時間の外の枠は捨てる（ADR 0006）
  A->>D: scheduled_blocks（提案）を保存
  A-->>W: 提案と理由（SSE）
  U->>W: 承認
  W->>A: POST 承認（If-Match: version）
  A->>D: 空き時間を計算し直す
  alt 重なりがある
    A-->>W: 409
  else 重なりがない
    A->>D: 承認済みにする
    A->>Q: 書き込みのジョブを投入
    A-->>W: 200
    Q->>C: events.insert（id＝作業枠のID）
    alt 成功、または既にある（409）
      Q->>D: 同期済みにする
    else 失敗
      Q->>Q: バックオフして再試行。上限で同期失敗
    end
  end
```

## Googleカレンダーの差分同期（フロー2）

```mermaid
sequenceDiagram
  autonumber
  participant B as スケジューラ（beat）
  participant R as Redis
  participant Q as ワーカー
  participant D as PostgreSQL
  participant C as Googleカレンダー

  B->>R: 同期の対象のカレンダーごとにジョブを投入
  R->>Q: ジョブ
  Q->>D: sync_states から syncToken、integration_accounts からトークン（復号）
  Q->>C: events.list（syncToken）
  alt 200
    C-->>Q: 変更された予定、nextSyncToken
    Q->>D: calendar_events に反映。自分の作業枠の予定なら scheduled_blocks の時間を更新、消されていれば取消
    Q->>D: 新しい syncToken を保存（同じトランザクション）
  else 410（syncToken が無効）
    Q->>C: 全件を取り直す（期間を区切る、F-09）
    Q->>D: calendar_events を置き換え、新しい syncToken を保存
  else 401（トークンの失効）
    Q->>C: リフレッシュトークンで更新
    alt 更新できない
      Q->>D: 連携を「要再連携」にする（IN-11）
    end
  else 429・5xx
    Q->>D: job_runs に記録
    Q->>R: バックオフして再投入
  end
```

- 同期の間隔（F-02）と、差分同期の範囲・繰り返し予定の扱い（F-09）は、P2 の前に決める。
