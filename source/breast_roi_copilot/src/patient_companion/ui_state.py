"""Session-only state helpers shared by patient pages."""

import os

import streamlit as st

from .schemas import PatientCase


def initialize_patient_state() -> None:
    st.session_state.setdefault("patient_case", None)
    st.session_state.setdefault("patient_chat", [])
    st.session_state.setdefault("patient_task_status", {})
    st.session_state.setdefault("patient_api_key_session", "")


def get_case() -> PatientCase | None:
    initialize_patient_state()
    value = st.session_state.patient_case
    if value is None or isinstance(value, PatientCase):
        return value
    # Streamlit hot reload can leave an instance of the previous PatientCase
    # class in session state. Serialize that stale model before validating it
    # against the freshly imported schema.
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    case = PatientCase.model_validate(value)
    st.session_state.patient_case = case
    return case


def get_patient_api_key() -> str:
    initialize_patient_state()
    session_key = str(st.session_state.get("patient_api_key_session", "")).strip()
    try:
        secret = st.secrets.get("PATIENT_OPENAI_API_KEY", "") or st.secrets.get(
            "OPENAI_API_KEY", ""
        )
    except (FileNotFoundError, KeyError):
        secret = ""
    environment_key = os.getenv("PATIENT_OPENAI_API_KEY", "") or os.getenv(
        "OPENAI_API_KEY", ""
    )
    return str(session_key or secret or environment_key)


def get_patient_model() -> str:
    try:
        secret = st.secrets.get("PATIENT_OPENAI_MODEL", "") or st.secrets.get(
            "OPENAI_MODEL", ""
        )
    except (FileNotFoundError, KeyError):
        secret = ""
    environment_model = os.getenv("PATIENT_OPENAI_MODEL", "") or os.getenv(
        "OPENAI_MODEL", ""
    )
    return str(secret or environment_model or "gpt-5.6-sol")
