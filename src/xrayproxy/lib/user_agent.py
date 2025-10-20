import re

MOBILE_USER_AGENT_PATTERN = re.compile("iPhone|iPad|Android|Mobile")
VERSION_PATTERN = re.compile("Version/(\\d+)\\.\\d+")


def is_mobile_user_agent(user_agent: str) -> bool:
    if MOBILE_USER_AGENT_PATTERN.search(user_agent) is not None:
        return True

    # iPhone/iPadのSafariでは「デスクトップ用Webサイトを表示」しないと使えず、
    # その際は以下のようなmacOS上のSafariと全く同じUser-Agentを送出する。
    #   Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)
    #   AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0.1 Safari/605.1.15
    # かなり乱暴ではあるが、デスクトップ版Safariまでモバイル端末と誤って判定されてしまうのを許容して
    # User-Agentに "Macintosh; Intel Mac OS X" かつ "Version/(26-31)" を含む場合もモバイル端末とみなす。
    if user_agent.find("Macintosh; Intel Mac OS X") != -1:
        match = VERSION_PATTERN.search(user_agent)
        if match is not None:
            version = int(match.group(1))
            if 26 <= version <= 31:
                return True

    return False
