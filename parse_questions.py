import re


def split_question_blocks(pages: list[dict]) -> list[dict]:
    """Split this practice-set format using numbered question headings."""

    text_parts = []
    page_ranges = []
    position = 0

    # Combine pages while remembering where each page starts and ends.
    for page in pages:
        page_text = page["text"] + "\n"

        page_ranges.append(
            {
                "page_number": page["page_number"],
                "start": position,
                "end": position + len(page_text),
            }
        )

        text_parts.append(page_text)
        position += len(page_text)

    full_text = "".join(text_parts)

    # Matches headings such as "1. Question" on a separate line.
    heading_pattern = re.compile(
        r"^[ \t]*(\d+)\.[ \t]*Question[ \t]*\r?$",
        flags=re.MULTILINE | re.IGNORECASE,
    )

    headings = list(heading_pattern.finditer(full_text))
    questions = []

    for index, heading in enumerate(headings):
        start = heading.start()

        # A block ends where the next question begins.
        end = (
            headings[index + 1].start()
            if index + 1 < len(headings)
            else len(full_text)
        )

        source_pages = [
            page["page_number"]
            for page in page_ranges
            if page["start"] < end and page["end"] > start
        ]

        # Match highlights only within this question's option section.
        block_text = full_text[start:end].strip()

        question_part = re.split(
            r"^[ \t]*Unattempted[ \t]*\r?$",
            block_text,
            maxsplit=1,
            flags=re.MULTILINE | re.IGNORECASE,
        )[0]

        normalized_question = " ".join(question_part.split()).casefold()

        green_answers = []

        for page in pages:
            if page["page_number"] not in source_pages:
                continue

            for evidence in page.get("green_answers", []):
                normalized_highlight = (
                    " ".join(evidence["text"].split()).casefold()
                )

                if (
                    normalized_highlight
                    and normalized_highlight in normalized_question
                ):
                    green_answers.append(evidence)
                    
        questions.append(
            {
                "source_number": int(heading.group(1)),
                "source_pages": source_pages,
                "raw_text": full_text[start:end].strip(),
                "green_answers": green_answers,
            }
        )

    return questions

def separate_question_sections(block: dict) -> dict:
    """Separate question content from feedback without guessing answers."""

    raw_text = block["raw_text"]
    review_reasons = []

    # Match the status marker only when it occupies a complete line.
    markers = list(
        re.finditer(
            r"^[ \t]*Unattempted[ \t]*\r?$",
            raw_text,
            flags=re.MULTILINE | re.IGNORECASE,
        )
    )

    question_and_options = ""
    source_feedback = ""

    if len(markers) != 1:
        review_reasons.append(
            "Expected exactly one 'Unattempted' boundary."
        )
    else:
        marker = markers[0]

        question_and_options = raw_text[:marker.start()].strip()
        source_feedback = raw_text[marker.end():].strip()

        # Remove only the numbered heading, not the question wording.
        question_and_options = re.sub(
            r"\A[ \t]*\d+\.[ \t]*Question[ \t]*\r?\n",
            "",
            question_and_options,
            count=1,
            flags=re.IGNORECASE,
        )

        if not question_and_options:
            review_reasons.append("Question content is empty.")

        if not source_feedback:
            review_reasons.append("Source explanation is missing.")

    if re.search(
        r"Use Page numbers below to navigate",
        raw_text,
        flags=re.IGNORECASE,
    ):
        review_reasons.append(
            "Website navigation text appears inside this question block."
        )

    return {
        "green_answers": block.get("green_answers", []),
        "source_number": block["source_number"],
        "source_pages": block["source_pages"],
        "question_and_options": question_and_options,
        "source_feedback": source_feedback,
        "review_reasons": review_reasons,
        "status": (
            "needs_review"
            if review_reasons
            else "sections_separated"
        ),
        "raw_text": raw_text,
    }
    
