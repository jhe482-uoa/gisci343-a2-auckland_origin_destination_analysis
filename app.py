from pathlib import Path
from shiny import App, ui, render, reactive
import pandas as pd
import matplotlib.pyplot as plt
from shinywidgets import output_widget, render_widget, register_widget
import geopandas as gpd
from ipyleaflet import GeoJSON, Map, GeoData, WidgetControl, basemaps, basemap_to_tiles, CircleMarker, link, LegendControl
from ipywidgets import HTML

GLOBAL_ZOOM = 9
SA2_ZOOM    = 13

_data_dir = Path(__file__).parent / "data"

work_sa2_data  = pd.read_csv(_data_dir / "2023-census-main-means-of-travel-to-work-by-statistical-area.csv")
study_sa2_data = pd.read_csv(_data_dir / "2023-census-main-means-of-travel-to-education-by-statistical.csv")

sa2shape2023 = gpd.read_file(_data_dir / "aucklandsa2-2023.gpkg")
sa2shape2023.to_crs(epsg=4326, inplace=True)

_projected = sa2shape2023.to_crs(epsg=2193)
center_x   = _projected.geometry.centroid.to_crs(epsg=4326).x.mean()
center_y   = _projected.geometry.centroid.to_crs(epsg=4326).y.mean()

COLORS = ['#67000D', '#EF3B2C', '#FC9272', '#FEE0D2', '#FFFFFF']

WORK_COLS = {
    "2023": {
        "total":     "work_2023_Total_stated",
        "home":      "2023_Work_at_home",
        "priv_car":  "2023_Drive_a_private_car_truck_or_van",
        "comp_car":  "2023_Drive_a_company_car_truck_or_van",
        "passenger": "2023_Passenger_in_a_car_truck_van_or_company_bus",
        "bus":       "2023_Public_bus",
        "train":     "2023_Train",
        "bicycle":   "2023_Bicycle",
        "walk":      "2023_Walk_or_jog",
        "ferry":     "2023_Ferry",
        "other":     "2023_Other",
    },
    "2018": {
        "total":     "work_2018_Total_stated",
        "home":      "2018_Work_at_home",
        "priv_car":  "2018_Drive_a_private_car_truck_or_van",
        "comp_car":  "2018_Drive_a_company_car_truck_or_van",
        "passenger": "2018_Passenger_in_a_car_truck_van_or_company_bus",
        "bus":       "2018_Public_bus",
        "train":     "2018_Train",
        "bicycle":   "2018_Bicycle",
        "walk":      "2018_Walk_or_jog",
        "ferry":     "2018_Ferry",
        "other":     "2018_Other",
    },
}
STUDY_COLS = {
    "2023": {
        "total":      "study_2023_Total_stated",
        "home":       "2023_Study_at_home",
        "drive":      "2023_Drive_a_car_truck_or_van",
        "passenger":  "2023_Passenger_in_a_car_truck_or_van",
        "bicycle":    "2023_Bicycle",
        "walk":       "2023_Walk_or_jog",
        "school_bus": "2023_School_bus",
        "bus":        "2023_Public_bus",
        "train":      "2023_Train",
        "ferry":      "2023_Ferry",
        "other":      "2023_Other",
    },
    "2018": {
        "total":      "study_2018_Total_stated",
        "home":       "2018_Study_at_home",
        "drive":      "2018_Drive_a_car_truck_or_van",
        "passenger":  "2018_Passenger_in_a_car_truck_or_van",
        "bicycle":    "2018_Bicycle",
        "walk":       "2018_Walk_or_jog",
        "school_bus": "2018_School_bus",
        "bus":        "2018_Public_bus",
        "train":      "2018_Train",
        "ferry":      "2018_Ferry",
        "other":      "2018_Other",
    },
}

