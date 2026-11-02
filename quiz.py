"""Run: python -m streamlit run quiz.py"""
import hashlib
import json
import streamlit as st


def validate_bank(bank):
    questions = bank.get('questions') if isinstance(bank, dict) else None
    if not isinstance(questions, list) or not questions:
        raise ValueError('The question bank must contain a nonempty questions list.')
    ids = set()
    for q in questions:
        if not isinstance(q, dict):
            raise ValueError('Invalid question entry.')
        qid = str(q.get('id', ''))
        if not qid or qid in ids:
            raise ValueError('Question IDs must be present and unique.')
        ids.add(qid)
        q['id'] = qid
        if not isinstance(q.get('question_text'), str) or not q['question_text'].strip():
            raise ValueError(f'Question {qid}: missing wording.')
        options = q.get('options', [])
        if not isinstance(options, list) or not 2 <= len(options) <= 8:
            raise ValueError(f'Question {qid}: invalid options.')
        labels = []
        for option in options:
            if not isinstance(option, dict) or not all(isinstance(option.get(k), str) and option[k].strip() for k in ('label', 'text')):
                raise ValueError(f'Question {qid}: invalid option.')
            labels.append(option['label'])
        correct = q.get('correct_labels')
        if len(set(labels)) != len(labels) or not isinstance(correct, list) or not correct or not all(isinstance(x, str) for x in correct) or not set(correct).issubset(labels):
            raise ValueError(f'Question {qid}: invalid answer key.')
    return questions


def score_question(question, selected):
    correct = set(question['correct_labels'])
    return len(set(selected) & correct) / len(correct)


def main():
    st.set_page_config(page_title='MCQ Practice Quiz', page_icon='📝')
    st.title('MCQ Practice Quiz')
    upload = st.file_uploader('Upload your downloaded question_bank.json', type=['json'])
    if upload is None:
        return
    raw = upload.getvalue()
    try:
        questions = validate_bank(json.loads(raw))
    except (ValueError, TypeError, KeyError) as exc:
        st.error(f'Unable to load question bank: {exc}')
        return
    digest = hashlib.sha256(raw).hexdigest()
    attempts = st.session_state.setdefault('quiz_attempts', {})
    attempt = attempts.setdefault(digest, {'answers': {}, 'flags': {}, 'position': 0, 'submitted': False, 'generation': 0})
    n = len(questions)
    prefix = f'{digest}:{attempt["generation"]}'
    st.caption(f'{n} questions • 1 mark each • No negative marks. Partial credit is split equally among correct answers.')
    st.caption('Progress is retained while this browser session remains open. Refreshing or closing it may reset progress.')
    if attempt['submitted']:
        scores = [score_question(q, attempt['answers'].get(q['id'], [])) for q in questions]
        total = sum(scores)
        a, b = st.columns(2)
        a.metric('Score', f'{total:.2f} / {n}')
        b.metric('Percentage', f'{100 * total / n:.2f}%')
        st.subheader('Answer review')
        for i, (q, score) in enumerate(zip(questions, scores)):
            selected = attempt['answers'].get(q['id'], [])
            with st.expander(f'Question {i + 1} — {score:.2f} / 1'):
                st.text(q['question_text'])
                for option in q['options']:
                    tags = []
                    if option['label'] in selected:
                        tags.append('Your selection')
                    if option['label'] in q['correct_labels']:
                        tags.append('Correct')
                    st.text(f'{option["label"]}. {option["text"]}' + (' [' + ', '.join(tags) + ']' if tags else ''))
                if not selected:
                    st.write('Unanswered')
                st.write('Source explanation')
                st.text(q.get('source_feedback') or 'No explanation supplied.')
        try:
            from rag_study import quiz_study_panel
            quiz_study_panel(questions, attempt['answers'], prefix)
        except ImportError:
            st.info('To enable study explanations, place rag_study.py beside quiz.py and install scikit-learn.')
        report = {'total_marks': total, 'maximum_marks': n, 'percentage': 100 * total / n,
                  'answers': attempt['answers'], 'flags': attempt['flags']}
        st.download_button('Download results', json.dumps(report, indent=2), 'quiz_results.json', 'application/json')
        if st.button('Start a new attempt'):
            attempt.update(answers={}, flags={}, position=0, submitted=False, generation=attempt['generation'] + 1)
            st.rerun()
        return

    def status(i):
        qid = questions[i]['id']
        return f'Question {i+1}' + (' • Flagged' if attempt['flags'].get(qid) else '') + (' • Answered' if attempt['answers'].get(qid) else '')

    # Navigation is outside the answer form; saved answers live independently of widgets.
    with st.form(prefix + ':jump'):
        target = st.selectbox('Go to a question', range(n), index=attempt['position'], format_func=status)
        if st.form_submit_button('Go'):
            attempt['position'] = target
            st.rerun()
    st.caption('Use Save before using Go to keep changes on the current question.')
    position = attempt['position']
    q = questions[position]
    qid = q['id']
    saved = attempt['answers'].get(qid, [])
    answered = sum(bool(attempt['answers'].get(item['id'])) for item in questions)
    st.progress(answered / n, text=f'{answered} of {n} answered')
    flagged = [str(i+1) for i, item in enumerate(questions) if attempt['flags'].get(item['id'])]
    st.caption('Flagged questions: ' + (', '.join(flagged) or 'None'))
    st.subheader(f'Question {position+1} of {n}')
    st.text(q['question_text'])
    with st.form(f'{prefix}:question:{qid}'):
        if len(set(q['correct_labels'])) > 1:
            st.write('Select all answers that apply.')
            selected = [o['label'] for o in q['options'] if st.checkbox(f'{o["label"]}. {o["text"]}', value=o['label'] in saved, key=f'{prefix}:{qid}:{o["label"]}')]
        else:
            labels = [o['label'] for o in q['options']]
            text = {o['label']: o['text'] for o in q['options']}
            choice = st.radio('Choose one answer', [None] + labels,
                              index=labels.index(saved[0])+1 if saved else 0,
                              format_func=lambda x: 'Unanswered' if x is None else f'{x}. {text[x]}', key=f'{prefix}:{qid}:radio')
            selected = [] if choice is None else [choice]
        flag = st.checkbox('Flag for later review', value=attempt['flags'].get(qid, False), key=f'{prefix}:{qid}:flag')
        left, middle, right = st.columns(3)
        previous = left.form_submit_button('Save & Previous', disabled=position == 0)
        save = middle.form_submit_button('Save')
        following = right.form_submit_button('Save & Next', disabled=position == n-1)
        submit = st.form_submit_button('Save & Submit entire quiz')
        if previous or save or following or submit:
            attempt['answers'][qid] = selected
            attempt['flags'][qid] = flag
            if previous:
                attempt['position'] -= 1
            if following:
                attempt['position'] += 1
            if submit:
                attempt['submitted'] = True
            st.rerun()
    st.caption('Submit scores all questions, including unanswered questions as zero, and opens the answer review.')


if __name__ == '__main__':
    main()
