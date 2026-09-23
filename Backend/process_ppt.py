import os
from pathlib import Path

class Ppt2Pdf:
    def __init__(self, name, ext):
        self.name = name
        self.ext = ext

    def convert_ppt_to_pdf(self):
        BASE_DIR = Path(__file__).resolve().parent

        input_path = BASE_DIR / f"{self.name}.{self.ext}"
        if not input_path.exists():
            input_path = Path("downloads") / f"{self.name}.{self.ext}"

        output_path = BASE_DIR / f"{self.name}.pdf"
        if not output_path.parent.exists():
            output_path = Path("downloads") / f"{self.name}.pdf"

        try:
            import aspose.slides as slides
            presentation = slides.Presentation(str(input_path))
            presentation.save(str(output_path), slides.export.SaveFormat.PDF)
            print(f"[SUCCESS] Converted PPT to PDF: {output_path}")
            return str(output_path)
        except ImportError:
            print("[INFO] aspose.slides not installed. Pdf2Json will parse PPTX natively using python-pptx.")
            return None
        except Exception as e:
            print(f"[WARN] PPT to PDF conversion error: {e}")
            return None

if __name__ == "__main__":
    obj = Ppt2Pdf("test", "pptx")
    obj.convert_ppt_to_pdf()
