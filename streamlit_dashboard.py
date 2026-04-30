import streamlit as st
import pandas as pd
from PIL import Image
import os
import plotly.express as px
import plotly.graph_objects as go
import base64

# Hardcoded credentials
USERNAME = "moon"
PASSWORD = "blehbleh"

# Login logic
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔒 Scrim Dashboard Login")
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")

    if st.button("Login"):
        if username_input == USERNAME and password_input == PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Incorrect username or password")
    st.stop()

def get_base64_image(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

st.set_page_config(page_title="Valorant Scrim Dashboard", layout="wide")
encoded_bg = get_base64_image("wallp.png")
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@300;400;500;600;700&display=swap');
    
    * {{
        font-family: 'Rajdhani', sans-serif !important;
    }}
    
    body {{
        background-image: url("data:image/jpg;base64,{encoded_bg}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
        color: #ffffff;
        font-family: 'Rajdhani', sans-serif !important;
    }}

    .stApp {{
        background-color: rgba(0, 0, 0, 0.85);
        font-family: 'Rajdhani', sans-serif !important;
    }}

    .block-container {{
        padding: 2rem;
        border-radius: 12px;
        font-family: 'Rajdhani', sans-serif !important;
    }}

    h1, h2, h3, h4, h5, h6, .stTabs, .stButton, p, div, span, label, input, select, textarea, button {{
        font-family: 'Rajdhani', sans-serif !important;
        color: #FDB913;
    }}

    .stDataFrame, .stTable {{
        background-color: #1a1a1a;
        font-family: 'Rajdhani', sans-serif !important;
    }}

    /* Tier badge styling */
    .tier-badge {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 13px;
        margin-right: 4px;
    }}
    .tier-1 {{ background: #FDB913; color: #000; }}
    .tier-2 {{ background: #9ca3af; color: #000; }}
    .tier-3 {{ background: #92400e; color: #fff; }}
    </style>
""", unsafe_allow_html=True)

st.title("Valorant Scrim Dashboard")
st.image("wolves_logo.png", width=100)


# ── Load CSVs ──────────────────────────────────────────────────────────────────
try:
    form_df = pd.read_csv("form.csv")
    form_df = form_df[['Column 1', 'Agent', 'Result']].dropna().reset_index(drop=True)
except Exception as e:
    form_df = pd.DataFrame()
    st.warning(f"⚠️ Couldn't load form.csv: {e}")

try:
    score_df = pd.read_csv("cleaned_score.csv")
    score_df['Date'] = pd.to_datetime(score_df['Date'], errors='coerce')
    # Ensure Tier is numeric; default to 1 if missing
    if 'Tier' in score_df.columns:
        score_df['Tier'] = pd.to_numeric(score_df['Tier'], errors='coerce').fillna(1).astype(int)
    else:
        score_df['Tier'] = 1
except Exception as e:
    score_df = pd.DataFrame()
    st.warning(f"⚠️ Couldn't load cleaned_score.csv: {e}")

try:
    foracs_df = pd.read_csv("foracs.csv")
except Exception as e:
    foracs_df = pd.DataFrame()
    st.warning(f"⚠️ Couldn't load foracs.csv: {e}")

# ── Global Tier Filter (sidebar) ───────────────────────────────────────────────
TIER_LABELS = {1: "Tier 1 — Top", 2: "Tier 2 — Mid", 3: "Tier 3 — Lower"}
TIER_COLORS = {1: "#FDB913", 2: "#9ca3af", 3: "#b45309"}

with st.sidebar:
    st.markdown("## 🏆 Scrim Tier Filter")
    st.markdown("Filter all stats by opponent tier:")

    if not score_df.empty:
        available_tiers = sorted(score_df['Tier'].unique())
    else:
        available_tiers = [1, 2, 3]

    selected_tiers = st.multiselect(
        "Select Tier(s)",
        options=available_tiers,
        default=available_tiers,
        format_func=lambda t: TIER_LABELS.get(t, f"Tier {t}"),
        key="global_tier_filter"
    )

    if not selected_tiers:
        st.warning("⚠️ No tier selected — showing all data.")
        selected_tiers = available_tiers

    # Show a summary of how many games per tier
    if not score_df.empty:
        st.markdown("---")
        st.markdown("**Games per tier:**")
        for t in available_tiers:
            count = len(score_df[score_df['Tier'] == t])
            wr = score_df[score_df['Tier'] == t]['Outcome'].str.lower().eq('win').mean()
            color = TIER_COLORS.get(t, "#ffffff")
            st.markdown(
                f"<span style='color:{color};font-weight:700'>Tier {t}</span> — "
                f"{count} games · {wr*100:.0f}% WR",
                unsafe_allow_html=True
            )

# Apply global tier filter to score_df for all tabs
if not score_df.empty:
    score_df_filtered = score_df[score_df['Tier'].isin(selected_tiers)].copy()
else:
    score_df_filtered = score_df.copy()

# ── Tab navigation ─────────────────────────────────────────────────────────────
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0

def load_svg_icon(filepath, size=28, color="#FFFFFF"):
    with open(filepath, 'r') as f:
        svg = f.read()
    svg = svg.replace('<svg', f'<svg width="{size}" height="{size}" style="fill: {color};"')
    return svg

icons = [
    load_svg_icon("assets/chart-simple-solid-full.svg"),
    load_svg_icon("assets/cubes-solid-full.svg"),
    load_svg_icon("assets/chart-line-solid-full.svg"),
    load_svg_icon("assets/gun-solid-full.svg"),
    load_svg_icon("assets/list-ol-solid-full.svg"),
    load_svg_icon("assets/compress-solid-full.svg")
]

tab_names = ["Overview", "Compositions", "Insights", "Pistol", "Stats", "Compare"]

st.markdown("""
    <style>
    .icon-tab-container {
        position: relative;
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        margin-bottom: 0.375rem !important;
    }
    .icon-display {
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 8px;
        cursor: pointer;
        padding: 8px;
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    .icon-display:hover { background: rgba(253, 185, 19, 0.1); transform: translateY(-2px); }
    .icon-display.active { background: #FDB913 !important; }
    .icon-display.active svg { fill: white !important; }
    button[data-testid*="icon_tab"]:hover {
        background: rgba(253, 185, 19, 0.1) !important;
        border-color: #FDB913 !important;
        transform: translateY(-2px);
        transition: all 0.2s ease;
    }
    button[data-testid*="icon_tab"].active {
        background: #FDB913 !important;
        border-color: #FDB913 !important;
        color: white !important;
    }
    hr { margin-top: 0.375rem !important; margin-bottom: 0.375rem !important; border: none !important; height: 1px !important; background-color: rgba(255,255,255,0.1) !important; }
    div[data-testid="stHorizontalBlock"] { margin-bottom: 0.375rem !important; }
    </style>
""", unsafe_allow_html=True)

cols = st.columns(6)
for idx, (col, icon, name) in enumerate(zip(cols, icons, tab_names)):
    with col:
        is_active = st.session_state.active_tab == idx
        active_class = "active" if is_active else ""
        st.markdown(f'<div class="icon-tab-container">', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="icon-display {active_class}" onclick="document.querySelector('button[data-testid*=\\'icon_tab_{idx}\\']').click()">
                {icon}
            </div>
        """, unsafe_allow_html=True)
        if st.button(name, key=f"icon_tab_{idx}", use_container_width=True, help=name):
            st.session_state.active_tab = idx
            st.rerun()
        if is_active:
            st.markdown(f"""
                <script>
                (function() {{
                    const button = document.querySelector('button[data-testid*="icon_tab_{idx}"]');
                    if (button) button.classList.add('active');
                }})();
                </script>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)

# Helper: show which tiers are active
def tier_badge_html(tiers):
    badges = ""
    for t in sorted(tiers):
        color = TIER_COLORS.get(t, "#aaa")
        badges += f"<span style='background:{color};color:{'#000' if t==1 else '#fff'};padding:2px 9px;border-radius:4px;font-weight:700;font-size:12px;margin-right:4px;'>T{t}</span>"
    return f"<div style='margin-bottom:0.5rem'>Showing: {badges}</div>"

# ── TAB 0: OVERVIEW ────────────────────────────────────────────────────────────
if st.session_state.active_tab == 0:
    st.markdown(tier_badge_html(selected_tiers), unsafe_allow_html=True)
    st.markdown("### 📅 Filter by Date Range")

    if not score_df_filtered.empty and 'Date' in score_df_filtered.columns:
        min_date = score_df_filtered['Date'].min().date()
        max_date = score_df_filtered['Date'].max().date()
        date_range = st.date_input(
            "Select Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="overview_date_range"
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date_overview, end_date_overview = date_range
        else:
            start_date_overview = end_date_overview = date_range
        filtered_score = score_df_filtered[
            (score_df_filtered['Date'].dt.date >= start_date_overview) &
            (score_df_filtered['Date'].dt.date <= end_date_overview)
        ]
    else:
        filtered_score = score_df_filtered

    st.subheader("Map Overview: Total Games, Wins, Draws, Losses, Win Rate")
    if not filtered_score.empty:
        summary = filtered_score.groupby('Map').agg(
            Games=('Outcome', 'count'),
            Wins=('Outcome', lambda x: (x.str.lower() == 'win').sum()),
            Draws=('Outcome', lambda x: (x.str.lower() == 'draw').sum()),
            Losses=('Outcome', lambda x: (x.str.lower() == 'loss').sum())
        ).reset_index()
        summary['Win Rate'] = summary['Wins'] / summary['Games']
        st.dataframe(summary.sort_values(by='Map'), use_container_width=True)

        st.markdown("### 🗺️ Map Win Rates")
        winrate_df = summary[['Map', 'Win Rate']].dropna().copy()
        winrate_df['Win Rate %'] = winrate_df['Win Rate'] * 100
        winrate_df = winrate_df.sort_values(by='Win Rate %', ascending=False)

        fig_map_wr = px.bar(
            winrate_df, x='Win Rate %', y='Map', orientation='h',
            text=winrate_df['Win Rate %'].apply(lambda x: f"{x:.1f}%"),
            title="Map Win Rates",
            color='Win Rate %', color_continuous_scale=['#ff0000', '#FDB913']
        )
        fig_map_wr.update_traces(textposition='outside', marker_line_color='#000000', marker_line_width=1.2)
        fig_map_wr.update_layout(
            plot_bgcolor='#000000', paper_bgcolor='#000000',
            font=dict(family='Rajdhani', size=14, color='#FDB913'),
            title_font=dict(size=20, color='#FDB913'),
            yaxis=dict(tickfont=dict(color='#ffffff'), categoryorder='total ascending', gridcolor='#333333'),
            xaxis=dict(title='Win Rate (%)', title_font=dict(color='#FDB913'), tickfont=dict(color='#ffffff'), gridcolor='#333333', range=[0, 100])
        )
        st.plotly_chart(fig_map_wr, use_container_width=True)

        # ── Win rate by Tier (grouped bar) ──
        st.markdown("### 📊 Win Rate by Map × Tier")
        tier_map_summary = score_df_filtered[
            (score_df_filtered['Date'].dt.date >= start_date_overview) &
            (score_df_filtered['Date'].dt.date <= end_date_overview)
        ].groupby(['Map', 'Tier']).agg(
            Games=('Outcome', 'count'),
            Wins=('Outcome', lambda x: (x.str.lower() == 'win').sum())
        ).reset_index()
        tier_map_summary['Win Rate %'] = tier_map_summary['Wins'] / tier_map_summary['Games'] * 100
        tier_map_summary['Tier Label'] = tier_map_summary['Tier'].map(lambda t: f"Tier {t}")

        fig_tier = px.bar(
            tier_map_summary, x='Map', y='Win Rate %',
            color='Tier Label',
            color_discrete_map={'Tier 1': '#FDB913', 'Tier 2': '#9ca3af', 'Tier 3': '#b45309'},
            barmode='group',
            text=tier_map_summary['Win Rate %'].apply(lambda x: f"{x:.0f}%"),
            title="Win Rate by Map & Tier"
        )
        fig_tier.update_traces(textposition='outside', marker_line_color='#333', marker_line_width=1)
        fig_tier.update_layout(
            plot_bgcolor='#000000', paper_bgcolor='#000000',
            font=dict(family='Rajdhani', color='#FDB913'),
            title_font=dict(size=18, color='#FDB913'),
            xaxis=dict(tickfont=dict(color='#fff'), gridcolor='#333'),
            yaxis=dict(range=[0, 110], tickfont=dict(color='#fff'), gridcolor='#333'),
            legend=dict(font=dict(color='#fff'))
        )
        st.plotly_chart(fig_tier, use_container_width=True)
    else:
        st.info("No scrim data for the selected tiers / date range.")

# ── TAB 1: COMPOSITIONS ────────────────────────────────────────────────────────
if st.session_state.active_tab == 1:
    st.markdown(tier_badge_html(selected_tiers), unsafe_allow_html=True)
    st.subheader("🥷 Top 5-agent Composition Win Rates by Map")
    if not form_df.empty:
        valid_maps = []
        for i in range(0, len(form_df) - 4, 5):
            block = form_df.iloc[i:i+5]
            if len(block) == 5 and block['Column 1'].nunique() == 1 and block['Result'].nunique() == 1:
                valid_maps.append(block['Column 1'].iloc[0])

        valid_maps = sorted(set(valid_maps))
        selected_map = st.selectbox("Select a map:", valid_maps)

        teams = []
        filtered_dates = set(score_df_filtered['Date'])
        for i in range(0, len(form_df) - 4, 5):
            block = form_df.iloc[i:i+5]
            map_match = block['Column 1'].iloc[0]
            result_match = block['Result'].iloc[0]

            if (
                len(block) == 5 and
                block['Column 1'].nunique() == 1 and
                block['Result'].nunique() == 1 and
                block['Column 1'].iloc[0] == selected_map
            ):
                match_filter = (
                    (score_df_filtered['Map'] == map_match) &
                    (score_df_filtered['Outcome'].str.lower() == result_match.lower()) &
                    (score_df_filtered['Date'].isin(filtered_dates))
                )
                if not score_df_filtered[match_filter].empty:
                    agents = tuple(sorted(block['Agent'].tolist()))
                    teams.append({'Composition': agents, 'Result': result_match})

        df = pd.DataFrame(teams)
        if not df.empty:
            df['Win'] = df['Result'].apply(lambda x: 1 if x.lower() == 'win' else 0)
            df['Draw'] = df['Result'].apply(lambda x: 1 if x.lower() == 'draw' else 0)
            df['Loss'] = df['Result'].apply(lambda x: 1 if x.lower() == 'loss' else 0)
            df['Game'] = 1

            grouped = df.groupby('Composition').agg(
                games=('Game', 'sum'),
                wins=('Win', 'sum'),
                draws=('Draw', 'sum'),
                losses=('Loss', 'sum')
            ).reset_index()

            grouped['Win Rate %'] = grouped['wins'] / grouped['games'] * 100
            grouped['Comp String'] = grouped['Composition'].apply(lambda x: '-'.join(x))
            grouped = grouped.sort_values(by='Win Rate %', ascending=False).head(15)
            grouped['First Agent'] = grouped['Composition'].apply(lambda x: x[0])

        if not grouped.empty:
            st.markdown("""
            <style>
            .composition-bar {
                display: flex; align-items: center; background: #2a2a2a;
                border: 1px solid #333; border-radius: 4px; padding: 8px; margin: 3px 0;
                min-height: 45px; position: relative; overflow: hidden;
            }
            .bar-background { position: absolute; left: 180px; top: 0; height: 100%; background: #FDB913; border-radius: 0 4px 4px 0; z-index: 1; }
            .agents-container { display: flex; gap: 4px; align-items: center; min-width: 170px; z-index: 2; position: relative; }
            .agent-icon-img { width: 28px; height: 28px; border-radius: 3px; border: 1px solid rgba(255,255,255,0.2); }
            .win-rate-info { margin-left: auto; z-index: 2; position: relative; color: white; font-weight: bold; text-align: right; padding-right: 12px; }
            .win-percentage { font-size: 16px; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); }
            .game-count { font-size: 11px; color: #ccc; }
            </style>
            """, unsafe_allow_html=True)

            st.markdown(f"### Top Compositions on {selected_map}")
            max_win_rate = grouped['Win Rate %'].max()

            for idx, row in grouped.iterrows():
                composition = row['Composition']
                win_rate = row['Win Rate %']
                games = row['games']
                bar_width_percent = (win_rate / max_win_rate * 80) if max_win_rate > 0 else 0

                icons_html = ""
                for agent in composition:
                    icon_name = agent.lower().replace('/', '_').replace(' ', '_')
                    icon_path = f"assets/agents/{icon_name}.png"
                    if os.path.exists(icon_path):
                        try:
                            with open(icon_path, "rb") as img_file:
                                img_data = base64.b64encode(img_file.read()).decode()
                            icons_html += f'<img src="data:image/png;base64,{img_data}" class="agent-icon-img" title="{agent}" />'
                        except:
                            icons_html += f'<div class="agent-icon-img" style="background:#666;color:white;display:flex;align-items:center;justify-content:center;font-size:10px;">{agent[:2]}</div>'
                    else:
                        icons_html += f'<div class="agent-icon-img" style="background:#666;color:white;display:flex;align-items:center;justify-content:center;font-size:10px;">{agent[:2]}</div>'

                st.markdown(f"""
                <div class="composition-bar">
                    <div class="bar-background" style="width:{bar_width_percent}%;"></div>
                    <div class="agents-container">{icons_html}</div>
                    <div class="win-rate-info">
                        <div class="win-percentage">{win_rate:.1f}%</div>
                        <div class="game-count">({games} games)</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info(f"No composition data for {selected_map} in selected tiers.")

    # Agent win rate heatmap (uses foracs_df — no tier filter needed here)
    st.subheader("📊 Win Rate by Agent by Player")
    if not foracs_df.empty and 'Result' in foracs_df.columns:
        foracs_agg = foracs_df.groupby(['Player', 'Agent']).agg(
            games=('Result', 'count'),
            wins=('Result', lambda x: (x.str.strip().str.lower() == 'win').sum())
        ).reset_index()
        foracs_agg['Win Rate %'] = (foracs_agg['wins'] / foracs_agg['games'] * 100).round(1)
        pivot = foracs_agg.pivot_table(index='Player', columns='Agent', values='Win Rate %', aggfunc='mean')
        pivot_wins = foracs_agg.pivot_table(index='Player', columns='Agent', values='wins', aggfunc='sum')
        pivot_games = foracs_agg.pivot_table(index='Player', columns='Agent', values='games', aggfunc='sum')
        if not pivot.empty:
            all_players = sorted(foracs_df['Player'].dropna().unique())
            all_agents = sorted(foracs_df['Agent'].dropna().unique())
            pivot = pivot.reindex(index=all_players, columns=all_agents)
            pivot_wins = pivot_wins.reindex(index=all_players, columns=all_agents)
            pivot_games = pivot_games.reindex(index=all_players, columns=all_agents)
            NOT_PLAYED = -1
            z = pivot.values.copy().astype(float)
            z[pd.isna(z)] = NOT_PLAYED
            customdata = []
            for player in all_players:
                row = []
                for agent in all_agents:
                    g = pivot_games.loc[player, agent] if pd.notna(pivot_games.loc[player, agent]) else 0
                    g = int(g)
                    if g == 0:
                        row.append("Not played")
                    else:
                        w = int(pivot_wins.loc[player, agent]) if pd.notna(pivot_wins.loc[player, agent]) else 0
                        wr = pivot.loc[player, agent]
                        wr = float(wr) if pd.notna(wr) else 0
                        row.append(f"Win Rate: {wr:.0f}% ({w}/{g})")
                customdata.append(row)
            text = [[f"{v:.0f}%" if v >= 0 else "" for v in row] for row in z]
            fig_heat = go.Figure(data=go.Heatmap(
                z=z, x=all_agents, y=all_players, customdata=customdata,
                zmin=NOT_PLAYED, zmax=100,
                colorscale=[[0,'#9ca3af'],[0.01,'#dc2626'],[0.06,'#fef08a'],[0.36,'#86efac'],[0.66,'#22c55e'],[1,'#14532d']],
                text=text, texttemplate="%{text}",
                textfont=dict(family='Rajdhani', size=12, color='white'),
                hoverongaps=False,
                hovertemplate="Player: %{y}<br>Agent: %{x}<br>%{customdata}<extra></extra>"
            ))
            fig_heat.update_layout(
                title="Win Rate % by Player and Agent",
                xaxis=dict(title='Agent', side='bottom', tickangle=-45, tickfont=dict(family='Rajdhani', color='#FDB913')),
                yaxis=dict(title='Player', tickfont=dict(family='Rajdhani', color='#FDB913'), autorange='reversed'),
                plot_bgcolor='#000000', paper_bgcolor='#000000',
                font=dict(family='Rajdhani', color='#FDB913'),
                title_font=dict(size=18, color='#FDB913'),
                margin=dict(l=80, r=40, t=60, b=120),
                height=max(400, 48*len(pivot.index)+120),
                width=max(400, 48*len(pivot.columns)+100)
            )
            st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("No foracs data available.")

# ── TAB 2: ROUND INSIGHTS ──────────────────────────────────────────────────────
if st.session_state.active_tab == 2:
    st.markdown(tier_badge_html(selected_tiers), unsafe_allow_html=True)
    st.subheader("📈 Round Insights")
    if not score_df_filtered.empty:
        maps = sorted(score_df_filtered['Map'].dropna().unique())
        dates = sorted(score_df_filtered['Date'].dropna().unique())

        col1, col2 = st.columns(2)
        selected_map = col1.selectbox("Filter by Map", ["All"] + maps)
        start_date = col1.selectbox("Start Date", dates, key="insight_start")
        end_date = col2.selectbox("End Date", dates, index=len(dates)-1, key="insight_end")

        filtered_df = score_df_filtered.copy()
        if selected_map != "All":
            filtered_df = filtered_df[filtered_df['Map'] == selected_map]
        if start_date and end_date:
            filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]

        def extract_wr(row, side):
            if pd.isna(row['Start']) or pd.isna(row['First Half WR']) or pd.isna(row['Second Half WR']):
                return None
            if side == 'Attack':
                return row['First Half WR'] if row['Start'] == 'Attack' else row['Second Half WR']
            elif side == 'Defence':
                return row['First Half WR'] if row['Start'] == 'Defence' else row['Second Half WR']
            return None

        filtered_df['Atk WR Derived'] = filtered_df.apply(lambda row: extract_wr(row, 'Attack'), axis=1)
        filtered_df['Def WR Derived'] = filtered_df.apply(lambda row: extract_wr(row, 'Defence'), axis=1)

        st.dataframe(filtered_df, use_container_width=True)

        st.markdown("### 🔍 Summary Stats")

        agg_dict = {
            'Games': ('Outcome', 'count'),
            'Wins': ('Outcome', lambda x: (x.str.lower() == 'win').sum()),
            'Draws': ('Outcome', lambda x: (x.str.lower() == 'draw').sum()),
            'Losses': ('Outcome', lambda x: (x.str.lower() == 'loss').sum()),
            'Avg_Atk_WR': ('Atk WR Derived', lambda x: pd.to_numeric(x.astype(str).str.replace('%','',regex=False), errors='coerce').mean()),
            'Avg_Def_WR': ('Def WR Derived', lambda x: pd.to_numeric(x.astype(str).str.replace('%','',regex=False), errors='coerce').mean()),
        }
        if 'Atk_PP_Success' in filtered_df.columns:
            agg_dict['Atk_PP_Success'] = ('Atk_PP_Success', lambda x: pd.to_numeric(x.fillna('0').astype(str).str.replace('%',''), errors='coerce').mean())
        if 'Def_PP_Success' in filtered_df.columns:
            agg_dict['Def_PP_Success'] = ('Def_PP_Success', lambda x: pd.to_numeric(x.fillna('0').astype(str).str.replace('%',''), errors='coerce').mean())

        summary = filtered_df.groupby('Map').agg(**agg_dict).reset_index()
        summary['Raw_Atk_WR'] = summary['Avg_Atk_WR']
        summary['Raw_Def_WR'] = summary['Avg_Def_WR']
        summary['Raw_Round_WR'] = (summary['Raw_Atk_WR'] + summary['Raw_Def_WR']) / 2
        summary['Round WR'] = summary['Raw_Round_WR'].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "-")
        summary['Avg_Atk_WR'] = summary['Avg_Atk_WR'].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "-")
        summary['Avg_Def_WR'] = summary['Avg_Def_WR'].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "-")

        display_cols = ['Map', 'Games', 'Wins', 'Draws', 'Losses', 'Avg_Atk_WR', 'Avg_Def_WR', 'Round WR']

        def highlight_win_rates(val, threshold_low=40, threshold_high=60):
            try:
                val = float(str(val).replace('%', ''))
            except:
                return ''
            if val >= threshold_high:
                return 'background-color: #14532d; color: white;'
            elif val < threshold_low:
                return 'background-color: #7f1d1d; color: white;'
            else:
                return 'background-color: #78350f; color: white;'

        styled_df = summary[display_cols].style\
            .map(highlight_win_rates, subset=['Avg_Atk_WR', 'Avg_Def_WR', 'Round WR'])\
            .set_properties(**{'text-align': 'center'})\
            .set_table_styles([{'selector': 'th', 'props': [('background-color','#1a1a1a'),('color','#FDB913'),('text-align','center')]}])

        st.dataframe(styled_df, use_container_width=True)

        # ── Per-tier breakdown inside Insights ──
        st.markdown("### 🏆 Round Win Rate by Tier")
        tier_insight = score_df_filtered.copy()
        if selected_map != "All":
            tier_insight = tier_insight[tier_insight['Map'] == selected_map]
        if start_date and end_date:
            tier_insight = tier_insight[(tier_insight['Date'] >= start_date) & (tier_insight['Date'] <= end_date)]

        tier_insight['Atk WR Derived'] = tier_insight.apply(lambda row: extract_wr(row, 'Attack'), axis=1)
        tier_insight['Def WR Derived'] = tier_insight.apply(lambda row: extract_wr(row, 'Defence'), axis=1)

        tier_summary = tier_insight.groupby('Tier').agg(
            Games=('Outcome', 'count'),
            Wins=('Outcome', lambda x: (x.str.lower() == 'win').sum()),
            Avg_Atk_WR=('Atk WR Derived', 'mean'),
            Avg_Def_WR=('Def WR Derived', 'mean'),
        ).reset_index()
        tier_summary['Win Rate %'] = tier_summary['Wins'] / tier_summary['Games'] * 100
        tier_summary['Atk WR %'] = tier_summary['Avg_Atk_WR'] * 100
        tier_summary['Def WR %'] = tier_summary['Avg_Def_WR'] * 100
        tier_summary['Tier Label'] = tier_summary['Tier'].map(lambda t: f"Tier {t}")

        tier_long = tier_summary.melt(
            id_vars='Tier Label',
            value_vars=['Win Rate %', 'Atk WR %', 'Def WR %'],
            var_name='Metric', value_name='Value'
        )
        fig_tier_ins = px.bar(
            tier_long, x='Tier Label', y='Value', color='Metric', barmode='group',
            text=tier_long['Value'].apply(lambda x: f"{x:.1f}%"),
            color_discrete_map={'Win Rate %': '#FDB913', 'Atk WR %': '#f97316', 'Def WR %': '#60a5fa'},
            title="Win / Atk / Def WR by Tier"
        )
        fig_tier_ins.update_traces(textposition='outside')
        fig_tier_ins.update_layout(
            plot_bgcolor='#000000', paper_bgcolor='#000000',
            font=dict(family='Rajdhani', color='#FDB913'),
            yaxis=dict(range=[0, 110], gridcolor='#333', tickfont=dict(color='#fff')),
            xaxis=dict(tickfont=dict(color='#fff')),
            legend=dict(font=dict(color='#fff'))
        )
        st.plotly_chart(fig_tier_ins, use_container_width=True)

        # Atk vs Def chart
        plot_df = summary[['Map', 'Raw_Atk_WR', 'Raw_Def_WR']].copy()
        plot_df.rename(columns={'Raw_Atk_WR': 'Attack', 'Raw_Def_WR': 'Defense'}, inplace=True)
        plot_df['Attack'] *= 100
        plot_df['Defense'] *= 100
        plot_df = plot_df.melt(id_vars='Map', var_name='Side', value_name='Win Rate (%)')
        plot_df['Map'] = pd.Categorical(plot_df['Map'], categories=plot_df.groupby('Map')['Win Rate (%)'].mean().sort_values(ascending=False).index, ordered=True)

        fig = px.bar(
            plot_df, x='Map', y='Win Rate (%)', color='Side',
            color_discrete_map={'Attack': '#FDB913', 'Defense': '#ffffff'},
            barmode='group',
            text=plot_df['Win Rate (%)'].apply(lambda x: f"{x:.1f}%"),
            title="Attack vs Defense Win Rates by Map"
        )
        fig.update_traces(textposition='outside', marker_line_color='#333333', marker_line_width=1.2, width=0.4)
        fig.update_layout(
            plot_bgcolor='#000000', paper_bgcolor='#000000',
            font=dict(color='#FDB913', family='Rajdhani'),
            title_font=dict(color='#FDB913', size=20),
            xaxis=dict(tickangle=-25, gridcolor='#333333'),
            yaxis=dict(range=[0, 100], gridcolor='#333333')
        )
        st.plotly_chart(fig, use_container_width=True)

        # Post-plant chart
        if 'Atk_PP_Success' in score_df_filtered.columns and 'Def_PP_Success' in score_df_filtered.columns:
            st.markdown("### 📊 Post-Plant Success Rate by Map")
            pp_source = filtered_df.copy()
            pp_df = pp_source.groupby('Map').agg({
                'Atk_PP_Success': lambda x: pd.to_numeric(x.astype(str).str.replace('%','',regex=False), errors='coerce').mean(),
                'Def_PP_Success': lambda x: pd.to_numeric(x.astype(str).str.replace('%','',regex=False), errors='coerce').mean()
            }).reset_index()

            label_map = {"Atk_PP_Success": "Post Plant", "Def_PP_Success": "Retakes"}
            sort_label = st.selectbox("Sort by", list(label_map.values()), index=0)
            sort_col = [k for k, v in label_map.items() if v == sort_label][0]
            sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True)
            ascending = sort_order == "Ascending"

            if pp_df['Atk_PP_Success'].max() <= 1.0:
                pp_df['Atk_PP_Success'] *= 100
                pp_df['Def_PP_Success'] *= 100

            pp_df = pp_df.sort_values(by=sort_col, ascending=ascending)
            pp_df['Map'] = pd.Categorical(pp_df['Map'], categories=pp_df['Map'], ordered=True)
            pp_df.rename(columns=label_map, inplace=True)
            pp_df_long = pp_df.melt(id_vars='Map', var_name='Side', value_name='Post-Plant Success (%)')

            fig_pp = px.bar(
                pp_df_long, x='Map', y='Post-Plant Success (%)', color='Side', barmode='stack',
                text=pp_df_long['Post-Plant Success (%)'].apply(lambda x: f"{x:.1f}%"),
                title="Post-Plant Success Rate (Stacked Atk + Def)",
                color_discrete_map={'Post Plant': '#FDB913', 'Retakes': '#ffffff'}
            )
            fig_pp.update_traces(textposition='inside', marker_line_color='#333333', marker_line_width=1.2)
            fig_pp.update_layout(
                plot_bgcolor='#000000', paper_bgcolor='#000000',
                font=dict(family='Rajdhani', size=14, color='#FDB913'),
                title_font=dict(size=20, color='#FDB913'),
                xaxis=dict(tickangle=-25, gridcolor='#333333', tickfont=dict(color='#fff')),
                yaxis=dict(range=[0, 100], gridcolor='#333333', tickfont=dict(color='#fff')),
                legend=dict(font=dict(color='#fff'))
            )
            st.plotly_chart(fig_pp, use_container_width=True)
    else:
        st.info("No data for selected tiers.")

# ── TAB 3: PISTOL ──────────────────────────────────────────────────────────────
if st.session_state.active_tab == 3:
    st.markdown(tier_badge_html(selected_tiers), unsafe_allow_html=True)
    st.subheader("🔫 Pistol Round Win Rate by Map")

    if not score_df_filtered.empty:
        min_date = score_df_filtered['Date'].min()
        max_date = score_df_filtered['Date'].max()

        start_date, end_date = st.date_input(
            "Select Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        filtered_df = score_df_filtered[
            (score_df_filtered['Date'] >= pd.to_datetime(start_date)) &
            (score_df_filtered['Date'] <= pd.to_datetime(end_date))
        ]

        filtered_df['Total Pistols Won'] = filtered_df['First Pistol'] + filtered_df['Second Pistol']
        grouped = filtered_df.groupby('Map').agg(
            Total_Pistols_Won=('Total Pistols Won', 'sum'),
            Total_Pistols_Played=('Map', 'count')
        ).reset_index()
        grouped['Total_Pistols_Played'] *= 2
        grouped['Pistol Win Rate (%)'] = (grouped['Total_Pistols_Won'] / grouped['Total_Pistols_Played']) * 100
        grouped = grouped.sort_values(by='Pistol Win Rate (%)', ascending=False)

        fig_pistol = px.bar(
            grouped, x='Map', y='Pistol Win Rate (%)',
            text=grouped['Pistol Win Rate (%)'].apply(lambda x: f"{x:.1f}%"),
            color='Pistol Win Rate (%)', color_continuous_scale=['#ff0000', '#FDB913'],
            title="Pistol Win Rates by Map"
        )
        fig_pistol.update_traces(textposition='outside', marker_line_color='#000000', marker_line_width=1.2)
        fig_pistol.update_layout(
            plot_bgcolor='#000000', paper_bgcolor='#000000',
            font=dict(family='Rajdhani', size=14, color='#FDB913'),
            title_font=dict(size=20, color='#FDB913'),
            xaxis=dict(tickfont=dict(color='#ffffff'), gridcolor='#333333'),
            yaxis=dict(range=[0,100], title='Win Rate (%)', title_font=dict(color='#FDB913'), tickfont=dict(color='#ffffff'), gridcolor='#333333')
        )
        st.plotly_chart(fig_pistol, use_container_width=True)

        # ── Pistol WR by Tier ──
        st.markdown("### 🏆 Pistol Win Rate by Tier")
        pistol_tier = filtered_df.groupby('Tier').agg(
            Total_Won=('Total Pistols Won', 'sum'),
            Total_Played=('Map', 'count')
        ).reset_index()
        pistol_tier['Total_Played'] *= 2
        pistol_tier['Pistol WR %'] = pistol_tier['Total_Won'] / pistol_tier['Total_Played'] * 100
        pistol_tier['Tier Label'] = pistol_tier['Tier'].map(lambda t: f"Tier {t}")

        fig_pt = px.bar(
            pistol_tier, x='Tier Label', y='Pistol WR %',
            text=pistol_tier['Pistol WR %'].apply(lambda x: f"{x:.1f}%"),
            color='Tier Label',
            color_discrete_map={'Tier 1': '#FDB913', 'Tier 2': '#9ca3af', 'Tier 3': '#b45309'},
            title="Pistol Win Rate by Opponent Tier"
        )
        fig_pt.update_traces(textposition='outside')
        fig_pt.update_layout(
            plot_bgcolor='#000000', paper_bgcolor='#000000',
            font=dict(family='Rajdhani', color='#FDB913'),
            yaxis=dict(range=[0,100], gridcolor='#333', tickfont=dict(color='#fff')),
            xaxis=dict(tickfont=dict(color='#fff')),
            showlegend=False
        )
        st.plotly_chart(fig_pt, use_container_width=True)

        st.markdown("### 🍰 2nd Round Outcomes by Map")
        if 'Atk 2nd' in filtered_df.columns and 'Def 2nd' in filtered_df.columns:
            conversion_data = pd.concat([
                filtered_df[['Map', 'Atk 2nd']].rename(columns={'Atk 2nd': 'Conversion'}),
                filtered_df[['Map', 'Def 2nd']].rename(columns={'Def 2nd': 'Conversion'})
            ])
            map_list = conversion_data['Map'].dropna().unique()
            selected_map_pistol = st.selectbox("Select a map to view 2nd round breakdown:", sorted(map_list))
            map_conversions = conversion_data[conversion_data['Map'] == selected_map_pistol]

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 🔁 After Winning Pistol (WW/WL)")
                filtered_win = map_conversions[map_conversions['Conversion'].isin(['WW', 'WL'])]
                if filtered_win.empty:
                    st.info("No data for pistol wins on this map.")
                else:
                    pie_data_win = filtered_win['Conversion'].value_counts(normalize=True).reset_index()
                    pie_data_win.columns = ['Conversion', 'Percentage']
                    pie_data_win['Percentage'] *= 100
                    fig_pie_win = px.pie(pie_data_win, names='Conversion', values='Percentage',
                        title=f"Pistol Conversion - {selected_map_pistol}", color='Conversion',
                        color_discrete_map={'WW': '#FDB913', 'WL': '#666666'}, hole=0.4)
                    fig_pie_win.update_traces(textinfo='label+percent', marker_line_color='#000000', marker_line_width=1.5)
                    fig_pie_win.update_layout(plot_bgcolor='#000000', paper_bgcolor='#000000',
                        font=dict(family='Rajdhani', size=14, color='#FDB913'),
                        title_font=dict(size=18, color='#FDB913'), legend=dict(font=dict(color='#ffffff')))
                    st.plotly_chart(fig_pie_win, use_container_width=True)

            with col2:
                st.markdown("#### 🔁 After Losing Pistol (LL/LW)")
                filtered_loss = map_conversions[map_conversions['Conversion'].isin(['LL', 'LW'])]
                if filtered_loss.empty:
                    st.info("No data for pistol losses on this map.")
                else:
                    pie_data_loss = filtered_loss['Conversion'].value_counts(normalize=True).reset_index()
                    pie_data_loss.columns = ['Conversion', 'Percentage']
                    pie_data_loss['Percentage'] *= 100
                    fig_pie_loss = px.pie(pie_data_loss, names='Conversion', values='Percentage',
                        title=f"Eco Round Outcomes - {selected_map_pistol}", color='Conversion',
                        color_discrete_map={'LL': '#444444', 'LW': '#3b82f6'}, hole=0.4)
                    fig_pie_loss.update_traces(textinfo='label+percent', marker_line_color='#000000', marker_line_width=1.5)
                    fig_pie_loss.update_layout(plot_bgcolor='#000000', paper_bgcolor='#000000',
                        font=dict(family='Rajdhani', size=14, color='#FDB913'),
                        title_font=dict(size=18, color='#FDB913'), legend=dict(font=dict(color='#ffffff')))
                    st.plotly_chart(fig_pie_loss, use_container_width=True)
    else:
        st.info("No data for selected tiers.")

# ── TAB 4: PLAYER STATS ────────────────────────────────────────────────────────
if st.session_state.active_tab == 4:
    st.subheader("🧑‍💼 Player Agent Stats")

    try:
        player_df = pd.read_csv("form.csv")
    except Exception as e:
        st.warning(f"Could not load player data: {e}")
        player_df = pd.DataFrame()

    if not player_df.empty:
        player_df['Date'] = pd.to_datetime(player_df['Date'], errors='coerce')
        player_df = player_df.dropna(subset=['Date'])

        all_players = sorted(player_df['Player'].dropna().unique())
        all_maps = sorted(player_df['Column 1'].dropna().unique())

        min_date = player_df['Date'].min().date()
        max_date = player_df['Date'].max().date()

        col1, col2 = st.columns(2)
        selected_player = col1.selectbox("Select a player:", all_players)
        start_date = col1.date_input("Start date:", min_value=min_date, max_value=max_date, value=min_date)
        end_date = col2.date_input("End date:", min_value=min_date, max_value=max_date, value=max_date)
        selected_map = col2.selectbox("Filter by Map:", ["All"] + all_maps)

        filtered = player_df[
            (player_df['Player'] == selected_player) &
            (player_df['Date'].dt.date >= start_date) &
            (player_df['Date'].dt.date <= end_date)
        ]
        if selected_map != "All":
            filtered = filtered[filtered['Column 1'] == selected_map]

        if not filtered.empty:
            agent_stats = filtered.groupby('Agent').agg(
                Rounds=('Rounds', 'sum'),
                Kills=('Kills', 'sum'),
                Deaths=('Deaths', 'sum'),
                Assists=('Assists', 'sum'),
                ACS=('ACS', 'mean'),
                FK=('FK', 'sum'),
                Plants=('Plants', 'sum'),
                FD=('FD', 'sum'),
                FD_Def=('FD Def', 'sum')
            ).reset_index()

            agent_stats['K/D Ratio'] = agent_stats['Kills'] / agent_stats['Deaths'].replace(0, float('nan'))
            agent_stats['K+A per Round'] = (agent_stats['Kills'] + agent_stats['Assists']) / agent_stats['Rounds'].replace(0, float('nan'))
            agent_stats['FK-FD'] = agent_stats['FK'] - agent_stats['FD']
            agent_stats['% FD on Def'] = (agent_stats['FD_Def'] / agent_stats['FD'].replace(0, float('nan'))) * 100
            agent_stats['% FD on Def'] = agent_stats['% FD on Def'].fillna(0)

            display_df = agent_stats.round(2)[['Agent','Rounds','Kills','Deaths','Assists','ACS','FK-FD','Plants','% FD on Def','K/D Ratio','K+A per Round']]
            st.markdown(f"### 🔍 Agent Performance for {selected_player} ({start_date} → {end_date})")
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No data for this player in the selected filters.")
    else:
        st.warning("No player stats found in form.csv")

    with st.expander("🐝 Player ACS Beeswarm Plot"):
        import seaborn as sns
        import matplotlib.pyplot as plt

        df = pd.read_csv("foracs.csv")
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['ACS'] = pd.to_numeric(df['ACS'], errors='coerce')

        players = sorted(df['Player'].dropna().unique())
        agents = sorted(df['Agent'].dropna().unique())
        maps = sorted(df['Map'].dropna().unique())
        dates = sorted(df['Date'].dropna().dt.date.unique())

        col1, col2 = st.columns(2)
        selected_player_bee = col1.selectbox("Select Player", players, key='bee_player')
        selected_agents = col2.multiselect("Filter by Agent(s)", agents, default=agents)
        selected_maps = st.multiselect("Filter by Map(s)", maps, default=maps)
        start_date_bee = st.date_input("Start Date", value=min(dates), min_value=min(dates), max_value=max(dates), key='bee_start')
        end_date_bee = st.date_input("End Date", value=max(dates), min_value=min(dates), max_value=max(dates), key='bee_end')

        filtered_df = df[
            (df['Player'] == selected_player_bee) &
            (df['Agent'].isin(selected_agents)) &
            (df['Map'].isin(selected_maps)) &
            (df['Date'].dt.date >= start_date_bee) &
            (df['Date'].dt.date <= end_date_bee)
        ]

        if not filtered_df.empty:
            avg_acs = filtered_df['ACS'].mean()
            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_facecolor('#000000')
            ax.set_facecolor('#000000')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#ffffff')
            ax.spines['bottom'].set_color('#ffffff')
            palette = sns.color_palette("husl", len(filtered_df['Agent'].unique()))
            sns.swarmplot(data=filtered_df, x='Map', y='ACS', hue='Agent', palette=palette, ax=ax)
            ax.axhline(avg_acs, color='yellow', linestyle='--', linewidth=1.5)
            ax.text(x=0.5, y=avg_acs+2, s=f"Avg ACS: {avg_acs:.1f}", color='yellow', fontsize=10, ha='left')
            ax.set_title(f"{selected_player_bee}'s ACS by Agent & Map", color='#FDB913', fontsize=14)
            ax.set_ylabel("ACS", color='white')
            ax.set_xlabel("Map", color='white')
            ax.tick_params(colors='white')
            ax.legend(title="Agent", loc='best', facecolor='#1a1a1a', labelcolor='white', title_fontsize=10, fontsize=9)
            st.pyplot(fig)
        else:
            st.info("No ACS data for selected filters.")

# ── TAB 5: COMPARE ─────────────────────────────────────────────────────────────
if st.session_state.active_tab == 5:
    st.subheader("🎚 Player vs VCT Benchmark Comparison")

    try:
        player_df = pd.read_csv("form.csv")
    except Exception as e:
        st.warning(f"Could not load player data: {e}")
        player_df = pd.DataFrame()

    if not player_df.empty:
        player_df['Date'] = pd.to_datetime(player_df['Date'], errors='coerce')
        player_df = player_df.dropna(subset=['Date'])

        all_players = sorted(player_df['Player'].dropna().unique())
        all_maps = sorted(player_df['Column 1'].dropna().unique())
        min_date = player_df['Date'].min().date()
        max_date = player_df['Date'].max().date()

        col1, col2 = st.columns(2)
        selected_player = col1.selectbox("Select a player:", all_players, key='compare_player')
        start_date = col1.date_input("Start date:", value=min_date, min_value=min_date, max_value=max_date, key='compare_start')
        end_date = col2.date_input("End date:", value=max_date, min_value=min_date, max_value=max_date, key='compare_end')
        selected_map = col2.selectbox("Filter by Map:", ["All"] + all_maps, key='compare_map')

        agent_roles = {
            'Jett':'Duelist','Raze':'Duelist','Reyna':'Duelist','Yoru':'Duelist','Phoenix':'Duelist','Iso':'Duelist','Waylay':'Duelist','Neon':'Duelist',
            'Skye':'Initiator','KAY/O':'Initiator','Breach':'Initiator','Fade':'Initiator','Sova':'Initiator','Gekko':'Initiator','Tejo':'Initiator',
            'Omen':'Controller','Brimstone':'Controller','Astra':'Controller','Viper':'Controller','Harbor':'Controller','Clove':'Controller',
            'Killjoy':'Sentinel','Cypher':'Sentinel','Chamber':'Sentinel','Sage':'Sentinel','Deadlock':'Sentinel','Vyse':'Sentinel'
        }
        vct_benchmarks = {
            'Duelist':    {'ACS':240,'KPR':0.90,'FBSR':0.55,'FKPR':0.18,'Atk_Entry':0.55},
            'Initiator':  {'ACS':196,'KPR':0.90,'FD':2,'K+A per Round':1,'Assists':10.0},
            'Controller': {'ACS':203,'KPR':0.90,'FD':2,'K+A per Round':1,'Multi_Kills':0.25},
            'Sentinel':   {'ACS':200,'KPR':0.90,'FD':2,'Multi_Kills':0.25,'Anchor_Time':48.0},
        }

        filtered = player_df[
            (player_df['Player'] == selected_player) &
            (player_df['Date'].dt.date >= start_date) &
            (player_df['Date'].dt.date <= end_date)
        ]
        if selected_map != "All":
            filtered = filtered[filtered['Column 1'] == selected_map]

        if not filtered.empty:
            if 'Atk_Entry' in filtered.columns:
                filtered['Atk_Entry'] = filtered['Atk_Entry'].fillna(0)

            for col in ['Rounds','Kills','Deaths','Assists','ACS','FK','FBSR','FKPR','KPR','Atk_Entry','FD','Multi-Kills']:
                if col in filtered.columns:
                    filtered[col] = pd.to_numeric(filtered[col].astype(str).str.replace('%','',regex=False), errors='coerce')

            agent_stats = filtered.groupby('Agent').agg(
                Rounds=('Rounds','sum'), Kills=('Kills','sum'), Deaths=('Deaths','sum'),
                Multi_Kills=('Multi_Kills','mean'), Assists=('Assists','mean'),
                ACS=('ACS','mean'), FK=('FK','sum'), FBSR=('FBSR','mean'),
                FKPR=('FKPR','mean'), KPR=('KPR','mean'), Atk_Entry=('Atk_Entry','mean'),
                FD=('FD','mean'), Anchor_Time=('Anchor_Time','mean')
            ).reset_index()

            agent_stats['K/D Ratio'] = agent_stats['Kills'] / agent_stats['Deaths'].replace(0, float('nan'))
            agent_stats['K+A per Round'] = (agent_stats['Kills'] + agent_stats['Assists']) / agent_stats['Rounds'].replace(0, float('nan'))
            agent_stats['Role'] = agent_stats['Agent'].map(agent_roles)

            selected_role = st.selectbox("Select Role:", sorted(vct_benchmarks.keys()), key='compare_role')
            role_agents = agent_stats[agent_stats['Role'] == selected_role]

            if not role_agents.empty:
                benchmark = vct_benchmarks[selected_role]
                player_avg = {}
                for stat in benchmark:
                    if stat == 'FK':
                        player_avg[stat] = (role_agents['FK'].sum() / role_agents['Rounds'].sum()) if role_agents['Rounds'].sum() > 0 else 0
                    elif stat == 'K+A per Round':
                        player_avg[stat] = (role_agents['Kills'].sum() + role_agents['Assists'].sum()) / role_agents['Rounds'].sum()
                    elif stat == 'K/D Ratio':
                        player_avg[stat] = role_agents['Kills'].sum() / role_agents['Deaths'].replace(0, float('nan')).sum()
                    else:
                        val = role_agents[stat].mean() if stat in role_agents.columns else 0
                        player_avg[stat] = val if pd.notna(val) else 0

                norm_base = {'ACS':300,'K/D Ratio':2.0,'FK':0.3,'K+A per Round':1.2,'KPR':1.2,'FBSR':1.0,'FKPR':0.3,'Atk_Entry':1.0,'FD':20.0,'Assists':20.0,'Multi_Kills':0.3,'Anchor_Time':80.0}

                categories = list(benchmark.keys())
                player_values = [player_avg.get(s,0) / norm_base[s] for s in categories]
                benchmark_values = [benchmark.get(s,0) / norm_base[s] for s in categories]

                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(r=player_values, theta=categories, fill='toself', name=selected_player, line=dict(color="#FDB913")))
                fig.add_trace(go.Scatterpolar(r=benchmark_values, theta=categories, fill='toself', name=f"VCT {selected_role} Avg", line=dict(color="#444444")))

                raw_values = []
                for stat in categories:
                    val = player_avg[stat]
                    bmark = benchmark[stat]
                    diff = val - bmark
                    sign = '+' if diff >= 0 else ''
                    color = "#14532d" if diff >= 0 else "#7f1d1d"
                    if stat in ['FBSR','FKPR','Atk_Entry']:
                        raw_values.append(f"<span style='color:{color}'><b>{stat}</b>: {sign}{diff*100:.1f}%</span>")
                    else:
                        raw_values.append(f"<span style='color:{color}'><b>{stat}</b>: {sign}{diff:.2f}</span>")

                fig.add_annotation(
                    text="<br>".join(raw_values), showarrow=False, align="left",
                    x=0.95, y=0.95, xref="paper", yref="paper",
                    bordercolor="#666", borderwidth=1, bgcolor="rgba(0,0,0,0.85)",
                    font=dict(color="white", size=12)
                )
                fig.update_layout(
                    polar=dict(
                        bgcolor="#000000",
                        radialaxis=dict(visible=False, showticklabels=False, ticks='', showline=False, gridcolor="#333333"),
                        angularaxis=dict(tickfont=dict(color="#FDB913"))
                    ),
                    showlegend=True, legend=dict(font=dict(color="#ffffff")),
                    plot_bgcolor='#000000', paper_bgcolor='#000000',
                    font=dict(family='Rajdhani', color='#FDB913'),
                    title=dict(text=f"{selected_role} Stats vs VCT Benchmark", font=dict(size=16, color='#FDB913')),
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No agents played in the selected role during this period.")
        else:
            st.info("No data found for this player in selected filters.")
    else:
        st.warning("No player stats found in form.csv")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
    <style>
        .footer { position:fixed; bottom:0; left:0; width:100%; background-color:#000000; color:#FDB913;
            text-align:center; font-size:13px; font-family:Rajdhani,sans-serif; padding:0.5rem 0; opacity:0.8; z-index:9999; }
    </style>
    <div class="footer">
        Made by: <b>Ominous</b> | X:
        <a href="https://x.com/_SushantJha" target="_blank" style="color:#FDB913;text-decoration:none;">@_SushantJha</a>
    </div>
""", unsafe_allow_html=True)
