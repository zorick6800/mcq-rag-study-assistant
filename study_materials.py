"""Step 1 of RAG: ingest separate study files and prepare cited passages."""
import hashlib
import json
from pathlib import Path
import pymupdf
import streamlit as st


def prepare_material(data, filename):
    document_id = hashlib.sha256(data).hexdigest()
    if filename.lower().endswith('.pdf'):
        with pymupdf.open(stream=data, filetype='pdf') as doc:
            if doc.needs_pass:
                raise ValueError('Password-protected PDFs are not supported.')
            pages = [{'page': i+1, 'text': p.get_text('text', sort=True)} for i, p in enumerate(doc)]
    else:
        pages = [{'page': None, 'text': data.decode('utf-8-sig')}]
    chunks = []
    for page in pages:
        words = page['text'].split()
        start = 0
        while start < len(words):
            end = min(start + 300, len(words))
            chunks.append({'chunk_id': f'{document_id}:{page["page"]}:{start}',
                           'document_id': document_id, 'source_filename': filename,
                           'page': page['page'], 'text': ' '.join(words[start:end])})
            if end == len(words):
                break
            start = end - 50
    return {'document_id': document_id, 'source_filename': filename, 'pages': pages, 'chunks': chunks}


def main():
    st.set_page_config(page_title='Study Materials')
    st.title('Study Materials')
    st.write('Upload the study sources you want the assistant to use for explanations.')
    uploads = st.file_uploader('Add study PDFs or UTF-8 text files', type=['pdf', 'txt'], accept_multiple_files=True)
    if not uploads:
        return
    documents, seen = [], set()
    for upload in uploads:
        data = upload.getvalue()
        digest = hashlib.sha256(data).hexdigest()
        if digest in seen:
            st.info(f'Skipped duplicate file: {upload.name}')
            continue
        seen.add(digest)
        try:
            with st.spinner(f'Reading {upload.name}…'):
                document = prepare_material(data, upload.name)
            if not document['chunks']:
                st.warning(f'{upload.name}: no text found. Scanned material needs OCR.')
                continue
            documents.append(document)
            empty = [p['page'] for p in document['pages'] if not p['text'].strip()]
            if empty:
                st.warning(f'{upload.name}: no text found on pages {empty}.')
        except Exception as exc:
            st.error(f'Could not read {upload.name}: {exc}')
    if not documents:
        return
    chunks = [chunk for doc in documents for chunk in doc['chunks']]
    a, b, c = st.columns(3)
    a.metric('Documents', len(documents))
    b.metric('Pages / text files', sum(len(doc['pages']) for doc in documents))
    c.metric('Passages', len(chunks))
    index = st.selectbox('Preview a document', range(len(documents)), format_func=lambda i: documents[i]['source_filename'])
    doc = documents[index]
    page_index = st.selectbox('Preview a page', range(len(doc['pages'])), format_func=lambda i: f'Page {i+1}', key=doc['document_id'])
    st.text_area('Extracted text', doc['pages'][page_index]['text'], height=350)
    st.caption('Check the reading order against the source, especially tables. Page numbers refer to PDF pages.')
    with st.expander('Preview passages prepared for retrieval'):
        for chunk in doc['chunks'][:3]:
            st.caption(f'{chunk["source_filename"]} • Page {chunk["page"] or "N/A"}')
            st.write(chunk['text'])
    bundle = {'schema_version': 1, 'purpose': 'study_materials', 'chunks': chunks}
    st.download_button('Download prepared study materials', json.dumps(bundle, ensure_ascii=False, indent=2), 'study_materials.json', 'application/json')
    st.info('Study passages are ready for the next step: retrieval and local Ollama answers. This page does not call an LLM yet.')


if __name__ == '__main__':
    main()
