from shiny import App, ui, render, reactive
import pandas as pd
import matplotlib.pyplot as plt
from shinywidgets import output_widget, render_widget
import geopandas as gpd
from ipyleaflet import Map, GeoData, LayersControl, basemaps, basemap_to_tiles, display, CircleMarker


# Inline sample data (replace with real data next week)
sa2_data = pd.read_csv(r"data/2023-census-main-means-of-travel-to-work-by-statistical-area.csv")
sa2_data.replace(-999,0,inplace=True)
# sa2_data = sa2_data[(sa2_data["2023_Total_stated"] > 0) | (sa2_data["2018_Total_stated"] > 0)]

path = r"data/statistical-area-2-2023-generalised-epsg4326.gpkg"

sa2shape2023 = gpd.read_file(path)

# sa2shape2023 = sa2shape2023.to_crs(epsg=4326)
# sa2shape2023['SA22023_V1'] = sa2shape2023['SA22023_V1'].astype(int)

merged2023 = sa2shape2023.merge(sa2_data,"left", left_on="SA22023_V1", right_on="SA22023_V1_00_usual_residence_address")
# print(merged2023)
center_x = sa2shape2023.geometry.centroid.x.mean()
center_y = sa2shape2023.geometry.centroid.y.mean()



app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.h2("Title"),
        ui.p("Author: Jeff He"),
        ui.input_radio_buttons("mode", "Mode", ["Leaving From", "Coming Into"], inline=True),
        ui.input_select("selected_sa2", "Select SA2", sorted(list(sa2_data["SA22023_V1_00_NAME_ASCII_usual_residence_address"].unique()))),
        ui.input_action_button("update", "Update"),
        ui.input_action_button("reset", "Reset")
        ),
    ui.navset_card_tab(
        ui.nav_panel(
            "Work",
            ui.h2("Maps"),
            output_widget("map_display"),
            ui.output_table("tbl")
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
        if input.mode() == "Leaving From":
            # print(input.selected_sa2())
            filtered = merged2023[merged2023["SA22023_V1_00_NAME_ASCII_usual_residence_address"] == input.selected_sa2()]
            return filtered
        else:
            # print(input.selected_sa2())
            filtered = merged2023[merged2023["SA22023_V1_00_NAME_ASCII_workplace_address"] == input.selected_sa2()]
            return filtered

    @render.text
    def summary():
        df = filter()
        if len(df) == 0:
            return "No suburbs match the current filter."
        return f"{len(df)} suburbs, mean income ${df['median_income'].mean():,.0f}."

    @reactive.Effect
    @reactive.event(input.reset)
    def _():
        if len(map_display.widget.layers) > 2:
            map_display.widget.layers = map_display.widget.layers[:2]
        
        map_display.widget.center = (center_y, center_x)
        map_display.widget.zoom = 5

    @render.table
    @reactive.event(input.update)
    def tbl():
        return filter()[["SA22023_V1_00_NAME_ASCII_usual_residence_address", "SA22023_V1_00_NAME_ASCII_workplace_address","2018_Total_stated", "2023_Total_stated"]]


    @render_widget
    def map_display():
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
    def _():
        selected_sa2 = sa2shape2023[sa2shape2023["SA22023__1"] == input.selected_sa2()]
        lat = selected_sa2.geometry.centroid.y.values[0]
        lon = selected_sa2.geometry.centroid.x.values[0]
        
        marker = CircleMarker(
            location=(lat, lon), 
            radius=5, 
            color="yellow", 
            fill_color="yellow", 
            fill_opacity=1.0,
            name="Selected Centre"
        )
        filtered = filter()
        if input.mode() == "Leaving From":
            target_ids = filtered["SA22023_V1_00_workplace_address"].unique()
            filtered = merged2023[merged2023["SA22023_V1"].isin(target_ids)].drop_duplicates(subset="SA22023_V1")

        new_layer = GeoData(
            geo_dataframe=filtered,
            style={'color': 'red', 'fillOpacity': 0.5},
            name="Filtered Results"
        )
        
        if len(map_display.widget.layers) > 2:
            map_display.widget.layers = map_display.widget.layers[:2]
        
        map_display.widget.add_layer(new_layer)
        map_display.widget.add_layer(marker)
        map_display.widget.center = (lat, lon)
        map_display.widget.zoom = 8

    @render.plot
    def chart():
        df = filter()
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.barh(df["suburb"], df["median_income"], color="steelblue")
        ax.set_xlabel("Median income (NZ$)")
        ax.set_title("Median income by suburb")
        plt.tight_layout()
        return fig

app = App(app_ui, server)