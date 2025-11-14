import dash_leaflet as dl
from dash_extensions.enrich import DashProxy, html, Input, Output, State, dcc, callback_context
from dash_extensions.javascript import arrow_function, assign
import dash
import plotly.express as px
import pandas as pd
from utils.data_loader import data_loader
from utils.geo_utils import set_data_loader, get_available_years, get_default_year

set_data_loader(data_loader)

from utils.geo_utils import reload_data_types
reload_data_types()

AVAILABLE_YEARS = get_available_years()
DEFAULT_YEAR = get_default_year()

from utils.geo_utils import (
    load_geojson_with_detail,
    get_legend_info,
    get_delta_legend_info,
    get_legend_info_with_mode,
    calculate_relative_shares,
    DATA_TYPES,
    REGIONS_STYLE,
    MAP_STYLES,
    DETAIL_LEVELS,
    CASES,
    DEFAULT_CASE,
    get_filtered_data_types,
    get_delta_legend_info_for_shares,
    get_available_years,
    get_default_year,
    set_data_loader,
    reload_data_types,
    get_legend_info_with_adjustment
)
from assets.analitics import CASE_ANALYTICS

# Конфигурация карты
MAP_CONFIG = {
    "CENTER": [60, 100],
    "ZOOM": 3,
    "MIN_ZOOM": 3,
    "MAX_ZOOM": 6,
    "BOUNDS": [[30.0, -120.0], [77.0, 330.0]],
    "BOUNDS_OPTIONS": {
        "maxBoundsViscosity": 0.5,
        "bounceAtZoomLimits": True,
    },
    "OTHER_OPTIONS": {
        "worldCopyJump": False,
    }
}

# JavaScript функция для стилей
style_handle = assign("""function(feature, context){
    const {classes, colorscale, style, colorProp, categorical, labels} = context.hideout;
    const value = feature.properties[colorProp];
    const noDataColor = '#d3d3d3';

    if (value === undefined || value === null) {
        return {...style, fillColor: noDataColor, fillOpacity: 0.3};
    }

    if (categorical === true && labels && Array.isArray(labels)) {
        const index = labels.indexOf(value);
        if (index >= 0 && index < colorscale.length) {
            return {
                ...style, 
                fillColor: colorscale[index], 
                fillOpacity: 0.7,
                weight: 2,
                color: "#333",
                opacity: 1
            };
        } else {
            return {
                ...style, 
                fillColor: noDataColor, 
                fillOpacity: 0.3,
                weight: 2,
                color: "#333", 
                opacity: 1
            };
        }
    }

    if (colorProp === "delta") {
        const numValue = Number(value);
        if (isNaN(numValue)) {
            return {...style, fillColor: noDataColor, fillOpacity: 0.3};
        }

        let colorIndex = 0;
        for (let i = 0; i < classes.length - 1; i++) {
            if (numValue >= classes[i] && numValue < classes[i + 1]) {
                colorIndex = i;
                break;
            }
        }

        if (numValue >= classes[classes.length - 1]) {
            colorIndex = colorscale.length - 1;
        }

        if (numValue < classes[0]) {
            colorIndex = 0;
        }

        const finalColor = colorscale[colorIndex];
        return {...style, fillColor: finalColor, fillOpacity: 0.7};
    }

    if (colorProp === "none") {
        return style;
    }

    const numValue = Number(value);
    if (isNaN(numValue)) {
        return {...style, fillColor: noDataColor, fillOpacity: 0.3};
    }

    let colorIndex = -1;
    for (let i = 0; i < classes.length - 1; i++) {
        if (numValue >= classes[i] && numValue < classes[i + 1]) {
            colorIndex = i;
            break;
        }
    }

    if (colorIndex === -1 && numValue >= classes[classes.length - 1]) {
        colorIndex = colorscale.length - 1;
    }

    if (numValue < classes[0]) {
        colorIndex = 0;
    }

    if (colorIndex >= 0 && colorIndex < colorscale.length) {
        return {
            ...style, 
            fillColor: colorscale[colorIndex], 
            fillOpacity: 0.7,
            weight: 2,
            color: "#333",
            opacity: 1
        };
    }

    return {...style, fillColor: noDataColor, fillOpacity: 0.3};
}""")

app = DashProxy(suppress_callback_exceptions=True)

# Начальные данные
initial_geojson = load_geojson_with_detail("assets/russia_regions_pf.geojson", DETAIL_LEVELS["high"]["value"], DEFAULT_YEAR)
legend_info = get_legend_info("none")

def create_empty_analytics():
    return html.Div([
        html.Div([
            html.Img(
                src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='64' viewBox='0 0 24 24' fill='none' stroke='%23ccc' stroke-width='1' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z'%3E%3C/path%3E%3Ccircle cx='12' cy='10' r='3'%3E%3C/circle%3E%3C/svg%3E",
                style={"width": "64px", "height": "64px", "opacity": "0.5", "marginBottom": "20px"}
            ),
            html.P("Выберите регионы на карте для отображения аналитики",
                   style={"fontSize": "16px", "color": "#666", "marginBottom": "10px"}),
            html.P("(кликните по регионам на карте)",
                   style={"color": "#999", "fontSize": "12px"})
        ], style={"textAlign": "center", "marginTop": "50px"})
    ])

