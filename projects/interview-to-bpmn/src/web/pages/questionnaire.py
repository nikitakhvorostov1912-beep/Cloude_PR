"""Interview questionnaire page — sections by themes, autosave, progress."""
import json
from datetime import datetime

import streamlit as st

from src.config import AppConfig, ProjectDir

QUESTIONNAIRE_BLOCKS = [
    {
        "id": "general",
        "title": "Общая информация об отделе",
        "icon": "1",
        "questions": [
            {"id": "1.1", "text": "Название отдела / подразделения", "type": "text"},
            {"id": "1.2", "text": "ФИО и должность респондента", "type": "text"},
            {"id": "1.3", "text": "Количество сотрудников в отделе", "type": "number"},
            {"id": "1.4", "text": "Кому подчиняется отдел (структура)", "type": "text"},
            {"id": "1.5", "text": "Основные функции и задачи отдела", "type": "textarea"},
            {"id": "1.6", "text": "С какими отделами взаимодействуете чаще всего?", "type": "textarea"},
            {"id": "1.7", "text": "Какие KPI/показатели эффективности отдела?", "type": "textarea"},
        ],
    },
    {
        "id": "processes",
        "title": "Бизнес-процессы (AS IS)",
        "icon": "2",
        "questions": [
            {"id": "2.1", "text": "Перечислите основные бизнес-процессы (3-7 ключевых)", "type": "textarea"},
            {"id": "2.2", "text": "Для каждого процесса: как он начинается (триггер)?", "type": "textarea"},
            {"id": "2.3", "text": "Для каждого процесса: какие основные шаги/этапы?", "type": "textarea"},
            {"id": "2.4", "text": "Для каждого процесса: кто участвует (роли)?", "type": "textarea"},
            {"id": "2.5", "text": "Для каждого процесса: чем он заканчивается (результат)?", "type": "textarea"},
            {"id": "2.6", "text": "Какие документы создаются/используются?", "type": "textarea"},
            {"id": "2.7", "text": "Есть ли точки принятия решений (развилки)?", "type": "textarea"},
            {"id": "2.8", "text": "Какие исключения/нештатные ситуации? Как обрабатываются?", "type": "textarea"},
            {"id": "2.9", "text": "Какова периодичность каждого процесса?", "type": "textarea"},
            {"id": "2.10", "text": "Объём операций (документов/транзакций в день/месяц)?", "type": "textarea"},
        ],
    },
    {
        "id": "documents",
        "title": "Документооборот",
        "icon": "3",
        "questions": [
            {"id": "3.1", "text": "Какие входящие документы получаете?", "type": "textarea"},
            {"id": "3.2", "text": "Какие исходящие документы формируете?", "type": "textarea"},
            {"id": "3.3", "text": "Какие внутренние документы используете?", "type": "textarea"},
            {"id": "3.4", "text": "Есть ли регламентированные формы документов?", "type": "textarea"},
            {"id": "3.5", "text": "Какие согласования требуются и с кем?", "type": "textarea"},
            {"id": "3.6", "text": "Где хранятся документы?", "type": "textarea"},
        ],
    },
    {
        "id": "automation",
        "title": "Текущая автоматизация",
        "icon": "4",
        "questions": [
            {"id": "4.1", "text": "Какие программы/системы используете сейчас?", "type": "textarea"},
            {"id": "4.2", "text": "Используете ли 1С? Какие конфигурации?", "type": "textarea"},
            {"id": "4.3", "text": "Что делаете в 1С, а что вне 1С?", "type": "textarea"},
            {"id": "4.4", "text": "Какие данные вводите вручную?", "type": "textarea"},
            {"id": "4.5", "text": "Есть ли обмен данными между системами?", "type": "textarea"},
            {"id": "4.6", "text": "Какие отчёты формируете? В каких системах?", "type": "textarea"},
        ],
    },
    {
        "id": "problems",
        "title": "Проблемы и болевые точки",
        "icon": "5",
        "questions": [
            {"id": "5.1", "text": "Какие операции занимают больше всего времени?", "type": "textarea"},
            {"id": "5.2", "text": "Где чаще всего возникают ошибки?", "type": "textarea"},
            {"id": "5.3", "text": "Какие процессы считаете неэффективными?", "type": "textarea"},
            {"id": "5.4", "text": "Что хотели бы изменить в первую очередь?", "type": "textarea"},
            {"id": "5.5", "text": "Есть ли дублирование данных / двойной ввод?", "type": "textarea"},
            {"id": "5.6", "text": "Какие задачи требуют немедленного решения?", "type": "textarea"},
            {"id": "5.7", "text": "Были ли случаи потери данных или документов?", "type": "textarea"},
        ],
    },
    {
        "id": "target",
        "title": "Требования к целевой системе (TO BE)",
        "icon": "6",
        "questions": [
            {"id": "6.1", "text": "Какие процессы обязательно автоматизировать?", "type": "textarea"},
            {"id": "6.2", "text": "Какие отчёты / аналитика необходимы руководству?", "type": "textarea"},
            {"id": "6.3", "text": "Какие интеграции с другими системами нужны?", "type": "textarea"},
            {"id": "6.4", "text": "Какие права доступа нужны?", "type": "textarea"},
            {"id": "6.5", "text": "Есть ли требования по срокам внедрения?", "type": "textarea"},
            {"id": "6.6", "text": "Есть ли сезонность / пиковые нагрузки?", "type": "textarea"},
            {"id": "6.7", "text": "Какие регуляторные / законодательные требования?", "type": "textarea"},
        ],
    },
    {
        "id": "nsi",
        "title": "НСИ (нормативно-справочная информация)",
        "icon": "7",
        "questions": [
            {"id": "7.1", "text": "Какие справочники ведёте?", "type": "textarea"},
            {"id": "7.2", "text": "Кто отвечает за ведение справочников?", "type": "text"},
            {"id": "7.3", "text": "Есть ли проблемы с качеством данных?", "type": "textarea"},
            {"id": "7.4", "text": "Какова структура и объём справочников?", "type": "textarea"},
        ],
    },
    {
        "id": "org",
        "title": "Организационные вопросы",
        "icon": "8",
        "questions": [
            {"id": "8.1", "text": "Кто будет ключевым пользователем новой системы?", "type": "text"},
            {"id": "8.2", "text": "Готовы ли сотрудники к обучению?", "type": "textarea"},
            {"id": "8.3", "text": "Есть ли сопротивление изменениям?", "type": "textarea"},
            {"id": "8.4", "text": "Кто принимает окончательные решения по процессам?", "type": "text"},
        ],
    },
]

