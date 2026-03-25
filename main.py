import time
import pandas as pd
import streamlit as st
import altair as alt
try:
    import plotly.graph_objects as go
except ImportError:
    go = None
from analysis import analyze_city_by_date, get_conversion_chart, analyze_time_gap, count_true_alerts_without_pre_alert
from analysis import count_true_alerts_without_pre_alert_by_day_part
from analysis import DAY_PART_ORDER
from analysis import compute_hourly_avg, compute_hourly_avg_mean_of_city_means
from etl import run_data_load_pipeline

PATH = "C:\\Users\\User\\Documents\\repos\\alertsAnalysis\\RawData"
PREFIX = "GetAlarmsHistory_"


def _render_table(
    df: pd.DataFrame,
    center_cols: list,
    highlight_column: str = None,
    highlight_threshold: float = None,
    highlight_color: str = None,
    extreme_color_rules: dict = None,
    no_color_column: str = None,
    no_color_value: str = None,
    row_color_column: str = None,
    row_color_value: str = None,
    row_color: str = None,
    container_extra_style: str = '',
    column_style_overrides: dict = None,
) -> None:
    column_style_overrides = column_style_overrides or {}
    headers = ''.join(
        f'<th style="text-align:center; padding:8px 12px; border-bottom:1px solid #4EC9B0; color:#4EC9B0; {column_style_overrides.get(col, "")}">{col}</th>'
        for col in df.columns
    )
    rows_html = ''

    numeric_extremes = {}
    if extreme_color_rules:
        df_for_extremes = df
        if no_color_column is not None and no_color_column in df.columns:
            df_for_extremes = df[df[no_color_column].astype(str) != str(no_color_value)]

        for col in extreme_color_rules.keys():
            if col not in df_for_extremes.columns:
                continue
            numeric_vals = pd.to_numeric(df_for_extremes[col], errors='coerce').dropna()
            if numeric_vals.empty:
                continue
            numeric_extremes[col] = (numeric_vals.min(), numeric_vals.max())

    for _, row in df.iterrows():
        cells = ''
        skip_row_coloring = (
            no_color_column is not None
            and no_color_column in df.columns
            and str(row[no_color_column]) == str(no_color_value)
        )
        force_row_color = (
            row_color_column is not None
            and row_color_column in df.columns
            and str(row[row_color_column]) == str(row_color_value)
            and row_color is not None
        )
        for col in df.columns:
            cell_style = f'text-align:{"center" if col in center_cols else "right"}; padding:6px 12px; {column_style_overrides.get(col, "")}'
            if force_row_color:
                cell_style += f'color: {row_color}; font-weight: 600;'
            
            # בדוק אם צריך להצביע את התא הזה
            if (not skip_row_coloring) and highlight_column and col == highlight_column and highlight_threshold is not None and highlight_color is not None:
                value = row[col]
                # הסר את ה-% אם קיים
                if isinstance(value, str):
                    try:
                        value = float(value.replace('%', '').strip())
                    except ValueError:
                        value = None
                else:
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        value = None
                
                if value is not None and value < highlight_threshold:
                    cell_style += f'color: {highlight_color};'

            if (not skip_row_coloring) and extreme_color_rules and col in numeric_extremes:
                rule = extreme_color_rules.get(col, {})
                value_num = pd.to_numeric(pd.Series([row[col]]), errors='coerce').iloc[0]
                if pd.notna(value_num):
                    min_val, max_val = numeric_extremes[col]
                    if value_num == min_val and 'min' in rule:
                        cell_style += f'color: {rule["min"]};'
                    if value_num == max_val and 'max' in rule:
                        cell_style += f'color: {rule["max"]};'
            
            cells += f'<td style="{cell_style}">{row[col]}</td>'
        rows_html += f'<tr>{cells}</tr>'
    html = (
        f'<div style="max-height:370px; overflow-y:auto; {container_extra_style}">'
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
        @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap');

        body {
            background-color: #181818;
            color: #e8e8e8;
            font-family: 'Open Sans', sans-serif !important;
        }

        .stApp, .block-container, .stMarkdown, .stSelectbox, .stButton, .stTabs, .stDataFrame, .stAlert {
            font-family: 'Open Sans', sans-serif !important;
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

        h3 {
            color: #ffffff !important;
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

        .vega-tooltip table {
            width: 100%;
        }

        .vega-tooltip {
            direction: rtl;
            text-align: right;
            transform: translate(72px, 12px) !important;
        }

        .vega-tooltip td:first-child {
            text-align: right;
            padding-right: 10px;
            font-weight: bold;
        }

        .vega-tooltip td:last-child {
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.set_page_config(page_title='אנליזת אזעקות - שאגת הארי', layout='wide')
    st.sidebar.title('ניווט')
    page = st.sidebar.radio('בחר עמוד', ['טעינת קבצי JSON', 'ניתוח הנתונים'], label_visibility='collapsed')

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
            color: #ffffff !important;
        }

        .stRadio label {
            color: #ffffff !important;
        }

        .stRadio [data-testid="stMarkdownContainer"] p {
            color: #ffffff !important;
        }

        .stRadio input[type="radio"]:checked + label {
            color: #ffffff !important;
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

        [data-testid='stSidebar'] [data-baseweb="select"] > div:first-child {
            border-color: #4EC9B0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if page == 'טעינת קבצי JSON':
        st.markdown("<h2 style='text-align:center; color:#ffffff; margin-bottom:2px;'>מערכת עיבוד וניתוח נתוני אזעקות</h2>", unsafe_allow_html=True)
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
            st.markdown("<h2 style='text-align:center; color:#ffffff; margin-bottom:2px;'>מערכת עיבוד וניתוח נתוני אזעקות</h2>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align:right; color:#a0a0a0; margin-top:0;'>ניתוח הנתונים</h3>", unsafe_allow_html=True)
            all_cities = sorted(_df_loaded['city'].dropna().unique())
            selected_city_shared = st.sidebar.selectbox('בחר עיר לניתוח', options=all_cities, key='shared_city_select')

            analysis_tab_hourly, analysis_tab_1, analysis_tab_2 = st.tabs([
                "כמות אזעקות",
                "פערי זמן",
                "יחס התראות לאזעקות",
            ])

            with analysis_tab_hourly:
                df_hourly = _df_loaded[_df_loaded['city'] == selected_city_shared].copy()
                if 'is_not_double_alert' in df_hourly.columns:
                    hourly_double_alert_mask = (
                        (df_hourly['alert_type'] == 'true_alert')
                        & (~df_hourly['is_not_double_alert'].fillna(False).astype(bool))
                    )
                    df_hourly = df_hourly[~hourly_double_alert_mask].copy()

                df_hourly_all = _df_loaded.copy()
                if 'is_not_double_alert' in df_hourly_all.columns:
                    hourly_double_alert_mask_all = (
                        (df_hourly_all['alert_type'] == 'true_alert')
                        & (~df_hourly_all['is_not_double_alert'].fillna(False).astype(bool))
                    )
                    df_hourly_all = df_hourly_all[~hourly_double_alert_mask_all].copy()

                def _compute_hourly_avg(source_df: pd.DataFrame) -> pd.DataFrame:
                    return compute_hourly_avg(source_df)

                def _compute_hourly_avg_mean_of_city_means(source_df: pd.DataFrame) -> pd.DataFrame:
                    return compute_hourly_avg_mean_of_city_means(source_df)

                hourly_avg_city = _compute_hourly_avg(df_hourly)
                hourly_avg_all = _compute_hourly_avg_mean_of_city_means(df_hourly_all)

                if hourly_avg_city.empty and hourly_avg_all.empty:
                    st.warning('לא נמצאו נתונים להצגת כמות אזעקות ממוצעת לפי שעה')
                else:
                    all_hours = pd.DataFrame({'hour': list(range(24))})
                    hourly_avg_city = all_hours.merge(hourly_avg_city, on='hour', how='left')
                    hourly_avg_city['כמות אזעקות ממוצעת'] = hourly_avg_city['כמות אזעקות ממוצעת'].fillna(0.0)

                    hourly_avg_all = all_hours.merge(hourly_avg_all, on='hour', how='left')
                    hourly_avg_all['כמות אזעקות ממוצעת'] = hourly_avg_all['כמות אזעקות ממוצעת'].fillna(0.0)

                    hourly_compare = all_hours.copy()
                    hourly_compare['עיר נבחרת'] = hourly_avg_city['כמות אזעקות ממוצעת']
                    hourly_compare['כל הארץ'] = hourly_avg_all['כמות אזעקות ממוצעת']
                    hourly_compare_long = hourly_compare.melt(
                        id_vars='hour',
                        value_vars=['עיר נבחרת', 'כל הארץ'],
                        var_name='קבוצה',
                        value_name='כמות אזעקות ממוצעת',
                    )

                    st.markdown("<h3 style='text-align:right; color:#4EC9B0; margin-bottom:6px;'>כמות אזעקות ממוצעת, חלוקה לשעות</h3>", unsafe_allow_html=True)

                    hour_base = alt.Chart(hourly_compare_long)
                    hour_bar = (
                        hour_base
                        .mark_bar()
                        .encode(
                            x=alt.X('hour:O', sort=list(range(24)), axis=alt.Axis(title='שעה', labelAngle=0, labelPadding=5)),
                            xOffset=alt.XOffset('קבוצה:N'),
                            y=alt.Y('כמות אזעקות ממוצעת:Q', axis=alt.Axis(title='כמות אזעקות ממוצעת')),
                            color=alt.Color(
                                'קבוצה:N',
                                scale=alt.Scale(domain=['עיר נבחרת', 'כל הארץ'], range=['#7831BA', '#FFA500']),
                                legend=alt.Legend(title=None, orient='bottom', direction='horizontal', columns=2, offset=0, padding=0),
                            ),
                            tooltip=[
                                alt.Tooltip('hour:O', title='שעה'),
                                alt.Tooltip('קבוצה:N', title=''),
                                alt.Tooltip('כמות אזעקות ממוצעת:Q', title='ממוצע', format='.2f'),
                            ],
                        )
                    )
                    hourly_chart = (
                        hour_bar
                        .properties(width='container', height=300)
                        .configure(padding={'top': 10, 'bottom': 0, 'left': 10, 'right': 10})
                    )
                    st.altair_chart(hourly_chart, use_container_width=True)
                    st.markdown(
                        "<div style='text-align:right; color:#a0a0a0; font-size:12px; margin-top:6px;'>* בנטרול אזעקות שהתרחשו בסמיכות מיידית לאזעקה אחרת</div>",
                        unsafe_allow_html=True,
                    )

            with analysis_tab_1:
                df_gap = _df_loaded
                df_gap_filtered = df_gap[df_gap['city'] == selected_city_shared]
                df_gap_effective = df_gap_filtered.copy()
                if 'is_not_double_alert' in df_gap_effective.columns:
                    double_alert_mask = (
                        (df_gap_effective['alert_type'] == 'true_alert')
                        & (~df_gap_effective['is_not_double_alert'].fillna(False).astype(bool))
                    )
                    df_gap_effective = df_gap_effective[~double_alert_mask].copy()

                result_gap = analyze_time_gap(df_gap_effective)
                if result_gap.empty:
                    st.warning('לא נמצאו נתונים לניתוח פערי זמן')
                else:
                    overall_parts = result_gap.copy()
                    overall_parts['gap_num'] = pd.to_numeric(overall_parts['זמן ממוצע (דקות)'], errors='coerce').fillna(0.0)
                    overall_parts['weighted_gap'] = overall_parts['gap_num'] * overall_parts['כמות אזעקות']
                    overall_parts = (
                        overall_parts.groupby('חלק ביום', as_index=False)
                        .agg(total_weighted_gap=('weighted_gap', 'sum'), כמות_אזעקות=('כמות אזעקות', 'sum'))
                    )
                    overall_parts['זמן ממוצע (דקות)'] = overall_parts.apply(
                        lambda r: 'לא היו אזעקות' if r['כמות_אזעקות'] == 0 else round(r['total_weighted_gap'] / r['כמות_אזעקות'], 1),
                        axis=1,
                    )
                    overall_parts['_sort'] = overall_parts['חלק ביום'].map(DAY_PART_ORDER)
                    total_alerts = int(overall_parts['כמות_אזעקות'].sum())
                    total_weighted_gap = overall_parts['total_weighted_gap'].sum()
                    total_avg_gap = 'לא היו אזעקות' if total_alerts == 0 else round(total_weighted_gap / total_alerts, 1)
                    no_pre_by_part = count_true_alerts_without_pre_alert_by_day_part(df_gap_effective)
                    avg_without_no_pre_by_part = pd.DataFrame(columns=['חלק ביום', 'זמן ממוצע, בנטרול אזעקות בלי התראה'])
                    total_avg_without_no_pre = 'לא היו אזעקות'

                    required_no_pre_cols = {
                        'alert_type',
                        'date_part',
                        'is_alert_without_pre_alert',
                        'time_between_pre_to_true_alert',
                    }
                    if required_no_pre_cols.issubset(df_gap_effective.columns):
                        true_with_pre = df_gap_effective[
                            (df_gap_effective['alert_type'] == 'true_alert')
                            & (~df_gap_effective['is_alert_without_pre_alert'].fillna(False).astype(bool))
                        ].copy()
                        true_with_pre['time_between_pre_to_true_alert'] = pd.to_numeric(
                            true_with_pre['time_between_pre_to_true_alert'], errors='coerce'
                        )
                        true_with_pre = true_with_pre.dropna(subset=['date_part', 'time_between_pre_to_true_alert'])

                        avg_without_no_pre_by_part = (
                            true_with_pre.groupby('date_part', as_index=False)
                            .agg(avg_gap_without_no_pre=('time_between_pre_to_true_alert', 'mean'))
                            .rename(columns={'date_part': 'חלק ביום'})
                        )
                        avg_without_no_pre_by_part['זמן ממוצע, בנטרול אזעקות בלי התראה'] = (
                            avg_without_no_pre_by_part['avg_gap_without_no_pre'].round(1)
                        )
                        avg_without_no_pre_by_part = avg_without_no_pre_by_part[
                            ['חלק ביום', 'זמן ממוצע, בנטרול אזעקות בלי התראה']
                        ]
                        if not true_with_pre.empty:
                            total_avg_without_no_pre = round(true_with_pre['time_between_pre_to_true_alert'].mean(), 1)

                    overall_parts = (
                        overall_parts.sort_values('_sort')
                        .drop(columns=['_sort', 'total_weighted_gap'])
                        .rename(columns={'כמות_אזעקות': 'כמות אזעקות'})
                        [['חלק ביום', 'זמן ממוצע (דקות)', 'כמות אזעקות']]
                    )
                    overall_parts = overall_parts.merge(no_pre_by_part, on='חלק ביום', how='left')
                    overall_parts['כמות אזעקות ללא התראה'] = overall_parts['כמות אזעקות ללא התראה'].fillna(0).astype(int)
                    overall_parts = overall_parts.merge(avg_without_no_pre_by_part, on='חלק ביום', how='left')
                    overall_parts['זמן ממוצע, בנטרול אזעקות בלי התראה'] = overall_parts[
                        'זמן ממוצע, בנטרול אזעקות בלי התראה'
                    ].apply(lambda x: 'לא היו אזעקות' if pd.isna(x) else round(float(x), 1))
                    total_row = pd.DataFrame([
                        {
                            'חלק ביום': 'סה"כ',
                            'זמן ממוצע (דקות)': total_avg_gap,
                            'כמות אזעקות': total_alerts,
                            'כמות אזעקות ללא התראה': int(overall_parts['כמות אזעקות ללא התראה'].sum()),
                            'זמן ממוצע, בנטרול אזעקות בלי התראה': total_avg_without_no_pre,
                        }
                    ])
                    overall_parts = pd.concat([overall_parts, total_row], ignore_index=True)
                    overall_parts = overall_parts[
                        [
                            'חלק ביום',
                            'זמן ממוצע (דקות)',
                            'זמן ממוצע, בנטרול אזעקות בלי התראה',
                            'כמות אזעקות',
                            'כמות אזעקות ללא התראה',
                        ]
                    ]
                    no_pre_count = count_true_alerts_without_pre_alert(df_gap_effective)
                    total_true_alerts = int((df_gap_effective['alert_type'] == 'true_alert').sum())
                    no_pre_pct = (no_pre_count / total_true_alerts * 100) if total_true_alerts > 0 else 0.0

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
                        .mark_rule(color='#FF69B4', strokeDash=[6, 3], strokeWidth=2)
                        .encode(
                            y=alt.Y('פער ממוצע חודשי:Q'),
                            tooltip=[alt.Tooltip('פער ממוצע חודשי:Q', format='.1f')],
                        )
                    )
                    st.markdown(
                        '<style>.vega-embed, .vega-embed svg, .vega-embed canvas { overflow: visible !important; }</style>',
                        unsafe_allow_html=True,
                    )
                    st.markdown("<h3 style='text-align:right; color:#4EC9B0; margin-bottom:6px;'>פער ממוצע בין התראה לאזעקה (דקות)</h3>", unsafe_allow_html=True)
                    chart = (
                        (bar + avg_line)
                        .properties(width='container', height=300)
                        .configure(padding={'top': 10, 'bottom': 60, 'left': 10, 'right': 10})
                    )
                    st.altair_chart(chart, use_container_width=True)
                    st.markdown(
                        "<div style='text-align:right; color:#a0a0a0; font-size:12px; margin-top:6px;'>* בנטרול אזעקות שהתרחשו בסמיכות מיידית לאזעקה אחרת</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown('<div style="margin-top:20px"></div>', unsafe_allow_html=True)

                    st.markdown("<h3 style='text-align:right; color:#4EC9B0; margin-bottom:6px;'>פער ממוצע בין התראה לאזעקה, לפי חלק ביום</h3>", unsafe_allow_html=True)
                    table_col, gauge_col = st.columns([3, 1])

                    with table_col:
                        _render_table(
                            overall_parts,
                            center_cols=['חלק ביום', 'זמן ממוצע (דקות)', 'זמן ממוצע, בנטרול אזעקות בלי התראה', 'כמות אזעקות', 'כמות אזעקות ללא התראה'],
                            column_style_overrides={
                                'חלק ביום': 'width: 15%; min-width: 150px;',
                                'זמן ממוצע (דקות)': 'width: 13%; min-width: 110px;',
                                'זמן ממוצע, בנטרול אזעקות בלי התראה': 'width: 20%; min-width: 130px;',
                                'כמות אזעקות ללא התראה': 'width: 20%; min-width: 90px;',
                            },
                            extreme_color_rules={
                                'זמן ממוצע (דקות)': {'min': '#8B0000', 'max': '#008000'},
                                'זמן ממוצע, בנטרול אזעקות בלי התראה': {'min': '#8B0000', 'max': '#008000'},
                                'כמות אזעקות': {'min': '#008000', 'max': '#8B0000'},
                                'כמות אזעקות ללא התראה': {'max': '#8B0000'},
                            },
                            no_color_column='חלק ביום',
                            no_color_value='סה"כ',
                            row_color_column='חלק ביום',
                            row_color_value='סה"כ',
                            row_color='#4EC9B0',
                            container_extra_style='border-left:2px solid #4EC9B0; padding-left:16px;',
                        )

                    with gauge_col:
                        st.markdown("<div style='text-align:center; color:#4EC9B0; font-weight:600; margin-bottom:6px;'>שיעור אזעקות ללא התראה מקדימה</div>", unsafe_allow_html=True)
                        if go is not None:
                            gauge_fig = go.Figure(
                                go.Indicator(
                                    mode='gauge+number',
                                    value=no_pre_pct,
                                    number={'suffix': '%', 'font': {'color': '#4EC9B0', 'size': 34}, 'valueformat': '.1f'},
                                    gauge={
                                        'axis': {'range': [0, 100], 'tickcolor': '#4EC9B0'},
                                        'bar': {'color': '#4EC9B0'},
                                        'bgcolor': '#2A2A2A',
                                        'bordercolor': '#4EC9B0',
                                        'steps': [
                                            {'range': [0, 50], 'color': '#1f1f1f'},
                                            {'range': [50, 100], 'color': '#3A1A1A'},
                                        ],
                                    },
                                )
                            )
                            gauge_fig.update_layout(
                                margin=dict(l=10, r=10, t=10, b=10),
                                paper_bgcolor='#1f1f1f',
                                plot_bgcolor='#1f1f1f',
                                height=290,
                                font={'color': '#4EC9B0'},
                            )
                            st.plotly_chart(gauge_fig, use_container_width=True, config={'displayModeBar': False})
                        else:
                            st.markdown(
                                f"<div style='text-align:center; color:#4EC9B0; font-size:28px; font-weight:700; margin-top:50px;'>{no_pre_pct:.1f}%</div>",
                                unsafe_allow_html=True,
                            )
                        st.markdown(
                            f"<div style='text-align:center; color:#a0a0a0; margin-top:2px; font-size:13px;'>"
                            f"{no_pre_count} מתוך {total_true_alerts} אזעקות אמת"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    st.markdown(
                        "<div style='text-align:right; color:#a0a0a0; font-size:12px; margin-top:6px;'>* בנטרול אזעקות שהתרחשו בסמיכות מיידית לאזעקה אחרת</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown('<div style="margin-top:20px"></div>', unsafe_allow_html=True)

                    result_gap_display = result_gap.copy()
                    result_gap_display['זמן ממוצע (דקות)'] = result_gap_display['זמן ממוצע (דקות)'].apply(
                        lambda x: x if isinstance(x, str) else round(float(x), 1)
                    )

                    st.markdown("<h3 style='text-align:right; color:#4EC9B0; margin-bottom:6px;'>פער ממוצע בין התראה לאזעקה, לפי חלק ביום, לפי תאריך</h3>", unsafe_allow_html=True)
                    _render_table(result_gap_display, center_cols=['חלק ביום', 'זמן ממוצע (דקות)'], highlight_column='זמן ממוצע (דקות)', highlight_threshold=5, highlight_color='#8B0000')
                    st.markdown(
                        "<div style='text-align:right; color:#a0a0a0; font-size:12px; margin-top:6px;'>* בנטרול אזעקות שהתרחשו בסמיכות מיידית לאזעקה אחרת</div>",
                        unsafe_allow_html=True,
                    )

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
                        .mark_rule(color='#FF69B4', strokeDash=[6, 3], strokeWidth=2)
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
                    st.markdown('<div style="margin-top:30px"></div>', unsafe_allow_html=True)
                    _render_table(result_table, center_cols=list(result_table.columns), highlight_column='שיעור המרה', highlight_threshold=50, highlight_color='#8B0000')


if __name__ == '__main__':
    main()


