import streamlit as st

pg = st.navigation([
    st.Page("pages/home.py",             title="Home",             icon="🏠"),
    st.Page("pages/market_summary.py",   title="Market Summary",   icon="📊"),
    st.Page("pages/3_month_outlook.py",  title="3-Month Outlook",  icon="📈"),
    st.Page("pages/methodology.py",      title="Methodology",      icon="📖"),
])
pg.run()