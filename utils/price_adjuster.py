import os
import pandas as pd
from typing import Dict, Optional

class PriceAdjuster:
    def __init__(self):
        self.regions_cpi = None
        self.districts_cpi = None
        self.base_year = 2023
        self._load_cpi_data()

    def _get_data_path(self, filename):
        current_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(current_dir)
        data_path = os.path.join(project_root, "data", filename)
        return data_path

    def _load_cpi_data(self):
        try:
            regions_path = self._get_data_path("regional_cpi.xlsx")
            if os.path.exists(regions_path):
                df = pd.read_excel(regions_path)
                df.set_index('region', inplace=True)
                self.regions_cpi = df / 100

            districts_path = self._get_data_path("federal_cpi.xlsx")
            if os.path.exists(districts_path):
                df = pd.read_excel(districts_path)
                df.set_index('federal_district', inplace=True)
                self.districts_cpi = df / 100
        except Exception as e:
            print(f"Ошибка загрузки данных ИПЦ: {e}")

    def calculate_cumulative_inflation(self, region: str, from_year: int, to_year: int,
                                       is_regions: bool = True) -> float:
        cpi_data = self.regions_cpi if is_regions else self.districts_cpi

        if cpi_data is None:
            return 1.0

        if region not in cpi_data.index:
            return 1.0

        try:
            if from_year not in cpi_data.columns or to_year not in cpi_data.columns:
                return 1.0

            if from_year == to_year:
                return 1.0

            if from_year < to_year:
                cumulative = 1.0
                for year in range(from_year, to_year):
                    cpi = cpi_data.loc[region, year]
                    cumulative *= cpi
            else:
                cumulative = 1.0
                for year in range(to_year, from_year):
                    cpi = cpi_data.loc[region, year]
                    cumulative *= cpi
                cumulative = 1.0 / cumulative

            return cumulative
        except Exception:
            return 1.0

    def adjust_value(self, value: float, region: str, data_year: int, target_year: int,
                     is_regions: bool = True) -> float:
        if value is None or value == 0:
            return value

        inflation_factor = self.calculate_cumulative_inflation(region, data_year, target_year, is_regions)
        adjusted_value = value * inflation_factor

        return adjusted_value

    def get_available_base_years(self) -> list:
        if self.regions_cpi is not None:
            return [int(col) for col in self.regions_cpi.columns]
        return list(range(2000, 2024))

price_adjuster = PriceAdjuster()