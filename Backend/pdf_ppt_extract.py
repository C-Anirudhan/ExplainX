import fitz  # PyMuPDF
import json
import io
from PIL import Image


class Pdf2Json:
    def __init__(self,name):
        self.name = name
        self.pdf = fitz.open(f"downloads/{name}.pdf")

        self.pdf_json = {}
        self.image_store = {}
        self.image_id = 1
        self.image_index = 1

    def extract(self):
        for page_no, page in enumerate(self.pdf, start=1):
            page_key = f"page_{page_no}"
            self.pdf_json[page_key] = {
                "text": page.get_text(),
                "images": []
            }

            for img in page.get_images(full=True):
                xref = img[0]
                img_data = self.pdf.extract_image(xref)
                image_bytes = img_data["image"]

                image_name = f"image{self.image_id}"
                self.image_store[image_name] = Image.open(io.BytesIO(image_bytes)).convert("RGB")

                self.pdf_json[page_key]["images"].append(image_name)
                self.image_id += 1
            
        for page_index in range(len(self.pdf)): # iterate over pdf pages
            page = self.pdf[page_index] # get the page
            image_list = page.get_images()

            # print the number of images found on the page
            if image_list:
                print(f"Found {len(image_list)} images on page {page_index}")
            else:
                print("No images found on page", page_index)

            for image_index, img in enumerate(image_list, start=1): # enumerate the image list
                xref = img[0] # get the XREF of the image
                pix = fitz.Pixmap(self.pdf, xref) # create a Pixmap

                if pix.n - pix.alpha > 3: # CMYK: convert to RGB first
                     pix = fitz.Pixmap(fitz.csRGB, pix)

                pix.save(f"langbase_json/ExtractedImages/{self.name}{self.image_index}.png") # save the image as png
                pix = None
                self.image_index += 1

        # Save JSON
        with open(f"langbase_json/{self.name}.json", "w") as f:
            json.dump(self.pdf_json, f, indent=2)

if __name__ == "__main__":
    obj = Pdf2Json("zero plastic article")
    obj.extract()