# Модальные окна
welcome_modal = html.Div([
    html.Div([
        html.Span("×", id="welcome-close", className="welcome-modal-close"),
        html.H2("Добро пожаловать в Аналитическую платформу регионов России!",
                style={"color": "#333", "marginBottom": "20px"}),

        html.P(
            "Эта платформа позволяет анализировать социально-экономические показатели регионов России через интерактивные карты и графики.",
            style={"color": "#666", "marginBottom": "30px", "fontSize": "16px"}),

        html.H3("Основные возможности:", style={"color": "#333", "marginBottom": "15px"}),

        html.Div([
            html.Div([
                html.Div("🗺️", className="welcome-feature-icon"),
                html.Div([
                    html.H4("Интерактивные карты"),
                    html.P("Визуализация данных на карте России с возможностью переключения между регионами и федеральными округами")
                ], className="welcome-feature-text")
            ], className="welcome-feature"),

            html.Div([
                html.Div("📊", className="welcome-feature-icon"),
                html.Div([
                    html.H4("Сравнение данных"),
                    html.P("Сравнение показателей между годами в абсолютных и относительных значениях")
                ], className="welcome-feature-text")
            ], className="welcome-feature"),

            html.Div([
                html.Div("🔍", className="welcome-feature-icon"),
                html.Div([
                    html.H4("Детальный анализ"),
                    html.P("Аналитика выбранных регионов с графиками, рейтингами и сводными таблицами")
                ], className="welcome-feature-text")
            ], className="welcome-feature"),

            html.Div([
                html.Div("🎯", className="welcome-feature-icon"),
                html.Div([
                    html.H4("Тематические кейсы"),
                    html.P("Готовые наборы показателей для анализа конкретных сценариев: население, производство и др.")
                ], className="welcome-feature-text")
            ], className="welcome-feature"),
        ]),

        html.Hr(style={"margin": "25px 0"}),

        html.Div([
            html.H4("Быстрый старт:", style={"marginBottom": "10px"}),
            html.Ol([
                html.Li("Выберите тип данных из выпадающего списка"),
                html.Li("Нажмите на регионы на карте для их выбора"),
                html.Li("Используйте правую панель для детального анализа"),
                html.Li("Сравнивайте данные между годами с помощью панели сравнения")
            ], style={"color": "#666", "paddingLeft": "20px"})
        ]),

        html.Div([
            html.Button("Начать работу", id="welcome-start-btn", className="welcome-button")
        ], style={"textAlign": "center", "marginTop": "30px"})
    ], className="welcome-modal-content")
], id="welcome-modal", className="welcome-modal")

case_modal = html.Div([
    html.Div([
        html.Span("×", id="case-description-close", className="welcome-modal-close"),
        html.H2(id="case-description-title", style={"color": "#333", "marginBottom": "20px"}),

        html.Div([
            html.H4("Описание кейса:", style={"color": "#333", "marginBottom": "10px"}),
            html.P(id="case-description-text",
                   style={"color": "#666", "marginBottom": "20px", "fontSize": "14px", "lineHeight": "1.5"})
        ]),

        html.Div([
            html.H4("Ключевые показатели:", style={"color": "#333", "marginBottom": "10px"}),
            html.Ul(id="case-indicators-list",
                    style={"color": "#666", "paddingLeft": "20px", "marginBottom": "20px"})
        ]),

        html.Div([
            html.H4("Аналитические выводы:", style={"color": "#333", "marginBottom": "10px"}),
            html.Div(id="case-insights", style={"color": "#666", "fontSize": "14px", "lineHeight": "1.5"})
        ]),

        html.Hr(style={"margin": "25px 0"}),

        html.Div([
            html.Button("Закрыть", id="case-description-ok", className="welcome-button")
        ], style={"textAlign": "center"})
    ], className="welcome-modal-content")
], id="case-description-modal", className="welcome-modal")

