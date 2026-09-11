"""Session-only patient care calendar."""

import calendar
from datetime import date

import streamlit as st

from src.patient_companion.schemas import TaskStatus
from src.patient_companion.tasks import build_care_tasks
from src.patient_companion.ui_state import get_case, initialize_patient_state

initialize_patient_state()
case = get_case()
if case is None:
    st.warning("请先在“我的档案”建立并确认档案。")
    st.stop()

tasks = build_care_tasks(case.events)
st.session_state.patient_task_status = {
    task.id: st.session_state.patient_task_status.get(task.id, TaskStatus.PENDING.value)
    for task in tasks
}

st.caption("任务只来自已确认医嘱或复诊安排，状态仅保存在当前浏览器会话。")
if not tasks:
    st.info("暂无可执行任务。请先返回“我的档案”确认医嘱。")
    st.stop()

today = date.today()
nearest_task_date = min(
    (task.due_date for task in tasks),
    key=lambda due_date: (abs((due_date - today).days), due_date),
)
st.session_state.setdefault("patient_calendar_date", nearest_task_date.isoformat())
st.session_state.setdefault(
    "patient_calendar_month",
    nearest_task_date.strftime("%Y-%m"),
)


def _select_calendar_date(selected_date: date) -> None:
    st.session_state.patient_calendar_date = selected_date.isoformat()
    st.session_state.patient_calendar_month = selected_date.strftime("%Y-%m")


def _shift_calendar_month(month_delta: int) -> None:
    year, month = map(int, st.session_state.patient_calendar_month.split("-"))
    month += month_delta
    if month < 1:
        year, month = year - 1, 12
    elif month > 12:
        year, month = year + 1, 1
    st.session_state.patient_calendar_month = f"{year:04d}-{month:02d}"


def _go_to_today() -> None:
    _select_calendar_date(today)


selected_date = date.fromisoformat(st.session_state.patient_calendar_date)
calendar_year, calendar_month = map(
    int,
    st.session_state.patient_calendar_month.split("-"),
)
tasks_by_date = {
    due_date: [task for task in tasks if task.due_date == due_date]
    for due_date in {task.due_date for task in tasks}
}

summary_columns = st.columns(3)
summary_columns[0].metric("全部安排", len(tasks))
summary_columns[1].metric(
    "待完成",
    sum(
        st.session_state.patient_task_status[task.id] == TaskStatus.PENDING.value
        for task in tasks
    ),
)
summary_columns[2].metric(
    "已完成",
    sum(
        st.session_state.patient_task_status[task.id] == TaskStatus.COMPLETED.value
        for task in tasks
    ),
)

with st.container(border=True, gap="small"):
    month_navigation = st.columns([1.5, 4, 1.5], vertical_alignment="center")
    month_navigation[0].button(
        "上月",
        icon=":material/chevron_left:",
        on_click=_shift_calendar_month,
        args=(-1,),
        width="stretch",
    )
    month_navigation[1].subheader(
        f"{calendar_year} 年 {calendar_month} 月",
        text_alignment="center",
    )
    month_navigation[2].button(
        "下月",
        icon=":material/chevron_right:",
        on_click=_shift_calendar_month,
        args=(1,),
        width="stretch",
    )

    weekday_columns = st.columns(7, gap="small")
    for column, weekday in zip(weekday_columns, "一二三四五六日", strict=True):
        column.caption(f"周{weekday}", text_alignment="center")

    month_grid = calendar.Calendar(firstweekday=0).monthdayscalendar(
        calendar_year,
        calendar_month,
    )
    for week_index, week in enumerate(month_grid):
        day_columns = st.columns(7, gap="small")
        for weekday_index, day_number in enumerate(week):
            if day_number == 0:
                day_columns[weekday_index].write("")
                continue
            day = date(calendar_year, calendar_month, day_number)
            day_tasks = tasks_by_date.get(day, [])
            label = str(day_number)
            if day_tasks:
                label = f"{day_number} · {len(day_tasks)}"
            day_columns[weekday_index].button(
                label,
                key=f"patient_calendar_day_{day.isoformat()}",
                type="primary" if day == selected_date else "secondary",
                help="；".join(task.instructions for task in day_tasks) or "当天暂无任务",
                on_click=_select_calendar_date,
                args=(day,),
                width="stretch",
            )

    st.button(
        "回到今天",
        icon=":material/today:",
        on_click=_go_to_today,
    )

selected_date = date.fromisoformat(st.session_state.patient_calendar_date)
selected_tasks = sorted(tasks_by_date.get(selected_date, []), key=lambda task: task.id)
weekday_name = "一二三四五六日"[selected_date.weekday()]
date_label = f"{selected_date.month} 月 {selected_date.day} 日 · 周{weekday_name}"
if selected_date == today:
    date_label = f"今天 · {date_label}"
st.subheader(date_label)

if not selected_tasks:
    st.info("这一天没有已确认的照护任务。请在日历中选择带任务数量的日期。")

for task in selected_tasks:
    with st.container(border=True):
        if task.due_date < today:
            st.badge("已逾期", color="red", icon=":material/warning:")
        elif task.due_date == today:
            st.badge("今日", color="blue", icon=":material/today:")
        st.markdown(f"**{task.instructions}**")
        if task.frequency:
            st.caption(f"频率：{task.frequency} · 来源事件：{task.source_event_id}")
        task_widget_key = f"patient_task_{task.id}"
        st.session_state.setdefault(
            task_widget_key,
            st.session_state.patient_task_status[task.id],
        )
        status = st.segmented_control(
            "任务状态",
            [status.value for status in TaskStatus],
            key=task_widget_key,
            width="stretch",
        )
        st.session_state.patient_task_status[task.id] = status
