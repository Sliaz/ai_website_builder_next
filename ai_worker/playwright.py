import re
from playwright.sync_api import Page, expect

class Playwright:
    def __init__(self, open_on: str = 'http://localhost:3000/'):
        self.open_on = open_on


    def test_has_title(self, page: Page):
        page.goto(self.open_on)

        # Expect a title "to contain" a substring.
        expect(page).to_have_title(re.compile("Playwright"))

    def test_page_exists(self, page: Page, url: str):
        page.goto(f"{self.open_on}{url}")
        expect(page).to_have_url(re.compile(url))

    def get_screenshot_of_component(self, page: Page, component_selector: str, path: str = "component.png"):
        page.locator(component_selector).screenshot(path=path)
