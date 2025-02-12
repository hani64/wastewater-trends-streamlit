import os
import pandas as pd
import streamlit as st

from utils import get_cursor, FETCH_LATEST_MEASURES_QUERY


def app():
    if "df_latest_obs" not in st.session_state:
        with get_cursor() as cursor:
            cursor.execute(FETCH_LATEST_MEASURES_QUERY)
            rows = [row.asDict() for row in cursor.fetchall()]
            st.session_state.df_latest_obs = pd.DataFrame(rows)

    # Filter the dataframe based on site names
    sites = st.session_state.df_latest_obs["name"].unique()
    sites = ["All Sites"] + list(sites)
    selected_sites = st.multiselect(
        "Select sites to filter by:", sites, default=["All Sites"]
    )
    # Filter the dataframe based on the selected measures
    measures = st.session_state.df_latest_obs["measure"].unique()
    selected_measures = st.multiselect(
        "Select measures to filter by:", measures, default=measures
    )
    # Filter the dataframe based on the selected measures and sites
    if "All Sites" in selected_sites:
        filtered_df = st.session_state.df_latest_obs[
            st.session_state.df_latest_obs["measure"].isin(selected_measures)
        ]
    else:
        filtered_df = st.session_state.df_latest_obs[
            st.session_state.df_latest_obs["measure"].isin(selected_measures)
            & st.session_state.df_latest_obs["name"].isin(selected_sites)
        ]

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "latestObsDT": st.column_config.DatetimeColumn(
                format="YYYY-MM-DD",
            ),
            "previousObsDT": st.column_config.DatetimeColumn(
                format="YYYY-MM-DD",
            ),
        },
    )


st.set_page_config(
    page_title="Latest Measures",
    page_icon="🆕",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🆕 Latest Measures")
print("app re-render")
app()
st.markdown(
    """
    ## Glossary
    | Column            | Description                                               |
    |-------------------|-----------------------------------------------------------|
    | `name`            | The site name.                                            |
    | `healthReg`       | The health region.                                        |
    | `siteID`          | The site ID.                                              |
    | `datasetID`       | The dataset ID.                                           |
    | `measure`         | The measure name.                                         |
    | `previousObs`     | The measure value that was observed before `latestObs`.   |
    | `latestObs`       | The measure value that was last recorded.                 |
    | `latestObsDT`     | The date at which `latestObs` was observed.               |
    | `previousReportDT`| The date at which the `previousObs` was reported.         |
    | `latestReportDT`  | The date at which the `latestObs` was reported.           |
    | `previousObsDT`   | The date at which the `previousObs` was observed.         |
    | `sampleID_previous` | The sample ID of the previous observation.              |
    | `sampleID_latest` | The sample ID of the latest observation.                  |
    """
)
