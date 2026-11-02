import pymupdf


def extract_pdf_pages(pdf_bytes: bytes) -> list[dict]:
    """Extract page text and green answer-box evidence."""
    pages = []

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        if document.needs_pass:
            raise ValueError("This PDF is password-protected.")

        for page_number, page in enumerate(document, start=1):
            green_answers = []
            option_boxes = []
            seen_rectangles = set()

            for shape in page.get_drawings():
                colour = shape.get("fill")
                rect = shape["rect"]

                if not colour or len(colour) != 3:
                    continue

                red, green, blue = colour

                # Tuned to the green option boxes in your updated PDF.
                is_green = (
                    green > red + 0.15
                    and green > blue + 0.10
                )

                is_option_sized = (
                    rect.width > page.rect.width * 0.4
                    and 12 < rect.height < 180
                )

                is_neutral = all(abs(a - b) < 0.005 for a, b in zip(colour, (0.97255, 0.98039, 0.98824)))
                if not ((is_green or is_neutral) and is_option_sized):
                    continue

                # Background and borders may describe the same box.
                rectangle_key = tuple(round(v, 1) for v in rect)

                if rectangle_key in seen_rectangles:
                    continue

                seen_rectangles.add(rectangle_key)

                highlighted_text = page.get_textbox(rect).strip()

                if highlighted_text:
                    option_boxes.append(
                        {
                            "text": highlighted_text,
                            "is_green": is_green,
                            "page_number": page_number,
                            "bbox": list(rect),
                        }
                    )

            green_answers = [box for box in option_boxes if box["is_green"]]
            pages.append(
                {
                    "page_number": page_number,
                    "text": page.get_text("text"),
                    "green_answers": green_answers,
                    "option_boxes": option_boxes,
                }
            )

    return pages