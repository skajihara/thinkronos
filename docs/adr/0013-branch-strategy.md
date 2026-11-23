# 0013 ブランチ戦略

## 状態

承認済み、2026-11-23（企画書の決定 G-01、L-01 を記録したもの）

## 背景

1人で開発し、フェーズの終わりにリリースする（v0.1.0 は P1）。業務システムの開発で多い、リリースの準備・本番の緊急修正・修正の取り込みの手順を練習したい。AIのエージェント（Claude Code）が `main` や `develop` を直接変えないことを、仕組みで守りたい。

## 比べた選択肢

| 案 | 特徴 |
|---|---|
| GitHub Flow（`main` と作業ブランチだけ） | 単純で、継続的にデプロイするサービスに向く。リリースの準備や緊急修正の手順を練習できない |
| Git-flow（`develop`、`release/`、`hotfix/`） | リリースの準備と緊急修正の手順がある。ブランチと環境（develop＝開発、main＝本番相当）を対応させやすい。手順が多い |
| トランクベース（`main` だけ、機能フラグ） | 小さく頻繁に入れる。フラグの管理が要る。個人開発では利点が小さい |

## 決定

Git-flow の簡略版にする。ブランチは `main`、`develop`、`feature/<Issue番号>-…`、`release/<版>`、`hotfix/<版>` と、マージしない試作の `spike/<Issue番号>-…`。`develop` へは squash マージ、`main` へは `release/` と `hotfix/` だけを入れる。

## 理由

- リリースブランチ、hotfix、`develop` への戻しの手順を練習できる。
- ルールセットは管理者も例外にしない。`main` に入れる元のブランチは、Actions（`branch-policy.yml`）で検査する。
- AIのエージェントは、フック（`block_protected_branch`）で `main` と `develop` への commit・push・merge を止める。

## 影響

- 必須のチェックは pr-title、branch-policy、commitlint、ci-gate、security-scan（ADR 0034）。
- Dependabot の `dependabot/*` は `develop` へのマージを許す（`branch-policy.yml`）。
- リリースの手順（`release-prepare.yml`、`release.yml`）は P1 の終わりに作る（実装計画 5-3）。

## 参照

- G-01、`CONTRIBUTING.md`、`docs/requirements/08-process.md`、ADR 0034