WORK_LABEL_MAP = {
    'Work at home': "home",  'Private car': "priv_car", 'Company car': "comp_car",
    'Passenger':    "passenger", 'Public bus': "bus",   'Train':       "train",
    'Bicycle':      "bicycle",   'Walk/jog':   "walk",  'Ferry':       "ferry",
    'Other':        "other",
}
STUDY_LABEL_MAP = {
    'Study at home': "home",       'Drive':       "drive",      'Passenger':  "passenger",
    'Bicycle':       "bicycle",    'Walk/jog':    "walk",       'School bus': "school_bus",
    'Public bus':    "bus",        'Train':       "train",      'Ferry':      "ferry",
    'Other':         "other",
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


def determine_color(pct):
    if pct > 25: return COLORS[0]
    if pct > 10: return COLORS[1]
    if pct > 5:  return COLORS[2]
    if pct > 1:  return COLORS[3]
    return COLORS[4]


app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.tags.style(".shiny-table th { text-align: left !important; }"),
        ui.h2("OD Insight: Work & Study Travel Trends"),
        ui.p("Author: Jeff He"),
        ui.card(ui.card_header("How to use this dashboard?"), ui.p("Customize your data view using the settings below. Don't forget to click 'Update' to load the new data :D ")),
        ui.input_radio_buttons("year",  "Census Year", ["2023", "2018"], inline=True),
        ui.input_radio_buttons("mode",  "Mode",        ["Origin", "Destination"], inline=True),
        ui.input_select(
            "selected_sa2", "Select SA2",
            sorted(sa2shape2023["SA22023__1"].unique()), selected="Auckland-University",
        ),
        ui.input_numeric("top_x", "Show top SA2s by commuters", value=None, min=0),
        ui.input_radio_buttons("top_x_order", "Order", ["Most", "Least"], inline=True),
        ui.input_action_button("update", "Update"),
        ui.input_action_button("reset",  "Reset"),
    ),
    ui.h3("Spatial Distribution"),
    ui.layout_column_wrap(
        ui.card(ui.card_header("Workplace Destinations"), output_widget("work_map"),  full_screen=True),
        ui.card(ui.card_header("Education Destinations"), output_widget("study_map"), full_screen=True),
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
                ui.card(ui.card_header("Work Data"), ui.download_button("downloadWork", "Download"),  ui.output_table("work_tbl")),
                ui.card(ui.card_header("Study Data"), ui.download_button("downloadStudy", "Download"), ui.output_table("study_tbl")),
                width=1/2,
            ),
        ),
    ),
)


