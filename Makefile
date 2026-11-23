# シェルに依存しない書き方にする（PowerShell から GNU Make を呼んでも動くように）。
# レシピは単純なコマンド1行だけにし、grep/awk などの外部コマンドや bash 構文を使わない。
.DEFAULT_GOAL := help
.PHONY: help setup up up-cpu down pull-models grafana test lint migrate seed gen-openapi agent-smoke gen-types web

COMPOSE_GPU = docker compose -f compose.yaml -f compose.gpu.yaml

help: ## 一覧を表示する
	$(info make help         この一覧)
	$(info make setup        git hooks を入れる（npm ci、pre-commit install）)
	$(info make up           全サービスを起動する（Ollama は GPU を使う）)
	$(info make up-cpu       全サービスを起動する（GPU なし）)
	$(info make down         全サービスを止める（データは残る）)
	$(info make pull-models  Ollama のモデルを取得する（qwen3:8b、bge-m3）)
	$(info make grafana      Grafana（ログ・メトリクス・トレース）のURLを表示する)
	$(info make lint         pre-commit を全ファイルに実行する)
	$(info make test         バックエンドのテスト（Docker が必要。Testcontainers を使う）)
	$(info make migrate      DBマイグレーションを実行する（make up の後）)
	$(info make seed         デモ用のシードを入れる（make up の後）)
	$(info make gen-openapi  openapi.json を作り直す)
	$(info make agent-smoke  エージェント（Ollama）で子ノードを提案させる（make up と make pull-models の後）)
	$(info make gen-types    openapi.json からフロントのAPI型を作り直す)
	$(info make web          画面の開発サーバーを起動する（http://localhost:5173、APIは make up で起動）)
	@echo (make 名前 で実行する)

setup: ## git hooks を入れる
	npm ci
	pre-commit install --hook-type pre-commit --hook-type commit-msg

up: ## 全サービスを起動する（GPU）
	$(COMPOSE_GPU) up -d --build --wait

up-cpu: ## 全サービスを起動する（GPUなし）
	docker compose up -d --build --wait

down: ## 全サービスを止める
	docker compose -f compose.yaml -f compose.gpu.yaml down

pull-models: ## Ollama のモデルを取得する
	docker compose exec ollama ollama pull qwen3:8b
	docker compose exec ollama ollama pull bge-m3

test: ## バックエンドのテスト
	uv run --directory backend pytest

lint: ## pre-commit を全ファイルに実行する
	pre-commit run --all-files

migrate: ## DBマイグレーション（所有者のロールで実行する）
	docker compose run --rm migrate

seed: ## デモ用のシードを入れる（何度実行してもよい）
	docker compose exec api python -m thinkronos.cli seed

gen-openapi: ## openapi.json（リポジトリ直下）を作り直す（C-28）
	uv run --directory backend python -m thinkronos.api.openapi ../openapi.json

agent-smoke: ## エージェントで子ノードを提案させる
	docker compose exec api python -m thinkronos.cli suggest

gen-types: ## openapi.json からフロントのAPI型を作る（C-28）
	npm --prefix frontend run gen-types

web: ## 画面の開発サーバー（Vite）。/api と /healthz は 127.0.0.1:8000 へ転送する
	npm --prefix frontend run dev

grafana: ## Grafana のURLを表示する
	@echo Grafana: http://127.0.0.1:3000 (ログイン不要。make up の後に開く)
