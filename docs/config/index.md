# 設定項目

## X-Ray Proxy全体の設定

| 設定項目        | 型     | デフォルト値            | 説明                                                                                                                                                                                                                                                                                     |
| --------------- | ------ | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `assets_dir`    | string | `"assets"`              | 静的ファイルの保存先ディレクトリ。絶対パスまたはX-Ray Proxy起動時のカレントディレクトリからの相対パス。<br>*基本的に変更する必要はありません。*                                                                                                                                          |
| `database_path` | string | `"data/x_ray_proxy.db"` | SQLiteデータベースのパス。絶対パスまたはX-Ray Proxy起動時のカレントディレクトリからの相対パス。<br>*基本的に変更する必要はありません。*                                                                                                                                                  |
| `log_verbosity` | string | `"DEBUG"`               | デバッグログ出力レベル。ここで設定した値がmitmproxyのログ出力レベル (`termlog_verbosity` オプションの値) 以上のときデバッグログが出力されます。<br>デフォルトでは `termlog_verbosity=INFO` のため、出力しない設定となります。<br>選択肢: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

設定例:

```toml
log_verbosity = "INFO"
```

## `[storage]` オブジェクトストレージ設定

各種リソースやログを保存する、Amazon S3互換のオブジェクトストレージの設定です。

> [!NOTE]
> X-RayプロジェクトではCloudflare R2を基準としているため、Amazon S3を含む他のオブジェクトストレージでは完全に期待通りの動作をしないかもしれません。[^1]

| 設定項目              | 型      | デフォルト値 | 説明                                                                                                                                           |
| --------------------- | ------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `region`              | string  | なし         | **[必須]** バケットのあるリージョン。                                                                                                          |
| `access_key_id`       | string  | なし         | **[必須]** アクセスキーID。                                                                                                                    |
| `secret_access_key`   | string  | なし         | **[必須]** シークレットアクセスキー。                                                                                                          |
| `endpoint_url`        | string  | なし         | S3 REST APIのエンドポイントURL。指定しない場合はAmazon S3デフォルトのエンドポイントが使用されます。                                            |
| `resource_bucket`     | string  | なし         | **[必須]** 画像リソースを保存するバケット名。<br>これら3つのバケット名は同じでも、違っていてもかまいません。                                   |
| `data_bucket`         | string  | なし         | **[必須]** マスターデータや母港データ等を保存するバケット名。                                                                                  |
| `api_log_bucket`      | string  | なし         | **[必須]** APIログを保存するバケット名。                                                                                                       |
| `allow_public_access` | boolean | `false`      | バケットにアップロードしたリソースやデータにパブリックアクセスを許可します。<br>ログは対象外で、バケットのデフォルトのままとなります。[^2][^3] |

設定例1: *Cloudflare R2*

```toml
[storage]
endpoint_url = "https://<ACCOUNT_ID>.r2.cloudflarestorage.com"
region = "auto" # Cloudflare R2の場合は"auto"を指定
access_key_id = "<accessKeyId>"
secret_access_key = "<secretAccessKey>"
resource_bucket = "x-ray"
data_bucket = "x-ray"
api_log_bucket = "x-ray-log"
allow_public_access = true
```

設定例2: *Amazon S3 東京リージョン*

```toml
[storage]
# S3の場合はendpoint_urlを指定しない
region = "ap-northeast-1"
access_key_id = "<accessKeyId>"
secret_access_key = "<secretAccessKey>"
resource_bucket = "x-ray"
data_bucket = "x-ray"
api_log_bucket = "x-ray-log"
allow_public_access = false
```

設定例3: *Docker Composeで同じコンテナグループ上にあるMinIO*

```toml
[storage]
endpoint_url = "http://minio:9000"
region = "us-east-1"
access_key_id = "dummy-access-key"
secret_access_key = "dummy-secret-key"
resource_bucket = "x-ray"
data_bucket = "x-ray"
api_log_bucket = "x-ray-log"
allow_public_access = true
```

## `[resource]` リソース保存設定

各種リソースをオブジェクトストレージに保存する設定です。

| 設定項目                  | 型      | デフォルト値 | 説明                                                                                                                                             |
| ------------------------- | ------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `save_mode`               | string  | `"default"`  | リソース保存モード。<br>選択肢: `all`, `default`, `least`, `none`                                                                                |
| `ship_graphic_versioning` | boolean | `false`      | 艦娘画像をバージョニングして過去のものも保存するかどうか。<br>立ち絵を期間限定グラフィックで固定する機能を利用するには、trueに設定してください。 |

| save_mode | 保存するリソース                                                                                                           |
| --------- | -------------------------------------------------------------------------------------------------------------------------- |
| `all`     | すべてのリソース。画像、音声、スクリプト等なんでも保存する。                                                               |
| `default` | X-Ray Webで使いそうなリソース。艦娘画像、装備画像、その他画像リソース等。                                                  |
| `least`   | X-Ray Webで最低限必要と思われるリソース。`default`と比べて保存する「その他」の画像リソースが絞られる。評価中なので非推奨。 |
| `none`    | 何も保存しない。航海日誌等の別ツールと連携してプロキシ機能だけを担当させたい場合に。                                       |

