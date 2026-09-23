import json
import uuid

class FullPageExtractor:
    def __init__(self, url):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        self.url = url
        self.result = {}

    def _infinite_scroll(self, page):
        print("Starting infinite scroll to uncover all data...")
        for _ in range(3): 
             page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
             page.wait_for_timeout(1000) 
        print("Completed scrolling.")

    def extract(self):
        try:
            from playwright.sync_api import sync_playwright
            from playwright_stealth import Stealth
        except ImportError:
            print("[WARN] playwright is not installed. FullPageExtractor disabled.")
            return {"error": "playwright not installed"}

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--enable-gpu-rasterization", "--ignore-gpu-blocklist"]
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            stealth = Stealth()
            stealth.apply_stealth_sync(page)

            print(f"Navigating to {self.url}...")
            page.goto(self.url, wait_until="networkidle")

            self._infinite_scroll(page)

            page_data = page.evaluate("""() => {
                let images = Array.from(document.querySelectorAll('img')).map(img => img.src).filter(Boolean);
                return {
                    text: document.body.innerText,
                    images: images
                };
            }""")

            browser.close()

            doc_uuid = str(uuid.uuid4())
            with open(f"langbase_json/{doc_uuid}.json", "w", encoding="utf-8") as f:
                json.dump({"page_1": page_data}, f, indent=2)

            return {"doc_uuid": doc_uuid, "data": page_data}

if __name__ == "__main__":
    extractor = FullPageExtractor("https://en.wikipedia.org/wiki/Artificial_intelligence")
