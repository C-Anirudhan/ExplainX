import os
import json
import chromadb
import torch
from PIL import Image
from sentence_transformers import SentenceTransformer
from transformers import CLIPProcessor, CLIPModel


class ChromaMultimodalDB:
    def __init__(self, name, collection_name="multimodal_pdf"):
        """
        json_path  : path to page-wise JSON
        image_dir  : directory containing images (image1.jpg, image2.png, etc.)
        """

        self.json_path = f"langbase_json/{name}.json"
        self.image_dir = f"langbase_json/ExtractedImages/"
        self.collection_name = collection_name

        # Load JSON
        with open(self.json_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        # Initialize Chroma
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(collection_name)

        # Load models
        self.text_model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        )

        self.clip_model = CLIPModel.from_pretrained(
            "openai/clip-vit-base-patch32"
        )
        self.clip_processor = CLIPProcessor.from_pretrained(
            "openai/clip-vit-base-patch32"
        )

    # --------------------------------------------------
    # INGEST TEXT
    # --------------------------------------------------
    def ingest_text(self):
        for page, content in self.data.items():
            text = content["text"]
            images = content.get("images", [])

            if not text.strip():
                continue

            embedding = self.text_model.encode(text).tolist()

            self.collection.add(
                ids=[page],
                embeddings=[embedding],
                documents=[text],
                metadatas=[{
                    "type": "text",
                    "page": page,
                    "images": ",".join(images)
                }]
            )

        print("✅ Text ingestion completed")

    # --------------------------------------------------
    # INGEST IMAGES
    # --------------------------------------------------
    def ingest_images(self):
        for filename in os.listdir(self.image_dir):
            image_id, ext = os.path.splitext(filename)
            image_path = os.path.join(self.image_dir, filename)

            if not ext.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                continue

            image = Image.open(image_path).convert("RGB")

            inputs = self.clip_processor(
                images=image,
                return_tensors="pt"
            )

            with torch.no_grad():
                embedding = self.clip_model.get_image_features(**inputs)

            self.collection.add(
                ids=[image_id],  # image1, image2 ...
                embeddings=[embedding[0].tolist()],
                metadatas=[{
                    "type": "image",
                    "image_name": image_id
                }]
            )

        print("✅ Image ingestion completed")

    # --------------------------------------------------
    # INGEST ALL
    # --------------------------------------------------
    def ingest_all(self):
        self.ingest_text()
        self.ingest_images()
        print("🚀 Full ingestion completed")

    # --------------------------------------------------
    # QUERY TEXT
    # --------------------------------------------------
    def query_text(self, query, top_k=3):
        query_embedding = self.text_model.encode(query).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        return results

    # --------------------------------------------------
    # GET IMAGES BY IDS
    # --------------------------------------------------
    def get_images(self, image_ids):
        return self.collection.get(ids=image_ids)

if __name__ == "__main__":
    obj = ChromaMultimodalDB("zero plastic article")
    obj.ingest_all()
    res = obj.query_text("summarize all pages",top_k=10)
    print(res)
    