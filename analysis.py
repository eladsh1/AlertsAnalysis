import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# %%
_DAY_PART_ORDER = {
    'חצות – 06:00': 0,
    '06:00 – 12:00': 1,
    '12:00 – 18:00': 2,
    '18:00 – חצות': 3,
}


def _day_part_label(hour: int) -> str:
    if hour < 6:
        return 'חצות – 06:00'
    elif hour < 12:
        return '06:00 – 12:00'
    elif hour < 18:
        return '12:00 – 18:00'
    else:
        return '18:00 – חצות'


def analyze_time_gap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate average time gap (in minutes) between a pre_alert and the
    following true_alert.

    The result is aggregated by date and by 4 day-part buckets.
    A true_alert with no matching pre_alert in the previous 15 minutes
    is counted as a 0-minute gap.
    """
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'], errors='coerce')
    df = df.dropna(subset=['datetime'])

    true_alerts = df[df['alert_type'] == 'true_alert'].copy()
    pre_alerts = df[df['alert_type'] == 'pre_alert'].copy()

    if true_alerts.empty:
        return pd.DataFrame()

    rows = []
    for city in true_alerts['city'].dropna().unique():
        city_true = true_alerts[true_alerts['city'] == city].sort_values('datetime')
        city_pre = pre_alerts[pre_alerts['city'] == city].sort_values('datetime')

        if city_pre.empty:
            city_true = city_true.copy()
            city_true['gap_minutes'] = 0.0
            rows.append(city_true[['date', 'hour', 'gap_minutes']])
        else:
            merged = pd.merge_asof(
                city_true[['datetime', 'date', 'hour']].reset_index(drop=True),
                city_pre[['datetime']].reset_index(drop=True).rename(columns={'datetime': 'pre_alert_time'}),
                left_on='datetime',
                right_on='pre_alert_time',
                direction='backward',
                tolerance=pd.Timedelta(minutes=15),
            )
            merged['gap_minutes'] = (
                (merged['datetime'] - merged['pre_alert_time']).dt.total_seconds() / 60
            ).fillna(0.0)
            rows.append(merged[['date', 'hour', 'gap_minutes']])

    combined = pd.concat(rows, ignore_index=True)
    combined['day_part'] = combined['hour'].apply(_day_part_label)

    result = (
        combined.groupby(['date', 'day_part'])
        .agg(
            gap_minutes_avg=('gap_minutes', 'mean'),
            alerts_count=('gap_minutes', 'size'),
        )
        .reset_index()
    )

    # Fill missing date × day_part combinations with "לא היו אזעקות"
    all_dates = result['date'].unique()
    all_parts = list(_DAY_PART_ORDER.keys())
    full_index = pd.MultiIndex.from_product([all_dates, all_parts], names=['date', 'day_part'])
    result = (
        result.set_index(['date', 'day_part'])
        .reindex(full_index)
        .reset_index()
    )
    daily_totals = (
        combined.groupby('date')
        .size()
        .reset_index(name='סה"כ אזעקות ביום')
        .rename(columns={'date': 'תאריך'})
    )

    result.columns = ['תאריך', 'חלק ביום', 'זמן ממוצע (דקות)', 'כמות אזעקות']
    result['זמן ממוצע (דקות)'] = result['זמן ממוצע (דקות)'].apply(
        lambda x: 'לא היו אזעקות' if pd.isna(x) else round(x, 2)
    )
    result['כמות אזעקות'] = result['כמות אזעקות'].fillna(0).astype(int)
    result = result.merge(daily_totals, on='תאריך', how='left')
    result['סה"כ אזעקות ביום'] = result['סה"כ אזעקות ביום'].fillna(0).astype(int)
    result['_sort'] = result['חלק ביום'].map(_DAY_PART_ORDER)
    result = result.sort_values(['תאריך', '_sort'], ascending=[False, True]).drop(columns=['_sort']).reset_index(drop=True)
    return result


# %%
def analyze_city_by_date(df, city_name):
    """
    מחשב אחוז המרה מ-pre_alert ל-true_alert עבור עיר מסוימת לפי תאריך
    ומחזיר DataFrame מסודר לפי תאריך עם ספירה ואחוז המרה.

    פרמטרים:
    - df: DataFrame עם הנתונים (חייב לכלול עמודות 'city', 'alert_type', 'date')
    - city_name: שם העיר לניתוח

    מחזיר:
    - DataFrame עם העמודות:
        'pre_alert', 'true_alert', 'conversion_rate'
      ומסודר לפי תאריך (index = date)
    """
    # 1️⃣ סינון לפי העיר
    df_city = df[df['city'] == city_name].copy()
    if df_city.empty:
        print(f"No data for city: {city_name}")
        return pd.DataFrame()

    # 3️⃣ ספירה לפי תאריך וסוג התרעה
    counts_by_date = df_city.groupby(['date', 'alert_type']).size().unstack(fill_value=0)

    # 4️⃣ לוודא שהעמודות קיימות
    for col in ['pre_alert', 'true_alert']:
        if col not in counts_by_date.columns:
            counts_by_date[col] = 0

    # 5️⃣ חישוב אחוז המרה
    counts_by_date['conversion_rate'] = counts_by_date['true_alert'] / counts_by_date['pre_alert'].replace(0, np.nan)
    counts_by_date['conversion_rate'] = round(counts_by_date['conversion_rate'] * 100,0).apply(lambda x: str(x) + '%')

    # 6️⃣ מיון לפי תאריך
    counts_by_date = counts_by_date.sort_index(ascending=False)

    counts_by_date
    return counts_by_date


# %%
import streamlit as st

def get_conversion_chart(df_city_by_date):
    # df_city_by_date already has pre_alert, true_alert, conversion_rate columns
    # Convert conversion_rate string back to float for charting if needed
    chart_df = df_city_by_date.copy()
    if 'conversion_rate' in chart_df.columns:
        chart_df['conversion_rate_float'] = chart_df['conversion_rate'].str.rstrip('%').replace('', '0').astype(float)
    return chart_df


def run_streamlit_app(df):
    st.set_page_config(page_title='ניתוח התראות', layout='wide')
    st.title('יחס המרה בין התרעות לאזעקות אמת')
    st.markdown('בחר עיר מהרשימה והתראה בסוגי התראה לפי תאריך.')

    cities = sorted(df['city'].dropna().unique())
    selected_city = st.selectbox('בחר עיר (דרופדאון)', options=cities)

    if selected_city:
        result = analyze_city_by_date(df, selected_city)
        if result.empty:
            st.warning(f'אין נתונים לעיר {selected_city}')
            return

        st.subheader(f'יחס המרה לעיר: {selected_city}')
        chart_df = get_conversion_chart(result)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('### טבלה')
            st.dataframe(result)
        with col2:
            st.markdown('### גרף')
            st.line_chart(chart_df['conversion_rate_float'])


if __name__ == '__main__':
    empty_df = pd.DataFrame(columns=['city', 'alert_type', 'date'])
    run_streamlit_app(empty_df)

# %%
