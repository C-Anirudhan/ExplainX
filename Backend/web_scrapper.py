import json
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import uuid

class FullPageExtractor:
    def __init__(self, url):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        self.url = url
        self.result = {}

    def _infinite_scroll(self, page):
        print("Starting infinite scroll to uncover all data...")
        # Wikipedia is long, but rarely 'infinite scroll'
        # We simulate a few scrolls to ensure lazy-loaded content loads if present
        for _ in range(3): 
             page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
             page.wait_for_timeout(1000) 
        print("Completed scrolling.")

    def extract(self):
        with sync_playwright() as p:
            # Using your RTX 3050 GPU for faster rendering
            browser = p.chromium.launch(
                headless=True,
                args=["--use-gl=egl", "--ignore-gpu-blocklist"]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36"
            )
            
            page = context.new_page()
            stealth = Stealth()
            stealth.apply_stealth_sync(page)

            print(f"Navigating to: {self.url}")
            
            # --- FIX: Changed wait_until condition to 'load' ---
            # 'load' is triggered when the page is fully loaded, less strict than 'networkidle'
            page.goto(self.url, wait_until="load", timeout=90000)

            self._infinite_scroll(page)

            self.result = {
                "metadata": {
                    "url": page.url,
                    "title": page.title(),
                },
                "content": {
                    "full_text": page.locator("body").inner_text(),
                    "html": page.content(),
                    "links": page.locator("a").evaluate_all("list => list.map(a => a.href)"),
                    "images": page.locator("img").evaluate_all("list => list.map(img => img.src)")
                }
            }

            browser.close()
            filename = self._save_to_file()
        return filename, self.result

    def _save_to_file(self):
        filename = f"{uuid.uuid4()}.json"
        with open(f"langbase_json/{filename}", "w", encoding="utf-8") as f:
            json.dump(self.result, f, indent=4, ensure_ascii=False)
        print(f"\nSUCCESS: Full content extracted to '{filename}'")
        return filename

if __name__ == "__main__":
    target_url = "https://en.wikipedia.org/wiki/MS_Dhoni" 
    extractor = FullPageExtractor(target_url)
    extractor.extract()
