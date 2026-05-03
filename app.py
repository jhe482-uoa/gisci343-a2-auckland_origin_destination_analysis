from shiny import App, ui, render, reactive
import pandas as pd
import matplotlib.pyplot as plt
from shinywidgets import output_widget, render_widget
import geopandas as gpd
from ipyleaflet import GeoJSON, Map, GeoData, LayersControl, ZoomControl, basemaps, basemap_to_tiles, display, CircleMarker, link, LegendControl

GLOBAL_ZOOM = 9
SA2_ZOOM = 13

work_sa2_data = pd.read_csv(r"data/2023-census-main-means-of-travel-to-work-by-statistical-area.csv")
study_sa2_data = pd.read_csv(r"data/2023-census-main-means-of-travel-to-education-by-statistical.csv")

sa2shape2023 = gpd.read_file(r"data/aucklandsa2-2023.gpkg")
sa2shape2023.to_crs(epsg=4326, inplace=True)

center_x = sa2shape2023.geometry.centroid.x.mean()
center_y = sa2shape2023.geometry.centroid.y.mean()


app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.tags.style("""
        .shiny-table th { text-align: left !important; }
        """),
        ui.h2("Weighted Average Travel Distance Analysis"),
        ui.p("Author: Jeff He"),
        ui.input_radio_buttons("mode", "Mode", ["Origin", "Destination"], inline=True),
        ui.input_select("selected_sa2", "Select SA2", sorted(list(sa2shape2023["SA22023__1"].unique())),selected="Auckland-University"),
        ui.input_action_button("update", "Update"),
        ui.input_action_button("reset", "Reset")
        ),
    ui.h3("Spatial Distribution"),
    ui.layout_column_wrap(
        ui.card(
            ui.card_header("Workplace Destinations"),
            output_widget("work_map"),
            full_screen=True,
            
        ),
        ui.card(
            ui.card_header("Education Destinations"),
            output_widget("study_map"),
            full_screen=True,
        ),
        width=1/2,
    ),

    ui.hr(),

    ui.navset_card_tab(
        ui.nav_panel(
            "Summary",
            ui.card(
                ui.card_header("Summary Table"),
                ui.output_table("summary_metrics"),
            ),
            ui.card(
                ui.card_header("Top 10 OD Chart"),
                ui.output_plot("od_chart")
            ),
            ui.card(
                ui.card_header("Commute Mode Analysis"),
                ui.output_plot("commute_chart") 
            )
        ),
        ui.nav_panel(
            "Data Tables",
            ui.layout_column_wrap(
                ui.card(ui.card_header("Work Data"), ui.output_table("work_tbl")),
                ui.card(ui.card_header("Study Data"), ui.output_table("study_tbl")),
                width=1/2
            )
        ),

    )
    )

