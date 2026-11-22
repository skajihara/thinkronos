---
inclusion: always
---

# Kiro 専用の指示

共通の規約は `AGENTS.md`（Kiroが自動で読む）と `docs/` にある。ここには Kiro 固有のことだけを書く。

- 仕様は設計から始める（design → requirements → tasks の順）。
- 要件を分析し、あいまいな点は書き出してから進める。
- 要件は `docs/` の要件ID（例：G-20）で参照し、要件の文を複製しない。
- テストは性質ベースのテストを優先し、例による確認で補う。
- 設計判断は `docs/adr/`、ブランチ・コミット・PRは `CONTRIBUTING.md` に従う。