設定例:

```toml
[resource]
save_mode = "default"
ship_graphic_versioning = true
```

## `[api_log]` APIログ保存設定

> [!NOTE]
> X-Ray Webアプリケーションで戦闘・演習・出撃ログの詳細な内容を閲覧するためには、各種ログの保存が必要になる予定です。

> [!IMPORTANT]
> 古いログを自動で削除する機能はなく、実装する予定もありません。<br>
> バケットのライフサイクルルールを適宜設定して削除してください。

| 設定項目            | 型      | デフォルト値 | 説明                                                       |
| ------------------- | ------- | ------------ | ---------------------------------------------------------- |
| `save_sortie_log`   | boolean | `false`      | 出撃ログを保存するかどうか。                               |
| `save_practice_log` | boolean | `false`      | 演習ログを保存するかどうか。                               |
| `save_other_log`    | boolean | `false`      | その他のAPIログを保存するかどうか。                        |
| `pretty`            | boolean | `false`      | JSONを改行とインデントで見やすく整形して保存するかどうか。 |

設定例:

```toml
[api_log]
save_sortie_log = true
save_practice_log = true
save_other_log = false
pretty = false
```

## `[logbook_kai]` 航海日誌(logbook-kai)連携設定

パッシブモードが有効な航海日誌(logbook-kai)との連携を行うための設定です。

| 設定項目  | 型      | デフォルト値  | 説明                                    |
| --------- | ------- | ------------- | --------------------------------------- |
| `enabled` | boolean | `false`       | logbook-kaiとの連携を有効にする。       |
| `host`    | string  | `"127.0.0.1"` | logbook-kaiのホスト名またはIPアドレス。 |
| `port`    | integer | `8888`        | logbook-kaiのポート番号。               |

設定例1: *ローカルホストでデフォルトのポートを待ち受けているlogbook-kaiに接続する*

```toml
[logbook_kai]
enabled = true
```

設定例2: *Dockerコンテナからローカルホストで9090番ポートを待ち受けているlogbook-kaiに接続する*

```toml
[logbook_kai]
enabled = true
host = "host.docker.internal"
port = 9090
```

## `[rewrite]` HTTPレスポンスの書き換え設定

HTTPレスポンスを書き換えてゲームのプレイ感に影響を与える設定です。[こちら](./rewrite.md)をご覧ください。

## `[[x_ray.webhook]]` X-Ray API Webhookの設定

X-Ray APIにAPIレスポンス情報を送信するための設定です。
配列で複数指定できるようになっています。通常は1つの設定で十分かと思われますが、開発上の都合で複数指定できた方が便利だったので。

| 設定項目        | 型     | デフォルト値 | 説明                                                                                                                  |
| --------------- | ------ | ------------ | --------------------------------------------------------------------------------------------------------------------- |
| `base_url`      | string | なし         | **[必須]** X-Ray API WebhookのベースURL。                                                                             |
| `client_id`     | string | `""`         | **[本番では必須]** Cloudflare AccessでService Auth用に発行したService TokenのClient ID。                              |
| `client_secret` | string | `""`         | **[本番では必須]** Cloudflare AccessでService Auth用に発行したService TokenのClient Secret。                          |
| `local_token`   | string | なし         | x-ray-local-helperで発行したBot用トークン。<br>ローカル開発では `client_id`, `client_secret` に代えてこれを指定する。 |

設定例1: *X-Ray APIがCloudflare Workers本番環境にある場合 <small>(または Cloudflare Tunnel + Cloudflare Access でローカル環境を公開している場合)</small>*

```toml
[[x_ray.webhook]]
base_url = "https://x-ray-api.example.com/webhook"
client_id = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.access"
client_secret = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

設定例2: *環境変数から値を取得*

```toml
[[x_ray.webhook]]
base_url = "https://x-ray-api.example.com/webhook"
client_id = "${CF_ACCESS_CLIENT_ID}"
client_secret = "${CF_ACCESS_CLIENT_SECRET}"
```

設定例3: *ローカルホストの開発環境*

```toml
[[x_ray.webhook]]
base_url = "http://localhost:8082/webhook"
local_token = "eyJhbG..............."
```

設定例4: *Dockerコンテナからローカルホストの開発環境*

```toml
[[x_ray.webhook]]
base_url = "http://host.docker.internal:8082/webhook"
local_token = "eyJhbG..............."
```

[^1]: 例えば、X-Ray ProxyではETagがオブジェクトのMD5ダイジェストである前提の実装になっていますが、S3ではバケットの暗号化設定によってはETagがMD5ダイジェストとは異なる値になることがあります。

[^2]: バケットのデフォルトでパブリックアクセスが許可されている場合は、`allow_public_access = false` に設定してもパブリックアクセスが許可されます。

[^3]: S3ではバケットのACLが有効になっていないと `allow_public_access = true` に設定した際に `AccessControlListNotSupported` エラーが発生してアップロードに失敗します。
