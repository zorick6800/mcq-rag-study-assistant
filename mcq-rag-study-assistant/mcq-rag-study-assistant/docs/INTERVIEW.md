# Resume and interview presentation

## Resume placement

Use **Personal Projects** (or **Selected Projects**), separate from employer experience.

**MCQ Practice Assistant with Local RAG | Python, Streamlit, PyMuPDF, scikit-learn, Ollama, Llama 3.2**

- Built a Python/Streamlit practice assistant that converts supported PDFs into interactive quizzes with review flags, partial-credit scoring and source-based answer review.
- Implemented a local RAG pipeline using document chunking, TF-IDF retrieval and Ollama-hosted Llama 3.2 to explain quiz questions from separately uploaded study materials.
- Added structured response validation, source citations, quotation checks and bounded retries to filter malformed or untraceable explanations.

One-line version: Built a Python/Streamlit quiz assistant with local RAG, combining PDF extraction, TF-IDF retrieval and Ollama-generated study explanations with source citations and deterministic scoring.

Skills: Retrieval-Augmented Generation (RAG), document ingestion and chunking, TF-IDF retrieval, local LLM integration, structured output validation, AI-assisted development.

Do not claim agentic AI, embeddings, vector databases, production deployment, measured accuracy improvements or employer adoption for this implementation.

## 60–90 second introduction

“I built a personal MCQ Practice Assistant to turn practice-test PDFs into an interactive quiz and help me understand mistakes using separate study materials. I used Python and Streamlit for the application and PyMuPDF for extraction. The quiz supports single and multiple answers, review flags and partial-credit scoring.

For the explanation layer, I split study documents into overlapping passages, kept source-page metadata, and used TF-IDF to retrieve relevant passages. I send those passages with the quiz context to Llama 3.2 running locally through Ollama. The model returns structured output, and my code checks source identifiers and supporting quotations before showing explanations.

A key design decision was to keep the answer key and scoring separate from generated explanations. One challenge was that the model sometimes paraphrased evidence or returned invalid citations. I added validation, filtering and one retry, while recognizing that matching a quotation does not prove the claim is correct. My next step is systematic evaluation and better retrieval before adding agentic functionality.”

## Questions to prepare

**Why is this RAG?** Relevant document passages are retrieved at request time and supplied to the model as context for generation. The model is not retrained on the PDFs.

**Why TF-IDF?** It provides a simple local baseline without an embedding service. It works well for explicit service names but can miss semantic matches and paraphrases. I would compare embeddings against the same evaluation set before switching.

**Why 300 words and 50 words overlap?** They are initial heuristics to balance context size and boundary continuity, not optimized settings. I need to evaluate whether they split definitions or mix topics.

**How are hallucinations handled?** Prompt constraints, structured JSON, source-ID validation and exact-quotation checks reduce some failure modes. They cannot prove factual correctness or semantic support. Unsupported points are omitted; a single retry is allowed when none validate.

**How is scoring protected?** A deterministic function compares selected labels with the fixed source key. The LLM cannot change marks. Multiple-answer credit is divided among correct choices; wrong selections have no penalty under the chosen practice rule.

**What was tested?** Local logic checks covered retrieval/no-match, quotation validation, retry success/fallback and scoring. The user exercised the quiz and local model manually. There is no full quality benchmark or deployment test yet.

**Is it agentic?** No. It is a predefined RAG workflow with a bounded retry. A future agent could choose retrieval queries and decide whether more evidence is needed, with explicit tool and iteration limits.

**Did you use AI to build it?** Yes. I used AI-assisted development to generate and refine code, tested the app locally and iterated on extraction and output failures. I would be transparent about that and explain the modules and tradeoffs I understand rather than claim every line was written unaided.

## Five-minute demo

1. Show the architecture and explain separation of answer key, scoring and study corpus.
2. Load the original demo bank, answer one question incorrectly and flag another.
3. Submit and show deterministic partial-credit results.
4. Load prepared demo study materials and request an explanation.
5. Open the source passages and compare one claim with its evidence.
6. Explain known limitations and next evaluation steps.

## Evaluation plan (not completed)

Select ten representative questions, including multi-select, unanswered, comparison, insufficient-evidence and conflicting-source cases. For each, record retrieval relevance, whether every factual claim is supported, whether the learner's actual choice is addressed, source citation validity, latency and fallback behavior. Review manually against the documents. Report real results only after running this evaluation.
