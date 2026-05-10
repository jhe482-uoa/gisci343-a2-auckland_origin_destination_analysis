import pandas as pd

work_sa2_data = pd.read_csv(r"data\2023-census-main-means-of-travel-to-work-by-statistical-area.csv")
study_sa2_data = pd.read_csv(r"data\2023-census-main-means-of-travel-to-education-by-statistical.csv")

work_sa2_data.replace(-999, 0, inplace=True)
study_sa2_data.replace(-999, 0, inplace=True)

work_sa2_data.rename(columns={
    'SA22023_V1_00_NAME_workplace_address':       'SA2_2023_V1_00_Destination_NAME',
    'SA22023_V1_00_NAME_usual_residence_address': 'SA2_2023_V1_00_Origin_NAME',
    '2023_Total_stated': 'work_2023_Total_stated',
    '2018_Total_stated': 'work_2018_Total_stated'
}, inplace=True)

study_sa2_data.rename(columns={
    'SA22023_V1_00_NAME_educational_institution_address': 'SA2_2023_V1_00_Destination_NAME',
    'SA22023_V1_00_NAME_usual_residence_address':         'SA2_2023_V1_00_Origin_NAME',
    '2023_Total_stated': 'study_2023_Total_stated',
    '2018_Total_stated': 'study_2018_Total_stated'
}, inplace=True)


work_sa2_data.to_csv(r"data\2023-census-main-means-of-travel-to-work-by-statistical-area.csv")
study_sa2_data.to_csv(r"data\2023-census-main-means-of-travel-to-education-by-statistical.csv")

print("Done :D")
"""aucklandsa2-2023.gpkg is clipped through ArcGIS Pro. It is a trimmed version of Statistical Area 2 2023 (generalised), clipped by Regional Council 2023 (generalised).
 Which can all be found on Stats NZ. It is clipped through ArcGIS Pro given the complexity of the task. """