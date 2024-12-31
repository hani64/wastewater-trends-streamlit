import streamlit as st

pages = {
    "Pages": [
        st.Page("ww-trends.py", title="Wastewater Trends", icon="🚰", default=True),
        st.Page("mpox.py", title="Mpox Trends", icon="Ⓜ️"),
    ],
}

pg = st.navigation(
    pages,
    expanded=True,
)

pg.run()
