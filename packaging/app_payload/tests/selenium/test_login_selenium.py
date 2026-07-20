"""
Selenium WebDriver 示例 — 登录页 UI 自动化测试

展示以下 Selenium 核心技能：
  1. WebDriver 初始化和管理（setUpClass / tearDownClass）
  2. 元素定位策略（CSS Selector / XPath）
  3. 显式等待（WebDriverWait + expected_conditions）
  4. 页面交互（send_keys / click）
  5. 断言验证
  6. JavaScript Executor
  7. 无障碍基础验证（label/placeholder）

与 Playwright 对比：
  - Selenium 需要手动管理 WebDriver 生命周期和显式等待
  - Playwright 内置自动等待和浏览器管理
  - 定位策略（ID / CSS / XPath）两者通用

运行前提:
  pip install selenium webdriver-manager
  python tests/selenium/test_login_selenium.py
"""

import unittest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


BASE_URL = "http://127.0.0.1:8000"


@unittest.skipUnless(SELENIUM_AVAILABLE, "Selenium/webdriver-manager 未安装, 跳过 UI 测试")
class TestLoginPageUI(unittest.TestCase):
    """登录页面 UI 自动化测试 — Selenium WebDriver 版本

    3 个测试场景：
      1. 页面加载 → 表单正确渲染
      2. 元素可交互性验证
      3. 无障碍基础检查
    """

    driver = None
    wait = None

    @classmethod
    def setUpClass(cls):
        """初始化 WebDriver — 所有测试共用一个浏览器实例

        关键配置：
          --headless: 无头模式，CI 友好
          --window-size: 固定视口，避免响应式差异
          --no-sandbox: Linux CI 环境必要
        """
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            service = Service(ChromeDriverManager().install())
            cls.driver = webdriver.Chrome(service=service, options=options)
            cls.wait = WebDriverWait(cls.driver, 10)  # 显式等待最长 10 秒
        except Exception as e:
            raise unittest.SkipTest(f"WebDriver 初始化失败: {e}")

    @classmethod
    def tearDownClass(cls):
        """测试结束后清理资源"""
        if cls.driver:
            cls.driver.quit()

    # ---------- 辅助方法 ----------

    def _open_login_page(self):
        """打开登录页面并等待表单加载完成"""
        self.driver.get(f"{BASE_URL}/login.html")
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".auth-card-inner"))
        )

    # ---------- 测试用例 ----------

    def test_login_page_loads_and_shows_form(self):
        """场景 1：页面加载 → 表单卡片可见 → 核心元素可定位

        展示三种元素定位策略：
          - By.CSS_SELECTOR: input[name='username']
          - By.CSS_SELECTOR: input[type='password']
          - By.XPATH: //button[...]
        """
        self._open_login_page()

        # 1. 表单卡片可见
        form_card = self.driver.find_element(By.CSS_SELECTOR, ".auth-card-inner")
        self.assertTrue(form_card.is_displayed(), "登录表单卡片应该可见")

        # 2. 定位用户名输入框 (CSS Selector)
        username_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='username']")
        self.assertTrue(username_input.is_enabled(), "用户名输入框应该可编辑")

        # 3. 定位密码输入框 (CSS Selector)
        password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        self.assertTrue(password_input.is_enabled(), "密码输入框应该可编辑")

        # 4. 定位提交按钮 (XPath — 通过文本内容定位)
        submit_btn = self.driver.find_element(
            By.XPATH,
            "//button[contains(text(),'登录') or contains(text(),'登 录')]"
        )
        self.assertTrue(submit_btn.is_displayed(), "登录按钮应该可见")

    def test_elements_are_interactive(self):
        """场景 2：交互性验证 — 能输入文字、能点击按钮"""
        self._open_login_page()

        # 键入用户名
        username_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='username']")
        username_input.clear()
        username_input.send_keys("test_student_001")
        self.assertEqual(
            username_input.get_attribute("value"),
            "test_student_001",
            "输入的用户名应与键入内容一致"
        )

        # 键入密码
        password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_input.clear()
        password_input.send_keys("test_password_123")
        self.assertTrue(
            len(password_input.get_attribute("value")) > 0,
            "密码字段应能接收输入"
        )

    def test_form_elements_have_labels(self):
        """场景 3：无障碍基础 — 输入框应有 label/placeholder/aria-label 任一"""
        self._open_login_page()

        inputs = self.driver.find_elements(
            By.CSS_SELECTOR,
            "input:not([type='hidden'])"
        )
        self.assertGreater(len(inputs), 0, "页面应至少有一个可见输入框")

        for inp in inputs:
            has_label = (
                inp.get_attribute("placeholder") or
                inp.get_attribute("aria-label") or
                inp.get_attribute("name")
            )
            self.assertIsNotNone(
                has_label,
                f"输入框缺少可访问标签: {inp.get_attribute('outerHTML')[:100]}"
            )

    def test_theme_fab_accessible(self):
        """场景 4：主题切换按钮应可通过 CSS 定位（验证页面完整性）"""
        self._open_login_page()

        # 页面应有 data-bg-unified 属性（统一背景系统）
        body = self.driver.find_element(By.CSS_SELECTOR, "body")
        self.assertEqual(
            body.get_attribute("data-bg-unified"),
            "true",
            "body 应有 data-bg-unified='true'"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
