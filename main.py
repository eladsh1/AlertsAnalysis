import time
import pandas as pd
import streamlit as st
import altair as alt
from analysis import analyze_city_by_date, get_conversion_chart, analyze_time_gap
from etl import run_data_load_pipeline

PATH = "C:\\Users\\User\\Documents\\repos\\alertsAnalysis\\RawData"
PREFIX = "GetAlarmsHistory_"


def _render_table(df: pd.DataFrame, center_cols: list) -> None:
    headers = ''.join(
        f'<th style="text-align:center; padding:8px 12px; border-bottom:1px solid #4EC9B0; color:#4EC9B0;">{col}</th>'
        for col in df.columns
    )
    rows_html = ''
    for _, row in df.iterrows():
        cells = ''.join(
            f'<td style="text-align:{"center" if col in center_cols else "right"}; padding:6px 12px;">{row[col]}</td>'
            for col in df.columns
        )
        rows_html += f'<tr>{cells}</tr>'
    html = (
        f'<div style="max-height:370px; overflow-y:auto;">'
        f'<table style="width:100%; border-collapse:collapse; direction:rtl; color:#e8e8e8;">'
        f'<thead style="position:sticky; top:0; background-color:#1f1f1f;"><tr>{headers}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def main():
    # RTL alignment for the app
    st.markdown(
        """
        <style>
        body {
            background-color: #181818;
            color: #e8e8e8;
        }

        .block-container {
            direction: rtl;
            text-align: right;
            padding-top: 0.8rem !important;
            background-color: #1f1f1f;
            color: #4EC9B0;
        }

        .stButton>button {
            background-color: #4a4a4a;
            color: #4EC9B0;
            border: 1px solid #666;
        }

        .stTitle {
            text-align: center;
        }

        .stTabs {
            color: #4EC9B0 !important;
        }

        [data-baseweb="tab"] {
            color: #4EC9B0 !important;
        }

        .stDataFrame {
            background-color: #1f1f1f !important;
        }

        [data-testid="stDataFrame"] > div {
            background-color: #1f1f1f !important;
        }

        iframe {
            background-color: #1f1f1f !important;
        }

        [data-baseweb="tab-panel"] {
            background-color: #1f1f1f !important;
        }

        .element-container {
            background-color: #1f1f1f !important;
        }

        section.main > div {
            background-color: #1f1f1f !important;
        }

        [data-baseweb="tab"][aria-selected="true"] {
            border-bottom-color: #4EC9B0 !important;
        }

        [data-baseweb="tab-highlight"] {
            background-color: #4EC9B0 !important;
        }

        .stAlert.stSuccess {
            background-color: rgba(120, 49, 186, 0.18) !important;
            color: white !important;
            border: 1px solid rgba(120, 49, 186, 0.5) !important;
        }

        .stAlert {
            background-color: rgba(0, 123, 255, 0.25) !important;
            color: white !important;
            border-radius: 8px !important;
        }

        .stAlert * {
            color: white !important;
        }

        .stSpinner div {
            color: white !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.set_page_config(page_title='אנליזת אזעקות - שאגת הארי', layout='wide')
    st.sidebar.title('ניווט')
    page = st.sidebar.radio('בחר עמוד', ['טעינת קבצי JSON', 'ניתוח הנתונים'])

    # Force sidebar to right side by CSS transform
    st.markdown(
        """
        <style>
        [data-testid='stSidebar'] {
            float: right !important;
            margin-left: 0px !important;
            margin-right: 0px !important;
            left: auto !important;
            right: 0 !important;
            background-color: rgb(24, 24, 24) !important;
            color: #e8e8e8 !important;
            border-left: none !important;
            border-right: 1px solid rgba(78, 201, 176, 0.5) !important;
        }

        [data-testid='stSidebar'] * {
            color: #4EC9B0 !important;
        }

        [data-testid='stSidebarNav'] {
            direction: rtl;
            text-align: right;
            background-color: rgb(24, 24, 24) !important;
            color: #4EC9B0 !important;
        }

        .stRadio > div {
            background-color: transparent !important;
            color: #4EC9B0 !important;
        }

        .stRadio > label {
            background-color: transparent !important;
        }

        [data-testid='stSidebar'] label {
            background-color: rgb(24, 24, 24) !important;
        }

        [data-testid='stSidebar'] .stRadio {
            background-color: rgb(24, 24, 24) !important;
        }

        [data-testid='stSidebar'] h1 {
            background-color: rgb(24, 24, 24) !important;
        }

        .stRadio label {
            color: #4EC9B0 !important;
        }

        .stRadio [data-testid="stMarkdownContainer"] p {
            color: #4EC9B0 !important;
        }

        .stRadio input[type="radio"]:checked + label {
            color: #4EC9B0 !important;
            font-weight: bold;
        }

        .stRadio div[role="radio"][aria-checked="true"] {
            background-color: #4EC9B0 !important;
            border-color: #4EC9B0 !important;
        }

        [data-baseweb="radio"] [data-checked="true"] div {
            background-color: #4EC9B0 !important;
            border-color: #4EC9B0 !important;
        }

        [data-baseweb="radio"] div:first-child {
            border-color: #4EC9B0 !important;
        }

        input[type="radio"] {
            accent-color: #4EC9B0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if page == 'טעינת קבצי JSON':
        st.markdown("<h2 style='text-align:center; color:#4EC9B0; margin-bottom:2px;'>מערכת עיבוד וניתוח נתוני אזעקות</h2>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:right; color:#a0a0a0; margin-top:0;'>טעינת קבצי JSON</h3>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button('טעינת נתונים'):
                with col2:
                    with st.spinner('טוען נתונים...'):
                        t_start = time.time()
                        df, logs = run_data_load_pipeline(PATH, PREFIX)
                        t_end = time.time()
                st.session_state['df'] = df
                st.session_state['logs'] = logs
                st.session_state['load_duration'] = round(t_end - t_start, 2)

        if 'df' in st.session_state:
            file_count = st.session_state["df"]["file_name"].nunique()
            duration = st.session_state.get('load_duration', '')
            duration_str = f' | זמן הטעינה היה {duration} שניות' if duration != '' else ''
            st.markdown(
                f"""
                <div style="
                    background-color: rgba(120, 49, 186, 0.18);
                    border: 1px solid rgba(120, 49, 186, 0.75);
                    border-radius: 8px;
                    color: white;
                    direction: rtl;
                    text-align: right;
                    padding: 0.9rem 1rem;
                    margin: 0.5rem 0 1rem 0;
                    line-height: 1.6;
                ">
                    <div>{file_count} קבצים נטענו בהצלחה | סה"כ {len(st.session_state["df"])} שורות{duration_str}</div>
                    <div style="margin-top: 0.6rem;">נתיב מקור הנתונים: {PATH}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            loaded_files = set(st.session_state["df"]["file_name"].dropna().unique())
            logs_df = st.session_state['logs'].copy()
            if not logs_df.empty and 'file_name' in logs_df.columns:
                logs_view = logs_df[logs_df['file_name'].isin(loaded_files)].copy()
                if 'loaded_at' in logs_view.columns:
                    logs_view = logs_view.sort_values('loaded_at', ascending=False)
                logs_view = logs_view.drop_duplicates(subset=['file_name'], keep='first')
                preferred_cols = ['file_name', 'rows_loaded', 'load_duration_seconds', 'loaded_at']
                existing_cols = [c for c in preferred_cols if c in logs_view.columns]
                logs_view = logs_view[existing_cols].sort_values('file_name')
                logs_view = logs_view.rename(
                    columns={
                        'file_name': 'שם קובץ',
                        'rows_loaded': 'כמות שורות שנטענו',
                        'load_duration_seconds': 'משך טעינה (שניות)',
                        'loaded_at': 'זמן טעינה',
                    }
                )
            else:
                logs_view = (
                    st.session_state["df"]
                    .groupby('file_name', as_index=False)
                    .size()
                    .rename(columns={'file_name': 'שם קובץ', 'size': 'כמות שורות שנטענו'})
                    .sort_values('שם קובץ')
                )

            tab1, tab2 = st.tabs(["לוג", "הנתונים שנטענו"])
            with tab1:
                st.dataframe(logs_view.sort_index(), use_container_width=True)
            with tab2:
                st.dataframe(st.session_state['df'])
    else:
        _df_loaded = st.session_state.get('df')
        if _df_loaded is None or _df_loaded.empty:
            st.info('צריך לטעון נתונים קודם מעמוד טעינת קבצי JSON')
        else:
            st.markdown("<h2 style='text-align:center; color:#4EC9B0; margin-bottom:2px;'>מערכת עיבוד וניתוח נתוני אזעקות</h2>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align:right; color:#a0a0a0; margin-top:0;'>ניתוח הנתונים</h3>", unsafe_allow_html=True)
            all_cities = sorted(_df_loaded['city'].dropna().unique())
            selected_city_shared = st.selectbox('בחר עיר לניתוח', options=all_cities, key='shared_city_select')

            analysis_tab_1, analysis_tab_2 = st.tabs([
                "פערי זמן",
                "יחס התראות לאזעקות",
            ])

            with analysis_tab_1:
                df_gap = _df_loaded
                df_gap_filtered = df_gap[df_gap['city'] == selected_city_shared]
                result_gap = analyze_time_gap(df_gap_filtered)
                if result_gap.empty:
                    st.warning('לא נמצאו נתונים לניתוח פערי זמן')
                else:
                    st.markdown("<h3 style='text-align:right; color:#4EC9B0; margin-bottom:6px;'>פער ממוצע בין התראה לאזעקה, לפי חלק ביום</h3>", unsafe_allow_html=True)
                    _render_table(result_gap, center_cols=['חלק ביום', 'זמן ממוצע (דקות)'])
                    st.markdown('<div style="margin-top:30px"></div>', unsafe_allow_html=True)
                    chart_base = result_gap.copy()
                    chart_base['gap_num'] = pd.to_numeric(chart_base['זמן ממוצע (דקות)'], errors='coerce').fillna(0.0)
                    chart_base['weighted_gap'] = chart_base['gap_num'] * chart_base['כמות אזעקות']
                    chart_data = (
                        chart_base.groupby('תאריך', as_index=True)
                        .agg(total_weighted_gap=('weighted_gap', 'sum'), total_alerts=('כמות אזעקות', 'sum'))
                    )
                    chart_data['פער ממוצע יומי (דקות)'] = chart_data.apply(
                        lambda r: 0.0 if r['total_alerts'] == 0 else r['total_weighted_gap'] / r['total_alerts'],
                        axis=1,
                    )
                    chart_data = chart_data[['פער ממוצע יומי (דקות)']].sort_index()
                    chart_df = chart_data.reset_index()
                    chart_df.columns = ['תאריך', 'פער ממוצע יומי (דקות)']
                    monthly_avg = chart_df['פער ממוצע יומי (דקות)'].mean()
                    base = alt.Chart(chart_df)
                    bar = (
                        base
                        .mark_bar(color="#7831BA")
                        .encode(
                            x=alt.X('תאריך:O', sort=None, axis=alt.Axis(labelAngle=0, title=None, labelPadding=5)),
                            y=alt.Y('פער ממוצע יומי (דקות):Q', scale=alt.Scale(zero=True)),
                            tooltip=[
                                alt.Tooltip('תאריך:O'),
                                alt.Tooltip('פער ממוצע יומי (דקות):Q', format='.1f'),
                            ],
                        )
                    )
                    avg_line = (
                        alt.Chart(pd.DataFrame({'פער ממוצע חודשי': [monthly_avg]}))
                        .mark_rule(color='red', strokeDash=[6, 3], strokeWidth=2)
                        .encode(
                            y=alt.Y('פער ממוצע חודשי:Q'),
                            tooltip=[alt.Tooltip('פער ממוצע חודשי:Q', format='.1f')],
                        )
                    )
                    st.markdown(
                        '<style>.vega-embed, .vega-embed svg, .vega-embed canvas { overflow: visible !important; }</style>',
                        unsafe_allow_html=True,
                    )
                    st.markdown("<h3 style='text-align:right; color:#4EC9B0; margin-bottom:6px;'>פער יומי ממוצע</h3>", unsafe_allow_html=True)
                    chart = (
                        (bar + avg_line)
                        .properties(width='container', height=300)
                        .configure(padding={'top': 10, 'bottom': 60, 'left': 10, 'right': 10})
                    )
                    st.altair_chart(chart, use_container_width=True)

            with analysis_tab_2:
                df_for_analysis = _df_loaded
                result = analyze_city_by_date(df_for_analysis, selected_city_shared)

                if result.empty:
                    st.warning(f'אין נתונים לעיר {selected_city_shared}')
                else:
                    chart_df = get_conversion_chart(result)
                    result_table = result.reset_index().rename(
                        columns={
                            'date': 'תאריך',
                            'true_alert': 'כמות אזעקות',
                            'pre_alert': 'כמות התראות',
                            'conversion_rate': 'שיעור המרה',
                        }
                    )
                    if 'end_alert' in result_table.columns:
                        result_table = result_table.drop(columns=['end_alert'])
                    st.markdown("<h3 style='text-align:right; color:#4EC9B0; margin-bottom:6px;'>שיעור המרה יומי בין כמות ההתראות לכמות האזעקות</h3>", unsafe_allow_html=True)
                    _render_table(result_table, center_cols=list(result_table.columns))
                    st.markdown('<div style="margin-top:30px"></div>', unsafe_allow_html=True)
                    st.markdown("<h3 style='text-align:right; color:#4EC9B0; margin-bottom:6px;'>שיעור המרה יומי</h3>", unsafe_allow_html=True)
                    conv_df = chart_df[['conversion_rate_float']].reset_index()
                    conv_df.columns = ['תאריך', 'שיעור המרה (%)']
                    conv_avg = conv_df['שיעור המרה (%)'].mean()
                    conv_bar = (
                        alt.Chart(conv_df)
                        .mark_bar(color="#7831BA")
                        .encode(
                            x=alt.X('תאריך:O', sort='ascending', axis=alt.Axis(labelAngle=0, title=None, labelPadding=5)),
                            y=alt.Y('שיעור המרה (%):Q', scale=alt.Scale(zero=True)),
                            tooltip=[
                                alt.Tooltip('תאריך:O'),
                                alt.Tooltip('שיעור המרה (%):Q', format='.1f'),
                            ],
                        )
                    )
                    conv_avg_line = (
                        alt.Chart(pd.DataFrame({'ממוצע חודשי (%)': [conv_avg]}))
                        .mark_rule(color='red', strokeDash=[6, 3], strokeWidth=2)
                        .encode(
                            y=alt.Y('ממוצע חודשי (%):Q'),
                            tooltip=[alt.Tooltip('ממוצע חודשי (%):Q', format='.1f')],
                        )
                    )
                    conv_chart = (
                        (conv_bar + conv_avg_line)
                        .properties(width='container', height=300)
                        .configure(padding={'top': 10, 'bottom': 60, 'left': 10, 'right': 10})
                    )
                    st.altair_chart(conv_chart, use_container_width=True)


if __name__ == '__main__':
    main()


