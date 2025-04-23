# Wastewater Data Validation App 

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://posit-connect-dv.phac-aspc.gc.ca/wastewater-KeyMetrics/) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Streamlit-based dashboard for monitoring, analyzing, and modifying wastewater measurements data. Changes to this app are currently set to continously deploy to an instance hosted on Posit Connect.


## 🚀 Features

- 🚰 View and impute CovN2, RSV, FluA, and FluB trend data
- 🦠 View and impute Mpox trend data
- 🆕 View the 2 most recent measures from any wastewater site
- ⚠️ View recorded measures with unusually large jumps in values 

## 🏗️ Architecture

```
wastewater-trends-streamlit/
├── app.py                    # Main application entry
├── views/                    # Page components
│   ├── ww-trends.py          # Handles the "Wastewater Trends" page
│   ├── mpox.py               # Handles the "Mpox Trends" page
│   ├── latest-measures.py    # Handles the "Latest Measures" page
│   ├── large-jumps.py        # Handles the "Large Jumps" page
│   ├── admin-page.py         # Shows a log of user actions to admin users
├── utils.py                  # Shared util functions
├── .env                      # Environment configuration
└── requirements.txt          # Dependencies
```

![App Architecture Diagram](diagram.png)


## 🛠️ Installation

```bash
git clone https://github.com/PHACDataHub/wastewater-trends-streamlit.git
cd wastewater-trends-streamlit
python -m venv .venv
source .venv/bin/activate # If on Linux
.venv\Scripts\activate # If on Windows
pip install -r requirements.txt
```
## 🔧 Configuration

Create a `.env` file in the project root:


```ini
# These values are available through ADB workspace
ADB_INSTANCE_NAME = ""
ADB_HTTP_PATH = ""
ADB_API_KEY = ""

# The names of the catalog tables used within each of the pages
WW_TRENDS_TABLE = ""
MPOX_TABLE = ""
LARGE_JUMPS_TABLE = ""
LOGS_TABLE = ""
LATEST_MEASURES_TABLE = ""
ALLSITES_TABLE = ""

# The job id of the jobs used to push data from ADB catalog to prod blob
WW_JOB_ID = ""
MPOX_JOB_ID = ""

DEVELOPMENT = "TRUE" # Only add this value in your dev environment
```

`ADB_INSTANCE_NAME`, `ADB_HTTP_PATH`, and `ADB_API_KEY` can be accessed by going to Databricks -> SQL Warehouse -> Wastewater Warehouse -> Connection Details -> Python. The code snippet that pops up on your screen will include these variables for our ADB instance and let you generate an API KEY.

The TABLE variables (`WW_TRENDS_TABLE`, `MPOX_TABLE`, etc.) can be found under Databricks -> Catalog -> hive_metastore -> wastewater. These tables can later renamed or moved if the app however the schema must be the same.


`WW_JOB_ID` and `MPOX_JOB_ID` are the jobs within Databricks that are responsible for syncing user changes with the main SQL DB aswell as sending email notifications. These can be found by going to Databricks -> Workflows and find the two jobs with the names **Wastewater - Push Streamlit Data - Mpox Trends** and **Wastewater - Push Streamlit Data - Respiratory Virus Trends**. If you click on either of these jobs you can find the JOB ID on the right under job details.

## 📈 Usage

`streamlit run app.py`

## 🔍 Troubleshooting

#### Common issues:

1. **Cold Cluster Startup:**  
   The first data load may take up to 5 minutes if the data cluster is cold. Please allow extra time on startup.

2. **Configuration Errors:**  
   - Ensure your `.env` file is set up correctly with the proper values for `ADB_INSTANCE_NAME`, `ADB_HTTP_PATH`, and `ADB_API_KEY`.  
   - Verify that the table names in the `.env` (e.g. `WW_TRENDS_TABLE`, `MPOX_TABLE`, etc.) are correct.

3. **Permission Issues:**  
   If you cannot modify data or load certain pages, check your permissions. In development mode, The `DEVELOPMENT` flag should be added to your `.env`.
