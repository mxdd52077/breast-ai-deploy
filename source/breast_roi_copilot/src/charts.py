"""Plotly chart builders kept separate from calculation and page code."""

import pandas as pd
import plotly.express as px

from src.i18n import t
from src.models.schemas import BreastROIResults


def cost_impact_chart(result: BreastROIResults):
    frame = pd.DataFrame({
        t("Category"): [t("Treatment Cost Avoided"), t("Screening Cost"), t("Follow-up Cost"), t("Net Savings")],
        t("Value"): [result.treatment_cost_avoided, result.screening_cost_total, result.followup_cost_total, result.net_savings],
    })
    fig = px.bar(frame, x=t("Value"), y=t("Category"), orientation="h", color=t("Category"), text_auto="$.3s")
    fig.update_layout(showlegend=False, xaxis_title=t("Dollars"), yaxis_title=None)
    return fig


def screening_reach_chart(result: BreastROIResults):
    frame = pd.DataFrame({
        t("Outcome"): [t("Additional Screened Women"), t("Recalled Patients")],
        t("People"): [result.additional_screened, result.recalled_patients],
    })
    fig = px.bar(frame, x=t("Outcome"), y=t("People"), color=t("Outcome"), text_auto=",.0f")
    fig.update_layout(showlegend=False)
    return fig


def sensitivity_chart(base_inputs, parameter: str, values: list[float]):
    from dataclasses import replace
    from src.models.breast_roi import calculate_breast_roi

    rows = []
    for value in values:
        outcome = calculate_breast_roi(replace(base_inputs, **{parameter: value}))
        rows.append({t("Value"): value, t("Net savings"): outcome.net_savings, "ROI": outcome.roi})
    return px.line(pd.DataFrame(rows), x=t("Value"), y=t("Net savings"), markers=True)
