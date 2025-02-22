"""
spritesmith形式のJSONファイルからCSSスプライトを生成するコマンド
"""

import argparse
from pathlib import PurePosixPath

from xrayproxy.lib.sprite import json_to_sprite, sprite_to_css, sprite_to_html


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="sprite",
        description="Make CSS or HTML from a sprite json file.",
    )
    parser.add_argument("file", nargs="?", help="sprite json file path")
    parser.add_argument("-n", "--name", help="sprite name")
    parser.add_argument("-f", "--format", help="output format", choices=["css", "html"], default="css")
    parser.add_argument("-o", "--output", help="output file path")
    args = parser.parse_args()

    with open(args.file, "r") as f:
        sprite = json_to_sprite(f.read())

    if args.name:
        sprite_name = args.name
    else:
        sprite_name = PurePosixPath(args.file).stem

    if args.format == "css":
        image_url = sprite_name + ".webp"
        content = sprite_to_css(sprite, sprite_name, image_url)
    else:
        css_url = sprite_name + ".css"
        content = sprite_to_html(sprite, sprite_name, css_url)

    if args.output:
        with open(args.output, "w") as f:
            f.write(content)
    else:
        print(content)

    return 0


if __name__ == "__main__":
    exit(main())
