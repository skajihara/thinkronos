# シェルに依存しない書き方にする（PowerShell から GNU Make を呼んでも動くように）。
# レシピは単純なコマンド1行だけにし、grep/awk などの外部コマンドや bash 構文を使わない。
.DEFAULT_GOAL := help
.PHONY: help setup up up-cpu down pull-models grafana test lint migrate gen-types

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
	$(info make test / migrate / gen-types  未実装（後続のIssueで実装）)
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

test: ## テスト（未実装）
	@echo test: not implemented yet

lint: ## pre-commit を全ファイルに実行する
	pre-commit run --all-files

migrate: ## DBマイグレーション（未実装）
	@echo migrate: not implemented yet

gen-types: ## API型の生成（未実装）
	@echo gen-types: not implemented yet

grafana: ## Grafana のURLを表示する
	@echo Grafana: http://127.0.0.1:3000 (ログイン不要。make up の後に開く)
