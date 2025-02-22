import datetime
import json
from typing import Any, Union


def filename_with_extension(filename: str, content_type: str) -> str:
    if "." in filename:
        extension = filename.split(".")[-1].lower()
    else:
        extension = None

    match (content_type, extension):
        case (
            ("image/png", "png")
            | ("image/gif", "gif")
            | ("image/jpeg", "jpg")
            | ("image/jpeg", "jpeg")
            | ("image/webp", "webp")
            | ("application/json", "json")
        ):
            return filename
        case ("image/png", _):
            return filename + ".png"
        case ("image/gif", _):
            return filename + ".gif"
        case ("image/jpeg", _):
            return filename + ".jpg"
        case ("image/webp", _):
            return filename + ".webp"
        case ("application/json", _):
            return filename + ".json"
        case _:
            return filename


def decode_json(content: bytes) -> Any:
    """
    Raises
    ------
    UnicodeDecodeError
        If the content is not a valid UTF-8
    json.JSONDecodeError
        If the content is not a valid JSON
    """
    json_str = content.decode("utf-8")
    if json_str.startswith("svdata="):
        return json.loads(json_str[7:])
    else:
        return json.loads(json_str)


def encode_json(data: Any, pretty: bool) -> str:
    indent = 2 if pretty else None
    separators = (", ", ": ") if pretty else (",", ":")

    return json.dumps(data, ensure_ascii=False, indent=indent, separators=separators)


def format_json(content: bytes, pretty: bool) -> str:
    """
    Raises
    ------
    UnicodeDecodeError
        If the content is not a valid UTF-8
    json.JSONDecodeError
        If the content is not a valid JSON
    """
    return encode_json(decode_json(content), pretty)


def timestamp_to_utc_datetime(epoch_milliseconds: Union[int, float]) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(epoch_milliseconds / 1000, datetime.timezone.utc)
