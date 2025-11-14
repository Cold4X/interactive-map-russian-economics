import json
import os
from typing import Dict, List, Optional, Union

# Кэш для геометрии
_geojson_cache = {}
_data_loader = None

# Уровни детализации (упрощено до 2 вариантов)
DETAIL_LEVELS = {
    "high": {"label": "Высокий", "value": 1.0},
    "low": {"label": "Низкий", "value": 0.7}
}

# Структура кейсов
CASES = {
    "eco": {
        "name": "Экономические показатели",
        "description": "Анализ среднедушевых доходов, ВРП и ВРП на душу населения с поправкой на инфляцию",
        "allowed_indicators": ["salary", "gdp", "gdp_per_capita"],
    },
    "population": {
        "name": "Динамика населения",
        "description": "Анализ изменения численности населения по регионам",
        "allowed_indicators": ["population"],
    },
    "production": {
        "name": "Структура производства",
        "description": "Изменение структуры промышленности по регионам",
        "allowed_indicators": ["mining_industry", "manufacturing_industry", "agriculture",
                               "services", "total_volume", "dominant_sector"],
    }
}

DEFAULT_CASE = "eco"

# Базовые стили
REGIONS_STYLE = dict(
    weight=2,
    opacity=1,
    color="darkblue",
    dashArray="3",
    fillOpacity=0.4,
    fillColor="lightblue"
)

# Стили карт
MAP_STYLES = {
    "minimal": {
        "name": "Минималистичная",
        "url": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "attribution": "© CARTO"
    },
    "osm": {
        "name": "OpenStreetMap",
        "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap contributors"
    },
    "dark": {
        "name": "Темная",
        "url": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        "attribution": "© CARTO"
    }
}


def set_data_loader(loader):
    global _data_loader
    _data_loader = loader


def get_available_years():
    if _data_loader:
        return _data_loader.get_available_years()
    return [2000, 2005, 2010, 2015, 2020, 2023]


def get_default_year():
    years = get_available_years()
    return 2023 if 2023 in years else years[-1] if years else 2023


def _get_data_loader():
    global _data_loader
    if _data_loader is None:
        try:
            from utils.data_loader import data_loader as dl
            _data_loader = dl
        except ImportError:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from data_loader import data_loader as dl
            _data_loader = dl
    return _data_loader


def get_data_types():
    data_loader = _get_data_loader()
    available_indicators = data_loader.get_available_indicators()

    data_types = {
        "none": {"label": "Без данных", "description": "Простая карта без данных"},
        "dominant_sector": {
            "label": "Преобладающий сектор экономики",
            "description": "Определение доминирующего сектора экономики в регионе"
        }
    }

    for indicator in available_indicators:
        data_types[indicator["type"]] = {
            "label": indicator["label"],
            "description": indicator["description"]
        }

    return data_types


class DataTypes:
    def __init__(self):
        self._data = None

    def _ensure_loaded(self):
        if self._data is None:
            self._data = get_data_types()

    def __getitem__(self, key):
        self._ensure_loaded()
        return self._data[key]

    def __iter__(self):
        self._ensure_loaded()
        return iter(self._data)

    def keys(self):
        self._ensure_loaded()
        return self._data.keys()

    def values(self):
        self._ensure_loaded()
        return self._data.values()

    def items(self):
        self._ensure_loaded()
        return self._data.items()

    def get(self, key, default=None):
        self._ensure_loaded()
        return self._data.get(key, default)


DATA_TYPES = DataTypes()


def reload_data_types():
    global DATA_TYPES
    DATA_TYPES = DataTypes()


def simplify_geometry(geometry: Dict, tolerance: float) -> Dict:
    try:
        from shapely.geometry import shape, mapping
        shapely_geom = shape(geometry)
        simplified_geom = shapely_geom.simplify(tolerance, preserve_topology=True)
        return mapping(simplified_geom)
    except ImportError:
        return _simplify_geometry_fallback(geometry, tolerance)
    except Exception as e:
        return geometry


