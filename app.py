"""
Business Intelligence Dashboard

Tech stack: Python, Pandas, Plotly, Dash

Structure:
- Data loading / cleaning
- KPI computation (programmatic)
- Visualization logic
- Callbacks + interactivity

This app uses a single central filter callback to update all KPIs and charts
so that the dashboard stays consistent with user selections.

Run: python app.py
"""
import pathlib
from datetime import datetime

import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

# -----------------------------
# Configuration / Data paths
# -----------------------------
ROOT = pathlib.Path(__file__).parent
DATA_PATH = ROOT / "data" / "sample_data.csv"


# -----------------------------
# Data Loading & Cleaning
# -----------------------------
def load_data(path: pathlib.Path) -> pd.DataFrame:
    """Load CSV and apply deterministic cleaning steps."""
    df = pd.read_csv(path)
    # Ensure correct dtypes
    df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
    df = df.dropna(subset=['order_date'])
    df['order_value'] = pd.to_numeric(df['order_value'], errors='coerce').fillna(0)
    df['delivery_time_minutes'] = pd.to_numeric(df['delivery_time_minutes'], errors='coerce')
    df['order_status'] = df['order_status'].astype(str)
    # Ensure repeat flag exists (some synthetic datasets may or may not have it)
    if 'is_repeat_customer' not in df.columns:
        df['is_repeat_customer'] = 0
    df['is_repeat_customer'] = df['is_repeat_customer'].astype(int)
    return df


orders = load_data(DATA_PATH)


# -----------------------------
# KPI Computation Helpers
# -----------------------------
def compute_kpis(df: pd.DataFrame) -> dict:
    """Return a dict of KPIs computed from the passed dataframe.

    Comments in code explain why each KPI matters for business users.
    """
    total_revenue = df['order_value'].sum()  # revenue shows topline performance
    total_orders = df['order_id'].nunique()  # volume is leading indicator of demand
    aov = total_revenue / total_orders if total_orders > 0 else 0  # average value per order

    # Repeat customer rate indicates customer loyalty and retention health
    repeat_customers = df[df['is_repeat_customer'] == 1]['customer_id'].nunique()
    unique_customers = df['customer_id'].nunique()
    repeat_rate = (repeat_customers / unique_customers) * 100 if unique_customers > 0 else 0

    # Cancellation rate signals friction / issues in ops or product
    cancellation_rate = (df['order_status'].value_counts().get('Cancelled', 0) / total_orders) * 100 if total_orders > 0 else 0

    return {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'aov': aov,
        'repeat_rate': repeat_rate,
        'cancellation_rate': cancellation_rate,
    }


# -----------------------------
# Visualization helpers
# -----------------------------
def fig_revenue_trend(df: pd.DataFrame):
    # Aggregate by day to show trend; convert index to datetime for plotting
    daily = df.groupby(df['order_date'].dt.date).agg({'order_value': 'sum'}).reset_index()
    fig = px.line(daily, x='order_date', y='order_value', title='Revenue Trend (Daily)', markers=True)
    fig.update_layout(yaxis_title='Revenue', xaxis_title='Date')
    return fig


def fig_orders_volume_trend(df: pd.DataFrame):
    daily = df.groupby(df['order_date'].dt.date).agg({'order_id': 'count'}).reset_index().rename(columns={'order_id': 'orders'})
    fig = px.area(daily, x='order_date', y='orders', title='Orders Volume Trend (Daily)')
    fig.update_layout(yaxis_title='Orders', xaxis_title='Date')
    return fig


def fig_city_performance(df: pd.DataFrame):
    city_rev = df.groupby('city').agg({'order_value': 'sum'}).reset_index().sort_values('order_value', ascending=False)
    fig = px.bar(city_rev, x='city', y='order_value', title='City-wise Revenue', text='order_value')
    fig.update_layout(xaxis={'categoryorder':'total descending'}, yaxis_title='Revenue')
    return fig


def fig_customer_behavior(df: pd.DataFrame):
    counts = df['is_repeat_customer'].map({0: 'New Customer', 1: 'Repeat Customer'}).value_counts().reset_index()
    counts.columns = ['customer_type', 'count']
    fig = px.pie(counts, names='customer_type', values='count', title='Repeat vs New Customers')
    return fig


def fig_operational_efficiency(df: pd.DataFrame):
    # Use a box plot to highlight distribution and outliers in delivery time (SLA breaches)
    fig = px.box(df, y='delivery_time_minutes', points='outliers', title='Delivery Time Distribution (minutes)')
    fig.update_layout(yaxis_title='Delivery Time (minutes)')
    return fig


# -----------------------------
# Dash App Layout
# -----------------------------
app = Dash(__name__)
server = app.server

initial_kpis = compute_kpis(orders)

