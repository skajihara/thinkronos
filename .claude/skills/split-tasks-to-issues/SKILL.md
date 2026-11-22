---
name: split-tasks-to-issues
description: tasks.md（仕様のタスク一覧）を、1PRに収まる大きさのGitHub Issueに分解する（G-16）。「tasks.md をIssueにして」と言われたときに使う。
argument-hint: <tasks.md のパス>
disable-model-invocation: true
---

# tasks.md から Issue への分解

1. 引数の tasks.md と、その仕様（requirements／design）を読む。要件IDを控える。
2. `.github/ISSUE_TEMPLATE/feature.yml`（または bug／tech-debt）の項目に沿って、各Issueの下書きを作る：背景・目的、やりたいこと、受け入れ条件（チェックボックス）、関連する要件ID、領域、優先度、仕様の作り方、着手できる条件。
3. 1つのIssueが1つのPRに収まる大きさになるよう分ける。大きければサブIssueにする。依存の順を書く。
4. タイトルは `[feat] …` の形式（テンプレートに従う）。
5. **Issueを作る前に、一覧（タイトル、領域、優先度、依存、要件ID）を見せて、Shingoの確認を取る。** 確認後に `gh issue create --title … --body-file …` で作る。承認なしに作らない。
6. 作ったIssueの番号を、tasks.md の各タスクに書き戻すかどうかは、Shingoに尋ねる。
