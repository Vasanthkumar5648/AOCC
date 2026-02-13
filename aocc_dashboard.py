import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit.connections import ExperimentalBaseConnection
import time

# Page config
st.set_page_config(
    page_title="🛫 AOCC - Airport Operations Control Centre",
    page_icon="🛫",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_connection():
    """Initialize MySQL connection using Streamlit secrets."""
    return st.connection("mysql", type="sql")

class AOCCDashboard:
    def init(self, conn):
        self.conn = conn
    
    def refresh_data(self):
        """Get real-time AOCC data."""
        query = """
        SELECT f.*, g.gate_number, g.status as gate_status,
               TIMESTAMPDIFF(MINUTE, f.eta, NOW()) as minutes_since_eta
        FROM flights f 
        LEFT JOIN gates g ON f.gate = g.gate_number
        WHERE f.created_at > DATE_SUB(NOW(), INTERVAL 6 HOUR)
        ORDER BY f.eta ASC
        """
        return self.conn.query(query)
    
    def get_gate_utilization(self):
        """Calculate gate utilization metrics."""
        query = """
        SELECT status, COUNT(*) as count
        FROM gates 
        GROUP BY status
        """
        return self.conn.query(query)
    
    def get_alerts(self):
        """Get active alerts."""
        query = """
        SELECT * FROM alerts 
        WHERE resolved = FALSE 
        ORDER BY created_at DESC 
        LIMIT 20
        """
        return self.conn.query(query)
    
    def get_kpis(self):
        """Calculate key performance indicators."""
        query = """
        SELECT 
            COUNT(*) as total_flights,
            SUM(CASE WHEN delay_min > 0 THEN 1 ELSE 0 END) as delayed_flights,
            AVG(delay_min) as avg_delay,
            (SELECT COUNT(*) FROM gates WHERE status = 'Occupied') as occupied_gates
        FROM flights 
        WHERE created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """
        return self.conn.query(query)

def main():
    st.title("🛫 AOCC - Airport Operations Control Centre")
    st.markdown("Salem Airport Real-time Operations Dashboard")
    
    conn = init_connection()
    aocc = AOCCDashboard(conn)
    
    # Auto-refresh
    if st.button("🔄 Refresh Data", key="refresh"):
        st.cache_data.clear()
        st.rerun()
    
    # KPIs Row
    kpis_df = aocc.get_kpis()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Flights", kpis_df["total_flights"][0], delta="24h")
    with col2:
        st.metric("Delayed Flights", kpis_df["delayed_flights"][0], delta="↑")
    with col3:
        st.metric("Avg Delay (min)", f"{kpis_df['avg_delay'][0]:.1f}")
    with col4:
        st.metric("Gate Utilization", f"{kpis_df['occupied_gates'][0]}/10")
    
    # Main Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Operations", "🚨 Alerts", "📈 Analytics", "⚙️ Operations"])
    
    with tab1:
        # Real-time Flights Table
        st.subheader("Live Flight Operations")
        df = aocc.refresh_data()
        
        st.dataframe(
            df,
            column_config={
                "status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["On Time", "Delayed", "Cancelled", "Boarding", "Departed"],
                    required=True
                ),
                "gate": st.column_config.TextColumn("Gate")
            },
            use_container_width=True,
            height=400
        )
    
    with tab2:
        # Alerts
        st.subheader("🚨 Active Alerts")
        alerts_df = aocc.get_alerts()
        
        if not alerts_df.empty:
            for _, alert in alerts_df.iterrows():
              st.error(f"{alert['severity']}: {alert['message']}", 
                        icon="🚨")
        else:
            st.success("✅ No active alerts")
    
    with tab3:
        # Analytics
        st.subheader("Gate Utilization")
        gate_df = aocc.get_gate_utilization()
        
        fig_pie = px.pie(gate_df, names='status', values='count',
                        title="Gate Status Distribution")
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # Delay Analysis
        col1, col2 = st.columns(2)
        with col1:
            delay_query = "SELECT delay_min FROM flights WHERE delay_min > 0"
            delays = conn.query(delay_query)["delay_min"].tolist()
            if delays:
                fig_hist = px.histogram(delays, nbins=20, title="Delay Distribution")
                st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            status_query = """
            SELECT status, COUNT(*) as count 
            FROM flights 
            WHERE created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            GROUP BY status
            """
            status_df = conn.query(status_query)
            fig_bar = px.bar(status_df, x='status', y='count', 
                           title="Flight Status (24h)")
            st.plotly_chart(fig_bar, use_container_width=True)
    
    with tab4:
        # Operations Control
        st.subheader("Quick Actions")
        
        with st.expander("➕ Add New Flight"):
            with st.form("add_flight"):
                col1, col2 = st.columns(2)
                with col1:
                    flight_id = st.text_input("Flight ID", value="AIxxx")
                    origin = st.selectbox("Origin", ["DEL", "BOM", "HYD", "BLR", "MAA"])
                with col2:
                    eta = st.datetime_input("ETA", datetime.now() + timedelta(minutes=30))
                    status = st.selectbox("Status", ["On Time", "Delayed", "Cancelled"])
                
                if st.form_submit_button("Add Flight"):
                    try:
                        conn.query("""
                            INSERT INTO flights (flight_id, origin, dest, eta, status) 
                            VALUES (%s, %s, 'Salem', %s, %s)
                        """, [flight_id, origin, eta, status])
                        st.success("Flight added successfully!")
                        st.rerun()
                    except:
                        st.error("Error adding flight")
        
        with st.expander("🔧 Assign Gates"):
            if st.button("Auto-assign Available Gates"):
                st.info("Gate assignment logic would run here")
    
    # Footer
    st.markdown("---")
    st.caption("👨‍💼 AOCC Operator Dashboard | Last updated: " + 
              datetime.now().strftime("%H:%M:%S IST"))

if name == "main":
    main()
                severity_color = {"Low": "green", "Medium": "orange", "High": "red"}
