import re
import unittest
from pathlib import Path


class HubNavigationTest(unittest.TestCase):
    def test_home_nav_points_to_registered_hub_route(self):
        hub_html = Path("html/hub.html").read_text(encoding="utf-8")

        home_link = re.search(
            r'<a\s+href="([^"]+)"\s+class="nav-item active"\s+data-section="home"',
            hub_html,
        )

        self.assertIsNotNone(home_link)
        self.assertEqual(home_link.group(1), "/hub.html")


if __name__ == "__main__":
    unittest.main()
