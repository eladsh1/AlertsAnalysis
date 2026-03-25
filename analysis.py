import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

DAY_PART_ORDER = {
    'חצות – 06:00': 0,
    '06:00 – 12:00': 1,
    '12:00 – 18:00': 2,
    '18:00 – חצות': 3,
}

def analyze_time_gap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate average time gap (in minutes) between a pre_alert and the
    following true_alert.

    The result is aggregated by date and by 4 day-part buckets.
    A true_alert with no matching pre_alert in the previous 15 minutes
    is counted as a 0-minute gap.
    """
    df = df.copy()
    required_cols = {'date_part', 'time_between_pre_to_true_alert'}
    if not required_cols.issubset(df.columns):
        return pd.DataFrame()

    true_alerts = df[df['alert_type'] == 'true_alert'].copy()
    if true_alerts.empty:
        return pd.DataFrame()

    combined = true_alerts.rename(
        columns={
            'date_part': 'day_part',
            'time_between_pre_to_true_alert': 'gap_minutes',
        }
    )[['date', 'day_part', 'gap_minutes']].copy()
    combined = combined.dropna(subset=['date', 'day_part'])
    combined['gap_minutes'] = pd.to_numeric(combined['gap_minutes'], errors='coerce').fillna(0.0)

    if combined.empty:
        return pd.DataFrame()

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
    all_parts = sorted(result['day_part'].dropna().unique(), key=lambda p: DAY_PART_ORDER.get(p, 99))
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
    result['_sort'] = result['חלק ביום'].map(DAY_PART_ORDER)
    result = result.sort_values(['תאריך', '_sort'], ascending=[False, True]).drop(columns=['_sort']).reset_index(drop=True)
    return result


def count_true_alerts_without_pre_alert(df: pd.DataFrame, lookback_minutes: int = 15) -> int:
    """
    Count true_alert events that do not have a preceding pre_alert
    in the previous lookback_minutes window (same city).
    """
    df = df.copy()
    if 'is_alert_without_pre_alert' in df.columns:
        return int(
            ((df['alert_type'] == 'true_alert') & (df['is_alert_without_pre_alert'].astype(bool))).sum()
        )

    df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'], errors='coerce')
    df = df.dropna(subset=['datetime'])

    true_alerts = df[df['alert_type'] == 'true_alert'].copy()
    pre_alerts = df[df['alert_type'] == 'pre_alert'].copy()

    if true_alerts.empty:
        return 0

    no_pre_count = 0
    for city in true_alerts['city'].dropna().unique():
        city_true = true_alerts[true_alerts['city'] == city].sort_values('datetime')
        city_pre = pre_alerts[pre_alerts['city'] == city].sort_values('datetime')

        if city_pre.empty:
            no_pre_count += len(city_true)
            continue

        merged = pd.merge_asof(
            city_true[['datetime']].reset_index(drop=True),
            city_pre[['datetime']].reset_index(drop=True).rename(columns={'datetime': 'pre_alert_time'}),
            left_on='datetime',
            right_on='pre_alert_time',
            direction='backward',
            tolerance=pd.Timedelta(minutes=lookback_minutes),
        )
        no_pre_count += int(merged['pre_alert_time'].isna().sum())

    return no_pre_count


def count_true_alerts_without_pre_alert_by_day_part(df: pd.DataFrame, lookback_minutes: int = 15) -> pd.DataFrame:
    """
    Count true_alert events without a preceding pre_alert in the previous
    lookback_minutes window, grouped by day part.
    """
    df = df.copy()
    required_cols = {'date_part', 'is_alert_without_pre_alert'}
    if not required_cols.issubset(df.columns):
        return pd.DataFrame(columns=['חלק ביום', 'כמות אזעקות ללא התראה'])

    true_no_pre = df[
        (df['alert_type'] == 'true_alert')
        & (df['is_alert_without_pre_alert'].astype(bool))
    ].copy()
    grouped = (
        true_no_pre.groupby('date_part', as_index=False)
        .size()
        .rename(columns={'date_part': 'חלק ביום', 'size': 'כמות אזעקות ללא התראה'})
    )

    all_parts = pd.DataFrame({
        'חלק ביום': sorted(df['date_part'].dropna().unique(), key=lambda p: DAY_PART_ORDER.get(p, 99))
    })
    grouped = all_parts.merge(grouped, on='חלק ביום', how='left')
    grouped['כמות אזעקות ללא התראה'] = grouped['כמות אזעקות ללא התראה'].fillna(0).astype(int)
    grouped['_sort'] = grouped['חלק ביום'].map(DAY_PART_ORDER)
    grouped = grouped.sort_values('_sort').drop(columns=['_sort']).reset_index(drop=True)
    return grouped


# %%
def analyze_city_by_date(df, city_name):
    """
    מחשב אחוז המרה מ-pre_alert ל-true_alert עבור עיר מסוימת לפי תאריך
    ומחזיר DataFrame מסודר לפי תאריך עם ספירה ואחוז המרה.
    
    מתעלם מ-true_alert שמגיעה תוך 2 דקות אחרי true_alert בלי pre_alert בינהן.

    פרמטרים:
    - df: DataFrame עם הנתונים (חייב לכלול עמודות 'city', 'alert_type', 'date', 'time')
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
    
    # הוסף עמודת datetime וסדר לפי זמן
    df_city['datetime'] = pd.to_datetime(df_city['date'] + ' ' + df_city['time'], errors='coerce')
    df_city = df_city.dropna(subset=['datetime']).sort_values('datetime')
    
    # סנן true_alerts שמגיעות תוך 2 דקות של true_alert בלי pre_alert בינהן
    true_alerts = df_city[df_city['alert_type'] == 'true_alert'].copy()
    
    if not true_alerts.empty:
        filtered_true_alerts = []
        
        for idx, row in true_alerts.iterrows():
            current_time = row['datetime']
            
            # מצא את ה-true_alert הקודמת
            earlier_true_alerts = true_alerts[true_alerts['datetime'] < current_time]
            previous_true_alert_time = None
            if not earlier_true_alerts.empty:
                previous_true_alert_time = earlier_true_alerts['datetime'].max()
            
            # בדוק אם צריך להתעלם מזו
            should_include = True
            if previous_true_alert_time is not None:
                time_diff = (current_time - previous_true_alert_time).total_seconds() / 60
                
                # אם ההפרש < 2 דקות, בדוק אם יש pre_alert בינהן
                if time_diff < 2:
                    pre_alerts_between = df_city[
                        (df_city['alert_type'] == 'pre_alert') & 
                        (df_city['datetime'] > previous_true_alert_time) & 
                        (df_city['datetime'] <= current_time)
                    ]
                    # אם אין pre_alert בטווח - תעלם ממנה
                    if len(pre_alerts_between) == 0:
                        should_include = False
            
            if should_include:
                filtered_true_alerts.append(row)
        
        # צור DataFrame חדש עם ה-true_alerts המסוננות
        if filtered_true_alerts:
            df_filtered = pd.concat([
                df_city[df_city['alert_type'] != 'true_alert'],
                pd.DataFrame(filtered_true_alerts)
            ])
        else:
            df_filtered = df_city[df_city['alert_type'] != 'true_alert']
    else:
        df_filtered = df_city

    # 3️⃣ ספירה לפי תאריך וסוג התרעה
    counts_by_date = df_filtered.groupby(['date', 'alert_type']).size().unstack(fill_value=0)

    # 4️⃣ לוודא שהעמודות קיימות
    for col in ['pre_alert', 'true_alert']:
        if col not in counts_by_date.columns:
            counts_by_date[col] = 0

    # 5️⃣ חישוב אחוז המרה
    counts_by_date['conversion_rate'] = counts_by_date['true_alert'] / counts_by_date['pre_alert'].replace(0, np.nan)
    counts_by_date['conversion_rate'] = round(counts_by_date['conversion_rate'] * 100,0).apply(lambda x: str(x) + '%')

    # 6️⃣ מיון לפי תאריך
    counts_by_date = counts_by_date.sort_index(ascending=False)

    return counts_by_date


