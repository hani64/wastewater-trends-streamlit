# Wastewater Trends Dashboard

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
├── blob_utils.py             # Shared util functions
├── .env                      # Environment configuration
└── requirements.txt          # Dependencies
```

## 🛠️ Installation

```bash
git clone https://github.com/PHACDataHub/wastewater-trends-streamlit.git
cd wastewater-trends-streamlit
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
## 🔧 Configuration

Create a `.env` file in the project root:


```ini
AZURE_BLOB_CONNECTION_STRING=your_connection_string
ACCOUNT_URL=your_account_url
CLIENT_ID=your_client_id
```

## 📈 Usage

`streamlit run app.py`

## 🔍 Troubleshooting

Common issues:

1. **Azure Connection Issues**
   - Verify credentials in `.env`
   - Try using the commented out connection method that uses `ManagedIdentityCredential` and `CLIENT_ID` instead of `AZURE_BLOB_CONNECTION_STRING`
   - Check that you are connected to the internal VPN
   - Ensure proper container permissions

2. **Data Loading Errors**
   - Check file format matches schema
