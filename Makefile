SHELL := bash
.DEFAULT_GOAL := help
.PHONY: help setup up down test lint migrate gen-types

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

setup: ## Install git hooks (pre-commit, commitlint)
	npm ci
	pre-commit install --hook-type pre-commit --hook-type commit-msg

up: ## Start the app (TODO: filled in by a later issue)
	@echo "up: not implemented yet"

down: ## Stop the app (TODO: filled in by a later issue)
	@echo "down: not implemented yet"

test: ## Run tests (TODO: filled in by a later issue)
	@echo "test: not implemented yet"

lint: ## Run linters (pre-commit hooks on all files)
	pre-commit run --all-files

migrate: ## Run DB migrations (TODO: filled in by a later issue)
	@echo "migrate: not implemented yet"

gen-types: ## Generate API types (TODO: filled in by a later issue)
	@echo "gen-types: not implemented yet"
