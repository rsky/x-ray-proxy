# X-Ray Proxy: A http(s) proxy for KanColle

X-Ray Proxyは、艦隊これくしょんのプレイを支援するためのプロキシサーバです。

名前は国際信号旗のX (X-Ray: *貴船の実施を止め、本船の信号に注意せよ*) とX線透視の両方に由来します。

実体はPythonで書かれた[mitmproxy](https://mitmproxy.org/)のアドオンスクリプトで、プロキシサーバの実装はmitmproxyに任せてリクエストとレスポンスの処理に特化した設計となっています。

これ単体ではなく、リソースやログを保存するためのAmazon S3互換オブジェクトストレージと、X-Ray Webアプリケーション(開発中)と組み合わせて利用します。

## 注意事項など

- ご利用は自己責任でお願いします。
- X-Ray WebアプリケーションはCloudflare Workers用に開発しています。

## 使い方

Python関連のツールやS3互換ストレージを自前で用意する場合は [スタートガイド（マニュアル編）](./docs/getting-started/index.md)を、Dockerコンテナ内に環境を作って利用する場合は [スタートガイド（Docker編）](./docs/getting-started/docker.md)を参照してください。

## ドキュメント

- スタートガイド
  - [マニュアル編](./docs/getting-started/index.md)
  - [Docker編](./docs/getting-started/docker.md)
- 設定
  - [設定項目一覧](./docs/config/index.md)
  - [HTTPレスポンスの書き換え設定](./docs/config/rewrite.md)
- コマンド
  - [コマンド一覧](./docs/command/index.md)
  - [Proxy起動オプション](./docs/command/proxy-options.md)
- [航海日誌 (logbook-kai) と組み合わせて使う](./docs/with-logbook-kai.md)

## ライセンス

[MIT License](./LICENSE.txt)
