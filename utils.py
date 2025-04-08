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
ALLSITES_TABLE = os.getenv("ALLSITES_TABLE")

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
    WHERE 
        CAST(latestObsDT AS DATE) > DATE_SUB(CURRENT_DATE(), 30)
"""

UPDATE_LARGE_JUMPS_QUERY = f"""
    UPDATE 
        {LARGE_JUMPS_TABLE}
    SET 
        actionItem = %(action_item)s
    WHERE 
        siteID = %(site_id)s 
    AND 
        datasetID = %(dataset_id)s 
    AND 
        measure = %(measure)s
    AND 
        previousObsDT = %(previous_obs_dt)s
    AND 
        latestObsDT = %(latest_obs_dt)s
"""

FETCH_LOG_QUERY = f"""
    SELECT 
        User,
        CAST(Time AS STRING),
        Page,
        Location,
        SiteID,
        Measure,
        EpiWeek,
        EpiYear,
        ChangedColumn,
        OldValue,
        NewValue
    FROM 
        {LOGS_TABLE}
"""

INSERT_LOG_QUERY = f"""
    INSERT INTO {LOGS_TABLE} (
        User,
        Time,
        Page,
        Location,
        SiteID,
        Measure,
        EpiWeek,
        EpiYear,
        ChangedColumn,
        OldValue,
        NewValue
    )
    VALUES (
        %(User)s,
        %(Time)s,
        %(Page)s,
        %(Location)s,
        %(SiteID)s,
        %(Measure)s,
        %(EpiWeek)s,
        %(EpiYear)s,
        %(ChangedColumn)s,
        %(OldValue)s,
        %(NewValue)s
    )
"""

DELETE_LOG_QUERY = f"""
    DELETE FROM 
        {LOGS_TABLE}
    WHERE User = %(User)s
    AND Time = %(Time)s
    AND Page = %(Page)s
    AND Location = %(Location)s
    AND SiteID = %(SiteID)s
    AND Measure = %(Measure)s
    AND EpiWeek = %(EpiWeek)s
    AND EpiYear = %(EpiYear)s
    AND ChangedColumn = %(ChangedColumn)s
    AND OldValue = %(OldValue)s
    AND NewValue = %(NewValue)s
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
    UPDATE 
        {MPOX_TABLE}
    SET 
        g2r_label = %(g2r_label)s
    WHERE 
        Location = %(location)s 
    AND 
        EpiYear = %(epi_year)s
    AND 
        EpiWeek = %(epi_week)s
    AND 
        Week_start = %(week_start)s
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

FETCH_BEFORE_LARGE_JUMP_QUERY = f"""
    SELECT * FROM 
        {ALLSITES_TABLE}
    WHERE 
        siteID = %(siteID)s 
    AND 
        measure = %(Measure)s 
    AND 
        collDT < CAST(%(previousObsDT)s AS DATE)
    ORDER BY collDT DESC 
    LIMIT 4
"""

FETCH_AFTER_LARGE_JUMP_QUERY = f"""
    SELECT * FROM 
        {ALLSITES_TABLE}
    WHERE 
        siteID = %(siteID)s 
    AND 
        measure = %(Measure)s 
    AND 
        collDT > CAST(%(latestObsDT)s AS DATE)
    ORDER BY collDT ASC 
    LIMIT 1
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


def trigger_job_run(page: str, log_entries: list[dict] = None) -> int:
    if os.getenv("DEVELOPMENT") == "TRUE":
        return 200

    # MAP page to job_id
    page_to_id = {"ww-trends": os.getenv("WW_JOB_ID"), "mpox": os.getenv("MPOX_JOB_ID")}

    url = f"{os.getenv("ADB_INSTANCE_NAME")}/api/2.2/jobs/run-now"
    payload = {
        "job_id": page_to_id[page],
        "job_parameters": {
            "user_email": get_username(),
            "changes": json.dumps(log_entries),
        },
    }
    headers = {
        "Authorization": f"Bearer {os.getenv('ADB_API_KEY')}",
        "Content-Type": "application/json",
    }

    # Send the POST request
    response = requests.post(url, json=payload, headers=headers)

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
        return "dev"
    return user_info.get("user")


def can_user_edit():
    if os.getenv("DEVELOPMENT") == "TRUE":
        return True
    if "is_editor" not in st.session_state:
        st.session_state.is_editor = "wastewater" in get_user_info().get("groups")
    return st.session_state.is_editor


def get_log_entry(
    old_data: pd.DataFrame, new_data: pd.DataFrame, page: str
) -> dict[str, str]:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = {
        "User": get_username(),
        "Time": current_time,
        "Page": page,
        "Location": old_data.get("Location", "N/A"),
        "SiteID": old_data.get("siteID", "N/A"),
        "Measure": old_data.get("measure", "mpox" if page == "Mpox Trends" else "N/A"),
        "EpiWeek": (
            str(int(old_data.get("EpiWeek"))) if page == "Mpox Trends" else "N/A"
        ),
        "EpiYear": (
            str(int(old_data.get("EpiYear"))) if page == "Mpox Trends" else "N/A"
        ),
        "ChangedColumn": "N/A",
        "OldValue": "N/A",
        "NewValue": "N/A",
    }

    # Note this assumes at most only one column can be changed
    for col in old_data.index:
        if old_data[col] != new_data[col]:
            log_entry["ChangedColumn"] = col
            log_entry["OldValue"] = str(old_data[col])
            log_entry["NewValue"] = str(new_data[col])

    # return log entry
    return log_entry
