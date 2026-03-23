import streamlit as st
from etl import run_data_load_pipeline

PATH = "C:\\Users\\User\\Documents\\repos\\alertsAnalysis\\RawData"
PREFIX = "GetAlarmsHistory_"


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

        [data-baseweb="tab"][aria-selected="true"] {
            border-bottom-color: blue !important;
        }

        [data-baseweb="tab-highlight"] {
            background-color: blue !important;
        }

        .stSuccess {
            background-color: #007bff !important;
            color: white !important;
        }

        .stAlert {
            background-color: rgba(0, 123, 255, 0.25) !important;
            color: white !important;
            border-radius: 8px !important;
        }

        .stAlert * {
            color: white !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.set_page_config(layout='wide')
    st.sidebar.title('ניווט')
    page = st.sidebar.radio('בחר עמוד', ['טעינת קבצי JSON', 'אנליזות'])

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
            background-color: #2d2d2d !important;
            color: #e8e8e8 !important;
        }

        [data-testid='stSidebar'] * {
            color: #4EC9B0 !important;
        }

        [data-testid='stSidebarNav'] {
            direction: rtl;
            text-align: right;
            background-color: #2d2d2d !important;
            color: #4EC9B0 !important;
        }

        .stRadio > div {
            background-color: #2d2d2d !important;
            color: #4EC9B0 !important;
        }

        .stRadio label {
            color: #4EC9B0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if page == 'טעינת קבצי JSON':
        st.title('טעינת קבצי JSON')
        loading = st.session_state.get('loading', False)
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button('טעינת נתונים'):
                st.session_state.loading = True
                st.rerun()
        with col2:
            if loading:
                st.markdown("<span style='color: white;'>טוען נתונים...</span>", unsafe_allow_html=True)
                st.spinner('')
        if loading:
            df, logs = run_data_load_pipeline(PATH, PREFIX)
            st.session_state.loading = False
            st.success(f'טעינת הנתונים הושלמה - {len(df)} שורות')
            tab1, tab2 = st.tabs(["לוגים", "הנתונים"])
            with tab1:
                st.dataframe(logs)
            with tab2:
                st.dataframe(df)
    else:
        st.title('ניתוח הנתונים')
        st.write('עמוד ניתוחים ריק בינתיים')


if __name__ == '__main__':
    main()


