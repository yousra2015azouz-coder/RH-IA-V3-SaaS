import fitz
import os

def extract_signatures(pdf_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    doc = fitz.open(pdf_path)
    count = 0
    for i in range(len(doc)):
        page = doc[i]
        images = page.get_images(full=True)
        for img in images:
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            
            # Extraction de toutes les images pour ne rien rater
            filename = f"signature_{xref}.png"
            pix.save(os.path.join(output_dir, filename))
            print(f"Image extraite : {filename} ({pix.width}x{pix.height})")
            count += 1
            pix = None

if __name__ == "__main__":
    extract_signatures("backend/static/model_approbation.pdf", "backend/static/signatures")
