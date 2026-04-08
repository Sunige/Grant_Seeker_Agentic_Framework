from pypdf import PdfReader

reader = PdfReader('d:\\Grant funded work\\ncc-technology-strategy-web.pdf')
text = ""
for i, page in enumerate(reader.pages):
    print(f"--- Page {i} ---")
    page_text = page.extract_text()
    if page_text:
        print(page_text)
