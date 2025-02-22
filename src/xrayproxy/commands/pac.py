"""
プロキシ自動構成スクリプトを生成するコマンド
"""

import argparse
import os
import shlex
import sys

from xrayproxy.lib.pac import generate_pac_script


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pac",
        description="Generates a PAC script for use with x-ray and mitmproxy.",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("-o", "--output", type=str)

    args = parser.parse_args()
    script = generate_pac_script(args.host, args.port).replace("\n", os.linesep)

    output = args.output
    if output:
        quoted_output = shlex.quote(output)
        if os.path.exists(output):
            answer = input(f"File {quoted_output} already exists. Are you sure to overwrite it? [y/N]: ")
            if answer.lower() not in ("y", "yes"):
                print("Aborted.", file=sys.stderr)
                return 1

        with open(output, "w") as f:
            f.write(script)
            f.write(os.linesep)
    else:
        print(script)

    return 0


if __name__ == "__main__":
    sys.exit(main())
