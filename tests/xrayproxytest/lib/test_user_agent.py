import unittest

from xrayproxy.config.rewrite import MobileUserAgentOptions
from xrayproxy.lib.user_agent import is_mobile_user_agent

options = MobileUserAgentOptions(
    safari=True,
    firefox=True,
    user_agent="Edg/",
)

class IsMobileUserAgentTest(unittest.TestCase):
    def test_chrome_android(self):
        user_agent = ("Mozilla/5.0 (Linux; Android 10; K)"
                      " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.0.0 Mobile Safari/537.36")
        self.assertEqual(is_mobile_user_agent(user_agent), True)

    def test_chrome_windows(self):
        user_agent = ("Mozilla/5.0 (Windows NT 11.0; Win64; x64)"
                      " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.166 Safari/537.36")
        self.assertEqual(is_mobile_user_agent(user_agent), False)

    def test_chrome_mac(self):
        user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                      " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
        self.assertEqual(is_mobile_user_agent(user_agent), False)

    def test_chrome_mac_with_options(self):
        user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                      " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
        self.assertEqual(is_mobile_user_agent(user_agent, options), False)

    def test_firefox_mobile(self):
        user_agent = "Mozilla/5.0 (Android 4.4; Mobile; rv:41.0) Gecko/41.0 Firefox/41.0"
        self.assertEqual(is_mobile_user_agent(user_agent), True)

    def test_firefox_tablet(self):
        user_agent = "Mozilla/5.0 (Android 4.4; Tablet; rv:41.0) Gecko/41.0 Firefox/41.0"
        self.assertEqual(is_mobile_user_agent(user_agent), True)

    def test_firefox_windows(self):
        user_agent = "Mozilla/5.0 (Windows NT x.y; Win64; x64; rv:10.0) Gecko/20100101 Firefox/10.0"
        self.assertEqual(is_mobile_user_agent(user_agent), False)

    def test_firefox_windows_with_options(self):
        user_agent = "Mozilla/5.0 (Windows NT x.y; Win64; x64; rv:10.0) Gecko/20100101 Firefox/10.0"
        self.assertEqual(is_mobile_user_agent(user_agent, options), True)

    def test_firefox_mac(self):
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:10.0) Gecko/20100101 Firefox/10.0"
        self.assertEqual(is_mobile_user_agent(user_agent), False)

    def test_safari_iphone(self):
        user_agent = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X)"
                      " AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0.1 Mobile/15E148 Safari/604.1")
        self.assertEqual(is_mobile_user_agent(user_agent), True)

    def test_safari_ipad(self):
        user_agent = ("Mozilla/5.0 (iPad; CPU iPad OS 18_7 like Mac OS X)"
                      " AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0.1 Mobile/15E148 Safari/604.1")
        self.assertEqual(is_mobile_user_agent(user_agent), True)

    def test_safari_mac(self):
        user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                      " AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0.1 Safari/605.1.15")
        self.assertEqual(is_mobile_user_agent(user_agent), False)

    def test_safari_mac_with_options(self):
        user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                      " AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0.1 Safari/605.1.15")

        self.assertEqual(is_mobile_user_agent(user_agent, options), True)

    def test_edge_android(self):
        user_agent = ("Mozilla/5.0 (Linux; Android 10; K)"
                      " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 EdgA/120.0.0.0")

        self.assertEqual(is_mobile_user_agent(user_agent), True)

    def test_edge_windows(self):
        user_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                      " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")

        self.assertEqual(is_mobile_user_agent(user_agent), False)

    def test_edge_windows_with_options(self):
        user_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                      " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")

        self.assertEqual(is_mobile_user_agent(user_agent, options), True)

if __name__ == '__main__':
    unittest.main()
