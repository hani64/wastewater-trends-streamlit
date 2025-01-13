import streamlit as st

pages = {
    "Pages": [
        st.Page("./views/ww-trends.py", title="Wastewater Trends", icon="🚰", default=True),
        st.Page("./views/mpox.py", title="Mpox Trends", icon="🦠"),
        st.Page("./views/latest-measures.py", title="Latest Measures", icon="🆕"),
        st.Page("./views/large-jumps.py", title="Large Jumps", icon="⚠️"),
    ],
}

pg = st.navigation(
    pages,
    expanded=True,
)

pg.run()
