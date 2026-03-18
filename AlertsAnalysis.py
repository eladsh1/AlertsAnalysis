# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: Python [conda env:base] *
#     language: python
#     name: conda-base-py
# ---

# %%
import re
import pandas as pd
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


# %%
def get_city_name_from_file_name(filename: str) -> str:
    """
    מחזירה את החלק אחרי 'GetAlarmsHistory_' עד "_" או ספרה או סוף הקובץ, בלי הסיומת '.json'
    """
    prefix = "GetAlarmsHistory_"
    # הורדת סיומת אם קיימת
    name_only = filename.rsplit(".json", 1)[0]
    
    if prefix in name_only:
        part = name_only.split(prefix, 1)[1]
        # מוציא עד "_" או עד ספרה
        match = re.match(r'([^\d_]+)', part)
        if match:
            return match.group(1)
    return None  


# %%
# unique_pairs = df[['category', 'category_desc']].drop_duplicates()
# print(unique_pairs)

def get_alert_key(value, alert_dict):
    """
    מקבלת ערך ובודקת לאיזה מפתח במילון הוא שייך
    מחזירה את המפתח כ-string או None אם לא נמצא
    """
    
    if (isinstance(value,str) and value.isdigit() or isinstance(value,int)):
        value_to_check = int(value)
    else:
        return None

    if not isinstance(alert_dict,dict):
        return None
    
    for key, values in alert_dict.items():
        if value_to_check in values:
            return key
    return None


# %%
def load_jsons_from_folder(folder_path: str, prefix: str) -> pd.DataFrame:
    """get folder path and iterate over the files in it 
    and combine all of the JSON files into one pandas DF"""
    
    folder = Path(folder_path)  
    dfs = []

    alert_dict = {
    'pre_alert': [14],
    'true_alert': [1, 2],
    'end_alert': [13]
    }

    for file in folder.iterdir():
        if file.is_file() and file.suffix.lower() == ".json" and file.name.startswith(prefix):
            try:
                df = pd.read_json(file)
                df["file_name"] = file.name
                df['city'] = get_city_name_from_file_name(str(file.name))
                df['alert_type'] = df['category'].apply(lambda x: get_alert_key(x, alert_dict))
                df['hour'] = pd.to_datetime(df['time'], format='%H:%M:%S').dt.hour
                df['date'] = pd.to_datetime(df['alertDate'], errors='coerce').dt.strftime('%Y-%m-%d')
                dfs.append(df)
            except Exception as e:
                print(f"Error in file {file.name}: {e}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# %%
#======================Main ETF ====================================

path = "C:\\Users\\User\\Documents\\repos\\alertsAnalysis\\RawData"
prefix = "GetAlarmsHistory_"

df = load_jsons_from_folder(path, prefix)

df.columns = ['city_zone', 'date', 'time', 'alertDate', 'category', 'category_desc',
       'matrix_id', 'rid', 'NAME_HE', 'NAME_EN', 'NAME_AR', 'NAME_RU',
       'file_name', 'city', 'alert_type', 'hour']

df = df[['city_zone', 'date', 'time', 'alertDate', 'category', 'category_desc',
       'NAME_HE', 'NAME_EN',
       'file_name', 'city', 'alert_type', 'hour']]


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
