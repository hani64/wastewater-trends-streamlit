from datetime import datetime
import os
from dotenv import load_dotenv
from databricks import sql
import pandas as pd
import streamlit as st
import json
import requests

load_dotenv()

LARGE_JUMPS_TABLE = os.getenv("LARGE_JUMPS_TABLE")
MPOX_TABLE = os.getenv("MPOX_TABLE")
WW_TRENDS_TABLE = os.getenv("WW_TRENDS_TABLE")
LOGS_TABLE = os.getenv("LOGS_TABLE")
LATEST_MEASURES_TABLE = os.getenv("LATEST_MEASURES_TABLE")

FETCH_LARGE_JUMPS_QUERY = f"""
    SELECT
        siteID,
        datasetID,
        measure,
        previousObs,
        latestObs,
        previousObsDT,
        latestObsDT,
        alertType,
        actionItem
    FROM
        {LARGE_JUMPS_TABLE}
"""

UPDATE_LARGE_JUMPS_QUERY = f"""
    UPDATE 
    {LARGE_JUMPS_TABLE}
    SET actionItem = %(action_item)s
    WHERE siteID = %(site_id)s 
    AND datasetID = %(dataset_id)s 
    AND measure = %(measure)s
    AND previousObsDT = %(previous_obs_dt)s
    AND latestObsDT = %(latest_obs_dt)s
"""

FETCH_LOG_QUERY = f"""
    SELECT 
        User,
        CAST(Time AS STRING),
        Page,
        siteID,
        Measure,
        Changes
    FROM 
        {LOGS_TABLE}
"""

INSERT_LOG_QUERY = f"""
    INSERT INTO {LOGS_TABLE} (
        User,
        Time,
        Page,
        siteID,
        Measure,
        Changes
    )
    VALUES (
        %(User)s,
        %(Time)s,
        %(Page)s,
        %(siteID)s,
        %(Measure)s,
        %(Changes)s
    )
"""

FETCH_MPOX_QUERY = f"""
    SELECT 
        Location, 
        EpiYear,
        EpiWeek, 
        Week_start, 
        g2r_label
    FROM 
        {MPOX_TABLE}
"""

UPDATE_MPOX_QUERY = f"""
    UPDATE {MPOX_TABLE}
    SET g2r_label = %(g2r_label)s
    WHERE Location = %(location)s 
    AND EpiYear = %(epi_year)s
    AND EpiWeek = %(epi_week)s
    AND Week_start = %(week_start)s
"""

FETCH_WW_TRENDS_QUERY = f"""
    SELECT 
        Location,
        measure,
        latestTrends,
        LatestLevel,
        Grouping,
        City,
        Province,
        Viral_Activity_Level
    FROM 
        {WW_TRENDS_TABLE}
"""

UPDATE_WW_TRENDS_QUERY = f"""
    UPDATE {WW_TRENDS_TABLE}
    SET Viral_Activity_Level = %(viral_activity_level)s
    WHERE Location = %(location)s 
    AND measure = %(measure)s
    AND City = %(city)s
    AND Province = %(province)s
"""

FETCH_LATEST_MEASURES_QUERY = f"""
    SELECT
        name,
        healthReg,
        siteID,
        datasetID,
        measure,
        previousObs,
        latestObs,
        previousObsDT,
        latestObsDT,
        previousReportDT,
        latestReportDT,
        sampleID_previous,
        sampleID_latest
    FROM
        {LATEST_MEASURES_TABLE}
"""


def get_db_connection():
    if "db_connection" not in st.session_state:
        st.session_state.db_connection = sql.connect(
            server_hostname=os.getenv("ADB_INSTANCE_NAME"),
            http_path=os.getenv("ADB_HTTP_PATH"),
            access_token=os.getenv("ADB_API_KEY"),
        )
        print("Created new database connection")
    return st.session_state.db_connection


def get_cursor():
    conn = get_db_connection()
    print("Created new cursor")
    return conn.cursor()


def trigger_job_run(page: str):
    # MAP page to job_id
    page_to_id = {"ww-trends": os.getenv("WW_JOB_ID"), "mpox": os.getenv("MPOX_JOB_ID")}

    url = f"{os.getenv("ADB_INSTANCE_NAME")}/api/2.2/jobs/run-now"
    payload = {"job_id": page_to_id[page]}

    # Send the POST request
    response = requests.post(url, json=payload)

    # Optionally, handle possible HTTP errors
    response.raise_for_status()

    return response.status_code


def get_user_info() -> dict:
    user_info_json = st.context.headers.get("Rstudio-Connect-Credentials")
    if user_info_json is None:
        return None
    return json.loads(user_info_json)


def get_username() -> str:
    user_info = get_user_info()
    if user_info is None:
        return "anon"
    return user_info.get("user")


def can_user_edit():
    if os.getenv("DEVELOPMENT") == "TRUE":
        return True
    if "is_editor" not in st.session_state:
        st.session_state.is_editor = "WW" in get_user_info().get("groups")
    return st.session_state.is_editor


def get_log_entry(
    username: str, old_data: pd.DataFrame, new_data: pd.DataFrame, page: str
) -> dict[str, str]:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Find the changes
    changes = {
        col: {"old": old_data[col], "new": new_data[col]}
        for col in old_data.index
        if old_data[col] != new_data[col]
    }

    log_entry = {
        "User": username,
        "Time": current_time,
        "Page": page,
        "siteID": old_data.get("siteID", "N/A"),
        "Measure": old_data.get("measure", "N/A"),
        "Changes": str(changes),
    }

    # return log entry
    return log_entry
