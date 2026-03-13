import fitz
import os

pdf_dir = r'C:\Users\LENOVO1430\ClaudeCode\Invest\community_report_pdf'
files = [
    '1월10일_티모씨.pdf',
    '1월10일_티모씨_한국주식.pdf',
    '1월16일_코세스.pdf',
    '1월4일_팔란티어.pdf',
    'Nike분석글.pdf'
]

out_dir = r'C:\Users\LENOVO1430\ClaudeCode\Invest\pdf_images'
os.makedirs(out_dir, exist_ok=True)

for f in files:
    path = os.path.join(pdf_dir, f)
    try:
        doc = fitz.open(path)
        total_pages = len(doc)
        print(f'===== {f} (pages: {total_pages}) =====')

        has_text = False
        for i in range(min(total_pages, 5)):
            page = doc[i]
            text = page.get_text()
            if text.strip():
                has_text = True
                print(f'--- Page {i+1} ---')
                print(text[:3000])

        if not has_text:
            print('No extractable text. Rendering pages as images...')
            for i in range(min(total_pages, 5)):
                page = doc[i]
                pix = page.get_pixmap(dpi=200)
                base = os.path.splitext(f)[0]
                img_path = os.path.join(out_dir, f'{base}_p{i+1}.png')
                pix.save(img_path)
                print(f'  Saved: {img_path}')

        doc.close()
    except Exception as e:
        print(f'Error processing {f}: {e}')
    print()