def _simplify_geometry_fallback(feature: Dict, detail_level: float) -> Dict:
    try:
        geometry = feature['geometry']
        geometry_type = geometry['type']
        coordinates = geometry['coordinates']

        if not coordinates:
            return feature

        step = max(1, int(1 / detail_level))

        if geometry_type == 'Polygon':
            simplified_coords = _simplify_polygon(coordinates, step)
        elif geometry_type == 'MultiPolygon':
            simplified_coords = _simplify_multipolygon(coordinates, step)
        else:
            simplified_coords = coordinates

        if not simplified_coords:
            return feature

        return {
            'type': 'Feature',
            'properties': feature['properties'],
            'geometry': {
                'type': geometry_type,
                'coordinates': simplified_coords
            }
        }
    except Exception:
        return feature


def _simplify_polygon(polygon_coords: List, step: int) -> List:
    simplified_polygon = []
    for ring in polygon_coords:
        if not ring:
            continue
        simplified_ring = []
        for i, coord in enumerate(ring):
            if i % step == 0 or i == 0 or i == len(ring) - 1:
                simplified_ring.append(coord)
        if len(simplified_ring) >= 3:
            simplified_polygon.append(simplified_ring)
    return simplified_polygon if simplified_polygon else polygon_coords


def _simplify_multipolygon(multipolygon_coords: List, step: int) -> List:
    simplified_multipolygon = []
    for polygon in multipolygon_coords:
        simplified_polygon = _simplify_polygon(polygon, step)
        if simplified_polygon:
            simplified_multipolygon.append(simplified_polygon)
    return simplified_multipolygon if simplified_multipolygon else multipolygon_coords


def load_geojson_with_detail(file_path, detail_level, year, data_type="none",
                             compare_year=None, comparison_mode="absolute",
                             display_mode="absolute", adjustment_year="none"):
    is_regions = "regions" in file_path

    with open(file_path, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)

    if detail_level < 1.0:
        for feature in geojson_data['features']:
            if 'geometry' in feature and feature['geometry']['type'] in ['Polygon', 'MultiPolygon']:
                feature['geometry'] = simplify_geometry(feature['geometry'], detail_level)

    if data_type == "none":
        for feature in geojson_data['features']:
            feature['properties'] = {'name': feature['properties'].get('name', 'Unknown')}
        return geojson_data

    data_loader = _get_data_loader()

    # Обработка преобладающего сектора
    if data_type == "dominant_sector":
        dominant_sectors = calculate_dominant_sector(year, is_regions)
        for feature in geojson_data['features']:
            region_name = feature['properties']['name']
            feature['properties']["dominant_sector"] = dominant_sectors.get(region_name, "Не определен")
        return geojson_data

    # Загрузка данных для текущего года
    current_data = data_loader.get_indicator_data(data_type, year, is_regions)

    if display_mode == "relative" and data_type != "total_volume":
        shares_data = calculate_relative_shares(data_type, year, is_regions)
        for feature in geojson_data['features']:
            region_name = feature['properties']['name']
            feature['properties'][data_type] = shares_data.get(region_name)
    else:
        for feature in geojson_data['features']:
            region_name = feature['properties']['name']
            feature['properties'][data_type] = current_data.get(region_name)

    # Корректировка цен для денежных показателей
    monetary_indicators = ["salary", "gdp", "gdp_per_capita", "mining_industry",
                           "manufacturing_industry", "agriculture", "water_supply",
                           "energy_supply", "services", "total_volume"]

    if (adjustment_year != "none" and
            data_type != "none" and
            data_type in monetary_indicators):
        try:
            from utils.price_adjuster import price_adjuster
            for feature in geojson_data['features']:
                region_name = feature['properties']['name']
                if data_type in feature['properties'] and feature['properties'][data_type] is not None:
                    original_value = feature['properties'][data_type]
                    adjusted_value = price_adjuster.adjust_value(
                        original_value, region_name, year, int(adjustment_year), is_regions
                    )
                    feature['properties'][data_type] = adjusted_value
        except Exception:
            pass

    # Режим сравнения
    if compare_year and compare_year != "none":
        _calculate_deltas_for_geojson(geojson_data, data_type, year, compare_year,
                                      comparison_mode, display_mode, is_regions)

    return geojson_data


