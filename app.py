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

work_sa2_data = pd.read_csv(_data_dir / "2023-census-main-means-of-travel-to-work-by-statistical-area.csv")
study_sa2_data = pd.read_csv(_data_dir / "2023-census-main-means-of-travel-to-education-by-statistical.csv")

sa2shape2023 = gpd.read_file(_data_dir / "aucklandsa2-2023.gpkg")
sa2shape2023.to_crs(epsg=4326, inplace=True)

base_geojson = json.loads(sa2shape2023.to_json())

center_x = sa2shape2023.geometry.centroid.x.mean()
center_y = sa2shape2023.geometry.centroid.y.mean()

COLORS = ['#67000D', '#EF3B2C', '#FC9272', '#FEE0D2', '#FFFFFF']
BREAKS = [(25, COLORS[0]), (10, COLORS[1]), (5, COLORS[2]), (1, COLORS[3]), (0, COLORS[4])]

def determine_color(pct):
    for threshold, color in BREAKS:
        if pct > threshold:
            return color
    return COLORS[-1]

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.tags.style(".shiny-table th { text-align: left !important; }"),
        ui.h2("Weighted Average Travel Distance Analysis"),
        ui.p("Author: Jeff He"),
        ui.input_radio_buttons("mode", "Mode", ["Origin", "Destination"], inline=True),
        ui.input_select("selected_sa2", "Select SA2", sorted(list(sa2shape2023["SA22023__1"].unique())), selected="Auckland-University"),
        ui.input_action_button("update", "Update"),
        ui.input_action_button("reset", "Reset"),
    ),
    ui.h3("Spatial Distribution"),
    ui.layout_column_wrap(
        ui.card(ui.card_header("Workplace Destinations"), output_widget("work_map"), full_screen=True),
        ui.card(ui.card_header("Education Destinations"), output_widget("study_map"), full_screen=True),
        width=1/2,
    ),
    ui.hr(),
    ui.navset_card_tab(
        ui.nav_panel(
            "Summary",
            ui.card(ui.card_header("Summary Table"), ui.output_table("summary_metrics")),
            ui.card(ui.card_header("Top 10 OD Chart"), ui.output_plot("od_chart")),
            ui.card(ui.card_header("Commute Mode Analysis"), ui.output_plot("commute_chart")),
        ),
        ui.nav_panel(
            "Data Tables",
            ui.layout_column_wrap(
                ui.card(ui.card_header("Work Data"), ui.output_table("work_tbl")),
                ui.card(ui.card_header("Study Data"), ui.output_table("study_tbl")),
                width=1/2,
            ),
        ),
    ),
)