def extract_question_options(section: dict) -> dict:
    """Extract draft options using this PDF's labels and indentation."""

    content = section["question_and_options"]
    review_reasons = list(section["review_reasons"])
    cleanup_notes = []

    # Remove the specific website navigation block in this export.
    navigation_pattern = re.compile(
        r"^[ \t]*Use Page numbers below to navigate to other"
        r"[ \t]*\r?\n"
        r"[ \t]*practice tests[ \t]*\r?\n"
        r"[ \t]*Pages:[ \t]*\r?\n"
        r"(?:[ \t]*\d+(?:[ \t]+\d+)*[ \t]*\r?\n)+",
        flags=re.MULTILINE | re.IGNORECASE,
    )

    content, removed_count = navigation_pattern.subn("", content)

    if removed_count:
        cleanup_notes.append(
            "Removed website page-navigation text. "
            "Compare the options with the original PDF."
        )

    lines = content.splitlines()

    # First preference: explicit option labels such as A. or B.
    label_pattern = re.compile(r"^[ \t]*([A-H])[.)][ \t\u00a0]+")

    labelled_starts = [
        (index, label_pattern.match(line))
        for index, line in enumerate(lines)
        if label_pattern.match(line)
    ]

    method = "explicit_labels"

    if len(labelled_starts) >= 2:
        starts = [index for index, _ in labelled_starts]
        labels = [match.group(1) for _, match in labelled_starts]

        expected_labels = [
            chr(ord("A") + index)
            for index in range(len(labels))
        ]

        if labels != expected_labels:
            review_reasons.append(
                "Option labels are not a continuous A, B, C sequence."
            )

    else:
        method = "indentation_candidate"

        # In this PDF, many unlabelled options begin with one space.
        # This is a heuristic, so its results always require review.
        starts = [
            index
            for index, line in enumerate(lines)
            if (
                line.startswith(" ")
                and len(line) > 1
                and not line[1].isspace()
                and line.strip()
            )
        ]

        labels = [
            chr(ord("A") + index)
            for index in range(len(starts))
        ]

        review_reasons.append(
            "Options were inferred from indentation. "
            "Confirm their boundaries against the PDF."
        )
        # Fallback for unlabelled, single-line options after a question mark.
    if method == "indentation_candidate" and not 2 <= len(starts) <= 8:
        question_endings = [
            index
            for index, line in enumerate(lines)
            if line.rstrip().endswith("?")
        ]

        if question_endings:
            last_question_line = question_endings[-1]

            candidate_starts = [
                index
                for index in range(last_question_line + 1, len(lines))
                if lines[index].strip()
            ]

            if 2 <= len(candidate_starts) <= 8:
                starts = candidate_starts

                labels = [
                    chr(ord("A") + index)
                    for index in range(len(starts))
                ]

                method = "lines_after_question_mark"

                review_reasons = [
                    reason
                    for reason in review_reasons
                    if reason != (
                        "Options were inferred from indentation. "
                        "Confirm their boundaries against the PDF."
                    )
                ]

                review_reasons.append(
                    "Each nonblank line after the final question mark "
                    "was treated as an option. Confirm that no option "
                    "wraps across multiple lines."
                )
    if not 2 <= len(starts) <= 8:
        review_reasons.append(
            "Could not identify between 2 and 8 option starts reliably."
        )

        return {
            **section,
            "question_text": content,
            "options": [],
            "option_method": method,
            "cleanup_notes": cleanup_notes,
            "review_reasons": list(dict.fromkeys(review_reasons)),
            "status": "needs_review",
        }

    question_text = "\n".join(lines[:starts[0]]).strip()
    options = []

    for index, start in enumerate(starts):
        end = (
            starts[index + 1]
            if index + 1 < len(starts)
            else len(lines)
        )

        option_text = "\n".join(lines[start:end]).strip()

        if method == "explicit_labels":
            option_text = re.sub(
                r"^[A-H][.)][ \t\u00a0]+",
                "",
                option_text,
                count=1,
            )

        options.append(
            {
                "label": labels[index],
                "text": option_text,
            }
        )

    if not question_text:
        review_reasons.append("Question text is empty.")

    if any(not option["text"] for option in options):
        review_reasons.append("One or more options are empty.")

    return {
        **section,
        "question_text": question_text,
        "options": options,
        "option_method": method,
        "cleanup_notes": cleanup_notes,
        "review_reasons": list(dict.fromkeys(review_reasons)),
        "status": "draft",
    }
    
def extract_answer_key(question: dict) -> dict:
    """Use green option highlights exclusively; never inspect explanations."""
    def normalize_option(text: str) -> str:
        text = re.sub(r"^\s*[A-H][.)]\s+", "", text, count=1)
        return " ".join(text.split()).casefold()

    options = question.get("options", [])
    evidence_items = question.get("green_answers", [])
    candidates = set()
    issues = []
    labels = [option["label"] for option in options]
    if len(labels) != len(set(labels)):
        issues.append("Extracted option labels are not unique.")
    if not evidence_items:
        issues.append("No green-highlighted answer was found for this question.")
    for evidence in evidence_items:
        highlighted = normalize_option(evidence.get("text", ""))
        matches = [option["label"] for option in options
                   if highlighted and normalize_option(option["text"]) == highlighted]
        if len(matches) == 1:
            candidates.add(matches[0])
        else:
            issues.append("A green highlight could not be matched to exactly one "
                          "complete option: " + evidence.get("text", ""))

    # Never publish a partial key when any highlight failed to match.
    correct_labels = [label for label in labels if label in candidates] if not issues else []
    return {
        **question,
        "answer_source": "green_highlight" if correct_labels else "unresolved",
        "correct_labels": correct_labels,
        "answer_issues": list(dict.fromkeys(issues)),
        "answer_status": "candidate_extracted" if correct_labels else "needs_review",
        "selection_type": ("multiple" if len(correct_labels) > 1 else
                           "single" if correct_labels else "unknown"),
    }
