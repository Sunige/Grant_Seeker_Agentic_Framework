"""
What: A simple scratchpad utility.
Why: Used historically to help extract the text payload from the NCC Strategy PDF so it could be fed into LLMs or converted into keyword lists.
How: Leverages `pypdf.PdfReader` to extract and print text blocks page by page.
"""
from pypdf import PdfReader

reader = PdfReader('d:\\Grant funded work\\ncc-technology-strategy-web.pdf')
text = ""
for i, page in enumerate(reader.pages):
    print(f"--- Page {i} ---")
    page_text = page.extract_text()
    if page_text:
        print(page_text)
