from pathlib import Path
from typing import Optional

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
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    def get_first_city(self) -> Optional[str]:
        df = self.load_data()
        if 'city' in df.columns and not df['city'].dropna().empty:
            return df['city'].dropna().iloc[0]
        return None
