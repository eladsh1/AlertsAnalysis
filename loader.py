from pathlib import Path

import pandas as pd
from loader_utils import get_alert_key, get_city_name_from_file_name

__all__ = ['Loader']


class Loader:
    def __init__(self, folder_path: str, prefix: str):
        self.folder_path = Path(folder_path)
        self.prefix = prefix
        self.alert_dict = {
            'pre_alert': [14],
            'true_alert': [1, 2],
            'end_alert': [13]
        }

    @staticmethod
    def _day_part_label(hour: int) -> str:
        if hour < 6:
            return 'חצות – 06:00'
        if hour < 12:
            return '06:00 – 12:00'
        if hour < 18:
            return '12:00 – 18:00'
        return '18:00 – חצות'

    def _add_analysis_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        out = df.copy()
        out['datetime'] = pd.to_datetime(out['date'] + ' ' + out['time'], errors='coerce')

        out['date_part'] = out['hour'].apply(self._day_part_label)
        out['is_not_double_alert'] = False
        out['is_alert_without_pre_alert'] = False
        out['time_between_pre_to_true_alert'] = 0.0

        valid_time = out['datetime'].notna()
        true_mask = (out['alert_type'] == 'true_alert') & valid_time
        pre_mask = (out['alert_type'] == 'pre_alert') & valid_time

        for city in out['city'].dropna().unique():
            city_true = out[true_mask & (out['city'] == city)].sort_values('datetime')
            if city_true.empty:
                continue

            city_pre = out[pre_mask & (out['city'] == city)].sort_values('datetime')

            # Match each true alert with the closest previous true alert in a 2-minute window.
            prev_true = pd.merge_asof(
                city_true[['datetime']].reset_index(),
                city_true[['datetime']].reset_index().rename(columns={'datetime': 'prev_true_time', 'index': 'prev_true_index'}),
                left_on='datetime',
                right_on='prev_true_time',
                direction='backward',
                allow_exact_matches=False,
                tolerance=pd.Timedelta(minutes=2),
            )

            out.loc[prev_true['index'], 'is_not_double_alert'] = prev_true['prev_true_time'].isna().values

            if city_pre.empty:
                out.loc[city_true.index, 'is_alert_without_pre_alert'] = True
                out.loc[city_true.index, 'time_between_pre_to_true_alert'] = 0.0
                continue

            # Match each true alert with the closest previous pre alert in a 15-minute window.
            prev_pre = pd.merge_asof(
                city_true[['datetime']].reset_index(),
                city_pre[['datetime']].reset_index().rename(columns={'datetime': 'prev_pre_time', 'index': 'prev_pre_index'}),
                left_on='datetime',
                right_on='prev_pre_time',
                direction='backward',
                allow_exact_matches=False,
                tolerance=pd.Timedelta(minutes=15),
            )

            no_pre_mask = prev_pre['prev_pre_time'].isna()
            out.loc[prev_pre['index'], 'is_alert_without_pre_alert'] = no_pre_mask.values

            gap_minutes = (
                (prev_pre['datetime'] - prev_pre['prev_pre_time']).dt.total_seconds() / 60
            ).fillna(0.0)
            out.loc[prev_pre['index'], 'time_between_pre_to_true_alert'] = gap_minutes.values

        out['is_not_double_alert'] = out['is_not_double_alert'].astype(bool)
        out['is_alert_without_pre_alert'] = out['is_alert_without_pre_alert'].astype(bool)
        out['time_between_pre_to_true_alert'] = out['time_between_pre_to_true_alert'].round(2)

        return out

    def _load_single_json(self, file_path: Path) -> pd.DataFrame:
        df = pd.read_json(file_path)
        df["file_name"] = file_path.name
        city = get_city_name_from_file_name(file_path.name)
        df['city'] = city
        df['alert_type'] = df['category'].apply(lambda x: get_alert_key(x, self.alert_dict))
        df['hour'] = pd.to_datetime(df['time'], format='%H:%M:%S').dt.hour
        df['date'] = pd.to_datetime(df['alertDate'], errors='coerce').dt.strftime('%Y-%m-%d')
        return df

    def load_data(self) -> pd.DataFrame:
        dfs = []
        for file in self.folder_path.iterdir():
            if file.is_file() and file.suffix.lower() == '.json' and file.name.startswith(self.prefix):
                try:
                    dfs.append(self._load_single_json(file))
                except Exception as e:
                    print(f"Error in file {file.name}: {e}")
        if not dfs:
            return pd.DataFrame()

        base_df = pd.concat(dfs, ignore_index=True)
        return self._add_analysis_columns(base_df)
