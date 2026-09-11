"""Synthetic care-gap detection performance evaluation."""

import pandas as pd
import streamlit as st

from src.evaluation import evaluate_classifier, threshold_sweep
from src.i18n import is_zh, t
from src.population import SyntheticPopulationConfig, generate_synthetic_population


@st.cache_data(max_entries=20)
def load_population(size: int, seed: int, noise: float) -> pd.DataFrame:
    return generate_synthetic_population(SyntheticPopulationConfig(size, seed, noise))


st.caption(t("Evaluate a care-gap detection score before using it to prioritize outreach."))
approved_population = st.session_state.get("approved_population")
approved_metadata = st.session_state.get("approved_population_metadata", {})
if approved_population is None:
    st.warning(
        t("Synthetic demo only: every patient record and performance result on this page is simulated. It is not an evaluation on HDR or real clinical data."),
        icon=":material/science:",
    )
else:
    st.success(
        f"{t('Approved session dataset')}: {approved_metadata.get('source_name', t('Uploaded dataset'))} · {len(approved_population):,} {t('rows')}",
        icon=":material/verified:",
    )

with st.sidebar:
    st.subheader(t("Evaluation settings"))
    threshold = st.slider(t("Decision threshold"), 0.10, 0.90, 0.50, 0.05)
    if approved_population is None:
        population_size = st.number_input(t("Synthetic population size"), 1_000, 100_000, 10_000, 1_000)
        model_noise = st.slider(t("Synthetic model noise"), 0.20, 2.00, 0.85, 0.05)
        seed = st.number_input(t("Random seed"), 0, 100_000, 42, 1)

if approved_population is None:
    population = load_population(int(population_size), int(seed), float(model_noise))
    st.session_state["synthetic_population_settings"] = {
        "population_size": int(population_size), "seed": int(seed), "model_noise": float(model_noise)
    }
else:
    population = approved_population.copy()
metrics = evaluate_classifier(population["ground_truth_gap"], population["care_gap_score"], threshold)

st.subheader(t("Operating-point performance"))
with st.container(horizontal=True):
    st.metric(t("Sensitivity"), f"{metrics.sensitivity:.1%}", border=True)
    st.metric(t("Specificity"), f"{metrics.specificity:.1%}", border=True)
    st.metric(t("Precision"), f"{metrics.precision:.1%}", border=True)
    st.metric(t("Accuracy"), f"{metrics.accuracy:.1%}", border=True)
    st.metric(t("F1 score"), f"{metrics.f1_score:.1%}", border=True)

left, right = st.columns(2)
with left.container(border=True, height="stretch"):
    st.subheader(t("Confusion matrix"))
    matrix = pd.DataFrame(
        [[metrics.true_positive, metrics.false_negative], [metrics.false_positive, metrics.true_negative]],
        index=[t("Actual care gap"), t("Actual no gap")],
        columns=[t("Predicted care gap"), t("Predicted no gap")],
    )
    st.dataframe(matrix, width="stretch")
    st.caption(t("Ground truth demo rule: a synthetic patient is overdue when time since last screening is at least two years."))

with right.container(border=True, height="stretch"):
    st.subheader(t("Product interpretation"))
    if is_zh():
        st.markdown(
            f"- 当前阈值为 **{threshold:.2f}**，每 100 个真实缺口约识别出 **{metrics.sensitivity * 100:.1f}** 个。\n"
            f"- 每 100 个被模型标记的人中，约 **{metrics.precision * 100:.1f}** 个确实存在缺口。\n"
            "- 阈值不是越高越好：提高阈值通常减少误报，但也可能漏掉更多需要外展的人。"
        )
    else:
        st.markdown(
            f"- At threshold **{threshold:.2f}**, the model finds about **{metrics.sensitivity * 100:.1f}** of every 100 true gaps.\n"
            f"- Of every 100 people flagged, about **{metrics.precision * 100:.1f}** truly have a gap.\n"
            "- A higher threshold usually reduces false positives but may miss more people who need outreach."
        )

with st.container(border=True):
    st.subheader(t("Threshold trade-off"))
    sweep = threshold_sweep(
        population["ground_truth_gap"], population["care_gap_score"],
        [round(value / 20, 2) for value in range(2, 19)],
    )
    chart = sweep[["threshold", "sensitivity", "specificity", "precision", "accuracy"]].rename(
        columns={
            "threshold": t("Threshold"), "sensitivity": t("Sensitivity"),
            "specificity": t("Specificity"), "precision": t("Precision"),
            "accuracy": t("Accuracy"),
        }
    )
    st.line_chart(chart, x=t("Threshold"), y=[t("Sensitivity"), t("Specificity"), t("Precision"), t("Accuracy")])

with st.expander(t("Inspect synthetic data and assumptions"), icon=":material/table_view:"):
    if approved_population is None or approved_metadata.get("is_synthetic"):
        st.caption(t("Patient IDs are fictional and prefixed SYN-. No PHI or real patient data is used."))
    else:
        st.caption(t("Patient identifiers were hashed locally before downstream use."))
    st.dataframe(population.head(100), hide_index=True, width="stretch")
    st.download_button(
        t("Download synthetic population (CSV)"), population.to_csv(index=False).encode("utf-8"),
        "synthetic_breast_screening_population.csv", "text/csv", icon=":material/download:",
    )