def server(input, output, session):
    work_geodata = GeoData(
    geo_dataframe=sa2shape2023,
    style={'color': 'grey', 'fillOpacity': 0.3, 'weight': 1},
    )
    study_geodata = GeoData(
        geo_dataframe=sa2shape2023,
        style={'color': 'grey', 'fillOpacity': 0.3, 'weight': 1},
    )

    work_m = Map(
        center=(center_y, center_x), zoom=GLOBAL_ZOOM,
        layers=(basemap_to_tiles(basemaps.CartoDB.Positron), work_geodata),
    )
    study_m = Map(
        center=(center_y, center_x), zoom=GLOBAL_ZOOM,
        layers=(basemap_to_tiles(basemaps.CartoDB.Positron), study_geodata),
    )

    link((work_m, "center"), (study_m, "center"))
    link((work_m, "zoom"),   (study_m, "zoom"))

    register_widget("work_map",  work_m)
    register_widget("study_map", study_m)



    @reactive.calc
    @reactive.event(input.update)
    def filter_data():
        selected = input.selected_sa2()
        year     = input.year()
        id_col   = "SA2_2023_V1_00_Destination_NAME" if input.mode() == "Destination" else "SA2_2023_V1_00_Origin_NAME"
        w_total  = WORK_COLS[year]["total"]
        s_total  = STUDY_COLS[year]["total"]

        def _filter(df, total_col):
            f     = df[df[id_col] == selected].copy()
            f     = f[f[total_col] > 0].copy()
            total = f[total_col].sum()
            f["commute_pct"] = (f[total_col] / total * 100) if total > 0 else 0
            return f

        return _filter(work_sa2_data, w_total), _filter(study_sa2_data, s_total)

    @reactive.calc
    @reactive.event(input.update)
    def merged_shapes():
        work_filtered, study_filtered = filter_data()
        year   = input.year()
        other  = "2018" if year == "2023" else "2023"
        id_col = "SA2_2023_V1_00_Origin_NAME" if input.mode() == "Destination" else "SA2_2023_V1_00_Destination_NAME"

        w_total = WORK_COLS[year]["total"]
        s_total = STUDY_COLS[year]["total"]
        w_other = WORK_COLS[other]["total"]
        s_other = STUDY_COLS[other]["total"]

        def merge(filtered, total_col, other_col):
            merged = sa2shape2023.merge(
                filtered[[id_col, "commute_pct", total_col, other_col]],
                left_on="SA22023__1", right_on=id_col,
            )
            merged = merged[merged[total_col] != 0].copy()
            top_x  = input.top_x()
            if top_x and top_x > 0:
                ascending = input.top_x_order() == "Least"
                merged = merged.sort_values(total_col, ascending=ascending).head(top_x)
            merged["fill_color"] = merged["commute_pct"].apply(determine_color)
            return merged

        return (
            merge(work_filtered,  w_total, w_other),
            merge(study_filtered, s_total, s_other),
        )

    @reactive.effect
    @reactive.event(input.update)
    def update_maps():
        work_shapes, study_shapes = merged_shapes()
        year          = input.year()
        other         = "2018" if year == "2023" else "2023"
        selected_name = input.selected_sa2()
        row           = sa2shape2023[sa2shape2023["SA22023__1"] == selected_name]
        lat           = float(row.geometry.centroid.y.values[0])
        lon           = float(row.geometry.centroid.x.values[0])
        w_total       = WORK_COLS[year]["total"]
        s_total       = STUDY_COLS[year]["total"]
        w_other       = WORK_COLS[other]["total"]
        s_other       = STUDY_COLS[other]["total"]

        work_html  = HTML("<i>Hover over a region</i>")
        study_html = HTML("<i>Hover over a region</i>")
        for m, h in [(work_m, work_html), (study_m, study_html)]:
            for c in [c for c in m.controls if isinstance(c, WidgetControl)]:
                m.remove_control(c)
            m.add_control(WidgetControl(widget=h, position="topright"))

        if not any(isinstance(c, LegendControl) for c in study_m.controls):
            study_m.add_control(LegendControl(
                legend={
                    ">25%":   COLORS[0], "10-25%": COLORS[1],
                    "5-10%":  COLORS[2], "1-5%":   COLORS[3], "<1%": COLORS[4],
                },
                title="Commuter %", position="bottomright",
            ))

        def make_layer(shapes, count_col, other_col, tooltip_html):
            label = "workers" if "work" in count_col.lower() else "students"
            def on_hover(feature, **kw):
                p = feature["properties"]
                tooltip_html.value = (
                    f"<b>{p['SA22023__1']}</b><br>"
                    f"{label.capitalize()} {year}: {int(p[count_col]):,}<br>"
                    f"{label.capitalize()} {other}: {int(p[other_col]):,}<br>"
                    f"Share: {p['commute_pct']:.1f}%"
                )
            layer = GeoJSON(
                data=shapes.__geo_interface__,
                hover_style={"fillColor": "cyan", "fillOpacity": 0.8},
                style_callback=lambda f: {
                    "fillColor": f["properties"]["fill_color"],
                    "color": "#666", "weight": 1, "fillOpacity": 0.7,
                },
            )
            layer.on_hover(on_hover)
            return layer

        new_work_layer  = make_layer(work_shapes,  w_total, w_other, work_html)
        new_study_layer = make_layer(study_shapes, s_total, s_other, study_html)

        work_marker  = CircleMarker(location=(lat, lon), radius=5, color="yellow", fill_color="yellow", fill_opacity=1.0)
        study_marker = CircleMarker(location=(lat, lon), radius=5, color="yellow", fill_color="yellow", fill_opacity=1.0)

        work_m.layers  = work_m.layers[:2]  + (new_work_layer,  work_marker)
        study_m.layers = study_m.layers[:2] + (new_study_layer, study_marker)

        work_m.center = (lat, lon)
        work_m.zoom   = SA2_ZOOM

    @reactive.effect
    @reactive.event(input.reset)
    def _reset_maps():
        work_m.layers  = work_m.layers[:2]
        study_m.layers = study_m.layers[:2]
        work_m.center  = (center_y, center_x)
        work_m.zoom    = GLOBAL_ZOOM

        for c in list(study_m.controls):
            if isinstance(c, LegendControl):
                study_m.remove_control(c)

        ui.update_radio_buttons("year",         selected="2023")
        ui.update_radio_buttons("mode",         selected="Origin")
        ui.update_select(       "selected_sa2", selected="Auckland-University")
        ui.update_numeric(      "top_x",        value="")
        ui.update_radio_buttons("top_x_order",  selected="Most")

        
    @render.table
    @reactive.event(input.update)
    def work_tbl():
        year = input.year()
        return filter_data()[0].sort_values(by=WORK_COLS[year]["total"], ascending=False)

    @render.table
    @reactive.event(input.update)
    def study_tbl():
        year = input.year()
        return filter_data()[1].sort_values(by=STUDY_COLS[year]["total"], ascending=False)

    @render.table
    @reactive.event(input.update)
    def summary_metrics():
        work_shapes, study_shapes = merged_shapes()
        selected_name = input.selected_sa2()
        year          = input.year()
        other         = "2018" if year == "2023" else "2023"
        w_total       = WORK_COLS[year]["total"]
        s_total       = STUDY_COLS[year]["total"]
        w_other       = WORK_COLS[other]["total"]
        s_other       = STUDY_COLS[other]["total"]

        def calc_avg_distance(shapes, total_col):
            shapes = shapes[shapes[total_col] > 0].copy().reset_index(drop=True)
            if len(shapes) == 0:
                return None
            shapes_proj   = shapes.to_crs(epsg=2193)
            selected_proj = sa2shape2023[sa2shape2023["SA22023__1"] == selected_name].to_crs(epsg=2193)
            distances_km  = shapes_proj.geometry.centroid.distance(selected_proj.geometry.centroid.iloc[0]) / 1000
            total_people  = shapes[total_col].sum()
            return (distances_km * shapes[total_col]).sum() / total_people if total_people > 0 else None

        def fmt_dist(val):
            return f"{val:.1f}" if val is not None else "N/A"

        top_x     = input.top_x()
        top_x_str = f" (top {top_x} {input.top_x_order().lower()})" if top_x else ""

        return pd.DataFrame({
            "Metric": [
                f"Work Weighted Avg commute distance (km){top_x_str}",
                "Total workers",
                f"Study Weighted Avg commute distance (km){top_x_str}",
                "Total students",
            ],
            year: [
                fmt_dist(calc_avg_distance(work_shapes,  w_total)),
                f"{work_shapes[w_total].sum():,.0f}",
                fmt_dist(calc_avg_distance(study_shapes, s_total)),
                f"{study_shapes[s_total].sum():,.0f}",
            ],
            other: [
                fmt_dist(calc_avg_distance(work_shapes,  w_other)),
                f"{work_shapes[w_other].sum():,.0f}",
                fmt_dist(calc_avg_distance(study_shapes, s_other)),
                f"{study_shapes[s_other].sum():,.0f}",
            ],
        })

    @render.plot
    @reactive.event(input.update)
    def od_chart():
        work_filtered, study_filtered = filter_data()
        id_col = "SA2_2023_V1_00_Origin_NAME" if input.mode() == "Destination" else "SA2_2023_V1_00_Destination_NAME"
        year   = input.year()
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
            ax.set_xlabel("% of total commuters\n")
            ax.set_title(title)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.1f}%"))

        label = "Origins" if input.mode() == "Destination" else "Destinations"
        plot_bar(ax1, work_filtered[work_filtered["commute_pct"]  != 0], f"\nWork {label} — {input.selected_sa2()} ({year})")
        plot_bar(ax2, study_filtered[study_filtered["commute_pct"] != 0], f"\nStudy {label} — {input.selected_sa2()} ({year})")
        plt.tight_layout()
        return fig

    @render.plot
    @reactive.event(input.update)
    def commute_chart():
        work_filtered, study_filtered = filter_data()
        sa2  = input.selected_sa2()
        mode = input.mode()

        def build_mode_cols(cols_dict, label_map):
            return {label: cols_dict[key] for label, key in label_map.items()}

        def get_totals(df, mode_cols):
            return {k: df[v].sum() for k, v in mode_cols.items() if df[v].sum() > 0}

        fig, axes = plt.subplots(2, 2, figsize=(14, 12))

        plots = [
            (axes[0, 0], work_filtered,  build_mode_cols(WORK_COLS["2023"],  WORK_LABEL_MAP),  f"\nWork 2023 — {sa2} ({mode})"),
            (axes[1, 0], work_filtered,  build_mode_cols(WORK_COLS["2018"],  WORK_LABEL_MAP),  f"\nWork 2018 — {sa2} ({mode})"),
            (axes[0, 1], study_filtered, build_mode_cols(STUDY_COLS["2023"], STUDY_LABEL_MAP), f"\nStudy 2023 — {sa2} ({mode})"),
            (axes[1, 1], study_filtered, build_mode_cols(STUDY_COLS["2018"], STUDY_LABEL_MAP), f"\nStudy 2018 — {sa2} ({mode})"),
        ]

        for ax, df, mode_cols, title in plots:
            totals = get_totals(df, mode_cols)
            if totals:
                ax.pie(totals.values(), labels=totals.keys(),
                       colors=[PIE_COLORS[k] for k in totals],
                       autopct="%1.1f%%", startangle=90)
            else:
                ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(title, fontsize=12)

        plt.tight_layout()
        return fig

    @render.download(
    filename=lambda: f"work_data_{input.selected_sa2()}_{input.year()}.csv",
    media_type="text/csv",
)
    async def downloadWork():
        yield filter_data()[0].sort_values(by=WORK_COLS[input.year()]["total"], ascending=False).to_csv(index=False)

    @render.download(
        filename=lambda: f"study_data_{input.selected_sa2()}_{input.year()}.csv",
        media_type="text/csv",
    )
    async def downloadStudy():
        yield filter_data()[1].sort_values(by=STUDY_COLS[input.year()]["total"], ascending=False).to_csv(index=False)


app = App(app_ui, server)