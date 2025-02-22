# スタートガイド（マニュアル編）

ここではX-Ray Proxyをマニュアルでインストールし、実行するまでの手順を説明します。

データを保存するために別途Amazon S3互換のオブジェクトストレージが必要です。X-Ray WebはCloudflare Workersで動かす前提のため、Cloudflare R2を使うことを想定しています。

Python関連のインストールやS3互換のストレージを用意したくない場合は、[スタートガイド（Docker編）](./docker.md)を参照してください。

## 1. セットアップ

Pythonのパッケージマネージャ[uv](https://docs.astral.sh/uv/)を利用します。uvのインストール方法は[公式ガイド](https://docs.astral.sh/uv/getting-started/installation/)を参照してください。

```console
git clone git@github.com:rsky/x-ray-proxy.git
cd x-ray-proxy
uv sync
```

## 2. データベースの初期化

`alembic.ini.dist` をコピーして `alembic.ini` を作成後、マイグレーション実行コマンドでデータベースを初期化します。

`alembic.ini` 中の `sqlalchemy.url` は後述する `config/xrayproxy.toml` の `database_path` と同じになるように設定してください。(デフォルト値で設定済みです)

```console
cp alembic.ini.dist alembic.ini
uv run poe db:migration:upgrade
```

## 3. 設定

サンプルの設定ファイル `config/examples/xrayproxy-sample.toml` をコピーして、設定ファイル `config/xrayproxy.toml` を作成・編集します。([設定項目の詳細](../config/index.md))

```console
cp config/examples/xrayproxy-sample.toml config/xrayproxy.toml
```

## 4. 実行

`uv run poe proxy` でX-Ray Proxyを起動します。起動後の画面はmitmproxyのインタラクティブCLIです。<br />
`Q` キーに続けて `Y` キーで終了します。

```console
uv run poe proxy
```

### 起動オプション

[起動オプション](../command/proxy-options.md)を参照。

## 5. HTTPプロキシ設定

端末またはWebブラウザのHTTPプロキシ設定を変更して、X-Ray Proxyを使うようにします。

※別の端末から利用する場合は下記説明の `localhost` をx-ray-proxyを動かしているマシンのローカルネットワーク上のアドレスに適宜置き換えてください。

### A. 手動設定

`localhost:8080` をHTTPプロキシとして設定します。

### B. 自動設定

`http://localhost:8080/proxy.pac` をプロキシ自動構成スクリプトとして設定します。

## 6. ルート認証局のSSL/TLS証明書をインストール

HTTPSプロキシを利用するためには、認証局の証明書を端末にインストールする必要があります。

[証明書についてのmitmproxy公式ドキュメント](https://docs.mitmproxy.org/stable/concepts-certificates/) に従ってインストールしてください。<br>
X-Ray Proxy自身がホスティングするプロキシ自動構成スクリプト `http://<host>:<port>/proxy.pac` では上記リンク先に記載されているドメイン `mitm.it` をmitmproxyを通すように設定しています。

証明書一式はmitmproxyのドキュメントに記載されているデフォルトの `~/.mitmproxy` でなく、x-ray-proxyの `data/mitmproxy` に保存されます。手動で証明書をインストールする場合は `data/mitmproxy/mitmproxy-ca-cert.pem` を使ってください。

## 7. アップデート

```console
git pull
uv sync
uv run poe db:migration:upgrade
```

## Appendix

### iOS/iPadOSでLANの外から利用したい場合

1. どうにかしてVPNで携帯端末からローカルネットワークに接続できるようにします。
2. VPN接続の設定でプロキシを「自動」、URLに `http://<x-ray-proxyを動かしているマシンのローカルネットワーク上のアドレス>:<port>/proxy.pac` を指定します。
3. VPN接続後、Safariで `http://mitm.it` にアクセスし、Webページの案内に従って証明書をインストール、ルート証明書を信頼します。

**【重要】** 証明書のインストールと信頼は別の作業です。インストールした証明書を信頼するには「設定」>「一般」>「情報」>「証明書信頼設定」>「ルート証明書を全面的に信頼」で「mitmproxy」を有効にします。
