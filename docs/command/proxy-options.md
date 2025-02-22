# プロキシ起動オプション

`uv run poe <proxy|dump|web>` に続けてオプションを指定することで、mitmproxyの起動オプションを指定できます。

## X-Ray Proxyの設定ファイルを指定

デフォルトでは `config` ディレクトリの `xrayproxy.toml` が読み込まれますが、`--set x_ray_config=path/to/another_config.toml` オプションで別の設定ファイルを指定できます。

## 非インタラクティブモード

`uv run poe proxy` に代えて `uv run poe dump` とするとインタラクティブなUIを使わずに通信内容をコンソールに出力します。<br />
終了するには `Ctrl+C` を押してください。<br />
Dockerコンテナではこのモードで起動します。

```console
uv run poe dump
```

## mitmproxyのWebインターフェイスを起動

`uv run poe proxy` に代えて `uv run poe web` とすることでmitmproxyのWebインターフェイスをプロキシサーバと同時に起動できます。

```console
uv run poe web
```

## mitmproxyのコマンドラインオプション

mitmproxyのオプションがそのまま使えます。以下に代表例を示します。

### mitmproxyのヘルプ

```console
uv run poe proxy --help
```

または

```console
uv run poe dump --help
```

または

```console
uv run poe web --help
```

`proxy` (mitmproxy), `dump` (mitmdump), `web` (mitmweb)で使えるオプションは大体同じですが、差違があります。詳細は `--help` で確認してください。

### リッスンするホスト・ポートを指定

```console
uv run poe proxy --listen-host=0.0.0.0 --listen-port=9999
```

## mitmproxyのオプション設定ファイル

コマンドラインオプションで紹介したホスト・ポートやプロキシ認証を含む各種設定は `data/mitmproxy/config.yaml` ファイルに記述できます。

※ `data/mitmproxy` ディレクトリには `config.yaml` 以外にも自動生成されるSSL/TLS証明書が保存されます。

設定項目の詳細は[mitmproxyの公式ドキュメント](https://docs.mitmproxy.org/stable/concepts-options/)を参照してください。
