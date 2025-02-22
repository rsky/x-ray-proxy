# スタートガイド（Docker編）

ここではDockerを使って起動する方法を説明します。

Docker ComposeによってX-Ray Proxyと、データの保存に使うAmazon S3互換のMinIOをまとめて起動することができます。

Python関連のインストールや別途S3互換のストレージを用意する必要はありません。X-Ray Webを使わず、X-Ray Proxyのみを使う場合に適しています。

## 1. Docker Desktopをインストール

[docker.com](https://www.docker.com/)からDocker Desktopをダウンロード、インストールしてください。

## 2. X-Ray Proxyをダウンロード

GitでX-Ray Proxyをclone、もしくはGitHubから[X-Ray Proxyのリリースページ](https://github.com/rsky/x-ray-proxy/releases)を開き、最新のリリースをダウンロードしてください。

### 例1: Gitでclone

```console
git clone git@github.com:rsky/x-ray-proxy.git
cd x-ray-proxy
```

### 例2: GitHubからダウンロード

x-ray-proxy-v1.0.0.tar.gzをダウンロード、展開してください。

```console
tar -xf x-ray-proxy-v1.0.0.tar.gz
cd x-ray-proxy-v1.0.0
```

## 3. Docker用の設定ファイルを作成

`config`ディレクトリにあるサンプル設定ファイルをコピー、適宜編集してください。[^1][^2]

```console
cp config/examples/xrayproxy-docker.toml config/xrayproxy-docker.toml
```

## 4. コンテナをビルド

初回起動の前やバージョンアップの際、または設定ファイルを編集した後は `docker compose build` でDockerコンテナをビルドしてください。[^3]

```console
docker compose build
```

## 5. コンテナを起動

`docker compose up` でDockerコンテナを起動します。または、`-d`オプションをつけてバックグラウンドで起動することもできます。

前者の場合、終了は`Ctrl+C`で行います。後者の場合はx-ray-proxyディレクトリにて`docker compose down`で停止します。

### 起動

```console
docker compose up
```

### 動作確認

Webブラウザまたはコンソールで `http://localhost:8080/proxy.pac` にアクセスし、プロキシ自動構成スクリプトが表示されることを確認してください。

```shell-session
$ curl http://localhost:8080/proxy.pac
function FindProxyForURL(url, host) {
  if (dnsDomainIs(host, ".kancolle-server.com")) {
    return "PROXY localhost:8080";
  }
  if (dnsDomainIs(host, "mitm.it")) {
      return "PROXY localhost:8080";
  }
  return "DIRECT";
}
```

### 終了

`docker compose up` → `Ctrl+C` でコンテナを停止した場合。

```shell-session
Gracefully stopping... (press Ctrl+C again to force)
[+] Stopping 3/3
 ✔ Container x-ray-proxy           Stopped                                        10.1s
 ✔ Container x-ray-create-buckets  Stopped                                         0.0s
 ✔ Container x-ray-minio           Stopped                                         0.1s
```

`docker compose up -d` → `docker compose down` でコンテナを停止した場合。

```shell-session
$ docker compose down
[+] Running 4/4
 ✔ Container x-ray-proxy           Removed                                        10.3s
 ✔ Container x-ray-create-buckets  Removed                                         0.0s
 ✔ Container x-ray-minio           Removed                                         0.3s
 ✔ Network x-ray-proxy_default     Removed                                         0.2s
```

## 6. HTTPプロキシ設定

端末またはWebブラウザのHTTPプロキシ設定を変更して、X-Ray Proxyを使うようにします。

※別の端末から利用する場合は下記説明の `localhost` をx-ray-proxyを動かしているマシンのローカルネットワーク上のアドレスに適宜置き換えてください。

### A. 手動設定

`localhost:8080` をHTTPプロキシとして設定してください。

### B. 自動設定

`http://localhost:8080/proxy.pac` をプロキシ自動構成スクリプトとして設定してください。

## 7. ルート認証局のSSL/TLS証明書をインストール

[スタートガイド（マニュアル編）](./index.md)の手順に従って、認証局の証明書をインストールしてください。

## Appendix

### TCPポートの変更

デフォルトでは、以下のポート番号でアクセスできるようになっています。

- X-Ray Proxy (mitmdump): `8080`
- MinIO: `9000`
- MinIO Console: `9001`

`compose.yaml` ファイルを編集してポート番号を変更できます。`ports` でホスト側のポート番号 (`:` の左側) を変更してください。

例: X-Ray Proxyを `8081` 番、MinIOを `39000` 番に変更し、MinIO Consoleを公開しない（`ports` 関連のみ抜粋）

```yaml
services:
  minio:
    ports:
      - "39000:9000"
      #- "9001:9001" 削除またはコメントアウトする
  proxy:
    ports:
      - "8081:8080"
```

### MinIOにアクセスしてデータを確認する

MinIOのWebインターフェイスにはWebブラウザから `http://localhost:9001` でアクセスし、保存されているデータの閲覧や削除等ができます。

> [!NOTE]
> データはローカルのファイルシステム上、`data/minio` ディレクトリに保存されていますが、生データではないのでオブジェクトのPublic URLか、WebインターフェイスもしくはAmazon S3互換クライアントを使わないと閲覧できません。<br>
> x-rayバケットのオブジェクトはバケットポリシーでPublicReadを許可しているため、`http://localhost:9000/x-ray/<オブジェクト名>` で直接アクセスできます。

### MinIOでオブジェクトのライフサイクルを指定する

x-ray-minioコンテナ上で `mc ilm` コマンドを使ってログファイルを残す期間等を指定できます。

例: x-ray-logバケットに30日でオブジェクトを削除するルールを追加する

まず `mc alias set` コマンドでルートユーザー権限を持った接続先のエイリアスを設定し、その後に `mc ilm rule add` コマンドでルールを追加、`mc ilm ls` コマンドでルールを確認します。

```shell-session
$ docker exec -it x-ray-minio /bin/bash
bash-4.4# mc alias set myminio http://minio:9000 dummy-access-key dummy-secret-key
Added `myminio` successfully.
bash-4.4# mc ilm rule add --expire-days 30 myminio/x-ray-log
Lifecycle configuration rule added with ID `d28qpm4qkm6sn29dag00` to myminio/x-ray-log.
bash-4.4# mc ilm ls myminio/x-ray-log
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ Expiration for latest version (Expiration)                                            │
├──────────────────────┬─────────┬────────┬──────┬────────────────┬─────────────────────┤
│ ID                   │ STATUS  │ PREFIX │ TAGS │ DAYS TO EXPIRE │ EXPIRE DELETEMARKER │
├──────────────────────┼─────────┼────────┼──────┼────────────────┼─────────────────────┤
│ d28qpm4qkm6sn29dag00 │ Enabled │ -      │ -    │             30 │ false               │
└──────────────────────┴─────────┴────────┴──────┴────────────────┴─────────────────────┘
bash-4.4# exit
exit
```

外部リンク: [mc ilmコマンドのドキュメント](https://min.io/docs/minio/linux/reference/minio-mc/mc-ilm.html)

[^1]: 設定ファイルの詳細は[設定ファイルのドキュメント](../config/index.md)を参照してください。

[^2]: `config/xrayproxy-docker.toml`が存在しない場合、`config/examples/xrayproxy-docker.toml`が読み込まれます。

[^3]: バージョンアップや設定ファイルの変更がある場合は、コンテナ停止→ビルド→再起動を行わないと変更が反映されません。
