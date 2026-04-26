import fitz
from PIL import Image
import os

def crop_signature_boxes(pdf_path, image_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    # Scale factor (since we rendered at matrix 3x3)
    scale = 3
    
    # Define boxes to look for
    targets = [
        ("fonctionnel", "Directeur Fonctionnel"),
        ("rh", "Directeur RH"),
        ("dg", "Directeur Général")
    ]
    
    img = Image.open(image_path)
    
    for key, text in targets:
        inst = page.search_for(text)
        if inst:
            # Get the first occurrence
            rect = inst[0]
            # Box is usually below the title. Let's take a larger area around it
            # Based on the screenshot, the box is approx 4.75cm wide
            # In points: 1cm = 28.35 pts. 4.75cm = 134.6 pts
            
            # We target the box area: from the title top to about 60 pts below
            x0 = rect.x0 - 5
            y0 = rect.y0 - 5
            x1 = x0 + 140 # approx width
            y1 = y0 + 70  # approx height
            
            # Convert to image coordinates
            crop_rect = (x0 * scale, y0 * scale, x1 * scale, y1 * scale)
            cropped = img.crop(crop_rect)
            cropped.save(os.path.join(output_dir, f"box_{key}.png"))
            print(f"Case extraite : box_{key}.png")

if __name__ == "__main__":
    crop_signature_boxes("backend/static/model_approbation.pdf", "backend/static/page_modele_hd.png", "backend/static/signatures")
