from shiny import App, ui, render, reactive
import pandas as pd
import matplotlib.pyplot as plt
from shinywidgets import output_widget, render_widget
import geopandas as gpd
from ipyleaflet import Map, GeoData, LayersControl, basemaps, basemap_to_tiles, display


# Inline sample data (replace with real data next week)
sa2_data = pd.read_csv(r"data\statsnz-2023-census-main-means-of-travel-to-work-by-statistical-area-CSV\2023-census-main-means-of-travel-to-work-by-statistical-area.csv")
sa2_data.replace(-999,0,inplace=True)
sa2_data = sa2_data[(sa2_data["2023_Total_stated"] > 0) | (sa2_data["2018_Total_stated"] > 0)]

path = r"data\statsnz-statistical-area-2-2023-generalised-SHP\statistical-area-2-2023-generalised.shp"
sa2shape2023 = gpd.read_file(path)
new_tiles = basemap_to_tiles(basemaps.CartoDB.Positron)

sa2shape2023 = sa2shape2023.to_crs(epsg=4326)
center_x = sa2shape2023.geometry.centroid.x.mean()
center_y = sa2shape2023.geometry.centroid.y.mean()
map = Map(center=(center_y, center_x), zoom=5, layers=(new_tiles, ))

geo_data = GeoData(geo_dataframe=sa2shape2023, style={'color': 'white', 'fillOpacity': 0.3, 'weight': 1},
    name='NZ Regions')

map.add_layer(geo_data)
display(map)


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
            "Work + Education",
            ui.h2("Maps"),
            # output_widget("both_display"),
            ui.output_table("tbl")
        ),
        ui.nav_panel(
            "Test",
            ui.h2("Maps"),
            output_widget("map_display"),
        )
    )
    )

def server(input, output, session):

    @reactive.calc
    @reactive.event(input.update)
    def filter():
        if input.mode() == "Leaving From":
            filtered = sa2_data[sa2_data["SA22023_V1_00_NAME_ASCII_usual_residence_address"] == input.selected_sa2()]
            return filtered
        else:
            filtered = sa2_data[sa2_data["SA22023_V1_00_NAME_ASCII_workplace_address"] == input.selected_sa2()]
            return filtered

    @render.text
    def summary():
        df = filter()
        if len(df) == 0:
            return "No suburbs match the current filter."
        return f"{len(df)} suburbs, mean income ${df['median_income'].mean():,.0f}."

    @render.table
    def tbl():
        return filter()


    @render_widget
    def map_display():
        m = Map(center=(-36.8485, 174.7633), zoom=10, basemap=basemaps.CartoDB.Positron)
        return m

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