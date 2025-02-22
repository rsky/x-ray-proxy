# 航海日誌 (logbook-kai) と組み合わせて使う

X-Ray Proxyは[@rskyが個人的にメンテナンスしている、パッシブモードが実装されたバージョンの航海日誌 (logbook-kai)](https://github.com/rsky/logbook-kai)と組み合わせて使えるようにデザインされています。

というか、開発中のX-Ray Webが使い物になるまでは航海日誌と併用せざるを得ない事情もあり。。。

mitmproxyが提供するルート認証局のSSL/TLS証明書を信頼することで、HTTP移行した艦これAPIに対応します。

## コンセプト

プロキシサーバとしての機能はX-Ray Proxyが担い、航海日誌が必要なレスポンスはX-Ray Proxyが航海日誌にHTTP POSTで転送します。

```mermaid
sequenceDiagram
  actor C as Client
  participant P as X-Ray Proxy
  participant K as *.kancolle-server.com
  participant S as R2/S3/MinIO,etc.
  participant X as (X-Ray API Webhook)
  participant L as logbook-kai

  C ->> P: request
  P ->> K: request
  K ->> P: response
  P -->> S: resource and json
  P -->> X: (request and response data)
  P -->> L: request and response data
  P ->> C: response
```

## X-Ray Proxyの設定

[設定ファイル](./config/index.md)の `[logbook_kai]` セクションで `enabled = true` にしてX-Ray Proxyを起動するとlogbook-kaiとの連携が有効になります。

```toml
[logbook_kai]
# logbook-kaiとの連携を有効にする。default: false
enabled = true
# logbook-kaiのホスト名またはIPアドレス。default: "127.0.0.1"
host = "127.0.0.1"
# logbook-kaiのポート番号。default: 8888
port = 8888
```