app.layout = html.Div([
    html.Div([
        html.H1('Business Intelligence Dashboard', style={'textAlign': 'center', 'color': 'white', 'margin': 0}),
        html.P('Operational Insights • Revenue • Orders • Delivery', style={'textAlign': 'center', 'color': 'rgba(255,255,255,0.9)', 'margin': '6px 0 0 0'})
    ], style={'background': 'linear-gradient(90deg, #0b69ff 0%, #0066d6 100%)', 'padding': '16px', 'borderRadius': '6px', 'marginBottom': '18px'}),

    # KPI Cards (inline styling to preserve original layout)
    html.Div([
        html.Div(f"Total Revenue: ${initial_kpis['total_revenue']:,.2f}", id='total-revenue', style={'fontSize': 24, 'padding': '10px'}),
        html.Div(f"Total Orders: {initial_kpis['total_orders']}", id='total-orders', style={'fontSize': 24, 'padding': '10px'}),
        html.Div(f"Average Order Value: ${initial_kpis['aov']:,.2f}", id='average-order-value', style={'fontSize': 24, 'padding': '10px'}),
        html.Div(f"Repeat Customer Rate: {initial_kpis['repeat_rate']:.2f}%", id='repeat-customer-rate', style={'fontSize': 24, 'padding': '10px'}),
        html.Div(f"Order Cancellation Rate: {initial_kpis['cancellation_rate']:.2f}%", id='cancellation-rate', style={'fontSize': 24, 'padding': '10px'}),
    ], style={'display': 'flex', 'justifyContent': 'space-around', 'marginBottom': '20px'}),

    # Charts (placeholders updated by callbacks)
    dcc.Graph(id='revenue-trend'),
    dcc.Graph(id='orders-volume-trend'),
    dcc.Graph(id='city-wise-performance'),
    dcc.Graph(id='customer-behavior-insights'),

    # Filters (kept below charts as in the prior formatting)
    dcc.DatePickerRange(
        id='date-range',
        start_date=orders['order_date'].min().date(),
        end_date=orders['order_date'].max().date(),
        display_format='YYYY-MM-DD'
    ),
    dcc.Dropdown(
        id='city-selector',
        options=[{'label': city, 'value': city} for city in orders['city'].unique()],
        multi=True,
        placeholder='Select City'
    ),
    dcc.Dropdown(
        id='order-status-filter',
        options=[{'label': 'Completed', 'value': 'Completed'}, {'label': 'Cancelled', 'value': 'Cancelled'}],
        multi=True,
        placeholder='Select Order Status'
    ),
    dcc.Graph(id='operational-efficiency')
])


# -----------------------------
# Centralized Filter + Update Callback
# -----------------------------
@app.callback(
    Output('total-revenue', 'children'),
    Output('total-orders', 'children'),
    Output('average-order-value', 'children'),
    Output('repeat-customer-rate', 'children'),
    Output('cancellation-rate', 'children'),
    Output('revenue-trend', 'figure'),
    Output('orders-volume-trend', 'figure'),
    Output('city-wise-performance', 'figure'),
    Output('customer-behavior-insights', 'figure'),
    Output('operational-efficiency', 'figure'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    Input('city-selector', 'value'),
    Input('order-status-filter', 'value'),
)
def update_dashboard(start_date, end_date, selected_cities, selected_statuses):
    # Apply filters
    dff = orders.copy()
    if start_date:
        dff = dff[dff['order_date'] >= pd.to_datetime(start_date)]
    if end_date:
        dff = dff[dff['order_date'] <= pd.to_datetime(end_date)]
    if selected_cities:
        dff = dff[dff['city'].isin(selected_cities)]
    if selected_statuses:
        dff = dff[dff['order_status'].isin(selected_statuses)]

    # Recompute KPIs from filtered data
    kpis = compute_kpis(dff)

    total_revenue_label = html.Div([
        html.H4('Total Revenue'),
        html.P(f"${kpis['total_revenue']:,.2f}", style={'fontSize': '20px', 'fontWeight': '600'})
    ])

    total_orders_label = html.Div([
        html.H4('Total Orders'),
        html.P(f"{kpis['total_orders']}", style={'fontSize': '20px', 'fontWeight': '600'})
    ])

    aov_label = html.Div([
        html.H4('Average Order Value (AOV)'),
        html.P(f"${kpis['aov']:,.2f}", style={'fontSize': '20px', 'fontWeight': '600'})
    ])

    repeat_label = html.Div([
        html.H4('Repeat Customer Rate'),
        html.P(f"{kpis['repeat_rate']:.2f}%", style={'fontSize': '20px', 'fontWeight': '600'})
    ])

    cancel_label = html.Div([
        html.H4('Order Cancellation Rate'),
        html.P(f"{kpis['cancellation_rate']:.2f}%", style={'fontSize': '20px', 'fontWeight': '600'})
    ])

    # Figures
    fig_rev = fig_revenue_trend(dff)
    fig_orders = fig_orders_volume_trend(dff)
    fig_city = fig_city_performance(dff)
    fig_cust = fig_customer_behavior(dff)
    fig_ops = fig_operational_efficiency(dff)

    return (
        total_revenue_label,
        total_orders_label,
        aov_label,
        repeat_label,
        cancel_label,
        fig_rev,
        fig_orders,
        fig_city,
        fig_cust,
        fig_ops,
    )


if __name__ == '__main__':
    # In production, set debug=False and consider using a WSGI server.
    app.run(debug=True)