app.layout = html.Div([
    html.Div([
        dl.Map(
            children=[
                dl.TileLayer(id="tile-layer"),
                dl.GeoJSON(
                    data=initial_geojson,
                    style=style_handle,
                    hoverStyle=arrow_function(dict(
                        weight=5,
                        color="yellow",
                        dashArray="",
                        fillOpacity=0.6
                    )),
                    hideout=dict(
                        colorscale=legend_info["colorscale"],
                        classes=legend_info["classes"],
                        style=REGIONS_STYLE,
                        colorProp=legend_info["colorProp"]
                    ),
                    id="geojson"
                )
            ],
            style={"height": "100vh", "width": "100vw"},
            center=MAP_CONFIG["CENTER"],
            zoom=MAP_CONFIG["ZOOM"],
            minZoom=MAP_CONFIG["MIN_ZOOM"],
            maxZoom=MAP_CONFIG["MAX_ZOOM"],
            maxBounds=MAP_CONFIG["BOUNDS"],
            maxBoundsViscosity=MAP_CONFIG["BOUNDS_OPTIONS"]["maxBoundsViscosity"],
            bounceAtZoomLimits=MAP_CONFIG["BOUNDS_OPTIONS"]["bounceAtZoomLimits"],
            worldCopyJump=MAP_CONFIG["OTHER_OPTIONS"]["worldCopyJump"],
            id="map"
        ),

        html.Div([
            html.Div([
                html.Div([
                    html.Button("📋 Описание кейса",
                                id="case-description-btn",
                                title="Показать описание текущего кейса",
                                style={
                                    "background": "white",
                                    "color": "#333",
                                    "border": "1px solid #ddd",
                                    "padding": "8px 12px",
                                    "borderRadius": "15px",
                                    "fontSize": "12px",
                                    "cursor": "pointer",
                                    "transition": "all 0.3s ease",
                                    "fontWeight": "500"
                                })
                ], className="case-description-top"),
            ], className="case-description-panel"),

            html.Div([
                html.Div([
                    dcc.Dropdown(
                        id="case-dropdown",
                        options=[{"label": case["name"], "value": case_id} for case_id, case in CASES.items()],
                        value=DEFAULT_CASE,
                        clearable=False,
                        style={
                            "width": "200px",
                            "backgroundColor": "white",
                            "border": "none"
                        }
                    ),
                ], className="case-selector-top"),
            ], className="case-panel"),

            html.Div([
                html.Div([
                    dcc.Dropdown(
                        id="data-type-dropdown",
                        options=[{"label": DATA_TYPES[dt]["label"], "value": dt} for dt in DATA_TYPES],
                        value="none",
                        clearable=False,
                        style={
                            "width": "150px",
                            "backgroundColor": "white",
                            "border": "none"
                        }
                    ),
                ], className="data-selector-top"),

                html.Div([
                    html.Span("Регионы", id="regions-label", className="switch-label active"),
                    html.Span("Округа", id="districts-label", className="switch-label"),
                ], className="map-controls-top"),

                html.Div([
                    dcc.Dropdown(
                        id="year-dropdown",
                        options=[{"label": str(year), "value": year} for year in AVAILABLE_YEARS],
                        value=DEFAULT_YEAR,
                        clearable=False,
                        style={
                            "width": "120px",
                            "backgroundColor": "white",
                            "border": "none"
                        }
                    ),
                ], className="year-selector-top"),
            ], className="main-controls-panel"),

            html.Div([
                html.Div([
                    dcc.Dropdown(
                        id="compare-year-dropdown",
                        options=[{"label": "Без сравнения", "value": "none"}] +
                                [{"label": f"Сравнить с {year}", "value": year} for year in AVAILABLE_YEARS],
                        value="none",
                        clearable=False,
                        style={
                            "width": "160px",
                            "backgroundColor": "white",
                            "border": "none"
                        }
                    ),
                ], style={"flex": "1"}),

                html.Div([
                    dcc.RadioItems(
                        id="comparison-mode-radio",
                        options=[
                            {"label": " Абсолютное", "value": "absolute"},
                            {"label": " Относительное", "value": "relative"}
                        ],
                        value="absolute",
                        inline=False,
                        labelStyle={
                            "display": "block",
                            "marginBottom": "2px",
                            "fontSize": "11px",
                            "whiteSpace": "nowrap"
                        },
                        style={
                            "color": "#666",
                        }
                    ),
                ], style={"marginLeft": "15px"}),
            ], className="comparison-panel"),

            html.Div([
                html.Span("Абсолютное", id="absolute-value-label", className="value-switch-label active"),
                html.Span("Доля в регионе", id="relative-value-label", className="value-switch-label"),
            ], className="value-switch-container", id="value-switch-container", style={"display": "none"}),
        ], className="top-panels-container"),

        html.Div([
            html.Div(id="map-legend", className="horizontal-legend"),
            html.Div([
                html.Div([
                    html.Span("Цены в ценах:",
                              style={"fontSize": "12px", "marginRight": "8px", "color": "black", "fontWeight": "bold"}),
                    dcc.Dropdown(
                        id="price-adjustment-dropdown",
                        options=[
                            {"label": "текущих", "value": "none"},
                            {"label": "2023 г.", "value": "2023"},
                            {"label": "2020 г.", "value": "2020"},
                            {"label": "2015 г.", "value": "2015"},
                            {"label": "2010 г.", "value": "2010"},
                            {"label": "2005 г.", "value": "2005"},
                            {"label": "2000 г.", "value": "2000"},
                        ],
                        value="none",
                        clearable=False,
                        style={
                            "width": "120px",
                            "backgroundColor": "white",
                            "border": "none",
                            "fontSize": "12px"
                        }
                    ),
                ], style={
                    "display": "flex",
                    "alignItems": "center",
                    "background": "rgba(255,255,255,0.95)",
                    "padding": "8px 12px",
                    "borderRadius": "8px",
                    "marginTop": "10px"
                })
            ], className="price-adjustment-container",
                style={"position": "absolute", "bottom": "20px", "left": "20px", "zIndex": "800", "background": "transparent"})
        ], style={"position": "relative"}),

        html.Div(id="hover-info", className="hover-info-center"),
    ], id="map-container"),

    html.Button("⚙️", id="left-toggle", className="sidebar-toggle left-toggle"),
    html.Button("☰", id="right-toggle", className="sidebar-toggle right-toggle"),

    html.Div([
        html.Div("Настройки карты", className="panel-title"),
        html.Div([
            html.Div([
                html.Label("Стиль карты:", style={"fontWeight": "bold", "marginBottom": "5px"}),
                dcc.Dropdown(
                    id="map-style-dropdown",
                    options=[{"label": style["name"], "value": style_key} for style_key, style in MAP_STYLES.items()],
                    value="minimal",
                    clearable=False,
                    style={"marginBottom": "20px"}
                ),
            ]),
            html.Div([
                html.Label("Детализация геометрии:", style={"fontWeight": "bold", "marginBottom": "5px"}),
                dcc.Dropdown(
                    id="detail-dropdown",
                    options=[{"label": level["label"], "value": key} for key, level in DETAIL_LEVELS.items()],
                    value="high",
                    clearable=False,
                    style={"marginBottom": "20px"}
                ),
                html.Div(id="detail-description", style={"marginTop": "10px", "fontSize": "12px", "color": "#666"})
            ], style={"marginBottom": "20px"}),
            html.Div([
                html.Hr(style={"margin": "20px 0", "borderColor": "#e9ecef"}),
                html.A(
                    [
                        html.Span("🐙", className="github-icon"),
                        html.Span("Проект на GitHub", style={"marginLeft": "8px"})
                    ],
                    href="https://github.com/Cold4X/interactive-map-russian-economics",
                    className="github-link",
                    target="_blank",
                    title="Посмотреть исходный код на GitHub"
                )
            ], style={"textAlign": "center"})
        ], className="panel-content")
    ], id="left-panel", className="side-panel left-panel"),

    html.Div([
        html.Div([
            html.Span("Аналитика", className="panel-title"),
            html.Button("Показать все", id="show-all-btn", style={"float": "right", "marginTop": "-5px"})
        ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"}),
        html.Div(create_empty_analytics(), id="right-panel-content", className="panel-content"),
    ], id="right-panel", className="side-panel right-panel"),

    dcc.Store(id="selected-regions", data=[]),
    dcc.Store(id="current-data-type", data="none"),
    dcc.Store(id="current-year", data=DEFAULT_YEAR),
    dcc.Store(id="current-case", data=DEFAULT_CASE),
    dcc.Store(id="compare-year", data="none"),
    dcc.Store(id="comparison-mode", data="absolute"),
    dcc.Store(id="value-display-mode", data="absolute"),
    dcc.Store(id="price-adjustment-year", data="none"),
    dcc.Store(id="first-visit", data=True),
    welcome_modal,
    case_modal,
], className="map-container", id="main-container")

# Вспомогательные функции
def get_regions_data(region_names, data_type, year, is_regions=True, adjustment_year="none"):
    regions_data = {}
    for region_name in region_names:
        years_data = {}
        for data_year in AVAILABLE_YEARS:
            indicator_data = data_loader.get_indicator_data(data_type, data_year, is_regions)
            if region_name in indicator_data:
                value = indicator_data[region_name]
                if adjustment_year != "none" and adjustment_year is not None and data_type not in ["population", "none"]:
                    try:
                        from utils.price_adjuster import price_adjuster
                        target_year = int(adjustment_year)
                        adjusted_value = price_adjuster.adjust_value(
                            value, region_name, data_year, target_year, is_regions
                        )
                        years_data[data_year] = adjusted_value
                    except Exception:
                        years_data[data_year] = value
                else:
                    years_data[data_year] = value
            else:
                years_data[data_year] = 0
        regions_data[region_name] = {data_type: years_data}
    return regions_data

def create_summary_tab(regions_data, data_type, year, adjustment_year="none"):
    data_list = []
    adjustment_info = ""
    if adjustment_year != "none":
        adjustment_info = f" (в ценах {adjustment_year} г.)"

    for region, data in regions_data.items():
        value = data.get(data_type, {}).get(year, 0)
        available_indicators = data_loader.get_available_indicators()
        indicator_meta = next((ind for ind in available_indicators if ind["type"] == data_type), None)
        unit = indicator_meta["unit"] if indicator_meta else ""

        data_list.append({
            'Регион': region,
            'Значение': round(value, 2),
            'Единица измерения': unit
        })

    if not data_list:
        return html.Div("Нет данных для выбранных регионов")

    df = pd.DataFrame(data_list)
    total_value = df['Значение'].sum()
    avg_value = df['Значение'].mean()
    max_value = df['Значение'].max()
    max_region = df.loc[df['Значение'].idxmax(), 'Регион'] if not df.empty else ""

    kpi_cards = html.Div([
        html.Div([
            html.Div(f"{total_value:,.0f}", style={"fontSize": "24px", "fontWeight": "bold", "color": "#007bff"}),
            html.Div(f"Суммарное значение{adjustment_info}", style={"fontSize": "12px", "color": "#666"})
        ], style={"textAlign": "center", "padding": "10px", "background": "#f8f9fa", "borderRadius": "5px", "flex": "1", "margin": "5px"}),

        html.Div([
            html.Div(f"{avg_value:,.0f}", style={"fontSize": "24px", "fontWeight": "bold", "color": "#28a745"}),
            html.Div(f"Среднее значение{adjustment_info}", style={"fontSize": "12px", "color": "#666"})
        ], style={"textAlign": "center", "padding": "10px", "background": "#f8f9fa", "borderRadius": "5px", "flex": "1", "margin": "5px"}),

        html.Div([
            html.Div(f"{max_value:,.0f}", style={"fontSize": "24px", "fontWeight": "bold", "color": "#dc3545"}),
            html.Div(f"Максимум: {max_region}{adjustment_info}", style={"fontSize": "12px", "color": "#666"})
        ], style={"textAlign": "center", "padding": "10px", "background": "#f8f9fa", "borderRadius": "5px", "flex": "1", "margin": "5px"}),
    ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": "20px"})

    table = dash.dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in df.columns],
        style_cell={'textAlign': 'left', 'padding': '10px', 'fontSize': '12px'},
        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        style_as_list_view=True,
    )

    return html.Div([
        kpi_cards,
        html.Hr(),
        html.H5(f"Детальные данные по регионам{adjustment_info}"),
        table
    ])

def create_charts_tab(regions_data, data_type, year, adjustment_year="none"):
    chart_data = []
    adjustment_info = ""
    if adjustment_year != "none":
        adjustment_info = f" (в ценах {adjustment_year} г.)"

    for region_name, data in regions_data.items():
        for y in AVAILABLE_YEARS:
            value = data.get(data_type, {}).get(y, 0)
            chart_data.append({
                'Регион': region_name,
                'Год': y,
                'Значение': value
            })

    if not chart_data:
        return html.Div("Нет данных для построения графиков")

    df = pd.DataFrame(chart_data)
    available_indicators = data_loader.get_available_indicators()
    indicator_meta = next((ind for ind in available_indicators if ind["type"] == data_type), None)
    indicator_label = indicator_meta["label"] if indicator_meta else "Показатель"

    charts = []

    # График динамики абсолютных значений
    trend_fig = px.line(df, x='Год', y='Значение', color='Регион',
                        title=f'Динамика {indicator_label.lower()} по годам{adjustment_info}')
    trend_fig.update_layout(height=300, showlegend=True)
    charts.append(dcc.Graph(figure=trend_fig, style={'marginBottom': '20px'}))

    # График динамики долей для производственных показателей
    production_indicators = ["mining_industry", "manufacturing_industry", "agriculture", "services", "water_supply", "energy_supply"]
    if data_type in production_indicators:
        shares_chart_data = []
        for region_name in regions_data.keys():
            for y in AVAILABLE_YEARS:
                current_value = regions_data[region_name].get(data_type, {}).get(y, 0)
                total_data = data_loader.get_indicator_data("total_volume", y, True)
                region_total = total_data.get(region_name, 1)
                if region_total > 0:
                    share = (current_value / region_total) * 100
                else:
                    share = 0
                shares_chart_data.append({
                    'Регион': region_name,
                    'Год': y,
                    'Доля, %': share
                })
        if shares_chart_data:
            shares_df = pd.DataFrame(shares_chart_data)
            shares_fig = px.line(shares_df, x='Год', y='Доля, %', color='Регион',
                                 title=f'Динамика доли {indicator_label.lower()} в общем объеме производства региона, %')
            shares_fig.update_layout(height=300, showlegend=True, yaxis_title="Доля в общем объеме производства региона, %")
            charts.append(dcc.Graph(figure=shares_fig, style={'marginBottom': '20px'}))

    # Столбчатая диаграмма для текущего года
    current_year_df = df[df['Год'] == year]
    if not current_year_df.empty:
        bar_fig = px.bar(current_year_df, x='Регион', y='Значение',
                         title=f'{indicator_label} по регионам ({year} год){adjustment_info}')
        bar_fig.update_layout(height=300, xaxis_tickangle=-45, showlegend=False)
        charts.append(dcc.Graph(figure=bar_fig))

    return html.Div(charts)

def create_rankings_tab(regions_data, data_type, year, adjustment_year="none"):
    adjustment_info = ""
    if adjustment_year != "none":
        adjustment_info = f" (в ценах {adjustment_year} г.)"

    data_list = []
    for region, data in regions_data.items():
        value = data.get(data_type, {}).get(year, 0)
        data_list.append({
            'Регион': region,
            'Значение': round(value, 2)
        })

    if not data_list:
        return html.Div("Нет данных для рейтингов")

    df = pd.DataFrame(data_list)
    available_indicators = data_loader.get_available_indicators()
    indicator_meta = next((ind for ind in available_indicators if ind["type"] == data_type), None)
    unit = indicator_meta["unit"] if indicator_meta else ""
    indicator_label = indicator_meta["label"] if indicator_meta else "Показатель"

    value_ranking = df.nlargest(min(10, len(df)), 'Значение')[['Регион', 'Значение']].reset_index(drop=True)
    value_ranking['Ранг'] = value_ranking.index + 1

    return html.Div([
        html.Div([
            html.H6(f"Топ регионов по {indicator_label.lower()}{adjustment_info}",
                    style={"marginBottom": "10px", "marginTop": "20px"}),
            dash.dash_table.DataTable(
                data=value_ranking.to_dict('records'),
                columns=[{"name": "Ранг", "id": "Ранг"},
                         {"name": "Регион", "id": "Регион"},
                         {"name": f"Значение, {unit}", "id": "Значение"}],
                style_cell={'fontSize': '12px', 'padding': '5px'},
                style_header={'fontWeight': 'bold'},
                page_size=10
            )
        ], style={"marginBottom": "30px"})
    ])

def create_analytics_panel(selected_regions, data_type, year, is_regions=True):
    if not selected_regions:
        return create_empty_analytics()

    object_type = "регионов" if is_regions else "округов"
    return html.Div([
        html.Div([html.H4(f"Аналитика {object_type} ({len(selected_regions)} выбрано)")],
                 style={"marginBottom": "20px"}),
        dcc.Tabs(id="analytics-tabs", value="summary", children=[
            dcc.Tab(label="Сводка", value="summary"),
            dcc.Tab(label="Графики", value="charts"),
            dcc.Tab(label="Рейтинги", value="rankings"),
        ]),
        html.Div(id="analytics-tab-content", style={"marginTop": "20px"})
    ])

def _format_legend_number(value):
    if value == 0:
        return "0"
    elif value < 1:
        return f"{value:.2f}"
    elif value < 10:
        return f"{value:.1f}"
    elif value < 1000:
        return f"{int(value)}"
    else:
        return f"{value:,.0f}".replace(",", " ")

def create_legend_content(legend_info, year, compare_year=None, display_mode="absolute", adjustment_year="none"):
    if not legend_info or "colorscale" not in legend_info or "classes" not in legend_info:
        return None

    colorscale = legend_info["colorscale"]
    classes = legend_info["classes"]

    if legend_info.get("categorical") and "labels" in legend_info:
        legend_items = []
        labels = legend_info["labels"]
        for i, label in enumerate(labels):
            if i < len(colorscale):
                legend_items.append(
                    html.Div([
                        html.Div(className="legend-color-horizontal",
                                 style={"backgroundColor": colorscale[i]}),
                        html.Span(label, className="legend-label-horizontal")
                    ], className="legend-item-horizontal")
                )
        title = legend_info.get("title", "Легенда")
        if year:
            title += f" ({year} год)"
        return html.Div([
            html.Div(title, className="legend-title-horizontal"),
            html.Div(legend_items, className="legend-items-horizontal")
        ])

    if not colorscale or not classes or len(colorscale) != len(classes) - 1:
        return None

    legend_items = []
    for i in range(len(colorscale)):
        if i < len(classes) - 1:
            lower_bound = _format_legend_number(classes[i])
            upper_bound = _format_legend_number(classes[i + 1])
            label = f"{lower_bound}-{upper_bound}"
        else:
            label = f"{_format_legend_number(classes[i])}+"

        legend_items.append(
            html.Div([
                html.Div(className="legend-color-horizontal", style={"backgroundColor": colorscale[i]}),
                html.Span(label, className="legend-label-horizontal")
            ], className="legend-item-horizontal")
        )

    if compare_year and compare_year != "none":
        title = legend_info.get("title", f"Изменение {year} vs {compare_year}")
    else:
        title = legend_info.get("title", "Легенда")
        title = f"{title} ({year} год)"

    if adjustment_year != "none":
        title += f" (в ценах {adjustment_year} г.)"

    return html.Div([
        html.Div(title, className="legend-title-horizontal"),
        html.Div(legend_items, className="legend-items-horizontal")
    ])

def get_legend_data(data_type, compare_year, comparison_mode, display_mode, is_regions, adjustment_year="none", target_year=None):
    if compare_year != "none":
        if display_mode == "relative" and data_type != "total_volume" and data_type not in ["salary", "gdp", "gdp_per_capita", "population"]:
            legend_info = get_delta_legend_info_for_shares(data_type, compare_year, comparison_mode, is_regions)
        else:
            legend_info = get_delta_legend_info(data_type, compare_year, comparison_mode, is_regions)
    else:
        legend_info = get_legend_info_with_adjustment(data_type, display_mode, is_regions, adjustment_year, target_year)
    return legend_info

def get_map_data(file_path, detail_level, year, data_type, compare_year, comparison_mode, display_mode, adjustment_year="none"):
    return load_geojson_with_detail(
        file_path,
        DETAIL_LEVELS[detail_level]["value"],
        year,
        data_type,
        compare_year,
        comparison_mode,
        display_mode,
        adjustment_year
    )

def get_active_layer(regions_class, districts_class):
    is_regions = "active" in regions_class
    file_path = "assets/russia_regions_pf.geojson" if is_regions else "assets/russia_districts_pf.geojson"
    return is_regions, file_path

# Callback'ы
@app.callback(
    [Output("geojson", "data"),
     Output("geojson", "hideout"),
     Output("map-legend", "children"),
     Output("regions-label", "className"),
     Output("districts-label", "className"),
     Output("current-data-type", "data"),
     Output("current-year", "data"),
     Output("compare-year", "data"),
     Output("comparison-mode", "data"),
     Output("price-adjustment-year", "data")],
    [Input("data-type-dropdown", "value"),
     Input("year-dropdown", "value"),
     Input("detail-dropdown", "value"),
     Input("regions-label", "n_clicks"),
     Input("districts-label", "n_clicks"),
     Input("compare-year-dropdown", "value"),
     Input("comparison-mode-radio", "value"),
     Input("value-display-mode", "data"),
     Input("price-adjustment-dropdown", "value")],
    [State("regions-label", "className"),
     State("districts-label", "className"),
     State("current-data-type", "data"),
     State("current-year", "data"),
     State("price-adjustment-year", "data")]
)
def master_callback(data_type, year, detail_level, regions_clicks, districts_clicks,
                    compare_year, comparison_mode, display_mode, adjustment_year,
                    regions_class, districts_class, current_data_type, current_year, current_adjustment):
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update, regions_class, districts_class, data_type, year, compare_year, comparison_mode, current_adjustment

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    new_regions_class = regions_class
    new_districts_class = districts_class

    if trigger_id == "regions-label":
        new_regions_class = "switch-label active"
        new_districts_class = "switch-label"
        is_regions = True
    elif trigger_id == "districts-label":
        new_regions_class = "switch-label"
        new_districts_class = "switch-label active"
        is_regions = False
    else:
        is_regions = "active" in regions_class

    file_path = "assets/russia_regions_pf.geojson" if is_regions else "assets/russia_districts_pf.geojson"

    geojson_data = get_map_data(file_path, detail_level, year, data_type, compare_year, comparison_mode, display_mode, adjustment_year)
    legend_info = get_legend_data(data_type, compare_year, comparison_mode, display_mode, is_regions, adjustment_year, year)

    hideout = dict(
        colorscale=legend_info["colorscale"],
        classes=legend_info["classes"],
        style=REGIONS_STYLE,
        colorProp=legend_info["colorProp"]
    )

    if data_type == "dominant_sector" and legend_info.get("categorical"):
        hideout["categorical"] = True
        hideout["labels"] = legend_info["labels"]

    legend_content = create_legend_content(legend_info, year, compare_year, display_mode, adjustment_year)

    return geojson_data, hideout, legend_content, new_regions_class, new_districts_class, data_type, year, compare_year, comparison_mode, adjustment_year

@app.callback(
    [Output("absolute-value-label", "className"),
     Output("relative-value-label", "className"),
     Output("value-display-mode", "data")],
    [Input("absolute-value-label", "n_clicks"),
     Input("relative-value-label", "n_clicks")],
    [State("absolute-value-label", "className"),
     State("relative-value-label", "className")]
)
def switch_display_mode(absolute_clicks, relative_clicks, absolute_class, relative_class):
    ctx = callback_context
    if not ctx.triggered:
        return "value-switch-label active", "value-switch-label", "absolute"

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == "absolute-value-label":
        return "value-switch-label active", "value-switch-label", "absolute"
    elif button_id == "relative-value-label":
        return "value-switch-label", "value-switch-label active", "relative"

    return absolute_class, relative_class, "absolute"

@app.callback(
    Output("value-switch-container", "style"),
    Input("current-data-type", "data")
)
def toggle_value_switch(data_type):
    production_indicators = ["mining_industry", "manufacturing_industry", "agriculture", "services", "water_supply", "energy_supply"]
    return {"display": "flex", "marginLeft": "10px"} if data_type in production_indicators else {"display": "none"}

@app.callback(
    [Output("data-type-dropdown", "options"),
     Output("data-type-dropdown", "value"),
     Output("current-case", "data")],
    [Input("case-dropdown", "value")],
    [State("data-type-dropdown", "value")]
)
def update_data_types_by_case(selected_case, current_value):
    filtered_data_types = get_filtered_data_types(selected_case)

    def shorten_label(full_label):
        short_names = {
            "Среднемесячная номинальная ЗП": "Средняя ЗП",
            "Валовой региональный продукт": "ВРП",
            "ВРП на душу населения": "ВРП на душу",
            "Добывающая промышленность": "Добывающая пром.",
            "Обрабатывающая промышленность": "Обрабатывающая пром.",
            "Суммарный объем": "Суммарный объем"
        }
        return short_names.get(full_label, full_label)

    options = [{"label": shorten_label(filtered_data_types[dt]["label"]), "value": dt} for dt in filtered_data_types]
    new_value = current_value if current_value in filtered_data_types else "none"

    return options, new_value, selected_case

@app.callback(
    [Output("selected-regions", "data", allow_duplicate=True),
     Output("right-panel-content", "children")],
    [Input("geojson", "clickData"),
     Input("show-all-btn", "n_clicks")],
    [State("selected-regions", "data"),
     State("current-data-type", "data"),
     State("current-year", "data"),
     State("regions-label", "className")],
    prevent_initial_call=True
)
def handle_region_selection(click_data, show_all_clicks, selected_regions, data_type, year, regions_class):
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update, create_empty_analytics()

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if selected_regions is None:
        selected_regions = []

    is_regions = "active" in regions_class

    if trigger_id == "show-all-btn":
        selected_regions = []
    elif trigger_id == "geojson" and click_data:
        region_name = click_data['properties'].get('name', 'Unknown')
        if region_name in selected_regions:
            selected_regions.remove(region_name)
        else:
            selected_regions.append(region_name)

    panel_content = create_analytics_panel(selected_regions, data_type, year, is_regions)
    return selected_regions, panel_content

@app.callback(
    Output("analytics-tab-content", "children"),
    [Input("analytics-tabs", "value"),
     Input("selected-regions", "data"),
     Input("current-data-type", "data"),
     Input("current-year", "data"),
     Input("regions-label", "className"),
     Input("price-adjustment-year", "data")],
    prevent_initial_call=True
)
def update_analytics_tab(active_tab, selected_regions, data_type, year, regions_class, adjustment_year):
    if not selected_regions or data_type == "none":
        return html.Div("Выберите регионы и тип данных для анализа")

    is_regions = "active" in regions_class
    regions_data = get_regions_data(selected_regions, data_type, year, is_regions, adjustment_year)

    if not regions_data:
        return html.Div("Нет данных для выбранных регионов")

    try:
        if active_tab == "summary":
            return create_summary_tab(regions_data, data_type, year, adjustment_year)
        elif active_tab == "charts":
            return create_charts_tab(regions_data, data_type, year, adjustment_year)
        elif active_tab == "rankings":
            return create_rankings_tab(regions_data, data_type, year, adjustment_year)
        return html.Div("Выберите вкладку")
    except Exception as e:
        return html.Div(f"Ошибка при отображении аналитики: {str(e)}")

@app.callback(
    Output("hover-info", "children"),
    [Input("geojson", "hoverData"),
     Input("current-data-type", "data"),
     Input("current-year", "data"),
     Input("compare-year", "data"),
     Input("comparison-mode", "data"),
     Input("value-display-mode", "data"),
     Input("price-adjustment-year", "data")],
    prevent_initial_call=True
)
def update_hover_info(feature, data_type, year, compare_year, comparison_mode, display_mode, adjustment_year):
    if not feature:
        return html.Div("Наведите на регион для информации")

    properties = feature.get('properties', {})
    region_name = properties.get('name', 'Неизвестно')
    adjustment_info = ""
    if adjustment_year != "none":
        adjustment_info = f" (в ценах {adjustment_year} г.)"

    absolute_indicators = ["salary", "gdp", "gdp_per_capita", "population"]

    if compare_year != "none" and compare_year is not None and 'delta' in properties:
        delta = properties['delta']
        if delta is not None:
            if data_type in absolute_indicators:
                if comparison_mode == "absolute":
                    return html.Div([
                        html.Strong(f"{region_name}"),
                        html.Br(),
                        f"{year} vs {compare_year}: {delta:+.0f} ед.{adjustment_info}"
                    ])
                else:
                    return html.Div([
                        html.Strong(f"{region_name}"),
                        html.Br(),
                        f"{year} vs {compare_year}: {delta:+.1f}%{adjustment_info}"
                    ])
            elif display_mode == "relative" and data_type != "total_volume":
                return html.Div([
                    html.Strong(f"{region_name}"),
                    html.Br(),
                    f"Изменение доли {year} vs {compare_year}: {delta:+.1f} п.п.{adjustment_info}"
                ])
            else:
                unit = "ед." if comparison_mode == "absolute" else "%"
                return html.Div([
                    html.Strong(f"{region_name}"),
                    html.Br(),
                    f"{year} vs {compare_year}: {delta:+.1f} {unit}{adjustment_info}"
                ])

    elif data_type != "none":
        value = properties.get(data_type)

        if value is None:
            return html.Div([
                html.Strong(f"{region_name}"),
                html.Br(),
                "Нет данных"
            ])

        if display_mode == "relative":
            display_text = f"{value:.1f}%"
            label = "Доля"
        else:
            available_indicators = data_loader.get_available_indicators()
            indicator_meta = next((ind for ind in available_indicators if ind["type"] == data_type), None)
            unit = indicator_meta["unit"] if indicator_meta else "ед."

            try:
                if value == int(value):
                    display_text = f"{value:,.0f} {unit}".replace(",", " ")
                else:
                    display_text = f"{value:,.1f} {unit}".replace(",", " ")
            except (TypeError, ValueError):
                display_text = f"{value} {unit}"

            label = "Значение"

        return html.Div([
            html.Strong(f"{region_name} ({year} год){adjustment_info}"),
            html.Br(),
            f"{label}: {display_text}"
        ])
    else:
        return html.Div([
            html.Strong(f"{region_name}"),
            html.Br(),
            "Выберите тип данных"
        ])

@app.callback(
    [Output("case-description-modal", "className"),
     Output("case-description-title", "children"),
     Output("case-description-text", "children"),
     Output("case-indicators-list", "children"),
     Output("case-insights", "children")],
    [Input("case-description-btn", "n_clicks"),
     Input("case-description-close", "n_clicks"),
     Input("case-description-ok", "n_clicks"),
     Input("current-case", "data")],
    prevent_initial_call=True
)
def manage_case_description(open_clicks, close_clicks, ok_clicks, current_case):
    ctx = callback_context
    if not ctx.triggered:
        return "welcome-modal", "", "", "", ""

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == "case-description-btn":
        case_data = CASE_ANALYTICS.get(current_case, {})
        title = case_data.get("title", "Описание кейса")
        description = case_data.get("description", "")
        indicators = case_data.get("indicators", [])
        insights_list = case_data.get("insights", [])

        indicators_children = [html.Li(indicator) for indicator in indicators]
        insights_children = html.Ul([html.Li(insight) for insight in insights_list])

        return "welcome-modal show-modal", title, description, indicators_children, insights_children

    elif trigger_id in ["case-description-close", "case-description-ok"]:
        return "welcome-modal", "", "", "", ""

    return "welcome-modal", "", "", "", ""

@app.callback(
    [Output("left-panel", "className"),
     Output("right-panel", "className"),
     Output("left-toggle", "className"),
     Output("right-toggle", "className")],
    [Input("left-toggle", "n_clicks"),
     Input("right-toggle", "n_clicks")],
    [State("left-panel", "className"),
     State("right-panel", "className")]
)
def toggle_panels(left_clicks, right_clicks, left_class, right_class):
    ctx = callback_context
    if not ctx.triggered:
        return left_class, right_class, "sidebar-toggle left-toggle", "sidebar-toggle right-toggle"

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    left_open = "panel-open" in left_class
    right_open = "panel-open" in right_class

    if button_id == "left-toggle":
        left_open = not left_open
        right_open = False
    elif button_id == "right-toggle":
        right_open = not right_open
        left_open = False

    left_panel_class = "side-panel left-panel" + (" panel-open" if left_open else "")
    right_panel_class = "side-panel right-panel" + (" panel-open" if right_open else "")
    left_btn_class = "sidebar-toggle left-toggle" + (" panel-open" if left_open else "")
    right_btn_class = "sidebar-toggle right-toggle" + (" panel-open" if right_open else "")

    return left_panel_class, right_panel_class, left_btn_class, right_btn_class

@app.callback(
    [Output("tile-layer", "url"),
     Output("tile-layer", "attribution"),
     Output("tile-layer", "subdomains")],
    Input("map-style-dropdown", "value")
)
def update_map_style(selected_style):
    style_config = MAP_STYLES[selected_style]
    url = style_config["url"]
    subdomains = ['a', 'b', 'c'] if "{s}" in url else None
    return url, style_config["attribution"], subdomains

@app.callback(
    Output("detail-description", "children"),
    Input("detail-dropdown", "value")
)
def update_detail_description(detail_level_key):
    level_info = DETAIL_LEVELS[detail_level_key]
    descriptions = {
        "high": "Максимальная детализация, рекомендуется для мощных компьютеров",
        "low": "Оптимальный баланс качества и производительности"
    }
    return f"{level_info['label']} ({level_info['value'] * 100:.0f}%) - {descriptions[detail_level_key]}"

@app.callback(
    [Output("current-data-type", "data", allow_duplicate=True),
     Output("current-year", "data", allow_duplicate=True)],
    Input("map", "id"),
    prevent_initial_call=False
)
def initialize_data(_):
    return "none", DEFAULT_YEAR

@app.callback(
    [Output("welcome-modal", "className"),
     Output("first-visit", "data")],
    [Input("welcome-close", "n_clicks"),
     Input("welcome-start-btn", "n_clicks"),
     Input("main-container", "id")],
    [State("first-visit", "data")]
)
def manage_welcome_modal(close_clicks, start_clicks, main_id, first_visit):
    ctx = callback_context

    if not ctx.triggered:
        if first_visit:
            return "welcome-modal show-modal", True
        else:
            return "welcome-modal", False

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id in ["welcome-close", "welcome-start-btn"]:
        return "welcome-modal", False

    if first_visit and trigger_id == "main-container":
        return "welcome-modal show-modal", True

    return "welcome-modal", first_visit

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8050)