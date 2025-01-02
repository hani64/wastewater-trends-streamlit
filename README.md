# Wastewater Trends Dashboard

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://posit-connect-dv.phac-aspc.gc.ca/wastewater-trends-app/) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Streamlit-based dashboard for monitoring, analyzing, and modifying wastewater measurements data. Changes to this app are currently set to continously deploy to an instance hosted on Posit Connect.


## 🚀 Features

- 🚰 View and impute CovN2, RSV, FluA, and FluB trend data
- 🦠 View and impute Mpox trend data
- 📊 View the 2 most recent measures from any wastewater site  

## 🏗️ Architecture

```
wastewater-trends-streamlit/
├── app.py              # Main application entry
├── views/              # Page components
├── .env                # Environment configuration
└── requirements.txt    # Dependencies
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

NOTE: the encoding variable are optional and should only be set if issue arise.

```ini
AZURE_BLOB_CONNECTION_STRING=your_connection_string
ACCOUNT_URL=your_account_url
CLIENT_ID=your_client_id

ENCODING_WWT=utf-8 
ENCODING_MPOX=utf-16be
ENCODING_ALL_SITES=utf-8
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
   - Verify CSV encoding match with `ENCODING` env. variables, if not override with optional env. vars (e.g. `ENCODING_MPOX`) 
   - Check file format matches schema