CHECKLIST = [
    "Все основные процессы отдела перечислены",
    "Для каждого процесса описаны: триггер, шаги, роли, результат",
    "Документооборот описан (входящие, исходящие, внутренние)",
    "Текущие системы и их использование зафиксированы",
    "Болевые точки и проблемы выявлены",
    "Требования к целевой системе сформулированы",
    "НСИ описана",
    "Определён ключевой пользователь",
    "Определены интеграции с другими отделами/системами",
    "Объёмы данных и периодичность операций зафиксированы",
]

TOTAL_QUESTIONS = sum(len(b["questions"]) for b in QUESTIONNAIRE_BLOCKS)


def show_questionnaire(project: ProjectDir, config: AppConfig):
    st.header("Анкета")

    project.questionnaires.mkdir(parents=True, exist_ok=True)

    # --- File selector ---
    existing = sorted(project.questionnaires.glob("*.json"))

    col_sel, col_new = st.columns([3, 1])
    with col_sel:
        options = ["Новая анкета"] + [f.stem for f in existing]
        choice = st.selectbox("Анкета", options, label_visibility="collapsed")
    with col_new:
        dept_name = st.text_input("Отдел", value="", key="q_dept_input")

    # Determine file path for autosave
    if choice == "Новая анкета":
        selected_file = None
        answers = {}
    else:
        selected_file = next((f for f in existing if f.stem == choice), None)
        if selected_file:
            with open(selected_file, encoding="utf-8") as f:
                answers = json.load(f)
        else:
            answers = {}

    # Initialize session state for answers
    state_key = "_questionnaire_answers"
    if state_key not in st.session_state or st.session_state.get("_q_file") != choice:
        st.session_state[state_key] = answers.copy()
        st.session_state["_q_file"] = choice

    answers = st.session_state[state_key]

    # --- Progress bar ---
    filled = sum(1 for k, v in answers.items() if k != "_checklist" and v)
    progress = filled / TOTAL_QUESTIONS if TOTAL_QUESTIONS else 0
    st.progress(progress, text=f"Заполнено: {filled}/{TOTAL_QUESTIONS}")

    st.markdown("---")

    # --- Sections by themes ---
    changed = False

    for block in QUESTIONNAIRE_BLOCKS:
        block_questions = block["questions"]
        block_filled = sum(1 for q in block_questions if answers.get(q["id"]))
        block_total = len(block_questions)
        label = f"{block['title']} ({block_filled}/{block_total})"

        with st.expander(label, expanded=block_filled < block_total):
            for q in block_questions:
                qid = q["id"]
                current = answers.get(qid, "")

                if q["type"] == "text":
                    new_val = st.text_input(
                        f"{qid}. {q['text']}", value=current, key=f"q_{qid}",
                    )
                elif q["type"] == "number":
                    new_val = st.number_input(
                        f"{qid}. {q['text']}",
                        value=int(current) if str(current).isdigit() else 0,
                        key=f"q_{qid}",
                    )
                elif q["type"] == "textarea":
                    new_val = st.text_area(
                        f"{qid}. {q['text']}", value=current, height=100, key=f"q_{qid}",
                    )
                else:
                    new_val = current

                if new_val != current:
                    answers[qid] = new_val
                    changed = True

    # --- Checklist ---
    st.markdown("---")
    st.subheader("Чек-лист полноты интервью")

    checklist_state = answers.get("_checklist", {})
    for i, item in enumerate(CHECKLIST):
        new_val = st.checkbox(
            item, value=checklist_state.get(str(i), False), key=f"check_{i}",
        )
        if new_val != checklist_state.get(str(i), False):
            checklist_state[str(i)] = new_val
            changed = True
    answers["_checklist"] = checklist_state

    # --- Summary metrics ---
    st.markdown("---")
    checked = sum(1 for v in checklist_state.values() if v)

    c1, c2 = st.columns(2)
    c1.metric("Заполнено вопросов", f"{filled}/{TOTAL_QUESTIONS}")
    c2.metric("Чек-лист", f"{checked}/{len(CHECKLIST)}")

    # --- Autosave ---
    if changed:
        st.session_state[state_key] = answers
        _autosave(answers, project, dept_name, selected_file)

    # --- Export ---
    st.markdown("---")
    _show_export(answers, project, dept_name, selected_file)


def _autosave(answers: dict, project: ProjectDir, dept_name: str, selected_file):
    """Autosave answers to file."""
    if selected_file:
        save_path = selected_file
    else:
        dept = dept_name or answers.get("1.1", "dept") or "dept"
        filename = f"questionnaire_{dept}.json"
        save_path = project.questionnaires / filename

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(answers, f, ensure_ascii=False, indent=2)
    st.success(f"Сохранено в {datetime.now().strftime('%H:%M')}")


def _show_export(answers: dict, project: ProjectDir, dept_name: str, selected_file):
    """Export section."""
    st.markdown("**Экспорт**")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Сохранить как новый файл", key="btn_save_quest_new"):
            dept = dept_name or answers.get("1.1", "dept") or "dept"
            filename = f"questionnaire_{dept}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
            save_path = project.questionnaires / filename
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(answers, f, ensure_ascii=False, indent=2)
            st.success(f"Сохранено: {filename}")

    with c2:
        data = json.dumps(answers, ensure_ascii=False, indent=2)
        st.download_button(
            "Скачать JSON",
            data=data,
            file_name="questionnaire.json",
            mime="application/json",
        )