def server(input, output, session):
    @reactive.calc
    @reactive.event(input.update)
    def filter():
        selected = input.selected_sa2()
        id_col = "SA2_2023_V1_00_Destination_NAME" if input.mode() == "Destination" else "SA2_2023_V1_00_Origin_NAME"
        
        work_filtered = work_sa2_data[work_sa2_data[id_col] == selected]
        work_total = work_filtered["work_2023_Total_stated"].sum()
        work_filtered["commute_pct"] = (work_filtered["work_2023_Total_stated"] / work_total) * 100 if work_total > 0 else 0

        study_filtered = study_sa2_data[study_sa2_data[id_col] == selected]
        study_total = study_filtered["study_2023_Total_stated"].sum()
        study_filtered["commute_pct"] = (study_filtered["study_2023_Total_stated"] / study_total) * 100 if study_total > 0 else 0
        # print(work_filtered, study_filtered)
        return (work_filtered, study_filtered)

    @render.plot
    @reactive.event(input.update)
    def od_chart():
        work_filtered, study_filtered = filter()
        id_col = "SA2_2023_V1_00_Origin_NAME" if input.mode() == "Destination" else "SA2_2023_V1_00_Destination_NAME"

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

        def plot_bar(ax, df, title):
            df = df[[id_col, "commute_pct"]].sort_values("commute_pct", ascending=False)
            top10 = df.head(10).sort_values("commute_pct", ascending=True)
            if len(df) > 10:
                other_pct = df.iloc[10:]["commute_pct"].sum()
                other_row = pd.DataFrame({id_col: ["Other"], "commute_pct": [other_pct]})
                plot_df = pd.concat([other_row, top10])  # Other always at bottom
            else:
                plot_df = top10
            colors = ['#bab0ac' if name == "Other" else '#E31A1C' for name in plot_df[id_col]]
            ax.barh(plot_df[id_col], plot_df["commute_pct"], color=colors)
            ax.set_xlabel("% of total commuters")
            ax.set_title(title)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.1f}%"))

        label = "Origins" if input.mode() == "Destination" else "Destinations"

        plot_bar(ax1, work_filtered, f"\nWork {label} — {input.selected_sa2()}")
        plot_bar(ax2, study_filtered, f"\nStudy {label} — {input.selected_sa2()}")

        plt.tight_layout()
        return fig

    @reactive.Effect
    @reactive.event(input.reset)
    def reset():
        work_map.widget.layers = work_map.widget.layers[:2]
        work_map.widget.center = (center_y, center_x)
        work_map.widget.zoom = GLOBAL_ZOOM
        for control in study_map.widget.controls:
            if isinstance(control, LegendControl):
                study_map.widget.remove_control(control)

    @render.table
    @reactive.event(input.update)
    def work_tbl():
        return filter()[0].sort_values(by='work_2023_Total_stated', ascending=False)    # [["SA2_2023_V1_00_Origin_NAME", "work_2018_Total_stated", "work_2023_Total_stated"]] # [["SA2_2023_V1_00_Destination_NAME", "work_2018_Total_stated", "work_2023_Total_stated"]]

    @render.table
    @reactive.event(input.update)
    def study_tbl():
        return filter()[1].sort_values(by='study_2023_Total_stated', ascending=False)   # [["SA2_2023_V1_00_Origin_NAME", "study_2018_Total_stated", "study_2023_Total_stated"]] # [["SA2_2023_V1_00_Destination_NAME", "study_2018_Total_stated", "study_2023_Total_stated"]]

    @render_widget
    def work_map():
        new_tiles = basemap_to_tiles(basemaps.CartoDB.Positron)
        
        geo_data = GeoData(
            geo_dataframe=sa2shape2023, 
            style={'color': 'grey', 'fillOpacity': 0.3, 'weight': 1},
            name='NZ Regions'
        )

        m = Map(center=(center_y, center_x), zoom=GLOBAL_ZOOM, layers=(new_tiles,))
        m.add_layer(geo_data)
  

        return m
    
    @render_widget
    def study_map():
        new_tiles = basemap_to_tiles(basemaps.CartoDB.Positron)
        
        geo_data = GeoData(
            geo_dataframe=sa2shape2023, 
            style={'color': 'grey', 'fillOpacity': 0.3, 'weight': 1},
            name='NZ Regions'
        )

        m = Map(center=(center_y, center_x), zoom=GLOBAL_ZOOM, layers=(new_tiles,))
        m.add_layer(geo_data)
        

        link((work_map.widget, "center"), (m, "center"))
        link((work_map.widget, "zoom"), (m, "zoom"))
        return m
    
    @reactive.calc
    @reactive.event(input.update)
    def merged_shapes():
        work_filtered, study_filtered = filter()
        id_col = "SA2_2023_V1_00_Origin_NAME" if input.mode() == "Destination" else "SA2_2023_V1_00_Destination_NAME"

        work_shapes = sa2shape2023.merge(
            work_filtered[[id_col, "commute_pct", "work_2023_Total_stated", "work_2018_Total_stated"]],
            left_on="SA22023__1", right_on=id_col
        )
        study_shapes = sa2shape2023.merge(
            study_filtered[[id_col, "commute_pct", "study_2023_Total_stated", "study_2018_Total_stated"]],
            left_on="SA22023__1", right_on=id_col
        )
        return work_shapes, study_shapes    

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
                "Work Weighted Avg commute distance (km)",
                "Total workers",
                "Study Weighted Avg commute distance (km)",
                "Total students"
            ],
            "2023": [
                f"{calc_avg_distance(work_shapes, 'work_2023_Total_stated'):.1f}",
                f"{work_shapes['work_2023_Total_stated'].sum():,.0f}",
                f"{calc_avg_distance(study_shapes, 'study_2023_Total_stated'):.1f}",
                f"{study_shapes['study_2023_Total_stated'].sum():,.0f}",
            ],
            "2018": [
                f"{calc_avg_distance(work_shapes, 'work_2018_Total_stated'):.1f}",
                f"{work_shapes['work_2018_Total_stated'].sum():,.0f}",
                f"{calc_avg_distance(study_shapes, 'study_2018_Total_stated'):.1f}",
                f"{study_shapes['study_2018_Total_stated'].sum():,.0f}",
            ]
        })

    @reactive.Effect
    @reactive.event(input.update)
    def map_update():
        selected_sa2 = sa2shape2023[sa2shape2023["SA22023__1"] == input.selected_sa2()]
        lat = selected_sa2.geometry.centroid.y.values[0]
        lon = selected_sa2.geometry.centroid.x.values[0]
        
        work_map_shapes, study_map_shapes = merged_shapes()
        
        COLORS = [ '#67000D','#EF3B2C', '#FC9272','#FEE0D2', '#FFFFFF',
        ]

        def determine_color(pct):
            if pct > 50: return COLORS[0]
            if pct > 25: return COLORS[1]
            if pct > 15: return COLORS[2]
            if pct > 5:  return COLORS[3]
            return COLORS[4]

        if not any(isinstance(control, LegendControl) for control in study_map.widget.controls):
            legend = LegendControl(
                legend={
                    ">50%":  COLORS[0],
                    "25-50%": COLORS[1],
                    "15-25%": COLORS[2],
                    "5-15%":  COLORS[3],
                    "<5%":    COLORS[4],
                },
                title="Commuter %",
                position="bottomright"
            )
            study_map.widget.add_control(legend)


        work_map_shapes['fill_color'] = work_map_shapes['commute_pct'].apply(determine_color)
        study_map_shapes['fill_color'] = study_map_shapes['commute_pct'].apply(determine_color)


        new_work_layer = GeoJSON(
            data=work_map_shapes.__geo_interface__,
            hover_style={'fillColor': 'cyan', 'fillOpacity': 0.8},
            style_callback=lambda feature: {
                'fillColor': feature['properties']['fill_color'],
                'color': '#666666',
                'weight': 1,
                'fillOpacity': 0.7
            },
        )
        new_study_layer = GeoJSON(
            data=study_map_shapes.__geo_interface__,
            hover_style={'fillColor': 'cyan', 'fillOpacity': 0.8},
            style_callback=lambda feature: {
                'fillColor': feature['properties']['fill_color'],
                'color': '#666666',
                'weight': 1,
                'fillOpacity': 0.7
            },
        )
        

        marker = CircleMarker(
            location=(lat, lon), 
            radius=5, 
            color="yellow", 
            fill_color="yellow", 
            fill_opacity=1.0,
            name="Selected Centre"
        )
        if len(work_map.widget.layers) > 2:
            work_map.widget.layers = work_map.widget.layers[:2]
            study_map.widget.layers = study_map.widget.layers[:2]
        
        work_map.widget.add_layer(new_work_layer)
        work_map.widget.add_layer(marker)
        work_map.widget.center = (lat, lon)
        work_map.widget.zoom = SA2_ZOOM

        study_map.widget.add_layer(new_study_layer)
        study_map.widget.add_layer(marker)
        # study_map.widget.center = (lat, lon)
        # study_map.widget.zoom = SA2_ZOOM

    @render.plot
    @reactive.event(input.update)
    def commute_chart():
        work_filtered, study_filtered = filter()

        work_mode_cols = {
            'Work at home': 'work_2023_Work_at_home',
            'Private car': 'work_2023_Drive_a_private_car_truck_or_van',
            'Company car': 'work_2023_Drive_a_company_car_truck_or_van',
            'Passenger': 'work_2023_Passenger_in_a_car_truck_van_or_company_bus',
            'Public bus': 'work_2023_Public_bus',
            'Train': 'work_2023_Train',
            'Bicycle': 'work_2023_Bicycle',
            'Walk/jog': 'work_2023_Walk_or_jog',
            'Ferry': 'work_2023_Ferry',
            'Other': 'work_2023_Other',
        }
        study_mode_cols = {
            'Study at home': 'study_2023_Study_at_home',
            'Drive': 'study_2023_Drive_a_car_truck_or_van',
            'Passenger': 'study_2023_Passenger_in_a_car_truck_or_van',
            'Bicycle': 'study_2023_Bicycle',
            'Walk/jog': 'study_2023_Walk_or_jog',
            'School bus': 'study_2023_School_bus',
            'Public bus': 'study_2023_Public_bus',
            'Train': 'study_2023_Train',
            'Ferry': 'study_2023_Ferry',
            'Other': 'study_2023_Other',
        }

        def get_totals(filtered_df, mode_cols):
            totals = {label: filtered_df[col].sum() for label, col in mode_cols.items()}
            # Drop zero values so they don't clutter the pie
            return {k: v for k, v in totals.items() if v > 0}

        COLORS = {
            'Work at home': '#4e79a7',
            'Study at home': '#4e79a7',
            'Company car':   '#f28e2b',
            'Private car':   '#e15759',
            'Drive':         '#e15759', # Equivalent of Private car from work data
            'Passenger':     '#ff9da7',
            'Bicycle':       '#edc948',
            'Walk/jog':      '#b07aa1',
            'School bus':    '#f28e2b',
            'Public bus':    '#76b7b2',
            'Train':         '#59a14f',
            'Ferry':         '#9c755f',
            'Other':         '#bab0ac',
        }

        work_totals = get_totals(work_filtered, work_mode_cols)
        study_totals = get_totals(study_filtered, study_mode_cols)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

        ax1.pie(
            work_totals.values(),
            labels=work_totals.keys(),
            colors=[COLORS[k] for k in work_totals.keys()],
            autopct='%1.1f%%',
            startangle=90
        )


        ax1.set_title(f"\nWork Commute Breakdown {input.selected_sa2()} ({input.mode()})", fontsize=12)

        ax2.pie(
            study_totals.values(),
            labels=study_totals.keys(),
            colors=[COLORS[k] for k in study_totals.keys()],
            autopct='%1.1f%%',
            startangle=90
        )        
        ax2.set_title(f"\nStudy Commute Breakdown {input.selected_sa2()} ({input.mode()})", fontsize=12)

        plt.tight_layout()
        return fig

app = App(app_ui, server)