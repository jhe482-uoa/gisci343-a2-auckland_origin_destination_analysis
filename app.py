from pathlib import Path
from shiny import App, ui, render, reactive
import pandas as pd
import matplotlib.pyplot as plt
from shinywidgets import output_widget, render_widget
import geopandas as gpd
import plotly.graph_objects as go
import json

GLOBAL_ZOOM = 9

_data_dir = Path(__file__).parent / "data"

work_sa2_data  = pd.read_csv(_data_dir / "2023-census-main-means-of-travel-to-work-by-statistical-area.csv")
study_sa2_data = pd.read_csv(_data_dir / "2023-census-main-means-of-travel-to-education-by-statistical.csv")

sa2shape2023 = gpd.read_file(_data_dir / "aucklandsa2-2023.gpkg")
sa2shape2023.to_crs(epsg=4326, inplace=True)

BASE_GEOJSON = json.loads(sa2shape2023.to_json())
SA2_NAMES    = sa2shape2023["SA22023__1"]
center_x     = sa2shape2023.geometry.centroid.x.mean()
center_y     = sa2shape2023.geometry.centroid.y.mean()

COLORS = ['#67000D', '#EF3B2C', '#FC9272', '#FEE0D2', '#FFFFFF']
COLORSCALE = [
    [0.00, COLORS[4]], [0.01, COLORS[4]],
    [0.01, COLORS[3]], [0.10, COLORS[3]],
    [0.10, COLORS[2]], [0.25, COLORS[2]],
    [0.25, COLORS[1]], [0.50, COLORS[1]],
    [0.50, COLORS[0]], [1.00, COLORS[0]],
]
LEGEND_ITEMS = [
    (">25%",   COLORS[0]),
    ("10–25%", COLORS[1]),
    ("5–10%",  COLORS[2]),
    ("1–5%",   COLORS[3]),
    ("<1%",    COLORS[4]),
]


def _build_legend():
    shapes, annotations = [], []

    shapes.append(dict(
        type="rect", xref="paper", yref="paper",
        x0=0.0, x1=0.12, y0=0.64, y1=1.04,
        fillcolor="white", opacity=0.9,
        line=dict(color="grey", width=1),
        layer="above",
    ))

    # Title
    annotations.append(dict(
        xref="paper", yref="paper",
        x=0.01, y=1.01,
        text="<b>Commuter %</b>",
        showarrow=False, font=dict(size=12), xanchor="left",
    ))

    for i, (label_text, color) in enumerate(LEGEND_ITEMS):
        y_top = 0.95 - i * 0.065
        y_bot = y_top - 0.045
        shapes.append(dict(
            type="rect", xref="paper", yref="paper",
            x0=0.01, x1=0.04, y0=y_bot, y1=y_top,
            fillcolor=color, line=dict(color="grey", width=1),
            layer="above",
        ))
        annotations.append(dict(
            xref="paper", yref="paper",
            x=0.05, y=(y_top + y_bot) / 2,
            text=label_text, showarrow=False,
            font=dict(size=11), xanchor="left", yanchor="middle",
        ))

    return shapes, annotations


app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.tags.style(".shiny-table th { text-align: left !important; }"),
        ui.h2("Weighted Average Travel Distance Analysis"),
        ui.p("Author: Jeff He"),
        ui.input_radio_buttons("mode", "Mode", ["Origin", "Destination"], inline=True),
        ui.input_select(
            "selected_sa2", "Select SA2",
            sorted(SA2_NAMES.unique()), selected="Auckland-University",
        ),
        ui.input_numeric("top_x", "Show top X SA2s by commuters", value=None, min=0),
        ui.input_radio_buttons("top_x_order", "Order", ["Most", "Least"], inline=True),
        ui.hr(),
        ui.input_action_button("update", "Update"),
        ui.input_action_button("reset",  "Reset"),
    ),
    ui.h3("Spatial Distribution"),
    ui.layout_column_wrap(
        ui.card(ui.card_header("Workplace Destinations"),  output_widget("work_map"),  full_screen=True),
        ui.card(ui.card_header("Education Destinations"),  output_widget("study_map"), full_screen=True),
        width=1/2,
    ),
    ui.hr(),
    ui.navset_card_tab(
        ui.nav_panel(
            "Summary",
            ui.card(ui.card_header("Summary Table"),         ui.output_table("summary_metrics")),
            ui.card(ui.card_header("Top 10 OD Chart"),       ui.output_plot("od_chart")),
            ui.card(ui.card_header("Commute Mode Analysis"),  ui.output_plot("commute_chart")),
        ),
        ui.nav_panel(
            "Data Tables",
            ui.layout_column_wrap(
                ui.card(ui.card_header("Work Data"),  ui.output_table("work_tbl")),
                ui.card(ui.card_header("Study Data"), ui.output_table("study_tbl")),
                width=1/2,
            ),
        ),
    ),
)


