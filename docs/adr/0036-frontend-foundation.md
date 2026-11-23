# 0036 フロントエンドの土台（UI部品、状態管理、API型）

## 状態

承認済み、2026-11-23

## 背景

画面の土台を作るにあたり、次を決める必要があった（B-05、C-11、B-07、C-19、C-28、Issue #14）。

- UIコンポーネントの基盤（B-05）
- フロントの状態管理（C-11）
- APIの型の作り方（C-28）と、画面とAPIを同じオリジンにする方法（C-19）
- TypeScript の版

## 比べた選択肢

| 項目 | 案 |
|---|---|
| UI部品（B-05） | shadcn/ui＋Base UI ／ shadcn/ui＋Radix ／ MUI などの完成品の部品集 |
| 状態管理（C-11） | TanStack Query＋Zustand ／ TanStack Query だけ ／ Redux Toolkit（RTK Query） |
| APIの呼び出し | openapi-typescript＋openapi-fetch ／ orval などのクライアント生成 |
| TypeScript | 5.9 ／ 6.0 ／ 7.0 |

## 決定

- **shadcn/ui＋Base UI**（style `base-nova`、色は neutral）。部品は `src/shared/ui/` に置く（Shingo が決定、推奨どおり）。
- **TanStack Query＋Zustand**。サーバーのデータは TanStack Query、画面の中の状態（テーマ、のちのマップエディタ）は Zustand（Shingo が決定、推奨どおり）。
- APIの型は **openapi-typescript** で `openapi.json` から `src/shared/api/schema.d.ts` を生成し、**openapi-fetch** で呼ぶ。手で型を書かない。
- 開発中は **Vite のプロキシ**で `/api` と `/healthz` を API（`127.0.0.1:8000`）へ転送し、画面と同じオリジンにする。
- **TypeScript 5.9**。React 19、Vite 8、Tailwind CSS 4、ESLint 9。
- ライトとダークは `<html>` の `dark` クラスで切り替え、選んだ値（ライト／ダーク／端末に合わせる）を localStorage に保存する。

## 理由

- shadcn/ui は部品のソースを自分のリポジトリに持つので、見た目を B-11 の表現に合わせて自由に変えられる。2026年7月から shadcn/ui の既定の土台は Base UI で、Radix も引き続き保守される（[shadcn/ui changelog: Base UI is now the default](https://ui.shadcn.com/docs/changelog/2026-07-base-ui-default)）。新しい部品はまず Base UI 向けに出るため、既定に合わせた。
- 状態の置き場所を「サーバーのデータ」と「画面の中の状態」で分けると、キャッシュと再取得をTanStack Queryに任せられ、マップエディタの頻繁な更新はZustandの小さなストアで扱える。
- openapi-fetch は生成した型だけで動き、実行時のコードが小さい。API定義の差分が型の差分になる。
- TypeScript 7.0 は typescript-eslint が対応していない（peerDependencies が `typescript >=4.8.4 <6.1.0`）。openapi-typescript 7.13 は `typescript ^5.x` を求める。両方を満たす 5.9 にした。
- ESLint 10 は eslint-plugin-jsx-a11y 6.10 が対応していない（peerDependencies が `eslint ^9` まで）ため、9 にした。

## 影響

- shadcn/ui の CLI（`npx shadcn add <部品>`）はローカルの PC で実行する。部品は CLI が作るファイル名（`button.tsx` など、小文字）のまま `src/shared/ui/` に置く。これは命名規則（コンポーネントは PascalCase）の例外とする。
- 最初のボタンは、作業した環境から shadcn/ui のレジストリに接続できなかったため、shadcn/ui のリポジトリ（`apps/v4/registry/bases/base/ui/button.tsx`、`styles/style-nova.css`）から手で写した。次に CLI で部品を入れるときに、`npx shadcn add button --overwrite` で置き換えてよい。
- APIを変えたら `make gen-openapi` と `make gen-types` を実行し、`openapi.json` と `schema.d.ts` を同じPRでコミットする。
- TypeScript 7 と ESLint 10 には、依存するツールが対応した時点で上げる（Dependabot のPRで判断する）。
- `src/features/` どうしの import と、`src/shared/` から `src/features/` への import は dependency-cruiser が止める（CIの `npm run lint`）。

## 参照

- Issue #14、#37（B-05）、#39（C-11）
- ADR 0034（CI）、0035（バックエンドの土台）