def get_legend_info_with_adjustment(data_type: str, display_mode: str, is_regions: bool = True, adjustment_year="none",
                                    target_year=None) -> Dict:
    if data_type == "none":
        return {
            "classes": [0, 1],
            "colorscale": ["#808080"],
            "title": "Нет данных",
            "colorProp": "none"
        }

    if display_mode == "relative":
        title = f"Доля {DATA_TYPES[data_type]['label']} в регионе, %"
        if adjustment_year != "none":
            title += f" (в ценах {adjustment_year} г.)"
        if target_year:
            title += f" ({target_year} год)"

        return {
            "classes": [0, 10, 20, 30, 40, 50, 100],
            "colorscale": ["#f7fbff", "#c6dbef", "#6baed6", "#3182bd", "#08519c", "#08306b"],
            "title": title,
            "colorProp": data_type,
            "unit": "%"
        }
    else:
        return get_legend_info(data_type, is_regions=is_regions, adjustment_year=adjustment_year,
                               target_year=target_year)


def _generate_classes_with_adjustment(data_type: str, is_regions: bool = True, adjustment_year="none",
                                      target_year=None) -> List[float]:
    data_loader = _get_data_loader()

    if target_year is None:
        target_year = get_default_year()

    regions_data = data_loader.get_indicator_data(data_type, target_year, is_regions)
    if not regions_data:
        return [0, 100, 500, 1000, 2000, 5000]

    values = []
    monetary_indicators = ["salary", "gdp", "gdp_per_capita", "mining_industry",
                           "manufacturing_industry", "agriculture", "water_supply",
                           "energy_supply", "services", "total_volume"]

    if adjustment_year != "none" and data_type in monetary_indicators:
        from .price_adjuster import price_adjuster
        for region_name, value in regions_data.items():
            if value is not None and value > 0:
                try:
                    adjusted_value = price_adjuster.adjust_value(
                        value, region_name, target_year, int(adjustment_year), is_regions
                    )
                    values.append(adjusted_value)
                except:
                    values.append(value)
    else:
        values = [v for v in regions_data.values() if v is not None and v > 0]

    if not values:
        return [0, 100, 500, 1000, 2000, 5000]

    min_val = min(values)
    max_val = max(values)

    if min_val == max_val:
        if min_val == 0:
            return [0, 1, 2, 3, 4, 5]
        else:
            base = min_val
            return [0, base * 0.5, base, base * 1.5, base * 2, base * 2.5]

    try:
        import numpy as np
        quantiles = np.quantile(values, [0, 0.2, 0.4, 0.6, 0.8, 1.0])
        classes = [float(q) for q in quantiles]

        for i in range(len(classes)):
            if classes[i] > 100:
                classes[i] = round(classes[i])
            elif classes[i] > 10:
                classes[i] = round(classes[i], 1)

        return classes
    except ImportError:
        step = (max_val - min_val) / 5
        classes = [min_val + i * step for i in range(6)]
        for i in range(len(classes)):
            if classes[i] > 100:
                classes[i] = round(classes[i])
            elif classes[i] > 10:
                classes[i] = round(classes[i], 1)
        return classes


def _calculate_deltas_for_geojson(geojson_data: Dict, data_type: str, current_year: int,
                                  compare_year: int, comparison_mode: str, display_mode: str,
                                  is_regions: bool):
    data_loader = _get_data_loader()
    absolute_indicators = ["salary", "gdp", "gdp_per_capita", "population"]

    if display_mode == "relative" and data_type != "total_volume" and data_type not in absolute_indicators:
        current_shares = calculate_relative_shares(data_type, current_year, is_regions)
        compare_shares = calculate_relative_shares(data_type, compare_year, is_regions)

        for feature in geojson_data['features']:
            region_name = feature['properties']['name']
            current_share = current_shares.get(region_name)
            compare_share = compare_shares.get(region_name)

            if current_share is not None and compare_share is not None:
                feature['properties']['delta'] = current_share - compare_share
            else:
                feature['properties']['delta'] = None
    else:
        compare_data = data_loader.get_indicator_data(data_type, compare_year, is_regions)

        for feature in geojson_data['features']:
            region_name = feature['properties']['name']
            current_value = feature['properties'].get(data_type)
            compare_value = compare_data.get(region_name)

            if current_value is not None and compare_value is not None:
                if comparison_mode == "absolute":
                    feature['properties']['delta'] = current_value - compare_value
                else:
                    if compare_value != 0:
                        feature['properties']['delta'] = ((current_value - compare_value) / compare_value) * 100
                    else:
                        feature['properties']['delta'] = 0
            else:
                feature['properties']['delta'] = None