def server(input, output, session):
    def _make_map_widget():
        legend_shapes, legend_annotations = _build_legend()
        fig = go.FigureWidget()

        fig.add_trace(go.Choroplethmapbox(
            geojson=BASE_GEOJSON,
            locations=SA2_NAMES,
            z=[0] * len(SA2_NAMES),
            featureidkey="properties.SA22023__1",
            colorscale=[[0, "rgba(180,180,180,0.3)"], [1, "rgba(180,180,180,0.3)"]],
            showscale=False, hoverinfo="skip",
            marker=dict(line=dict(color="grey", width=1)),
        ))
        fig.add_trace(go.Choroplethmapbox(
            geojson={}, locations=[], z=[],
            featureidkey="properties.SA22023__1",
            colorscale=COLORSCALE,
            zmin=0, zmax=100, showscale=False,
            marker=dict(line=dict(color="#666", width=1), opacity=0.7),
        ))
        fig.add_trace(go.Scattermapbox(
            lat=[], lon=[], mode="markers",
            marker=dict(size=12, color="yellow"),
            showlegend=False,
        ))

        fig.update_layout(
            mapbox=dict(
                style="carto-positron",
                center=dict(lat=center_y, lon=center_x),
                zoom=GLOBAL_ZOOM,
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            shapes=legend_shapes,
            annotations=legend_annotations,
        )
        return fig

    work_widget  = _make_map_widget()
    study_widget = _make_map_widget()

    @render_widget
    def work_map():
        return work_widget

    @render_widget
    def study_map():
        return study_widget

    @reactive.calc
    @reactive.event(input.update)
    def filter_data():
        selected = input.selected_sa2()
        id_col   = "SA2_2023_V1_00_Destination_NAME" if input.mode() == "Destination" else "SA2_2023_V1_00_Origin_NAME"

        def _filter(df, total_col):
            f     = df[df[id_col] == selected].copy()
            total = f[total_col].sum()
            f["commute_pct"] = (f[total_col] / total * 100) if total > 0 else 0
            return f

        return _filter(work_sa2_data, "work_2023_Total_stated"), _filter(study_sa2_data, "study_2023_Total_stated")

    @reactive.calc
    @reactive.event(input.update)
    def merged_shapes():
        work_filtered, study_filtered = filter_data()
        id_col = "SA2_2023_V1_00_Origin_NAME" if input.mode() == "Destination" else "SA2_2023_V1_00_Destination_NAME"

        def _merge(filtered, total_col, old_col):
            merged = sa2shape2023.merge(
                filtered[[id_col, "commute_pct", total_col, old_col]],
                left_on="SA22023__1", right_on=id_col,
            )
            merged = merged[merged[total_col] != 0].copy()

            top_x = input.top_x()
            if top_x and top_x > 0:
                ascending = input.top_x_order() == "Least"
                merged = (
                    merged.sort_values(total_col, ascending=ascending)
                          .head(top_x)
                )
            return merged

        return (
            _merge(work_filtered,  "work_2023_Total_stated",  "work_2018_Total_stated"),
            _merge(study_filtered, "study_2023_Total_stated", "study_2018_Total_stated"),
        )

    def _update_widget(widget, shapes, count_col, old_col, lat, lon, selected_name):
        label = "Workers" if "work" in count_col else "Students"
        geojson = json.loads(shapes.to_json())
        with widget.batch_update():
            t              = widget.data[1]
            t.geojson      = geojson
            t.locations    = shapes["SA22023__1"]
            t.z            = shapes["commute_pct"]
            t.customdata   = shapes[[count_col, old_col, "commute_pct"]].values
            t.hovertemplate = (
                "<b>%{location}</b><br>"
                f"{label} 2023: %{{customdata[0]:,.0f}}<br>"
                f"{label} 2018: %{{customdata[1]:,.0f}}<br>"
                "Share: %{customdata[2]:.1f}%"
                "<extra></extra>"
            )
            widget.data[2].lat           = [lat]
            widget.data[2].lon           = [lon]
            widget.data[2].text          = [selected_name]
            widget.data[2].hovertemplate = "<b>%{text}</b> (selected)<extra></extra>"
            widget.layout.mapbox.center  = dict(lat=lat, lon=lon)
            widget.layout.mapbox.zoom    = 11

    @reactive.effect
    @reactive.event(input.update)
    def _update_maps():
        work_shapes, study_shapes = merged_shapes()
        selected_name = input.selected_sa2()
        row = sa2shape2023[sa2shape2023["SA22023__1"] == selected_name]
        lat = float(row.geometry.centroid.y.values[0])
        lon = float(row.geometry.centroid.x.values[0])

        _update_widget(work_widget,  work_shapes,  "work_2023_Total_stated",  "work_2018_Total_stated",  lat, lon, selected_name)
        _update_widget(study_widget, study_shapes, "study_2023_Total_stated", "study_2018_Total_stated", lat, lon, selected_name)

    @reactive.effect
    @reactive.event(input.reset)
    def _reset_maps():
        for widget in (work_widget, study_widget):
            with widget.batch_update():
                widget.data[1].locations        = []
                widget.data[1].z                = []
                widget.data[2].lat              = []
                widget.data[2].lon              = []
                widget.layout.mapbox.center     = dict(lat=center_y, lon=center_x)
                widget.layout.mapbox.zoom       = GLOBAL_ZOOM
        ui.update_numeric("update_numeric", value="")

    @render.table
    @reactive.event(input.update)
    def work_tbl():
        return filter_data()[0].sort_values(by="work_2023_Total_stated", ascending=False)

    @render.table
    @reactive.event(input.update)
    def study_tbl():
        return filter_data()[1].sort_values(by="study_2023_Total_stated", ascending=False)

    @render.table
    @reactive.event(input.update)
    def summary_metrics():
        work_shapes, study_shapes = merged_shapes()
        selected_name = input.selected_sa2()
 
        def calc_avg_distance(shapes, total_col):
            shapes = shapes[shapes[total_col] > 0].copy().reset_index(drop=True)
            if len(shapes) == 0:
                return None
            shapes_proj   = shapes.to_crs(epsg=2193)
            selected_proj = sa2shape2023[sa2shape2023["SA22023__1"] == selected_name].to_crs(epsg=2193)
            distances_km  = shapes_proj.geometry.centroid.distance(selected_proj.geometry.centroid.iloc[0]) / 1000
            total_people  = shapes[total_col].sum()
            return (distances_km * shapes[total_col]).sum() / total_people if total_people > 0 else None

 
        top_x     = input.top_x()
        top_x_str = f" (top {top_x} {input.top_x_order().lower()})" if top_x else ""
        def fmt_dist(val):
            return f"{val:.1f}" if val is not None else "N/A"


        return pd.DataFrame({
            "Metric": [
                f"Work Weighted Avg commute distance (km){top_x_str}",
                "Total workers",
                f"Study Weighted Avg commute distance (km){top_x_str}",
                "Total students",
            ],
            "2023": [
                fmt_dist(calc_avg_distance(work_shapes,  'work_2023_Total_stated')),
                f"{work_shapes['work_2023_Total_stated'].sum():,.0f}",
                fmt_dist(calc_avg_distance(study_shapes, 'study_2023_Total_stated')),
                f"{study_shapes['study_2023_Total_stated'].sum():,.0f}",
            ],
            "2018": [
                fmt_dist(calc_avg_distance(work_shapes,  'work_2018_Total_stated')),
                f"{work_shapes['work_2018_Total_stated'].sum():,.0f}",
                fmt_dist(calc_avg_distance(study_shapes, 'study_2018_Total_stated')),
                f"{study_shapes['study_2018_Total_stated'].sum():,.0f}",
            ],
        })



    @render.plot
    @reactive.event(input.update)
    def od_chart():
        work_filtered, study_filtered = filter_data()
        id_col = "SA2_2023_V1_00_Origin_NAME" if input.mode() == "Destination" else "SA2_2023_V1_00_Destination_NAME"
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

        def plot_bar(ax, df, title):
            df    = df[[id_col, "commute_pct"]].sort_values("commute_pct", ascending=False)
            top10 = df.head(10).sort_values("commute_pct", ascending=True)
            if len(df) > 10:
                other_row = pd.DataFrame({id_col: ["Other"], "commute_pct": [df.iloc[10:]["commute_pct"].sum()]})
                plot_df   = pd.concat([other_row, top10])
            else:
                plot_df = top10
            ax.barh(plot_df[id_col], plot_df["commute_pct"],
                    color=["#bab0ac" if n == "Other" else "#E31A1C" for n in plot_df[id_col]])
            ax.set_xlabel("% of total commuters")
            ax.set_title(title)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.1f}%"))

        label = "Origins" if input.mode() == "Destination" else "Destinations"
        plot_bar(ax1, work_filtered,  f"\nWork {label} — {input.selected_sa2()}")
        plot_bar(ax2, study_filtered, f"\nStudy {label} — {input.selected_sa2()}")
        plt.tight_layout()
        return fig

    @render.plot
    @reactive.event(input.update)
    def commute_chart():
        work_filtered, study_filtered = filter_data()

        work_mode_cols = {
            'Work at home': 'work_2023_Work_at_home',
            'Private car':  'work_2023_Drive_a_private_car_truck_or_van',
            'Company car':  'work_2023_Drive_a_company_car_truck_or_van',
            'Passenger':    'work_2023_Passenger_in_a_car_truck_van_or_company_bus',
            'Public bus':   'work_2023_Public_bus',
            'Train':        'work_2023_Train',
            'Bicycle':      'work_2023_Bicycle',
            'Walk/jog':     'work_2023_Walk_or_jog',
            'Ferry':        'work_2023_Ferry',
            'Other':        'work_2023_Other',
        }
        study_mode_cols = {
            'Study at home': 'study_2023_Study_at_home',
            'Drive':         'study_2023_Drive_a_car_truck_or_van',
            'Passenger':     'study_2023_Passenger_in_a_car_truck_or_van',
            'Bicycle':       'study_2023_Bicycle',
            'Walk/jog':      'study_2023_Walk_or_jog',
            'School bus':    'study_2023_School_bus',
            'Public bus':    'study_2023_Public_bus',
            'Train':         'study_2023_Train',
            'Ferry':         'study_2023_Ferry',
            'Other':         'study_2023_Other',
        }
        PIE_COLORS = {
            'Work at home':  '#4e79a7', 'Study at home': '#4e79a7',
            'Company car':   '#f28e2b', 'Private car':   '#e15759',
            'Drive':         '#e15759', 'Passenger':     '#ff9da7',
            'Bicycle':       '#edc948', 'Walk/jog':      '#b07aa1',
            'School bus':    '#f28e2b', 'Public bus':    '#76b7b2',
            'Train':         '#59a14f', 'Ferry':         '#9c755f',
            'Other':         '#bab0ac',
        }

        def get_totals(df, mode_cols):
            return {k: df[v].sum() for k, v in mode_cols.items() if df[v].sum() > 0}

        work_totals  = get_totals(work_filtered,  work_mode_cols)
        study_totals = get_totals(study_filtered, study_mode_cols)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
        ax1.pie(work_totals.values(),  labels=work_totals.keys(),
                colors=[PIE_COLORS[k] for k in work_totals],  autopct="%1.1f%%", startangle=90)
        ax2.pie(study_totals.values(), labels=study_totals.keys(),
                colors=[PIE_COLORS[k] for k in study_totals], autopct="%1.1f%%", startangle=90)
        ax1.set_title(f"\nWork Commute Breakdown — {input.selected_sa2()} ({input.mode()})",  fontsize=12)
        ax2.set_title(f"\nStudy Commute Breakdown — {input.selected_sa2()} ({input.mode()})", fontsize=12)
        plt.tight_layout()
        return fig


app = App(app_ui, server)