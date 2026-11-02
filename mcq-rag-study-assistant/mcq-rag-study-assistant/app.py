import streamlit as st
import json
import hashlib

from parse_questions import (
    split_question_blocks,
    separate_question_sections,
    extract_question_options,
    extract_answer_key,
)

from extract_pdf import extract_pdf_pages


st.set_page_config(
    page_title="MCQ Practice Assistant",
    page_icon="📝",
    layout="centered",
)


@st.cache_data(show_spinner=False)
def extract_uploaded_pdf(pdf_bytes: bytes) -> list[dict]:
    """Avoid repeating extraction when only the preview page changes."""
    return extract_pdf_pages(pdf_bytes)


st.title("MCQ Practice Assistant")
st.write(
    "Upload a practice-test PDF containing questions, "
    "answer options, correct answers, and explanations."
)

uploaded_file = st.file_uploader(
    "Choose your practice-test PDF",
    type=["pdf"],
    accept_multiple_files=False,
)

if uploaded_file is not None:
    st.success(f"Selected: {uploaded_file.name}")
    st.write(f"File size: {uploaded_file.size / 1024:.1f} KB")

    try:
        with st.spinner("Extracting PDF text..."):
            pages = extract_pdf_pages(uploaded_file.getvalue())
            
    except Exception:
        st.error(
            "Unable to read this PDF. Check that it opens normally "
            "and is not password-protected."
        )
        st.stop()

    if not pages:
        st.warning("This PDF contains no pages.")
        st.stop()

    total_characters = sum(len(page["text"]) for page in pages)
    empty_pages = [
        page["page_number"]
        for page in pages
        if not page["text"].strip()
    ]

    col1, col2 = st.columns(2)
    col1.metric("Pages", len(pages))
    col2.metric("Extracted characters", f"{total_characters:,}")

    if empty_pages:
        st.warning(
            f"No text was found on pages: {empty_pages}. "
            "These may be blank or scanned pages requiring OCR."
        )

    st.subheader("Preview extracted text")
    st.caption(
        "Compare this text with the original PDF. "
        "Check for missing words, options, or explanations."
    )

    selected_page = st.selectbox(
        "Choose a page",
        options=range(1, len(pages) + 1),
        format_func=lambda number: f"Page {number}",
    )

    page_text = pages[selected_page - 1]["text"]
    st.code(page_text or "(No text extracted)", language=None)

    full_text = "\n\n".join(
        f"--- PAGE {page['page_number']} ---\n{page['text']}"
        for page in pages
    )

    st.download_button(
        label="Download extracted text",
        data=full_text,
        file_name="extracted_text.txt",
        mime="text/plain",
    )
    
    st.divider()
    st.subheader("Detected question blocks")

    questions = split_question_blocks(pages)

    st.metric("Questions detected", len(questions))

    if not questions:
        st.warning(
            "No numbered question headings were detected. "
            "This document may use a different format."
        )

    else:
        question_numbers = [
            question["source_number"]
            for question in questions
        ]

        if len(question_numbers) != len(set(question_numbers)):
            st.warning(
                "Repeated question numbers detected. "
                "The document may contain multiple practice sets."
            )

        expected_numbers = list(range(1, len(questions) + 1))

        if question_numbers != expected_numbers:
            st.warning(
                "Question numbering is not a continuous sequence "
                "starting at 1. Review the detected blocks."
            )

        selected_index = st.selectbox(
            "Choose a question block",
            options=range(len(questions)),
            format_func=lambda index: (
                f"Question {questions[index]['source_number']}"
            ),
        )

        selected_question = questions[selected_index]

        page_labels = ", ".join(
            str(number)
            for number in selected_question["source_pages"]
        )

        st.caption(f"Source pages: {page_labels}")

        st.code(
            selected_question["raw_text"],
            language=None,
        )

        st.download_button(
            label="Download question blocks as JSON",
            data=json.dumps(
                questions,
                indent=2,
                ensure_ascii=False,
            ),
            file_name="question_blocks.json",
            mime="application/json",
        )
                # Separate question content from the source explanation.
        st.divider()
        st.subheader("Separated question content")

        structured_question = separate_question_sections(
            selected_question
        )

        for reason in structured_question["review_reasons"]:
            st.warning(reason)

        st.write("Question and options")
        st.code(
            structured_question["question_and_options"]
            or "(Could not separate question content)",
            language=None,
        )

        with st.expander("Source answer and explanation"):
            st.code(
                structured_question["source_feedback"]
                or "(Could not separate source feedback)",
                language=None,
            )

        st.caption(
            "Preparation preview only. Answers will remain hidden "
            "during the actual test."
        )

        # Extract individual options from the question content.
        st.divider()
        st.subheader("Draft question and options")

        parsed_question = extract_question_options(
            structured_question
        )

        for note in parsed_question["cleanup_notes"]:
            st.info(note)

        for reason in parsed_question["review_reasons"]:
            st.warning(reason)

        st.write("Question")
        st.text(parsed_question["question_text"])

        st.write("Options")

        for option in parsed_question["options"]:
            st.text(f"{option['label']}. {option['text']}")

        st.caption(
            "Draft extraction: compare wording and option boundaries "
            "with the source before using this question in a test."
        )
        
        st.divider()
        st.subheader("Draft answer key")

        question_with_answer = extract_answer_key(parsed_question)

        for issue in question_with_answer["answer_issues"]:
            st.warning(issue)

        if question_with_answer["correct_labels"]:
            st.write(
                "Source answer label(s): "
                + ", ".join(question_with_answer["correct_labels"])
            )

            for option in question_with_answer["options"]:
                if option["label"] in question_with_answer["correct_labels"]:
                    st.text(
                        f"{option['label']}. {option['text']}"
                    )

        st.caption(
            "This is a candidate answer key extracted from the source, "
            "not an independent verification of its correctness."
        )
        
    st.divider()
    st.subheader("Create question bank")

    quiz_questions = []
    unresolved_questions = []

    for index, block in enumerate(questions):
        sections = separate_question_sections(block)
        parsed = extract_question_options(sections)
        result = extract_answer_key(parsed)

        options = result.get("options", [])
        correct_labels = result.get("correct_labels", [])

        option_labels = [
            option["label"] for option in options
        ]

        issues = []

        if not result.get("question_text", "").strip():
            issues.append("Question wording is missing.")

        if not 2 <= len(options) <= 8:
            issues.append("Could not identify the options.")

        if any(not option["text"].strip() for option in options):
            issues.append("An option is empty.")

        if len(option_labels) != len(set(option_labels)):
            issues.append("Option labels repeat.")

        if not correct_labels:
            issues.append("Could not extract an explicit answer key.")

        if not set(correct_labels).issubset(option_labels):
            issues.append("Answer key does not match the options.")

        issues.extend(result.get("answer_issues", []))

        if issues:
            unresolved_questions.append(
                {
                    "source_number": block["source_number"],
                    "source_pages": block["source_pages"],
                    "issues": list(dict.fromkeys(issues)),
                    "raw_text": block["raw_text"],
                }
            )
            continue

        quiz_questions.append(
            {
                "id": str(index),
                "source_number": block["source_number"],
                "source_pages": block["source_pages"],
                "question_text": result["question_text"],
                "options": options,
                "correct_labels": correct_labels,
                "selection_type": (
                    "multiple"
                    if len(correct_labels) > 1
                    else "single"
                ),
                "source_feedback": result["source_feedback"],
                "status": "auto_extracted",
                "extraction_warnings": result.get("review_reasons", []),
            }
        )

    included_col, unresolved_col = st.columns(2)

    included_col.metric("Included in quiz", len(quiz_questions))
    unresolved_col.metric("Unresolved", len(unresolved_questions))

    st.caption(
        "Questions are included automatically after basic structural "
        "checks. Extracted wording and answer keys are not independently "
        "verified."
    )

    if unresolved_questions:
        st.warning(
            f"{len(unresolved_questions)} questions could not be "
            "converted reliably and are excluded from this quiz."
        )

        with st.expander("View unresolved questions"):
            for item in unresolved_questions:
                st.write(
                    f"Question {item['source_number']}: "
                    + " ".join(item["issues"])
                )

        st.download_button(
            "Download unresolved questions",
            data=json.dumps(
                unresolved_questions,
                indent=2,
                ensure_ascii=False,
            ),
            file_name="unresolved_questions.json",
            mime="application/json",
        )

    if quiz_questions:
        question_bank = {
            "schema_version": 1,
            "document_id": hashlib.sha256(
                uploaded_file.getvalue()
            ).hexdigest(),
            "source_filename": uploaded_file.name,
            "source_question_count": len(questions),
            "included_question_count": len(quiz_questions),
            "excluded_question_count": len(unresolved_questions),
            "questions": quiz_questions,
        }

        st.download_button(
            "Download question bank",
            data=json.dumps(
                question_bank,
                indent=2,
                ensure_ascii=False,
            ),
            file_name="question_bank.json",
            mime="application/json",
        )
    else:
        st.error(
            "No questions could be converted with the current parser."
        )