def calculate_relative_shares(data_type: str, year: int, is_regions: bool = True) -> Dict[str, float]:
    data_loader = _get_data_loader()
    indicator_data = data_loader.get_indicator_data(data_type, year, is_regions)
    total_volume_data = data_loader.get_indicator_data("total_volume", year, is_regions)

    if not indicator_data or not total_volume_data:
        return {}

    relative_shares = {}
    for region_name, value in indicator_data.items():
        if region_name in total_volume_data and total_volume_data[region_name] != 0:
            share = (value / total_volume_data[region_name]) * 100
            relative_shares[region_name] = share
        else:
            relative_shares[region_name] = 0

    return relative_shares


def calculate_dominant_sector(year: int, is_regions: bool = True) -> Dict[str, str]:
    data_loader = _get_data_loader()
    sectors = {
        "mining_industry": "Добывающая",
        "manufacturing_industry": "Обрабатывающая",
        "agriculture": "Сельское хозяйство",
        "services": "Сфера услуг"
    }

    dominant_sectors = {}
    sector_data = {}

    for sector_type, sector_name in sectors.items():
        sector_data[sector_type] = data_loader.get_indicator_data(sector_type, year, is_regions)

    all_regions = set()
    for sector in sector_data.values():
        all_regions.update(sector.keys())

    for region in all_regions:
        max_share = 0
        dominant_sector = "Не определен"
        total_volume_data = data_loader.get_indicator_data("total_volume", year, is_regions)
        region_total = total_volume_data.get(region, 0)

        if region_total > 0:
            for sector_type, sector_name in sectors.items():
                sector_value = sector_data[sector_type].get(region, 0)
                share = (sector_value / region_total) * 100

                if share > max_share:
                    max_share = share
                    dominant_sector = sector_name

        if max_share < 25:
            dominant_sector = "Диверсифицированная"

        dominant_sectors[region] = dominant_sector

    return dominant_sectors


