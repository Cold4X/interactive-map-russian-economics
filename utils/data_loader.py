import pandas as pd
import os
from typing import Dict, List, Optional

class DataLoader:
    def __init__(self):
        self.regions_data = {}
        self.districts_data = {}
        self.available_years = [2000, 2005, 2010, 2015, 2020, 2023]
        self._load_all_data()

    def _load_all_data(self):
        for year in self.available_years:
            try:
                regions_file = f"data/regions_data_{year}.xlsx"
                if os.path.exists(regions_file):
                    self.regions_data[year] = pd.read_excel(regions_file)

                districts_file = f"data/federal_districts_data_{year}.xlsx"
                if os.path.exists(districts_file):
                    self.districts_data[year] = pd.read_excel(districts_file)
            except Exception as e:
                print(f"Ошибка загрузки данных за {year} год: {e}")

    def get_available_indicators(self) -> List[Dict]:
        for year in reversed(self.available_years):
            if year in self.regions_data and not self.regions_data[year].empty:
                return self._extract_indicators_from_data(self.regions_data[year])
        return []

    def _extract_indicators_from_data(self, data: pd.DataFrame) -> List[Dict]:
        if data.empty:
            return []

        indicators = []
        columns = [col for col in data.columns if col != 'region' and col != 'federal_district']

        indicator_mapping = {
            'Население': 'population',
            'Среднемесячная номинальная ЗП': 'salary',
            'Валовой региональный продукт': 'gdp',
            'ВРП на душу населения': 'gdp_per_capita',
            'Добывающая промышленность': 'mining_industry',
            'Обрабатывающая промышленность': 'manufacturing_industry',
            'Сельское хозяйство': 'agriculture',
            'Водоснабжение': 'water_supply',
            'Электроснабжение': 'energy_supply',
            'Суммарный объем': 'total_volume',
            'Сфера услуг': 'services'
        }

        for rus_name in columns:
            eng_name = indicator_mapping.get(rus_name)
            if eng_name is None:
                eng_name = rus_name.lower().replace(' ', '_')

            indicators.append({
                "type": eng_name,
                "label": rus_name,
                "description": rus_name,
                "unit": self._get_unit(rus_name)
            })

        return indicators

    def _get_unit(self, indicator_name: str) -> str:
        units = {
            'Население': 'тыс. чел.',
            'Среднемесячная номинальная ЗП': 'руб.',
            'Валовой региональный продукт': 'млн руб.',
            'ВРП на душу населения': 'тыс. руб.',
            'Добывающая промышленность': 'ед.',
            'Обрабатывающая промышленность': 'ед.',
            'Сельское хозяйство': 'ед.',
            'Водоснабжение': 'ед.',
            'Электроснабжение': 'ед.',
            'Суммарный объем': 'ед.',
            'Сфера услуг': 'ед.'
        }
        return units.get(indicator_name, 'ед.')

    def get_indicator_data(self, indicator_type: str, year: int, is_regions: bool = True) -> Dict[str, float]:
        if year not in self.available_years:
            return {}

        data_source = self.regions_data if is_regions else self.districts_data
        region_col = 'region' if is_regions else 'federal_district'

        if year not in data_source or data_source[year].empty:
            return {}

        reverse_mapping = {
            'population': 'Население',
            'salary': 'Среднемесячная номинальная ЗП',
            'gdp': 'Валовой региональный продукт',
            'gdp_per_capita': 'ВРП на душу населения',
            'mining_industry': 'Добывающая промышленность',
            'manufacturing_industry': 'Обрабатывающая промышленность',
            'agriculture': 'Сельское хозяйство',
            'water_supply': 'Водоснабжение',
            'energy_supply': 'Электроснабжение',
            'services': 'Сфера услуг',
            'total_volume': 'Суммарный объем'
        }

        column_name = reverse_mapping.get(indicator_type, indicator_type)

        if column_name not in data_source[year].columns:
            return {}

        result = {}
        for _, row in data_source[year].iterrows():
            region_name = row[region_col]
            value = row[column_name]

            if self._is_missing_value(value):
                continue

            try:
                if isinstance(value, str):
                    cleaned_value = value.replace(' ', '').replace(',', '.')
                    numeric_value = float(cleaned_value)
                else:
                    numeric_value = float(value)

                result[region_name] = numeric_value
            except (ValueError, TypeError):
                continue

        return result

    def _is_missing_value(self, value) -> bool:
        if value is None or pd.isna(value):
            return True

        if isinstance(value, str):
            cleaned = value.strip()
            if (cleaned == '...' or cleaned == '' or cleaned == '0' or
                cleaned.lower() == 'null' or cleaned.lower() == 'n/a' or
                cleaned.lower() == 'нет данных'):
                return True

        if isinstance(value, (int, float)) and value == 0:
            return False

        return False

    def get_available_years(self) -> List[int]:
        return self.available_years

data_loader = DataLoader()