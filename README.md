## 1. Motivation and Audience

### 1.1 What problem does the dashboard address?

This dashboard addresses the housing affordability problem and the phenomenon of spatial mismatch. It answers a critical question: "Are residents being pushed further away from economic or education hubs over time?". By calculating the weighted average travel distance for Statistical Area 2 (SA2) regions in Auckland, it serves as a key indicator of whether affordable housing is being supplied near high-demand employment and education hubs.  

### 1.2 Who is it for?

Two possible user for this dashboard could be property developers or council urban planners. Their goal is similar but their role and contribution is different:

Property Developers: To identify economic or education hubs where high travel distances imply a significant demand for new residential housing in closer proximity.  

Council Urban Planners: To identify areas suffering from spatial mismatch-where households are living far away from economic hubs-and to consider upzoning nearby areas for higher-density residential development. 

### 1.3 What insight does it enable?

Comparison of weighted average travel distance for work and study between 2023 and 2018 Census data, enabling a side-by-side analysis of catchment trends.


## 2. Setup and Installation
To run this dashboard locally for development or testing, follow these steps:

### 2.1 Prerequisites
- Python: 3.13+

- Install uv: pip install uv

- Install Quarto: http://quarto.org/

### 2.2 Installation Steps
Clone the repository:
```bash
# Clone the repository
git clone https://github.com/jhe482-uoa/gisci343-a2-auckland_origin_destination_analysis
cd gisci343-a2-auckland_origin_destination_analysis

# Sync dependencies and activate virtual environment
uv sync
source .venv/bin/activate
```

### 2.3 Running the App
Execute the following command to launch the Shiny app locally:

```bash
shiny run --reload app.py
```
The app will be available at http://127.0.0.1:8000. Alternatively, refer to the output for the console.

## 3. Deployment
This dashboard is deployed as a Shinylive application, which allows the entire Python environment to run locally in the user's web browser using WebAssembly. This eliminates the need for a dedicated back-end Python server.

### 3.1 Deployment Workflow
Static Export: The application was converted from a dynamic Python script into a set of static web files using the shinylive CLI:

```bash
shinylive export . docs
```
This process bundles app.py, your datasets, and the necessary web assets into a standalone directory.

Version Control: The resulting /docs folder was committed and pushed to the main branch of the GitHub repository. This folder contains the HTML, JavaScript, and WebAssembly assets required to host the app.

Hosting via GitHub Pages: The live site is hosted using GitHub Pages, configured to serve content directly from the /docs directory on the main branch.

### 3.2 Live Access
The dashboard is publicly accessible at the following URL:
https://jhe482-uoa.github.io/gisci343-a2-auckland_origin_destination_analysis/


## 4. Data Acquisition
The data for this dashboard was sourced from Stats NZ and processed using a combination of GIS software and Python scripts to ensure optimal performance and accuracy.

### 4.1 Spatial Data (Auckland SA2 Boundaries)
- Source: Statistical Area 2 2023 (Generalised) and Regional Council 2023 (Generalised) datasets from Stats NZ.  

- Processing (ArcGIS Pro): Because the national SA2 dataset does not contain region attributes, the Auckland regional boundary was used as a template. A spatial clip was performed in ArcGIS Pro to extract only the SA2 polygons located within the Auckland Region.

- File: data/aucklandsa2-2023.gpkg.  

### 4.2 Census Data (Origin-Destination Pairs)

- Source: 2023 Census "Main means of travel to work" and "Main means of travel to education" datasets.

- Processing (Python):The data_prep.py script was used to clean the raw CSV files.  

- Value Cleaning: Replaced all -999 (no data/confidentiality suppressed) values with 0 for consistent visualization.  

- Normalization: Renamed inconsistent column headers from the raw Stats NZ format into standardized Origin_NAME and Destination_NAME formats for reactive merging within the app.

- Files: data/2023-census-main-means-of-travel-to-work-by-statistical-area.csv and data/2023-census-main-means-of-travel-to-education-by-statistical.csv.  

## 5. Limitations and Future Improvements

Nothing in this world is perfect, and neither is this dashboard. Below highlights a few limitations and future improvements:

- People who "work/study from home" are also included in the calculation of the weighted average travel distance. This may introduce a skew in the actual average distance travelled. However, they are included under the assumption that they are working/studying from home because of inaccessibility (i.e., living too far away).

- The dashboard only uses the SA2 shape from 2023 for both the 2023 and 2018 average distance calculations. The 2023 SA2 shape may have slightly deviated from 2018. Meaning the actual area and the underlying population may differ, leading to false results.

- The coverage of the dashboard is only in Auckland. However, this can easily be updated to include other regions. The reason only Auckland SA2 is included is to reduce data size and improve dashboard performance.

- An additional setting to link/unlink both maps to provide further flexibility for the user.