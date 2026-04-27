import fitz
import json

def analyze_pdf(path):
    doc = fitz.open(path)
    page = doc[0]
    
    # Trouver tous les blocs de texte et leurs positions
    words = page.get_text("words") # (x0, y0, x1, y1, word, block_no, line_no, word_no)
    
    # Regrouper par lignes (grossièrement) pour plus de clarté
    lines = {}
    for w in words:
        y0 = round(w[1], 1)
        if y0 not in lines: lines[y0] = []
        lines[y0].append(w)
    
    sorted_lines = sorted(lines.keys())
    
    analysis = []
    for y in sorted_lines:
        line_text = " ".join([w[4] for w in sorted(lines[y], key=lambda x: x[0])])
        analysis.append({
            "y": y,
            "text": line_text,
            "bbox": [min(w[0] for w in lines[y]), y, max(w[2] for w in lines[y]), max(w[3] for w in lines[y])]
        })
        
    print(json.dumps(analysis, indent=2))

if __name__ == "__main__":
    analyze_pdf(r"C:\Users\Session Youssef\Downloads\model demande d'approbation.pdf")
