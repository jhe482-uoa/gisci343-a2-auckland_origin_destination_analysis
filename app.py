from shiny import App, ui, render, reactive
import pandas as pd
import matplotlib.pyplot as plt
from shinywidgets import output_widget, render_widget
import geopandas as gpd
from ipyleaflet import GeoJSON, Map, GeoData, LayersControl, basemaps, basemap_to_tiles, display, CircleMarker


work_sa2_data = pd.read_csv(r"data/2023-census-main-means-of-travel-to-work-by-statistical-area.csv")
study_sa2_data = pd.read_csv(r"data/2023-census-main-means-of-travel-to-education-by-statistical.csv")
path = r"data/statistical-area-2-2023-generalised-epsg4326.gpkg"

sa2shape2023 = gpd.read_file(path)


# merged2023 = sa2shape2023.merge(work_sa2_data,"left", left_on="SA22023_V1", right_on="SA2_2023_V1_00_usual_residence_address").merge(study_sa2_data,"left", left_on="SA22023_V1", right_on="SA2_2023_V1_00_usual_residence_address")
center_x = sa2shape2023.geometry.centroid.x.mean()
center_y = sa2shape2023.geometry.centroid.y.mean()


app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.h2("Title"),
        ui.p("Author: Jeff He"),
        ui.input_radio_buttons("mode", "Mode", ["Leaving From", "Coming Into"], inline=True),
        ui.input_select("selected_sa2", "Select SA2", sorted(list(sa2shape2023["SA22023__1"].unique()))),
        ui.input_action_button("update", "Update"),
        ui.input_action_button("reset", "Reset")
        ),
    ui.navset_card_tab(
        ui.nav_panel(
            "Work",
            ui.h2("Maps"),
            output_widget("work_map"),
            output_widget("study_map"),
            ui.output_table("work_tbl"),
            ui.output_table("study_tbl")
        ),
        ui.nav_panel(
            "Test",
            ui.h2("Maps"),
            
        )
    )
    )

def server(input, output, session):
    @reactive.calc
    @reactive.event(input.update)
    def filter():
        selected = input.selected_sa2()
        id_col = "SA2_2023_V1_00_Destination_NAME" if input.mode() == "Leaving From" else "SA2_2023_V1_00_Origin_NAME"
        work_filtered = work_sa2_data[work_sa2_data[id_col] == selected]
        work_total = work_filtered["work_2023_Total_stated"].sum()
        work_filtered["commute_pct"] = (work_filtered["work_2023_Total_stated"] / work_total) * 100 if work_total > 0 else 0
        study_filtered = study_sa2_data[study_sa2_data[id_col] == selected]
        study_total = study_filtered["study_2023_Total_stated"].sum()
        study_filtered["commute_pct"] = (study_filtered["study_2023_Total_stated"] / study_total) * 100 if study_total > 0 else 0
        print(work_filtered, study_filtered)
        return (work_filtered, study_filtered)



    @render.text
    def summary():
        df = filter()
        if len(df) == 0:
            return "No suburbs match the current filter."
        return f"{len(df)} suburbs, mean income ${df['median_income'].mean():,.0f}."

    @reactive.Effect
    @reactive.event(input.reset)
    def reset():

        work_map.widget.layers = work_map.widget.layers[:2]
        
        work_map.widget.center = (center_y, center_x)
        work_map.widget.zoom = 5

    @render.table
    @reactive.event(input.update)
    def work_tbl():
        return filter()[0][["SA2_2023_V1_00_Origin_CODE", "SA2_2023_V1_00_Destination_CODE","work_2018_Total_stated", "work_2023_Total_stated"]]
    
    @render.table
    @reactive.event(input.update)
    def study_tbl():
        return filter()[1][["SA2_2023_V1_00_Origin_CODE", "SA2_2023_V1_00_Destination_CODE","study_2018_Total_stated", "study_2023_Total_stated"]]

    @render_widget
    def work_map():
        new_tiles = basemap_to_tiles(basemaps.CartoDB.Positron)
        
        geo_data = GeoData(
            geo_dataframe=sa2shape2023, 
            style={'color': 'grey', 'fillOpacity': 0.3, 'weight': 1},
            name='NZ Regions'
        )

        m = Map(center=(center_y, center_x), zoom=5, layers=(new_tiles,))
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

        m = Map(center=(center_y, center_x), zoom=5, layers=(new_tiles,))
        m.add_layer(geo_data)

        return m


    @reactive.Effect
    @reactive.event(input.update)
    def map_update():
        selected_sa2 = sa2shape2023[sa2shape2023["SA22023__1"] == input.selected_sa2()]
        lat = selected_sa2.geometry.centroid.y.values[0]
        lon = selected_sa2.geometry.centroid.x.values[0]

        work_filtered, study_filtered = filter()
        id_col =  "SA2_2023_V1_00_Origin_NAME" if input.mode() == "Leaving From" else "SA2_2023_V1_00_Destination_NAME"
        
        work_map_shapes = sa2shape2023.merge(work_filtered[[id_col, "commute_pct"]], 
                                        left_on="SA22023__1", 
                                        right_on=id_col)
        study_map_shapes = sa2shape2023.merge(study_filtered[[id_col, "commute_pct"]], 
                                        left_on="SA22023__1", 
                                        right_on=id_col)
        
        def determine_color(pct):
            if pct > 20: return '#800026' 
            if pct > 10: return '#BD0026'
            if pct > 5:  return '#E31A1C'
            if pct > 2:  return '#FC4E2A'
            return '#FFEDA0'

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
        work_map.widget.zoom = 8

        study_map.widget.add_layer(new_study_layer)
        study_map.widget.add_layer(marker)
        study_map.widget.center = (lat, lon)
        study_map.widget.zoom = 8

    # @render.plot
    # def chart():
    #     df = filter()
    #     fig, ax = plt.subplots(figsize=(7, 4))
    #     ax.barh(df["suburb"], df["median_income"], color="steelblue")
    #     ax.set_xlabel("Median income (NZ$)")
    #     ax.set_title("Median income by suburb")
    #     plt.tight_layout()
    #     return fig

app = App(app_ui, server)