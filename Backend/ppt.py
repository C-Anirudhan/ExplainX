import subprocess
from pathlib import Path


class Ppt2Pdf:
    def __init__(self, name, ext):
        self.name = name
        self.ext = ext

    def convert(self):
        BASE_DIR = Path(__file__).resolve().parent
        ppt = BASE_DIR / "downloads" / "PPTS" / f"{self.name}.{self.ext}"
        out_dir = BASE_DIR / "downloads"

        cmd = [
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(ppt)
        ]

        subprocess.run(cmd, check=True)
        print("✅ Clean PDF generated (no watermark)")


if __name__ == "__main__":
    Ppt2Pdf("ExplainX-Universal-Multimodal-Content-Explainer (1)", "pptx").convert()
