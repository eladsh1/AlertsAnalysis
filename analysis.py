import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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
    run_streamlit_app(df)

# %%
