# AGENTS.md

このファイルは、このリポジトリでコードを扱う際に AI エージェント（Gemini CLI や Claude Code）に指針を提供します。

## プロジェクトの概要

X-Ray Proxy は、mitmproxy アドオンとして構築された「艦隊これくしょん（艦これ）」用の Python ベースの HTTP/HTTPS プロキシです。ゲームのトラフィックをインターセプトして処理し、リソースを S3 互換のオブジェクトストレージに保存したり、API レスポンスを X-Ray ウェブアプリケーションに送信したりします。

## 最優先ルール

- 回答は必ず日本語で行うこと。
- 作業後に自動でコミットしてはいけない。コミットは必ずユーザーの指示を受けてから行うこと。
- 既存の未コミット変更はユーザーの作業である可能性がある。依頼されていない差分は巻き戻さないこと。
- コミットメッセージは日本語で、 [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/#specification) に従って記述すること。

## コミット前の必須手順

変更をコミットする前に、必ず以下の手順を実行してコードの品質を確認し、すべてのチェックがパスすることを確認してから、コミットを提案または実行してください。

整形によって変更が生じた場合はその変更を再ステージしてください。

また、lintでエラーが検知された場合は3回まで修正を試みてください。3回以上の再試行はせず、コミットを中止してユーザーの指示を受けてください。

### Pythonスクリプトに変更がある場合

1. **コードの整形**: `uv run poe format`
2. **静的解析とリンターの実行**: `uv run poe lint`
3. **テストの実行**: `uv run poe test`

### Markdownドキュメントに変更がある場合

1. **ドキュメントの整形**: `uv run poe format:docs`

### SQLファイルに変更がある場合

1. **SQL整形**: `./bin/format_sql.sh`

`format_sql.sh` は `sql-formatter` を使用してSQLファイルを整形します。`sql-formatter` がインストールされていない場合は、ユーザーにインストールを促してください。

`sql-formatter` はNPMを使って `npm install -g sql-formatter` でグローバルにインストールすることを想定しています。

## 開発コマンド

### コアコマンド (uv および poethepoet 経由)

- `uv run poe proxy` - mitmproxy を使用してプロキシサーバーを起動
- `uv run poe dump` - mitmdump を使用してダンプモードで起動
- `uv run poe web` - mitmweb を使用してウェブインターフェース付きで起動

### データベース管理

- `uv run poe db:migration:upgrade` - データベースマイグレーションを適用
- `uv run poe db:migration:revision` - 新しいマイグレーションを作成

### コード品質

- `uv run poe lint` - すべてのリンター（ruff, mypy）を実行
- `uv run poe format` - コードの整形（ruff）
- `uv run poe test` - ユニットテストの実行（unittest discover を使用）
- `uv run python -m unittest tests.xrayproxytest.module.test_class.test_method` - 単一のテストを実行

### ユーティリティコマンド

- `uv run poe log:list` - API ログを一覧表示
- `uv run poe pac` - PAC ファイルを生成
- `uv run poe search` - 検索機能
- `uv run poe sprite` - スプライト操作

### Docker での開発

- `docker compose up` - フルスタック（MinIO + プロキシ）を起動
- `docker compose up minio` - ストレージ用の MinIO のみを起動

## アーキテクチャ

### 主要コンポーネント

**XRayAddon** (`src/xrayproxy/addons/xray.py`): リクエスト/レスポンス処理をオーケストレートする主要な mitmproxy アドオン。非同期ハンドラーを使用し、データベース接続、S3 ストレージ、HTTP セッションを管理します。
プロキシ起動時のエントリポイントとなるスクリプトは `src/xrayproxy/scripts/xray.py` です。

**ハンドラーシステム**:

- リクエストハンドラー (`src/xrayproxy/handlers/request/`): 着信リクエストを処理
- レスポンスハンドラー (`src/xrayproxy/handlers/response/`): 発信レスポンスを処理
- すべてのハンドラーは `BaseRequestHandler` または `BaseResponseHandler` を継承します。

**設定**: `src/xrayproxy/config/` にある TOML ベースの設定システム。各サブシステム（X-Ray, ストレージ, 書き換えルールなど）の階層構造を持ちます。

**データベース**: SQLite を使用し、SQLAlchemy ORM と sqlc（型安全なクエリ用）を併用。スキーマは `sql/schema.sql` にあり、生成されたコードは `src/xrayproxy/generated/sqlc/` に配置されます。

### 主要なディレクトリ

- `src/xrayproxy/addons/` - mitmproxy アドオンの実装
- `src/xrayproxy/handlers/` - リクエスト/レスポンス処理ロジック
- `src/xrayproxy/config/` - 設定管理
- `src/xrayproxy/lib/` - ユーティリティライブラリ（HTTP, ハッシュ, 艦船データなど）
- `src/xrayproxy/commands/` - CLI コマンドの実装
- `migration/` - Alembic データベースマイグレーション
- `sql/` - データベーススキーマとクエリ

## 設定

プロキシには TOML 設定ファイルが必要です（デフォルト: `config/xrayproxy.toml`）。設定例については `config/examples/` を参照してください。

主な設定セクション:

- `x_ray` - X-Ray サーバーの Webhook 設定
- `storage` - S3 互換オブジェクトストレージの設定
- `resource` - リソース保存の設定
- `rewrite` - レスポンス書き換えルール
- `logbook_kai` - 航海日誌 拡張版との連携設定

## 開発セットアップ

1. 依存関係のインストール: `uv sync`
2. ストレージ用 MinIO のセットアップ: `docker compose up minio`
3. データベースマイグレーションの実行: `uv run poe db:migration:upgrade`
4. 設定のコピーとカスタマイズ: `cp config/examples/xrayproxy-sample.toml config/xrayproxy.toml`
5. プロキシの起動: `uv run poe proxy`

## コード生成

- データベースクエリは `sql/queries/*.sql` から sqlc を介して `src/xrayproxy/generated/sqlc/` に生成されます。
- スキーマやクエリを変更した後は、外部コマンドである `sqlc generate` を実行して再生成してください。
- 生成されたファイルはリンターの対象外です（`pyproject.toml` で設定）。

## コードスタイル

- Ruff フォーマッターを使用（Black互換、行長 119 文字）
- Ruff によるインポート順序の整理（isort互換）
- 厳格な mypy 型チェックが有効
