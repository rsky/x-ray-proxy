"""
spritesmithのJSONからCSSとスプライト一覧HTMLを生成する。
もはやCSSスプライトの時代は終わったが、画像を分解して個別に保存するのが面倒なのと、
画像とJSONはそれぞれ別々のHTTPリクエストで取得するので、そのタイミングによる
画像とJSONのバージョン違いを避けるためにJSONをCSSに変換することとした。
"""

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class Size:
    w: int
    h: int


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class Rect(Size):
    x: int
    y: int


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class Frame:
    frame: Rect
    rotated: bool
    trimmed: bool
    sprite_source_size: Rect
    source_size: Size


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class Meta:
    app: str
    image: str
    format: str
    size: Size
    scale: int


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class Sprite:
    frames: dict[str, Frame]
    meta: Meta


INDEX_HTML_START = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>%sprite_name%</title>
  <link rel="stylesheet" type="text/css" href="%encoded_css_object_key%">
  <style>
    body {
      margin: 0;
      padding: 0;
    }
    dl {
      margin: 0;
      padding: 0;
    }
    dt {
      margin: 0;
      padding: 12px;
      background-color: lightgray;
      color: black;
      line-height: 1.0;
      font-family: 'Courier New', 'Courier', monospace;
      font-size: 1rem;
      font-style: normal;
      font-weight: bold;
    }
    dd {
      margin: 0;
      padding: 12px;
      line-height: 1.0;
    }
    dd div {
      border: 1px solid black;
    }
  </style>
</html>
<body>
  <dl>"""

INDEX_HTML_END = """
  </dl>
</body>
</html>
"""


def json_to_sprite(sprite_json: str | bytes) -> Sprite:
    """ "
    JSONからSpriteオブジェクトを生成する
    JSONのバリデーションは省略
    呼び出し側でエラーハンドリングしてください
    """
    return data_to_sprite(json.loads(sprite_json))


def sprite_to_css(sprite: Sprite, sprite_name: str, image_url: str) -> str:
    """
    SpriteオブジェクトからCSSを生成する
    frame.rotated, frame.trimmed および meta.scale はそれぞれ false, false, 1 であることを前提とし、対応しない
    """
    base_class_name = f"sprite_{sprite_name}"

    css = f""".{base_class_name} {{
  display: inline flow-root;
  background-image: url({image_url});
}}
"""

    for name, frame in sprite.frames.items():
        css += f""".{base_class_name}.{name} {{
  width: {frame.source_size.w}px;
  height: {frame.source_size.h}px;
  background-position: -{frame.frame.x}px -{frame.frame.y}px;
}}
"""

    return css


def sprite_to_html(sprite: Sprite, sprite_name: str, css_url: str) -> str:
    """
    Spriteオブジェクトから生成したCSSのスプライト一覧HTMLを生成する
    """
    base_class_name = f"sprite_{sprite_name}"
    html = INDEX_HTML_START.replace("%sprite_name%", sprite_name).replace("%encoded_css_object_key%", css_url)
    for name, frame in sprite.frames.items():
        html += f"""
  <dt>.{base_class_name}.{name} ({frame.source_size.w}&times;{frame.source_size.h})</dt>
  <dd><div class="{base_class_name} {name}"></div></dd>"""
    html += INDEX_HTML_END

    return html


def dict_to_frame(data: dict[str, Any]) -> Frame:
    return Frame(
        frame=Rect(**data["frame"]),
        rotated=data["rotated"],
        trimmed=data["trimmed"],
        sprite_source_size=Rect(**data["spriteSourceSize"]),
        source_size=Size(**data["sourceSize"]),
    )


def data_to_sprite(data: Any) -> Sprite:
    size = data["meta"].pop("size")
    return Sprite(
        frames={k: dict_to_frame(v) for k, v in data["frames"].items()},
        meta=Meta(size=Size(**size), **data["meta"]),
    )