def server(input, output, session):

    LEGEND_ITEMS = [(">25%", COLORS[0]), ("10–25%", COLORS[1]), ("5–10%", COLORS[2]), ("1–5%", COLORS[3]), ("<1%", COLORS[4])]

    def _legend():
        shapes, annotations = [], []
        for i, (label_text, color) in enumerate(LEGEND_ITEMS):
            y = 0.98 - i * 0.06
            shapes.append(dict(type="rect", xref="paper", yref="paper",
                               x0=0.01, x1=0.035, y0=y - 0.04, y1=y,
                               fillcolor=color, line=dict(color="grey", width=1)))
            annotations.append(dict(xref="paper", yref="paper", x=0.04, y=y - 0.02,
                                    text=label_text, showarrow=False, font=dict(size=11), xanchor="left"))
        annotations.append(dict(xref="paper", yref="paper", x=0.01, y=1.01,
                                text="<b>Commuter %</b>", showarrow=False, font=dict(size=12), xanchor="left"))
        return shapes, annotations

    def create_base_widget():
        fig = go.FigureWidget()
        
        fig.add_trace(go.Choroplethmapbox(
            geojson=base_geojson,
            locations=sa2shape2023["SA22023__1"],
            z=[0] * len(sa2shape2023),
            featureidkey="properties.SA22023__1",
            colorscale=[[0, "rgba(180,180,180,0.3)"], [1, "rgba(180,180,180,0.3)"]],
            showscale=False, hoverinfo="skip",
            marker=dict(line=dict(color="grey", width=1)),
        ))
        
        # Trace 1: Active Choropleth (Starts empty)
        fig.add_trace(go.Choroplethmapbox(
            geojson={}, locations=[], z=[],
            featureidkey="properties.SA22023__1",
            colorscale=[
                [0.00, COLORS[4]], [0.01, COLORS[4]],
                [0.01, COLORS[3]], [0.10, COLORS[3]],
                [0.10, COLORS[2]], [0.25, COLORS[2]],
                [0.25, COLORS[1]], [0.50, COLORS[1]],
                [0.50, COLORS[0]], [1.00, COLORS[0]],
            ],
            zmin=0, zmax=100, showscale=False,
            marker=dict(line=dict(color="#666", width=1), opacity=0.7),
        ))
        
        fig.add_trace(go.Scattermapbox(
            lat=[], lon=[], mode="markers",
            marker=dict(size=12, color="yellow"),
            showlegend=False,
        ))

        legend_shapes, legend_annotations = _legend()
        fig.update_layout(
            mapbox=dict(style="carto-positron", center=dict(lat=center_y, lon=center_x), zoom=GLOBAL_ZOOM),
            margin=dict(l=0, r=0, t=0, b=0),
            shapes=legend_shapes,
            annotations=legend_annotations,
        )
        return fig

    work_map_widget = create_base_widget()
    study_map_widget = create_base_widget()

    @render_widget
    def work_map():
        return work_map_widget

    @render_widget
    def study_map():
        return study_map_widget

    @reactive.calc
    @reactive.event(input.update)
    def filter_data():
        selected = input.selected_sa2()
        id_col = "SA2_2023_V1_00_Destination_NAME" if input.mode() == "Destination" else "SA2_2023_V1_00_Origin_NAME"

        work_filtered = work_sa2_data[work_sa2_data[id_col] == selected].copy()
        work_total = work_filtered["work_2023_Total_stated"].sum()
        work_filtered["commute_pct"] = (work_filtered["work_2023_Total_stated"] / work_total * 100) if work_total > 0 else 0

        study_filtered = study_sa2_data[study_sa2_data[id_col] == selected].copy()
        study_total = study_filtered["study_2023_Total_stated"].sum()
        study_filtered["commute_pct"] = (study_filtered["study_2023_Total_stated"] / study_total * 100) if study_total > 0 else 0

        return work_filtered, study_filtered

    @reactive.calc
    @reactive.event(input.update)
    def merged_shapes():
        work_filtered, study_filtered = filter_data()
        id_col = "SA2_2023_V1_00_Origin_NAME" if input.mode() == "Destination" else "SA2_2023_V1_00_Destination_NAME"

        work_shapes = sa2shape2023.merge(
            work_filtered[[id_col, "commute_pct", "work_2023_Total_stated", "work_2018_Total_stated"]],
            left_on="SA22023__1", right_on=id_col
        )
        study_shapes = sa2shape2023.merge(
            study_filtered[[id_col, "commute_pct", "study_2023_Total_stated", "study_2018_Total_stated"]],
            left_on="SA22023__1", right_on=id_col
        )
        
        work_shapes  = work_shapes[work_shapes["work_2023_Total_stated"]   != 0].copy()
        study_shapes = study_shapes[study_shapes["study_2023_Total_stated"] != 0].copy()
        
        return work_shapes, study_shapes


    # --- 3. IN-PLACE MAP UPDATES ---
    @reactive.effect
    @reactive.event(input.update)
    def update_maps_in_place():
        work_shapes, study_shapes = merged_shapes()
        selected_name = input.selected_sa2()
        
        selected_row = sa2shape2023[sa2shape2023["SA22023__1"] == selected_name]
        lat = float(selected_row.geometry.centroid.y.values[0])
        lon = float(selected_row.geometry.centroid.x.values[0])

        with work_map_widget.batch_update():
            work_map_widget.data[1].geojson = json.loads(work_shapes.to_json())
            work_map_widget.data[1].locations = work_shapes["SA22023__1"]
            work_map_widget.data[1].z = work_shapes["commute_pct"]
            work_map_widget.data[1].customdata = work_shapes[["work_2023_Total_stated", "commute_pct"]].values
            work_map_widget.data[1].hovertemplate = "<b>%{location}</b><br>Workers: %{customdata[0]:,.0f}<br>Share: %{customdata[1]:.2f}%<extra></extra>"
            
            work_map_widget.data[2].lat = [lat]
            work_map_widget.data[2].lon = [lon]
            work_map_widget.data[2].text = [selected_name]
            work_map_widget.data[2].hovertemplate = "<b>%{text}</b> (selected)<extra></extra>"
            
            work_map_widget.layout.mapbox.center = dict(lat=lat, lon=lon)
            work_map_widget.layout.mapbox.zoom = 11

        with study_map_widget.batch_update():
            study_map_widget.data[1].geojson = json.loads(study_shapes.to_json())
            study_map_widget.data[1].locations = study_shapes["SA22023__1"]
            study_map_widget.data[1].z = study_shapes["commute_pct"]
            study_map_widget.data[1].customdata = study_shapes[["study_2023_Total_stated", "commute_pct"]].values
            study_map_widget.data[1].hovertemplate = "<b>%{location}</b><br>Students: %{customdata[0]:,.0f}<br>Share: %{customdata[1]:.2f}%<extra></extra>"
            
            study_map_widget.data[2].lat = [lat]
            study_map_widget.data[2].lon = [lon]
            study_map_widget.data[2].text = [selected_name]
            study_map_widget.data[2].hovertemplate = "<b>%{text}</b> (selected)<extra></extra>"

            study_map_widget.layout.mapbox.center = dict(lat=lat, lon=lon)
            study_map_widget.layout.mapbox.zoom = 11


    @reactive.effect
    @reactive.event(input.reset)
    def reset_maps():
        # Clear active layers and reset view
        with work_map_widget.batch_update():
            work_map_widget.data[1].locations = []
            work_map_widget.data[1].z = []
            work_map_widget.data[2].lat = []
            work_map_widget.data[2].lon = []
            work_map_widget.layout.mapbox.center = dict(lat=center_y, lon=center_x)
            work_map_widget.layout.mapbox.zoom = GLOBAL_ZOOM
            
        with study_map_widget.batch_update():
            study_map_widget.data[1].locations = []
            study_map_widget.data[1].z = []
            study_map_widget.data[2].lat = []
            study_map_widget.data[2].lon = []
            study_map_widget.layout.mapbox.center = dict(lat=center_y, lon=center_x)
            study_map_widget.layout.mapbox.zoom = GLOBAL_ZOOM

    @render.table
    @reactive.event(input.update)
    def work_tbl():
        return filter_data()[0].sort_values(by="work_2023_Total_stated", ascending=False)

    @render.table
    @reactive.event(input.update)
    def study_tbl():
        return filter_data()[1].sort_values(by="study_2023_Total_stated", ascending=False)

    @render.plot
    @reactive.event(input.update)
    def od_chart():
        work_filtered, study_filtered = filter_data()
        id_col = "SA2_2023_V1_00_Origin_NAME" if input.mode() == "Destination" else "SA2_2023_V1_00_Destination_NAME"
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

        def plot_bar(ax, df, title):
            df = df[[id_col, "commute_pct"]].sort_values("commute_pct", ascending=False)
            top10 = df.head(10).sort_values("commute_pct", ascending=True)
            if len(df) > 10:
                other_row = pd.DataFrame({id_col: ["Other"], "commute_pct": [df.iloc[10:]["commute_pct"].sum()]})
                plot_df = pd.concat([other_row, top10])
            else:
                plot_df = top10
            colors = ["#bab0ac" if name == "Other" else "#E31A1C" for name in plot_df[id_col]]
            ax.barh(plot_df[id_col], plot_df["commute_pct"], color=colors)
            ax.set_xlabel("% of total commuters")
            ax.set_title(title)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.1f}%"))

        label = "Origins" if input.mode() == "Destination" else "Destinations"
        plot_bar(ax1, work_filtered,  f"\nWork {label} — {input.selected_sa2()}")
        plot_bar(ax2, study_filtered, f"\nStudy {label} — {input.selected_sa2()}")
        plt.tight_layout()
        return fig

    @render.table
    @reactive.event(input.update)
    def summary_metrics():
        work_shapes, study_shapes = merged_shapes()
        selected_name = input.selected_sa2()

        def calc_avg_distance(shapes, total_col):
            shapes = shapes[shapes[total_col] > 0].copy().reset_index(drop=True)
            if len(shapes) == 0:
                return None
            shapes_proj = shapes.to_crs(epsg=2193)
            selected_proj = sa2shape2023[sa2shape2023["SA22023__1"] == selected_name].to_crs(epsg=2193)
            selected_centroid = selected_proj.geometry.centroid.iloc[0]
            distances_km = shapes_proj.geometry.centroid.distance(selected_centroid) / 1000
            total_people = shapes[total_col].sum()
            return (distances_km * shapes[total_col]).sum() / total_people if total_people > 0 else None

        return pd.DataFrame({
            "Metric": [
                "Work Weighted Avg commute distance (km)", "Total workers",
                "Study Weighted Avg commute distance (km)", "Total students",
            ],
            "2023": [
                f"{calc_avg_distance(work_shapes,  'work_2023_Total_stated'):.1f}",
                f"{work_shapes['work_2023_Total_stated'].sum():,.0f}",
                f"{calc_avg_distance(study_shapes, 'study_2023_Total_stated'):.1f}",
                f"{study_shapes['study_2023_Total_stated'].sum():,.0f}",
            ],
            "2018": [
                f"{calc_avg_distance(work_shapes,  'work_2018_Total_stated'):.1f}",
                f"{work_shapes['work_2018_Total_stated'].sum():,.0f}",
                f"{calc_avg_distance(study_shapes, 'study_2018_Total_stated'):.1f}",
                f"{study_shapes['study_2018_Total_stated'].sum():,.0f}",
            ],
        })

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
                colors=[PIE_COLORS[k] for k in work_totals.keys()],  autopct="%1.1f%%", startangle=90)
        ax2.pie(study_totals.values(), labels=study_totals.keys(),
                colors=[PIE_COLORS[k] for k in study_totals.keys()], autopct="%1.1f%%", startangle=90)
        ax1.set_title(f"\nWork Commute Breakdown — {input.selected_sa2()} ({input.mode()})",  fontsize=12)
        ax2.set_title(f"\nStudy Commute Breakdown — {input.selected_sa2()} ({input.mode()})", fontsize=12)
        plt.tight_layout()
        return fig


app = App(app_ui, server)