def main():
    print("Hello from gisci343-a2-auckland-origin-destination-analysis!")


if __name__ == "__main__":
    main()
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


    merged2023 = sa2shape2023.merge(work_sa2_data,"left", left_on="SA22023_V1", right_on="SA2_2023_V1_00_usual_residence_address").merge(study_sa2_data,"left", left_on="SA22023_V1", right_on="SA2_2023_V1_00_usual_residence_address")
    print(merged2023.columns)
