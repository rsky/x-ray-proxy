# X-Ray Proxyで利用可能なコマンド一覧

`format`, `lint` 以外のコマンドはそれぞれ `--help` オプションを付けることで、コマンドの詳細な説明を表示できます。

## ユーザー向けコマンド

| コマンド                          | 説明                                                                                        |
| --------------------------------- | ------------------------------------------------------------------------------------------- |
| `uv run poe proxy`                | X-Ray Proxyをインタラクティブモードで起動します。([オプションについて](./proxy-options.md)) |
| `uv run poe dump`                 | X-Ray Proxyを非インタラクティブモードで起動します。                                         |
| `uv run poe web`                  | X-Ray ProxyをmitmproxyのWebインターフェイスありで起動します。                               |
| `uv run poe search`               | 収集したマスターデータを元に艦娘・深海棲艦を検索し、情報を表示します。                      |
| `uv run poe pac`                  | プロキシ自動構成スクリプトを出力します。                                                    |
| `uv run poe db:migration:upgrade` | データベースのスキーマを最新に更新するマイグレーションを行います。                          |
| `uv run poe log:list`             | データベースに保存されているAPIログ情報をJSON Lines形式でリスト表示します。                 |
| `uv run poe log:truncate`         | データベースに保存されているAPIログの古いレコードを削除します。                             |

## 開発者向けコマンド

| コマンド                           | 説明                                                                                                                     |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `uv run poe test`                  | テストを実行します。                                                                                                     |
| `uv run poe format`                | ソースコードのフォーマットを行います。                                                                                   |
| `uv run poe lint`                  | ソースコードの静的解析を行います。                                                                                       |
| `uv run poe sprite`                | [spritesmith](https://github.com/twolfson/spritesmith)形式のJSONファイルからCSSスプライトを生成します。                  |
| `uv run poe db:migration:revision` | データベースマイグレーションの新しいリビジョンを作成します。                                                             |
| `sqlc generate`                    | [sqlc](https://github.com/sqlc-dev/sqlc)を使って`./sql`ディレクトリ以下のSQLファイルを元にPythonコードを生成します。[^1] |

[^1]: `sqlc` は別途インストールする必要があります。
