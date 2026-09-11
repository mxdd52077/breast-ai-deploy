"""Grounded patient education chat page."""

import streamlit as st

from src.patient_companion.knowledge import load_knowledge
from src.patient_companion.provider import PatientAIError, answer_with_openai
from src.patient_companion.rag import URGENT_TERMS, answer_from_demo, retrieve_chunks
from src.patient_companion.ui_state import (
    get_case,
    get_patient_api_key,
    get_patient_model,
    initialize_patient_state,
)

initialize_patient_state()
case = get_case()
stage = case.profile.treatment_stage if case else None
chunks = load_knowledge()

st.info(
    "回答仅来自已审核知识片段。涉及治疗选择、改药或知识库证据不足时，请咨询治疗团队。",
    icon=":material/verified_user:",
)

for message in st.session_state.patient_chat:
    with st.chat_message(message["role"]):
        st.write(message["content"])

question = st.chat_input("例如：治疗期间疲劳应该记录什么？", submit_mode="disable")
if question:
    st.session_state.patient_chat.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)
    retrieved = retrieve_chunks(question, chunks, stage=stage)
    try:
        if any(term in question for term in URGENT_TERMS):
            answer = answer_from_demo(question, [])
        elif get_patient_api_key():
            answer = answer_with_openai(
                question,
                retrieved,
                api_key=get_patient_api_key(),
                model=get_patient_model(),
            )
        else:
            answer = answer_from_demo(question, retrieved)
    except PatientAIError as exc:
        answer = answer_from_demo(question, [])
        st.error(str(exc))

    sources = {chunk.id: chunk for chunk in retrieved}
    response_text = answer.answer
    with st.chat_message("assistant"):
        st.write(response_text)
        if answer.safety_notice:
            st.caption(answer.safety_notice)
        for citation in answer.citations:
            source = sources[citation]
            st.markdown(f"来源：[{source.publisher} · {source.title}]({source.source_url})")
    st.session_state.patient_chat.append({"role": "assistant", "content": response_text})
