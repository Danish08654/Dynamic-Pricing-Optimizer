import streamlit as st
import requests
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Dynamic Pricing Optimizer",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Dynamic Pricing Optimizer")

CATEGORIES = ['Electronics','Clothing','Home & Garden',
              'Sports','Beauty','Books','Food & Grocery']

#  Sidebar 
st.sidebar.header("Product Details")

product_id       = st.sidebar.number_input("Product ID", 0, 999, 1)
category         = st.sidebar.selectbox("Category", CATEGORIES)
base_cost        = st.sidebar.number_input("Unit Cost ($)", 1.0, 1000.0, 45.0, step=1.0)
base_price       = st.sidebar.number_input("Current Price ($)", 1.0, 2000.0, 99.0, step=1.0)
competitor_price = st.sidebar.number_input("Competitor Price ($)", 1.0, 2000.0, 95.0, step=1.0)

st.sidebar.markdown("**📅 Context**")
day_of_week      = st.sidebar.selectbox("Day of Week",
    options=[0,1,2,3,4,5,6],
    format_func=lambda x: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][x])
month            = st.sidebar.slider("Month", 1, 12, 5)
is_weekend       = int(day_of_week >= 5)
season_mult      = st.sidebar.slider("Season Multiplier", 0.5, 2.5, 1.0, 0.05)

st.sidebar.markdown("**🎯 Strategy**")
strategy = st.sidebar.radio("Optimisation Goal",
    ["margin", "revenue", "balanced"],
    format_func=lambda x: {
        "margin":   "Maximise Margin",
        "revenue":  "Maximise Revenue",
        "balanced": "Balanced"
    }[x])

run_btn = st.sidebar.button("Get Price Recommendation", type="primary",
                             use_container_width=True)

#  Main 
if run_btn:
    payload = {
        "product_id":       product_id,
        "category":         category,
        "base_cost":        base_cost,
        "base_price":       base_price,
        "competitor_price": competitor_price,
        "day_of_week":      day_of_week,
        "month":            month,
        "is_weekend":       is_weekend,
        "season_multiplier":season_mult,
        "strategy":         strategy,
    }

    with st.spinner("Optimising price..."):
        try:
            resp   = requests.post(f"{API_URL}/recommend", json=payload)
            result = resp.json()
        except Exception as e:
            st.error(f"API connection failed: {e}")
            st.stop()

    # Direction banner
    dir_color = {"INCREASE": "green", "DECREASE": "#e67e22", "HOLD": "steelblue"}
    direction = result['price_direction']
    color     = dir_color.get(direction, "gray")

    st.markdown(
        f"<div style='background:{color};padding:16px;border-radius:10px;"
        f"text-align:center;color:white;font-size:22px;font-weight:600'>"
        f"RECOMMENDED PRICE: ${result['recommended_price']} "
        f"({result['price_change_pct']:+.1f}%) — {direction}</div>",
        unsafe_allow_html=True
    )
    st.markdown("")

    # Metrics row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Current Price",    f"${result['current_price']}")
    c2.metric("Optimal Price",    f"${result['recommended_price']}",
              delta=f"{result['price_change_pct']:+.1f}%")
    c3.metric("Predicted Demand", f"{result['predicted_demand']:.0f} units")
    c4.metric("Predicted Margin", f"${result['predicted_margin']:.0f}")
    c5.metric("vs Competitor",    f"{result['vs_competitor_pct']:+.1f}%")

    st.divider()
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Price Decision Summary")

        current_margin = (base_price - base_cost) * result['predicted_demand']

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=['Current Price', 'Recommended Price'],
            y=[base_price, result['recommended_price']],
            marker_color=['steelblue', color],
            text=[f"${base_price}", f"${result['recommended_price']}"],
            textposition='outside'
        ))
        fig.update_layout(
            title="Price Comparison",
            yaxis_title="Price ($)",
            height=300,
            margin=dict(t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Top 3 Price Alternatives")

        for i, alt in enumerate(result['top_3_alternatives']):
            rank = ["🥇", "🥈", "🥉"][i]
            st.markdown(
                f"{rank} **${alt['price']}** — "
                f"Demand: {alt['demand']:.0f} · "
                f"Margin: ${alt['margin']:.0f} · "
                f"Revenue: ${alt['revenue']:.0f}"
            )

        st.markdown("")
        st.info(
            f"**Strategy:** {strategy.capitalize()}  \n"
            f"**Margin %:** {result['margin_pct']*100:.1f}%  \n"
            f"**A/B Test Ready:** {'✅ Yes' if result['ab_test_ready'] else '❌ No'}"
        )

    # Price curve simulation
    st.divider()
    st.subheader("Price vs Margin & Revenue Curve")

    prices  = np.linspace(base_cost * 1.15, base_price * 2.0, 60)
    margins  = []
    revenues = []

    for p in prices:
        estimated_demand = max(0, result['predicted_demand'] *
                               (1 + (base_price - p) / base_price * 1.2))
        margins.append((p - base_cost) * estimated_demand)
        revenues.append(p * estimated_demand)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=prices, y=margins, name="Margin ($)",
                              line=dict(color='tomato', width=2)))
    fig2.add_trace(go.Scatter(x=prices, y=revenues, name="Revenue ($)",
                              line=dict(color='steelblue', width=2),
                              yaxis='y2'))
    fig2.add_vline(x=result['recommended_price'],
                   line_dash="dash", line_color="green",
                   annotation_text=f"Optimal ${result['recommended_price']}")
    fig2.add_vline(x=base_price,
                   line_dash="dot", line_color="gray",
                   annotation_text=f"Current ${base_price}")
    fig2.update_layout(
        height=350,
        yaxis=dict(title="Margin ($)", titlefont=dict(color='tomato')),
        yaxis2=dict(title="Revenue ($)", titlefont=dict(color='steelblue'),
                    overlaying='y', side='right'),
        legend=dict(x=0.01, y=0.99),
        margin=dict(t=30, b=20)
    )
    st.plotly_chart(fig2, use_container_width=True)
