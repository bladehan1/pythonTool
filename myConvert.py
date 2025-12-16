from pdf2docx import Converter
import sys
pdf_file = str(sys.argv[1])
docx_file = str(sys.argv[2])
#pdf_file = '/Users/blade/Downloads/validatorBridge.pdf'
#docx_file = '/Users/blade/tmp/sample.docx'

# convert pdf to docx
cv = Converter(pdf_file)
cv.convert(docx_file)      # all pages by default
cv.close()
