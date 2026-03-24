import sqlite3
import time
from pathlib import Path
from loader import Loader
import pandas as pd


DB_PATH = Path('alerts_analysis.db')


def _ensure_db_schema(conn: sqlite3.Connection):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS load_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            rows_loaded INTEGER NOT NULL,
            load_duration_seconds REAL NOT NULL,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS alerts_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_zone TEXT,
            date TEXT,
            time TEXT,
            alertDate TEXT,
            category INTEGER,
            category_desc TEXT,
            NAME_HE TEXT,
            NAME_EN TEXT,
            NAME_AR TEXT,
            NAME_RU TEXT,
            file_name TEXT,
            city TEXT,
            alert_type TEXT,
            hour INTEGER,
            date_part TEXT,
            is_not_double_alert BOOLEAN,
            is_alert_without_pre_alert BOOLEAN,
            time_between_pre_to_true_alert REAL
        )
    ''')

    # Backward-compatible migration for existing DBs.
    existing_cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(alerts_data)").fetchall()
    }
    required_new_cols = {
        'date_part': 'TEXT',
        'is_not_double_alert': 'BOOLEAN',
        'is_alert_without_pre_alert': 'BOOLEAN',
        'time_between_pre_to_true_alert': 'REAL',
    }
    for col, col_type in required_new_cols.items():
        if col not in existing_cols:
            conn.execute(f'ALTER TABLE alerts_data ADD COLUMN {col} {col_type}')

    conn.commit()


def _save_load_log(conn: sqlite3.Connection, file_name: str, rows_loaded: int, load_seconds: float):
    conn.execute('''
        INSERT INTO load_logs (file_name, rows_loaded, load_duration_seconds)
        VALUES (?, ?, ?)
    ''', (file_name, rows_loaded, load_seconds))
    conn.commit()


def _save_data_to_sqlite(conn: sqlite3.Connection, df: pd.DataFrame):
    # Using pandas to_sql for simplicity
    df.to_sql('alerts_data', conn, if_exists='append', index=False)


def load_and_prepare_data(folder_path: str, prefix: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    """
    Loads JSON alert files using Loader, logs per-file metadata to sqlite, 
    saves final data to sqlite and returns DataFrame.
    """
    loader = Loader(folder_path, prefix)
    df = loader.load_data()

    expected_columns = ['city_zone', 'date', 'time', 'alertDate', 'category', 'category_desc',
       'matrix_id', 'rid', 'NAME_HE', 'NAME_EN', 'NAME_AR', 'NAME_RU',
         'file_name', 'city', 'alert_type', 'hour', 'date_part',
         'is_not_double_alert', 'is_alert_without_pre_alert', 'time_between_pre_to_true_alert']

    if set(expected_columns).issubset(df.columns):
        df = df[expected_columns]
    else:
        # Keep only available columns from expected list in order
        available = [c for c in expected_columns if c in df.columns]
        df = df[available]

    selected_cols = ['city_zone', 'date', 'time', 'alertDate', 'category', 'category_desc',
         'NAME_HE', 'NAME_EN', 'file_name', 'city', 'alert_type', 'hour', 'date_part',
         'is_not_double_alert', 'is_alert_without_pre_alert', 'time_between_pre_to_true_alert']
    selected_cols = [c for c in selected_cols if c in df.columns]
    final_df = df[selected_cols]

    with sqlite3.connect(db_path) as conn:
        _ensure_db_schema(conn)

        # write all rows to sqlite data table
        _save_data_to_sqlite(conn, final_df)

        # log per-file load data by directly walking raw files to count rows
        folder = Path(folder_path)
        for file in folder.iterdir():
            if file.is_file() and file.suffix.lower() == '.json' and file.name.startswith(prefix):
                start = time.time()
                tmp = pd.read_json(file)
                duration = time.time() - start
                _save_load_log(conn, file.name, len(tmp), duration)

    return final_df


def get_load_logs(db_path: Path = DB_PATH) -> pd.DataFrame:
    """Fetch load logs from sqlite database."""
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query('SELECT * FROM load_logs ORDER BY loaded_at DESC', conn)


from typing import Callable, Optional


def run_data_load_pipeline(folder_path: str, prefix: str, db_path: Path = DB_PATH, progress_callback: Optional[Callable[[int], None]] = None) -> pd.DataFrame:
    """Run ETL load pipeline and return loaded DataFrame and logs."""
    if progress_callback:
        progress_callback(10)

    df = load_and_prepare_data(folder_path, prefix, db_path)

    if progress_callback:
        progress_callback(70)

    logs = get_load_logs(db_path)

    if progress_callback:
        progress_callback(100)

    return df, logs
