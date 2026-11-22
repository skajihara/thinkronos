@AGENTS.md

# Claude Code 専用の指示
- 作業はIssueの「Claude Codeへの指示」コメントに従う。手順は `/issue-workflow` スキルにある。
- 計画はIssueに「## 計画」としてコメントして止まる。「## 承認」が付くまで実装しない。
- PRを作ったら「## 結果」をコメントして止まる。PRはマージしない。Issueはクローズしない。
- Shingoの作業が必要なものは、PowerShellのコマンド、または画面の場所と押すものを具体的に書く。
- フックが `main` / `develop` 上の `git commit` / `push` / `merge` を止める。ブランチを切ってから作業する。
- 権限モードは個人設定で行い、`.claude/settings.json` には書かない。
