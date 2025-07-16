import pypdf
from docx import Document
from docx.text.paragraph import Paragraph
import requests
from io import BytesIO


class Reader:
    def __init__(self, path: str):
        self.path = path
        self.doc = None
        if path.endswith('.pdf'):
            self.text = self.read_pdf(path)
        elif path.endswith('.txt'):
            self.text = [self.read_txt(path)]
        elif path.endswith('.docx'):
            self.doc, self.text = self.read_docx(path)
        elif path.startswith('http'):
            self.text = [self.read_webpage(path)]
        else:
            raise ValueError(f'Path was not recognized: \n{path}')
        

    def read_pdf(self, file_path: str) -> list[str]:

        if file_path.startswith('http'):
            
            req = requests.get(file_path)
            assert req.status_code == 200, f'Request for pdf file was unsuccessful:\n{file_path}'
            reader = pypdf.PdfReader(BytesIO(req.content))

        else:

            # creating a pdf reader object
            reader = pypdf.PdfReader(file_path)
        
        text = [page.extract_text() for page in reader.pages]
        return text


    def read_txt(self, file_path):

        text = open(file_path, 'r').read()
        return text


    def read_webpage(self, url):

        req = requests.get(url)
        assert req.status_code == 200, f'Request for webpage file was unsuccessful:\n{url}'

        return req.text


    def read_docx(self, file_path: str) -> list[Paragraph]:

        doc = Document('../documents/Test document.docx')

        paragraph_lst = []
        paragraph_lst.extend(doc.paragraphs)
        paragraph_lst.extend(paragraph 
                            for section in doc.sections 
                            for paragraph in section.header.paragraphs)
        paragraph_lst.extend(paragraph 
                            for section in doc.sections 
                            for paragraph in section.footer.paragraphs)
        paragraph_lst.extend(paragraph 
                            for table in doc.tables 
                            for row in table.table.rows 
                            for cell in row.cells 
                            for paragraph in cell.paragraphs)
        
        return doc, paragraph_lst
    



# read_pdf(r'documents\Notice of Repurchasing shares\inputs\Notice of Repurchasing shares ENG.pdf')
# read_pdf('https://www.managementsolutions.com/sites/default/files/minisite/static/72b0015f-39c9-4a52-ba63-872c115bfbd0/llm/pdf/rise-of-llm.pdf')

# read_txt(r'documents\Notice of Repurchasing shares\inputs\Notice of Repurchasing shares ENG.txt')

# read_webpage('https://en.wikipedia.org/wiki/Large_language_model')


def translate(text):
    import re
    translation = []
    for word in text.split(' '):
        i = re.search('[aeiou]', word.lower())
        if i is None:
            translation.append(word)
            continue
        else:
            i = i.start()
        word = word[i:] + word[:i] + 'ay' if i > 0 else word + 'yay'
        word = re.sub(r'(\w+)([.,!?\'"])(\w+)', r'\1\3\2', word) 
        translation.append(word)
    return ' '.join(translation)


# below is an example of how translation can be done for docx and re-inserted with the same structure.
# note that run-level format/style is lost because we won't want to translate below sentence-level,
# so only paragraph-level format/style can be maintained
"""
read_doc = Reader(r'documents\Test document.docx')
doc, paragraphs = read_doc.doc, read_doc.text
for p in paragraphs:
    text = p.text
    # perform translation, below is a placeholder function:
    translated = translate(text)
    p.text = translated

doc.save(r'documents\test_output.docx')
"""