# %%
import streamlit as st

def compute_hourly_avg(source_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute average number of true alerts per hour for a given DataFrame
    (typically filtered to a single city).
    Returns a DataFrame with columns ['hour', 'כמות אזעקות ממוצעת'].
    """
    source = source_df[source_df['alert_type'] == 'true_alert'].copy()
    if 'hour' not in source.columns or source.empty:
        return pd.DataFrame(columns=['hour', 'כמות אזעקות ממוצעת'])

    source['hour'] = pd.to_numeric(source['hour'], errors='coerce')
    source = source.dropna(subset=['hour'])
    if source.empty:
        return pd.DataFrame(columns=['hour', 'כמות אזעקות ממוצעת'])

    source['hour'] = source['hour'].astype(int)
    source = source[(source['hour'] >= 0) & (source['hour'] <= 23)]
    if source.empty:
        return pd.DataFrame(columns=['hour', 'כמות אזעקות ממוצעת'])

    if 'date' in source.columns:
        source['date_only'] = pd.to_datetime(source['date'], errors='coerce').dt.date
        source = source.dropna(subset=['date_only'])
        if not source.empty:
            hourly_counts_by_date = (
                source.groupby(['date_only', 'hour'], as_index=False)
                .size()
                .rename(columns={'size': 'כמות אזעקות'})
            )
            return (
                hourly_counts_by_date.groupby('hour', as_index=False)
                .agg(**{'כמות אזעקות ממוצעת': ('כמות אזעקות', 'mean')})
            )

    return (
        source.groupby('hour', as_index=False)
        .size()
        .rename(columns={'size': 'כמות אזעקות ממוצעת'})
    )


def compute_hourly_avg_mean_of_city_means(source_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a national average: first average per city per hour, then
    average across cities — so that large cities don't dominate.
    Returns a DataFrame with columns ['hour', 'כמות אזעקות ממוצעת'].
    """
    source = source_df[source_df['alert_type'] == 'true_alert'].copy()
    required_cols = {'city', 'hour'}
    if not required_cols.issubset(source.columns) or source.empty:
        return pd.DataFrame(columns=['hour', 'כמות אזעקות ממוצעת'])

    source['hour'] = pd.to_numeric(source['hour'], errors='coerce')
    source = source.dropna(subset=['city', 'hour'])
    if source.empty:
        return pd.DataFrame(columns=['hour', 'כמות אזעקות ממוצעת'])

    source['hour'] = source['hour'].astype(int)
    source = source[(source['hour'] >= 0) & (source['hour'] <= 23)]
    if source.empty:
        return pd.DataFrame(columns=['hour', 'כמות אזעקות ממוצעת'])

    if 'date' in source.columns:
        source['date_only'] = pd.to_datetime(source['date'], errors='coerce').dt.date
        source = source.dropna(subset=['date_only'])
        if not source.empty:
            city_hour_by_date = (
                source.groupby(['city', 'date_only', 'hour'], as_index=False)
                .size()
                .rename(columns={'size': 'כמות אזעקות'})
            )
            city_hour_avg = (
                city_hour_by_date.groupby(['city', 'hour'], as_index=False)
                .agg(**{'ממוצע עירוני לשעה': ('כמות אזעקות', 'mean')})
            )
            return (
                city_hour_avg.groupby('hour', as_index=False)
                .agg(**{'כמות אזעקות ממוצעת': ('ממוצע עירוני לשעה', 'mean')})
            )

    city_hour_counts = (
        source.groupby(['city', 'hour'], as_index=False)
        .size()
        .rename(columns={'size': 'כמות אזעקות'})
    )
    return (
        city_hour_counts.groupby('hour', as_index=False)
        .agg(**{'כמות אזעקות ממוצעת': ('כמות אזעקות', 'mean')})
    )


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
