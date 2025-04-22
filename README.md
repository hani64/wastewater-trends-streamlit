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
│   ├── large-jumps.py        # Handles the "Large Jumps" page
│   ├── latest-measures.py    # Handles the "Latest Measures" page
│   ├── mpox.py               # Handles the "Mpox Trends" page
│   ├── ww-trends.py          # Handles the "Wastewater Trends" page
├── utils.py                  # Shared util functions
├── .env                      # Environment configuration
└── requirements.txt          # Dependencies
```

```mermaid
graph
    subgraph "Database"
        style Database fill:#fff6d4

        I[Databricks SQL Warehouse]
        J[(WW_TRENDS_TABLE)]
        K[(MPOX_TABLE)]
        L[(LARGE_JUMPS_TABLE)]
        M[(LOGS_TABLE)]
        N[(LATEST_MEASURES_TABLE)]
        O[(ALLSITES_TABLE)]
    end

    subgraph "Application"
    style Application fill:#fff6d4
        A[app.py]
        
        subgraph "Views"
            style Views fill:#ffe7e0
            subgraph F["admin-page.py"]
                app_admin[app]
            end

            subgraph E["large-jumps.py"]
                app_large_jumps[app]
                app_large_jumps --> create_jump_plot
                app_large_jumps --> edit_data_form_large_jumps
            end

            subgraph D["latest-measures.py"]
                app_latest_measures[app]
            end

            subgraph C["mpox.py"]
                app_mpox[app]
                app_mpox --> edit_data_form_mpox
            end

            subgraph B["ww-trends.py"]
                app_ww[app]
                app_ww --> create_sunburst_graph
                app_ww --> edit_data_form_ww
            end
        end

        subgraph "Shared&nbspUtilities"
            style Shared&nbspUtilities fill:#fcf0ff
            G[utils.py]
            H[.env]
            
            subgraph "Core&nbspFunctions"
                style Core&nbspFunctions fill:#cffae0
                get_db_connection[get_db_connection]
                get_cursor[get_cursor]
                trigger_job_run[trigger_job_run]
                get_user_info[get_user_info]
                get_username[get_username]
                can_user_edit[can_user_edit]
                get_log_entry[get_log_entry]
            end

            subgraph "SQL&nbspQuery&nbspTemplates"
                style SQL&nbspQuery&nbspTemplates fill:#d5f2f5

                select_ww_data[FETCH_WW_TRENDS_QUERY]
                update_ww[UPDATE_WW_TRENDS_QUERY]
                select_mpox_data[FETCH_MPOX_QUERY]
                update_mpox[UPDATE_MPOX_QUERY]
                select_jumps_data[FETCH_LARGE_JUMPS_QUERY]
                update_jumps[UPDATE_LARGE_JUMPS_QUERY]
                select_logs[FETCH_LOG_QUERY]
                insert_log[INSERT_LOG_QUERY]
                delete_log[DELETE_LOG_QUERY]
                select_latest[FETCH_LATEST_MEASURES_QUERY]
                select_before_jump[FETCH_BEFORE_LARGE_JUMP_QUERY]
                select_after_jump[FETCH_AFTER_LARGE_JUMP_QUERY]
            end
        end

        %% Connections
        A --> B & C & D & E & F
        Views -->|Uses| Shared&nbspUtilities
        G --> SQL&nbspQuery&nbspTemplates
        
        G --> get_cursor
        get_cursor --> get_db_connection
        G --> trigger_job_run
        G --> get_username
        G --> can_user_edit
        G --> get_log_entry
        H -->|Secret Variables| G
        G -->|SQL Queries| I
        I --> J & K & L & M & N & O
        trigger_job_run --> get_username
        get_username --> get_user_info
        can_user_edit --> get_user_info
        get_log_entry --> get_username

        %% Feature Nodes
        create_sunburst_graph[create_sunburst_graph]
        edit_data_form_ww[edit_data_form]
        edit_data_form_mpox[edit_data_form]
        create_jump_plot[create_jump_plot]
        edit_data_form_large_jumps[edit_data_form]

        %% Legend
        subgraph Node&nbspLegend
        style Node&nbspLegend fill:#ffffff
            z1[Application Root]
            z2[Python Files]
            z3[Defined Constant Variables]
            z4[Database]
            z5[Functions]
        end

        %% Component descriptions
        classDef main fill:#f9f,stroke:#333,stroke-width:2px
        classDef views fill:#c6e2ff,stroke:#333,stroke-width:2px
        classDef env fill:#ffcccb,stroke:#333,stroke-width:2px
        classDef db fill:#bfb,stroke:#333,stroke-width:2px
        classDef feature fill:#ffd700,stroke:#333,stroke-width:2px

        class A,z1 main
        class B,C,D,E,F,G,z2 views
        class H,select_ww_data,update_ww,select_mpox_data,update_mpox,select_jumps_data,update_jumps,select_logs,insert_log,delete_log,select_latest,select_before_jump,select_after_jump,z3 env
        class I,J,K,L,M,N,O,z4 db
        class create_sunburst_graph,edit_data_form_ww,edit_data_form_mpox,create_jump_plot,edit_data_form_large_jumps,get_db_connection,get_cursor,trigger_job_run,get_user_info,get_username,can_user_edit,get_log_entry,z5 feature
    end

```


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
