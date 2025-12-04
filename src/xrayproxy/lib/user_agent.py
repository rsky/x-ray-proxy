import re
from typing import Optional

from xrayproxy.config.rewrite import MobileUserAgentOptions

MOBILE_USER_AGENT_PATTERN = re.compile("iPhone|iPad|Android")


def is_mobile_user_agent(user_agent: str, options: Optional[MobileUserAgentOptions]) -> bool:
    if MOBILE_USER_AGENT_PATTERN.search(user_agent) is not None:
        return True

    if options is None:
        return False

    if options.safari and "Safari/" in user_agent and "Chrome/" not in user_agent and "Edg/" not in user_agent:
        return True

    if options.firefox and "Firefox/" in user_agent:
        return True

    if options.user_agent is not None and options.user_agent in user_agent:
        return True

    return False
