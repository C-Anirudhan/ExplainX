# text_to_image.py

from diffusers import StableDiffusionPipeline
import torch
from datetime import datetime

# Load Stable Diffusion (best model for 6GB VRAM)
print("Loading Stable Diffusion model...")

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16
).to("cuda")

print("Model loaded successfully.\n")


def generate_image(prompt: str):
    print(f"Generating image for prompt:\n\"{prompt}\"")

    result = pipe(
        prompt=prompt,
        num_inference_steps=50,    # ~2–3 seconds
        guidance_scale=10         # makes image follow prompt better
    )

    image = result.images[0]

    # Save with timestamp
    filename = f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    image.save(filename)

    print(f"Saved image as {filename}")
    return filename


if __name__ == "__main__":
    while True:
        user_prompt = input("Enter your prompt: ")
        generate_image(user_prompt)