def get_legend_info(data_type: str, is_regions: bool = True, adjustment_year="none", target_year=None) -> Dict:
    if data_type == "none":
        return {
            "classes": [0, 1],
            "colorscale": ["#808080"],
            "title": "Нет данных",
            "colorProp": "none"
        }

    if data_type == "dominant_sector":
        sectors = ["Добывающая", "Обрабатывающая", "Сельское хозяйство", "Сфера услуг", "Диверсифицированная"]
        colors = ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#feca57"]

        return {
            "classes": list(range(len(sectors) + 1)),
            "colorscale": colors,
            "title": "Преобладающий сектор экономики",
            "colorProp": "dominant_sector",
            "categorical": True,
            "labels": sectors
        }

    data_loader = _get_data_loader()
    available_indicators = data_loader.get_available_indicators()
    indicator_meta = next((ind for ind in available_indicators if ind["type"] == data_type), None)

    if indicator_meta:
        classes = _generate_classes_with_adjustment(data_type, is_regions, adjustment_year, target_year)
        colorscale = _get_colorscale(data_type)

        if len(classes) < 2:
            classes = [0, 100, 500, 1000, 2000, 5000]
        if len(colorscale) < len(classes) - 1:
            colorscale = colorscale * (len(classes) // len(colorscale) + 1)
            colorscale = colorscale[:len(classes) - 1]

        title = f"{indicator_meta['label']}, {indicator_meta['unit']}"
        if adjustment_year != "none":
            title += f" (в ценах {adjustment_year} г.)"
        if target_year:
            title += f" ({target_year} год)"

        return {
            "classes": classes,
            "colorscale": colorscale,
            "title": title,
            "colorProp": data_type
        }
    else:
        title = "Данные загружаются..."
        if adjustment_year != "none":
            title += f" (в ценах {adjustment_year} г.)"
        if target_year:
            title += f" ({target_year} год)"

        return {
            "classes": [0, 100, 500, 1000, 2000, 5000],
            "colorscale": ["#c6e48b", "#7bc96f", "#239a3b", "#196127", "#0d3b1e"],
            "title": title,
            "colorProp": data_type
        }


def get_delta_legend_info(data_type: str, compare_year: int, comparison_mode: str, is_regions: bool = True) -> Dict:
    if compare_year == "none":
        return get_legend_info(data_type, is_regions)

    data_loader = _get_data_loader()
    current_year = get_default_year()

    deltas = []
    for region in data_loader.get_indicator_data(data_type, current_year, is_regions):
        compare_data = data_loader.get_indicator_data(data_type, compare_year, is_regions)
        if region in compare_data:
            current_val = data_loader.get_indicator_data(data_type, current_year, is_regions)[region]
            compare_val = compare_data[region]

            if current_val is not None and compare_val is not None:
                if comparison_mode == "absolute":
                    delta = current_val - compare_val
                else:
                    delta = ((current_val - compare_val) / compare_val) * 100 if compare_val != 0 else 0
                deltas.append(delta)

    if not deltas:
        return get_default_delta_legend_info(comparison_mode)

    min_delta = min(deltas)
    max_delta = max(deltas)

    if comparison_mode == "relative":
        min_delta = max(min_delta, -100)
        max_delta = min(max_delta, 100)

    return create_delta_legend_info(min_delta, max_delta, comparison_mode, data_type)


def get_delta_legend_info_for_shares(data_type: str, compare_year: int, comparison_mode: str,
                                     is_regions: bool = True) -> Dict:
    current_shares = calculate_relative_shares(data_type, get_default_year(), is_regions)
    compare_shares = calculate_relative_shares(data_type, compare_year, is_regions)

    share_deltas = []
    for region in current_shares:
        if region in compare_shares and current_shares[region] is not None and compare_shares[region] is not None:
            delta_pp = current_shares[region] - compare_shares[region]
            share_deltas.append(delta_pp)

    if not share_deltas:
        return get_default_share_delta_legend_info()

    min_delta = min(share_deltas)
    max_delta = max(share_deltas)

    min_delta = max(min_delta, -70)
    max_delta = min(max_delta, 70)

    return create_share_delta_legend_info(min_delta, max_delta, data_type)


def get_default_delta_legend_info(comparison_mode: str) -> Dict:
    if comparison_mode == "absolute":
        classes = [-1000, -500, -100, -50, 0, 50, 100, 500, 1000]
        colorscale = ['#8b0000', '#ff0000', '#ff6666', '#ffcccc', '#f0f0f0', '#ccffcc', '#66ff66', '#00ff00', '#008000']
    else:
        classes = [-100, -50, -20, -10, 0, 10, 20, 50, 100]
        colorscale = ['#8b0000', '#ff0000', '#ff6666', '#ffcccc', '#f0f0f0', '#ccffcc', '#66ff66', '#00ff00', '#008000']

    return {
        "colorscale": colorscale,
        "classes": classes,
        "colorProp": "delta",
        "title": "Изменение (%)" if comparison_mode == "relative" else "Абсолютное изменение"
    }


def get_default_share_delta_legend_info() -> Dict:
    classes = [-70, -50, -30, -10, 0, 10, 30, 50, 70]
    colorscale = ['#8b0000', '#ff0000', '#ff6666', '#ffcccc', '#f0f0f0', '#ccffcc', '#66ff66', '#00ff00', '#008000']

    return {
        "colorscale": colorscale,
        "classes": classes,
        "colorProp": "delta",
        "title": "Изменение доли (п.п.)"
    }


def create_delta_legend_info(min_val: float, max_val: float, comparison_mode: str, data_type: str) -> Dict:
    if comparison_mode == "absolute":
        max_abs = max(abs(min_val), abs(max_val))
        if max_abs < 10:
            step = 1
        elif max_abs < 50:
            step = 5
        elif max_abs < 200:
            step = 20
        elif max_abs < 1000:
            step = 100
        else:
            step = 500

        negative_classes = [-step * i for i in range(4, 0, -1)]
        positive_classes = [step * i for i in range(1, 5)]
        classes = negative_classes + [0] + positive_classes
    else:
        max_abs = max(abs(min_val), abs(max_val))
        if max_abs < 10:
            step = 2
        elif max_abs < 30:
            step = 5
        elif max_abs < 70:
            step = 10
        else:
            step = 20

        negative_classes = [-step * i for i in range(4, 0, -1)]
        positive_classes = [step * i for i in range(1, 5)]
        classes = negative_classes + [0] + positive_classes

    colorscale = [
        '#8b0000', '#ff0000', '#ff6666', '#ffcccc', '#f0f0f0',
        '#ccffcc', '#66ff66', '#00ff00', '#008000'
    ]

    num_colors_needed = len(classes) - 1
    if num_colors_needed < len(colorscale):
        start_idx = (len(colorscale) - num_colors_needed) // 2
        colorscale = colorscale[start_idx:start_idx + num_colors_needed]

    title = "Абсолютное изменение" if comparison_mode == "absolute" else "Относительное изменение (%)"

    return {
        "colorscale": colorscale,
        "classes": classes,
        "colorProp": "delta",
        "title": title
    }


def create_share_delta_legend_info(min_val: float, max_val: float, data_type: str) -> Dict:
    max_abs = max(abs(min_val), abs(max_val))

    if max_abs < 5:
        step = 1
    elif max_abs < 15:
        step = 3
    elif max_abs < 30:
        step = 5
    elif max_abs < 50:
        step = 10
    else:
        step = 15

    negative_classes = [-step * i for i in range(4, 0, -1)]
    positive_classes = [step * i for i in range(1, 5)]
    classes = negative_classes + [0] + positive_classes

    colorscale = [
        '#8b0000', '#ff0000', '#ff6666', '#ffcccc', '#f0f0f0',
        '#ccffcc', '#66ff66', '#00ff00', '#008000'
    ]

    num_colors_needed = len(classes) - 1
    if num_colors_needed < len(colorscale):
        start_idx = (len(colorscale) - num_colors_needed) // 2
        colorscale = colorscale[start_idx:start_idx + num_colors_needed]

    return {
        "colorscale": colorscale,
        "classes": classes,
        "colorProp": "delta",
        "title": "Изменение доли (п.п.)"
    }


def _get_colorscale(data_type: str) -> List[str]:
    color_schemes = {
        "population": ["#c6e48b", "#7bc96f", "#239a3b", "#196127", "#0d3b1e"],
        "gdp": ["#c6dbef", "#6baed6", "#3182bd", "#08519c", "#08306b"],
        "salary": ["#fcbba1", "#fb6a4a", "#de2d26", "#a50f15", "#67000d"],
        "gdp_per_capita": ["#e5f5e0", "#c7e9c0", "#a1d99b", "#74c476", "#41ab5d"],
        "mining_industry": ["#ffffcc", "#ffeda0", "#fed976", "#feb24c", "#fd8d3c"],
        "manufacturing_industry": ["#fddbc7", "#f4a582", "#d6604d", "#b2182b", "#67001f"],
        "agriculture": ["#dadaeb", "#bcbddc", "#9e9ac8", "#756bb1", "#54278f"],
        "water_supply": ["#c6dbef", "#6baed6", "#3182bd", "#08519c", "#08306b"],
        "energy_supply": ["#fcbba1", "#fb6a4a", "#de2d26", "#a50f15", "#67000d"],
        "total_volume": ["#e5f5e0", "#c7e9c0", "#a1d99b", "#74c476", "#41ab5d"],
        "services": ["#e6f3ff", "#b3d9ff", "#80bfff", "#4da6ff", "#1a8cff"],
        "dominant_sector": [
            "#ff6b6b", "#4ecdc4", "#ffe66d", "#96ceb4", "#feca57"
        ]
    }
    return color_schemes.get(data_type, ["#c6e48b", "#7bc96f", "#239a3b", "#196127", "#0d3b1e"])

def get_legend_info_with_mode(data_type: str, display_mode: str, is_regions: bool = True, target_year=None) -> Dict:
    """Получение информации для легенды с учетом режима отображения и года"""
    if data_type == "none":
        return {
            "classes": [0, 1],
            "colorscale": ["#808080"],
            "title": "Нет данных",
            "colorProp": "none"
        }

    if display_mode == "relative":
        title = f"Доля {DATA_TYPES[data_type]['label']} в регионе, %"
        if target_year:
            title += f" ({target_year} год)"

        return {
            "classes": [0, 10, 20, 30, 40, 50, 100],
            "colorscale": ["#f7fbff", "#c6dbef", "#6baed6", "#3182bd", "#08519c", "#08306b"],
            "title": title,
            "colorProp": data_type,
            "unit": "%"
        }
    else:
        return get_legend_info(data_type, is_regions=is_regions, target_year=target_year)

def get_filtered_data_types(case_id: str = "free") -> Dict:
    if case_id not in CASES:
        case_id = "free"

    case = CASES[case_id]
    all_data_types = get_data_types()

    filtered_data_types = {"none": all_data_types["none"]}

    for indicator_type in case["allowed_indicators"]:
        if indicator_type in all_data_types:
            filtered_data_types[indicator_type] = all_data_types[indicator_type]

    return filtered_data_types