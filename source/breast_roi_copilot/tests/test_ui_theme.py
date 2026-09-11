from pathlib import Path

from src.ui.brand import BRAND_HEADER_JS, GLOBAL_CSS, header_content, role_for_path


def test_mvp_entrypoint_does_not_offer_an_incomplete_english_toggle() -> None:
    app_source = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
    assert '"English"' not in app_source
    assert 'st.session_state["app_language"] = "中文"' in app_source


def test_role_switcher_has_descriptive_cards_and_active_state() -> None:
    app_source = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
    assert "筛查决策与 ROI 管理" in app_source
    assert "个人资料与照护追踪" in app_source
    assert "entry-card is-active" in app_source


def test_workspace_entry_uses_root_query_routes_to_avoid_unregistered_page_modal() -> None:
    app_source = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
    assert 'href="/?workspace=institution"' in app_source
    assert 'href="/?workspace=patient"' in app_source
    assert 'href="/patient-profile"' not in app_source


def test_patient_confirmation_page_exposes_clear_next_steps() -> None:
    page_source = (
        Path(__file__).parents[1] / "app_pages" / "patient_profile.py"
    ).read_text(encoding="utf-8")
    assert "查看照护报告" in page_source
    assert "查看照护日历" in page_source
    assert 'st.page_link("app_pages/patient_report.py"' in page_source
    assert 'st.page_link("app_pages/patient_tasks.py"' in page_source


def test_header_content_distinguishes_patient_and_institution_modes() -> None:
    patient = header_content("患者陪伴助手", "我的档案")
    institution = header_content("机构决策平台", "AI 决策助手")

    assert patient["kicker"] == "PATIENT CARE NAVIGATOR"
    assert patient["title"] == "我的档案"
    assert institution["kicker"] == "SCREENING DECISION INTELLIGENCE"


def test_gsap_header_honors_reduced_motion_and_cleans_up() -> None:
    assert "gsap" in BRAND_HEADER_JS.lower()
    assert "prefers-reduced-motion" in BRAND_HEADER_JS
    assert "ctx.revert()" in BRAND_HEADER_JS


def test_global_styles_include_mobile_focus_and_active_states() -> None:
    assert "@media (max-width: 768px)" in GLOBAL_CSS
    assert ":focus-visible" in GLOBAL_CSS
    assert ":active" in GLOBAL_CSS


def test_role_for_path_keeps_the_two_navigation_trees_separate() -> None:
    assert role_for_path("") == "机构决策平台"
    assert role_for_path("data_intake") == "机构决策平台"
    assert role_for_path("patient-profile") == "患者陪伴助手"
    assert role_for_path("patient_knowledge") == "患者陪伴助手"
