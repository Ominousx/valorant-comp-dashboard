import streamlit as st
import pandas as pd
from PIL import Image
import os
import plotly.express as px
import plotly.graph_objects as go
import base64



# ── Auth ───────────────────────────────────────────────────────────────────────
USERNAME = "moon"
PASSWORD = "bleh"

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
encoded_bg = get_base64_image("wallt.png")
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@300;400;500;600;700&display=swap');
    * {{ font-family: 'Rajdhani', sans-serif !important; }}
    body {{
        background-image: url("data:image/jpg;base64,{encoded_bg}");
        background-size: cover; background-position: center;
        background-attachment: fixed; background-repeat: no-repeat;
        color: #ffffff; font-family: 'Rajdhani', sans-serif !important;
    }}
    .stApp {{ background-color: rgba(0,0,0,0.85); font-family: 'Rajdhani', sans-serif !important; }}
    .block-container {{ padding: 2rem; border-radius: 12px; font-family: 'Rajdhani', sans-serif !important; }}
    h1,h2,h3,h4,h5,h6,.stTabs,.stButton,p,div,span,label,input,select,textarea,button {{
        font-family: 'Rajdhani', sans-serif !important; color: #E63946;
    }}
    .stDataFrame,.stTable {{ background-color: #1a1a1a; font-family: 'Rajdhani', sans-serif !important; }}
    </style>
""", unsafe_allow_html=True)

st.title("Valorant Scrim Dashboard")
st.image("tyloo_logo.png", width=100)

# ── Load CSVs ──────────────────────────────────────────────────────────────────
try:
    form_df = pd.read_csv("form.csv")
    form_df = form_df[['Column 1', 'Agent', 'Result']].dropna().reset_index(drop=True)
except Exception as e:
    form_df = pd.DataFrame()
    st.warning(f"⚠️ Couldn't load form.csv: {e}")

@st.cache_data
def load_and_aggregate_matches(path="Advanced_Data-_Sheet1.csv"):
    """Read round-level data and aggregate into match-level rows."""
    raw = pd.read_csv(path)
    raw.columns = raw.columns.str.strip()
    for col in ['Result', 'Side', 'Site', 'Plant XvY', 'Pistol']:
        if col in raw.columns:
            raw[col] = raw[col].astype(str).str.strip().replace('nan', '')

    records = []
    for (map_name, team, date), match in raw.groupby(['Map', 'Team', 'Date'], sort=False):
        match = match.sort_values('Round').reset_index(drop=True)
        tier = match['Tier'].dropna().iloc[0] if 'Tier' in match.columns and match['Tier'].notna().any() else None

        r1  = match[match['Round'] == 1].iloc[0]  if len(match[match['Round'] == 1])  > 0 else None
        r13 = match[match['Round'] == 13].iloc[0] if len(match[match['Round'] == 13]) > 0 else None
        first_pistol  = 1 if (r1  is not None and r1['Result'].lower()  == 'win') else 0
        second_pistol = 1 if (r13 is not None and r13['Result'].lower() == 'win') else 0
        start_side    = r1['Side'] if r1 is not None else None

        first_half  = match[match['Round'] <= 12]
        second_half = match[match['Round'] >= 13]
        first_rounds_won  = (first_half['Result'].str.lower()  == 'win').sum()
        second_rounds_won = (second_half['Result'].str.lower() == 'win').sum()
        first_half_wr  = round(first_rounds_won  / len(first_half),  2) if len(first_half)  > 0 else None
        second_half_wr = round(second_rounds_won / len(second_half), 2) if len(second_half) > 0 else None

        def conversion(pistol_won, round_num):
            r = match[match['Round'] == round_num]
            if len(r) == 0:
                return None
            won = r.iloc[0]['Result'].lower() == 'win'
            if pistol_won:
                return 'WW' if won else 'WL'
            else:
                return 'LW' if won else 'LL'

        if start_side == 'Attack':
            atk_2nd = conversion(first_pistol,  2)
            def_2nd = conversion(second_pistol, 14)
        else:
            def_2nd = conversion(first_pistol,  2)
            atk_2nd = conversion(second_pistol, 14)

        planted    = match[(match['Time at Plant'].notna()) & (match['Time at Plant'].astype(str).str.strip() != '')]
        atk_plants = planted[planted['Side'] == 'Attack']
        def_plants = planted[planted['Side'] == 'Defence']
        atk_pp = round((atk_plants['Result'].str.lower() == 'win').sum() / len(atk_plants), 2) if len(atk_plants) > 0 else 0
        def_pp = round((def_plants['Result'].str.lower() == 'win').sum() / len(def_plants), 2) if len(def_plants) > 0 else 0

        site_pp = {}
        for site in ['A', 'B', 'C']:
            sa = atk_plants[atk_plants['Site'] == site]
            sd = def_plants[def_plants['Site'] == site]
            site_pp[f'Atk_PP_{site}'] = round((sa['Result'].str.lower() == 'win').sum() / len(sa), 2) if len(sa) > 0 else None
            site_pp[f'Def_PP_{site}'] = round((sd['Result'].str.lower() == 'win').sum() / len(sd), 2) if len(sd) > 0 else None

        total_won  = (match['Result'].str.lower() == 'win').sum()
        total_lost = (match['Result'].str.lower() == 'loss').sum()
        outcome = 'Win' if total_won > total_lost else 'Loss' if total_lost > total_won else 'Draw'

        records.append({
            'Date': date, 'Map': map_name, 'Team': team, 'Start': start_side,
            'First Pistol': first_pistol, 'First Rounds': first_rounds_won, 'First Half WR': first_half_wr,
            'Second Pistol': second_pistol, 'Second Rounds': second_rounds_won, 'Second Half WR': second_half_wr,
            'Atk_PP_Success': atk_pp, 'Def_PP_Success': def_pp,
            **site_pp,
            'Atk 2nd': atk_2nd, 'Def 2nd': def_2nd,
            'Outcome': outcome, 'Tier': tier,
        })

    out = pd.DataFrame(records)
    col_order = [
        'Date', 'Map', 'Team', 'Start',
        'First Pistol', 'First Rounds', 'First Half WR',
        'Second Pistol', 'Second Rounds', 'Second Half WR',
        'Atk_PP_Success', 'Def_PP_Success',
        'Atk_PP_A', 'Atk_PP_B', 'Atk_PP_C',
        'Def_PP_A', 'Def_PP_B', 'Def_PP_C',
        'Atk 2nd', 'Def 2nd', 'Outcome', 'Tier'
    ]
    out = out[[c for c in col_order if c in out.columns]]
    return out


@st.cache_data
def load_raw_rounds(path="Advanced_Data-_Sheet1.csv"):
    """Return cleaned round-level data for round-grain analyses (e.g. site post-plant)."""
    raw = pd.read_csv(path)
    raw.columns = raw.columns.str.strip()
    for col in ['Result', 'Side', 'Site', 'Plant XvY', 'Pistol', 'Team', 'Map']:
        if col in raw.columns:
            raw[col] = raw[col].astype(str).str.strip().replace('nan', '')
    if 'Date' in raw.columns:
        raw['Date'] = pd.to_datetime(raw['Date'], errors='coerce')
    if 'Tier' in raw.columns:
        raw['Tier'] = pd.to_numeric(raw['Tier'], errors='coerce')
    # Mark plant rounds
    raw['Planted'] = raw['Time at Plant'].notna() & (raw['Time at Plant'].astype(str).str.strip() != '')
    return raw

try:
    score_df = load_and_aggregate_matches("Advanced_Data-_Sheet1.csv")
    score_df['Date'] = pd.to_datetime(score_df['Date'], errors='coerce')
    if 'Tier' in score_df.columns:
        score_df['Tier'] = pd.to_numeric(score_df['Tier'], errors='coerce').fillna(1).astype(int)
    else:
        score_df['Tier'] = 1
    rounds_df = load_raw_rounds("Advanced_Data-_Sheet1.csv")
except Exception as e:
    score_df = pd.DataFrame()
    rounds_df = pd.DataFrame()
    st.warning(f"⚠️ Couldn't load/aggregate Advanced_Data-_Sheet1.csv: {e}")

try:
    foracs_df = pd.read_csv("foracs.csv")
except Exception as e:
    foracs_df = pd.DataFrame()
    st.warning(f"⚠️ Couldn't load foracs.csv: {e}")

# ── Sidebar Tier Filter ────────────────────────────────────────────────────────
TIER_LABELS = {1: "Tier 1 — Top", 2: "Tier 2 — Mid", 3: "Tier 3 — Lower"}
TIER_COLORS = {1: "#E63946", 2: "#9ca3af", 3: "#9a3412"}

with st.sidebar:
    st.markdown("## 🏆 Scrim Tier Filter")
    st.markdown("Filter all stats by opponent tier:")
    available_tiers = sorted(score_df['Tier'].unique()) if not score_df.empty else [1, 2, 3]
    selected_tiers = st.multiselect(
        "Select Tier(s)", options=available_tiers, default=available_tiers,
        format_func=lambda t: TIER_LABELS.get(t, f"Tier {t}"),
        key="global_tier_filter"
    )
    if not selected_tiers:
        st.warning("⚠️ No tier selected — showing all data.")
        selected_tiers = available_tiers
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

score_df_filtered = score_df[score_df['Tier'].isin(selected_tiers)].copy() if not score_df.empty else score_df.copy()

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
    .icon-tab-container { position:relative; width:100%; display:flex; flex-direction:column; align-items:center; margin-bottom:0.375rem !important; }
    .icon-display { display:flex; align-items:center; justify-content:center; margin-bottom:8px; cursor:pointer; padding:8px; border-radius:8px; transition:all 0.2s ease; }
    .icon-display:hover { background:rgba(230,57,70,0.1); transform:translateY(-2px); }
    .icon-display.active { background:#E63946 !important; }
    hr { margin-top:0.375rem !important; margin-bottom:0.375rem !important; border:none !important; height:1px !important; background-color:rgba(255,255,255,0.1) !important; }
    </style>
""", unsafe_allow_html=True)

cols = st.columns(6)
for idx, (col, icon, name) in enumerate(zip(cols, icons, tab_names)):
    with col:
        is_active = st.session_state.active_tab == idx
        active_class = "active" if is_active else ""
        st.markdown(f'<div class="icon-tab-container">', unsafe_allow_html=True)
        st.markdown(f'<div class="icon-display {active_class}">{icon}</div>', unsafe_allow_html=True)
        if st.button(name, key=f"icon_tab_{idx}", use_container_width=True, help=name):
            st.session_state.active_tab = idx
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<hr style='margin:0.5rem 0;'>", unsafe_allow_html=True)

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
        date_range = st.date_input("Select Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="overview_date_range")
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
            color='Win Rate %', color_continuous_scale=['#450a0a', '#E63946']
        )
        fig_map_wr.update_traces(textposition='outside', marker_line_color='#000000', marker_line_width=1.2)
        fig_map_wr.update_layout(
            plot_bgcolor='#000000', paper_bgcolor='#000000',
            font=dict(family='Rajdhani', size=14, color='#E63946'),
            title_font=dict(size=20, color='#E63946'),
            yaxis=dict(tickfont=dict(color='#ffffff'), categoryorder='total ascending', gridcolor='#333333'),
            xaxis=dict(title='Win Rate (%)', title_font=dict(color='#E63946'), tickfont=dict(color='#ffffff'), gridcolor='#333333', range=[0, 100])
        )
        st.plotly_chart(fig_map_wr, use_container_width=True)

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
            tier_map_summary, x='Map', y='Win Rate %', color='Tier Label',
            color_discrete_map={'Tier 1': '#E63946', 'Tier 2': '#9ca3af', 'Tier 3': '#9a3412'},
            barmode='group',
            text=tier_map_summary['Win Rate %'].apply(lambda x: f"{x:.0f}%"),
            title="Win Rate by Map & Tier"
        )
        fig_tier.update_traces(textposition='outside', marker_line_color='#333', marker_line_width=1)
        fig_tier.update_layout(
            plot_bgcolor='#000000', paper_bgcolor='#000000',
            font=dict(family='Rajdhani', color='#E63946'),
            title_font=dict(size=18, color='#E63946'),
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
                len(block) == 5 and block['Column 1'].nunique() == 1 and
                block['Result'].nunique() == 1 and block['Column 1'].iloc[0] == selected_map
            ):
                match_filter = (
                    (score_df_filtered['Map'] == map_match) &
                    (score_df_filtered['Outcome'].str.lower() == result_match.lower()) &
                    (score_df_filtered['Date'].isin(filtered_dates))
                )
                if not score_df_filtered[match_filter].empty:
                    agents = tuple(sorted(block['Agent'].tolist()))
                    teams.append({'Composition': agents, 'Result': result_match})
        df_comp = pd.DataFrame(teams)
        if not df_comp.empty:
            df_comp['Win']  = df_comp['Result'].apply(lambda x: 1 if x.lower() == 'win'  else 0)
            df_comp['Draw'] = df_comp['Result'].apply(lambda x: 1 if x.lower() == 'draw' else 0)
            df_comp['Loss'] = df_comp['Result'].apply(lambda x: 1 if x.lower() == 'loss' else 0)
            df_comp['Game'] = 1
            grouped = df_comp.groupby('Composition').agg(
                games=('Game','sum'), wins=('Win','sum'), draws=('Draw','sum'), losses=('Loss','sum')
            ).reset_index()
            grouped['Win Rate %'] = grouped['wins'] / grouped['games'] * 100
            grouped['Comp String'] = grouped['Composition'].apply(lambda x: '-'.join(x))
            grouped = grouped.sort_values(by='Win Rate %', ascending=False).head(15)

            st.markdown("""
            <style>
            .composition-bar { display:flex; align-items:center; background:#2a2a2a; border:1px solid #333; border-radius:4px; padding:8px; margin:3px 0; min-height:45px; position:relative; overflow:hidden; }
            .bar-background { position:absolute; left:180px; top:0; height:100%; background:#E63946; border-radius:0 4px 4px 0; z-index:1; }
            .agents-container { display:flex; gap:4px; align-items:center; min-width:170px; z-index:2; position:relative; }
            .agent-icon-img { width:28px; height:28px; border-radius:3px; border:1px solid rgba(255,255,255,0.2); }
            .win-rate-info { margin-left:auto; z-index:2; position:relative; color:white; font-weight:bold; text-align:right; padding-right:12px; }
            .win-percentage { font-size:16px; text-shadow:1px 1px 2px rgba(0,0,0,0.8); }
            .game-count { font-size:11px; color:#ccc; }
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

    st.subheader("📊 Win Rate by Agent by Player")
    if not foracs_df.empty and 'Result' in foracs_df.columns:
        foracs_agg = foracs_df.groupby(['Player', 'Agent']).agg(
            games=('Result', 'count'),
            wins=('Result', lambda x: (x.str.strip().str.lower() == 'win').sum())
        ).reset_index()
        foracs_agg['Win Rate %'] = (foracs_agg['wins'] / foracs_agg['games'] * 100).round(1)
        pivot       = foracs_agg.pivot_table(index='Player', columns='Agent', values='Win Rate %', aggfunc='mean')
        pivot_wins  = foracs_agg.pivot_table(index='Player', columns='Agent', values='wins',      aggfunc='sum')
        pivot_games = foracs_agg.pivot_table(index='Player', columns='Agent', values='games',     aggfunc='sum')
        if not pivot.empty:
            all_players = sorted(foracs_df['Player'].dropna().unique())
            all_agents  = sorted(foracs_df['Agent'].dropna().unique())
            pivot       = pivot.reindex(index=all_players, columns=all_agents)
            pivot_wins  = pivot_wins.reindex(index=all_players, columns=all_agents)
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
                        w  = int(pivot_wins.loc[player, agent]) if pd.notna(pivot_wins.loc[player, agent]) else 0
                        wr = float(pivot.loc[player, agent]) if pd.notna(pivot.loc[player, agent]) else 0
                        row.append(f"Win Rate: {wr:.0f}% ({w}/{g})")
                customdata.append(row)
            text = [[f"{v:.0f}%" if v >= 0 else "" for v in row] for row in z]
            fig_heat = go.Figure(data=go.Heatmap(
                z=z, x=all_agents, y=all_players, customdata=customdata,
                zmin=NOT_PLAYED, zmax=100,
                colorscale=[[0,'#9ca3af'],[0.01,'#7f1d1d'],[0.06,'#fecaca'],[0.36,'#fca5a5'],[0.66,'#ef4444'],[1,'#7f1d1d']],
                text=text, texttemplate="%{text}",
                textfont=dict(family='Rajdhani', size=12, color='white'),
                hoverongaps=False,
                hovertemplate="Player: %{y}<br>Agent: %{x}<br>%{customdata}<extra></extra>"
            ))
            fig_heat.update_layout(
                title="Win Rate % by Player and Agent",
                xaxis=dict(title='Agent', side='bottom', tickangle=-45, tickfont=dict(family='Rajdhani', color='#E63946')),
                yaxis=dict(title='Player', tickfont=dict(family='Rajdhani', color='#E63946'), autorange='reversed'),
                plot_bgcolor='#000000', paper_bgcolor='#000000',
                font=dict(family='Rajdhani', color='#E63946'),
                title_font=dict(size=18, color='#E63946'),
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
        maps  = sorted(score_df_filtered['Map'].dropna().unique())
        dates = sorted(score_df_filtered['Date'].dropna().dt.date.unique())

        col1, col2 = st.columns(2)
        selected_map = col1.selectbox("Filter by Map", ["All"] + maps)
        start_date   = col1.selectbox("Start Date", dates, format_func=lambda d: d.strftime("%Y-%m-%d"), key="insight_start")
        end_date     = col2.selectbox("End Date", dates, index=len(dates)-1, format_func=lambda d: d.strftime("%Y-%m-%d"), key="insight_end")

        filtered_df = score_df_filtered.copy()
        if selected_map != "All":
            filtered_df = filtered_df[filtered_df['Map'] == selected_map]
        if start_date and end_date:
            filtered_df = filtered_df[(filtered_df['Date'].dt.date >= start_date) & (filtered_df['Date'].dt.date <= end_date)]

        def extract_wr(row, side):
            if pd.isna(row['Start']) or pd.isna(row['First Half WR']) or pd.isna(row['Second Half WR']):
                return None
            if side == 'Attack':
                return row['First Half WR'] if row['Start'] == 'Attack' else row['Second Half WR']
            elif side == 'Defence':
                return row['First Half WR'] if row['Start'] == 'Defence' else row['Second Half WR']
            return None

        filtered_df['Atk WR Derived'] = filtered_df.apply(lambda row: extract_wr(row, 'Attack'),  axis=1)
        filtered_df['Def WR Derived'] = filtered_df.apply(lambda row: extract_wr(row, 'Defence'), axis=1)

        filtered_df['Date'] = filtered_df['Date'].dt.strftime('%Y-%m-%d')

        st.dataframe(filtered_df, use_container_width=True)

        st.markdown("### 🔍 Summary Stats")
        agg_dict = {
            'Games':       ('Outcome', 'count'),
            'Wins':        ('Outcome', lambda x: (x.str.lower() == 'win').sum()),
            'Draws':       ('Outcome', lambda x: (x.str.lower() == 'draw').sum()),
            'Losses':      ('Outcome', lambda x: (x.str.lower() == 'loss').sum()),
            'Avg_Atk_WR':  ('Atk WR Derived', 'mean'),
            'Avg_Def_WR':  ('Def WR Derived', 'mean'),
        }
        if 'Atk_PP_Success' in filtered_df.columns:
            agg_dict['Atk_PP_Success'] = ('Atk_PP_Success', 'mean')
        if 'Def_PP_Success' in filtered_df.columns:
            agg_dict['Def_PP_Success'] = ('Def_PP_Success', 'mean')

        summary = filtered_df.groupby('Map').agg(**agg_dict).reset_index()
        summary['Raw_Atk_WR']   = summary['Avg_Atk_WR']
        summary['Raw_Def_WR']   = summary['Avg_Def_WR']
        summary['Raw_Round_WR'] = (summary['Raw_Atk_WR'] + summary['Raw_Def_WR']) / 2
        summary['Round WR']     = summary['Raw_Round_WR'].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "-")
        summary['Avg_Atk_WR']   = summary['Avg_Atk_WR'].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "-")
        summary['Avg_Def_WR']   = summary['Avg_Def_WR'].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "-")

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
            .set_table_styles([{'selector': 'th', 'props': [('background-color','#1a1a1a'),('color','#E63946'),('text-align','center')]}])
        st.dataframe(styled_df, use_container_width=True)

        # Atk vs Def chart
        plot_df = summary[['Map', 'Raw_Atk_WR', 'Raw_Def_WR']].copy()
        plot_df.rename(columns={'Raw_Atk_WR': 'Attack', 'Raw_Def_WR': 'Defense'}, inplace=True)
        plot_df['Attack']   *= 100
        plot_df['Defense']  *= 100
        plot_df = plot_df.melt(id_vars='Map', var_name='Side', value_name='Win Rate (%)')
        fig = px.bar(
            plot_df, x='Map', y='Win Rate (%)', color='Side',
            color_discrete_map={'Attack': '#E63946', 'Defense': '#ffffff'},
            barmode='group',
            text=plot_df['Win Rate (%)'].apply(lambda x: f"{x:.1f}%"),
            title="Attack vs Defense Win Rates by Map"
        )
        fig.update_traces(textposition='outside', marker_line_color='#333333', marker_line_width=1.2, width=0.4)
        fig.update_layout(
            plot_bgcolor='#000000', paper_bgcolor='#000000',
            font=dict(color='#E63946', family='Rajdhani'),
            title_font=dict(color='#E63946', size=20),
            xaxis=dict(tickangle=-25, gridcolor='#333333'),
            yaxis=dict(range=[0, 100], gridcolor='#333333')
        )
        st.plotly_chart(fig, use_container_width=True)

        # Post-plant stacked chart
        if 'Atk_PP_Success' in score_df_filtered.columns and 'Def_PP_Success' in score_df_filtered.columns:
            st.markdown("### 📊 Post-Plant Success Rate by Map")
            pp_df = filtered_df.groupby('Map').agg({
                'Atk_PP_Success': 'mean',
                'Def_PP_Success': 'mean'
            }).reset_index()
            label_map = {"Atk_PP_Success": "Post Plant", "Def_PP_Success": "Retakes"}
            sort_label = st.selectbox("Sort by", list(label_map.values()), index=0)
            sort_col   = [k for k, v in label_map.items() if v == sort_label][0]
            sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True)
            ascending  = sort_order == "Ascending"
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
                color_discrete_map={'Post Plant': '#E63946', 'Retakes': '#ffffff'}
            )
            fig_pp.update_traces(textposition='inside', marker_line_color='#333333', marker_line_width=1.2)
            fig_pp.update_layout(
                plot_bgcolor='#000000', paper_bgcolor='#000000',
                font=dict(family='Rajdhani', size=14, color='#E63946'),
                title_font=dict(size=20, color='#E63946'),
                xaxis=dict(tickangle=-25, gridcolor='#333333', tickfont=dict(color='#fff')),
                yaxis=dict(range=[0, 100], gridcolor='#333333', tickfont=dict(color='#fff')),
                legend=dict(font=dict(color='#fff'))
            )
            st.plotly_chart(fig_pp, use_container_width=True)

        # ── Site-wise Post-Plant Breakdown (uses round-level data) ────────────
        if not rounds_df.empty:
            st.markdown("### 📍 Post-Plant Success by Site")

            # Filter round-level data by tier + date only — map is chosen independently below
            rd = rounds_df[rounds_df['Tier'].fillna(1).astype(int).isin(selected_tiers)].copy() if 'Tier' in rounds_df.columns else rounds_df.copy()
            if start_date and end_date:
                rd = rd[(rd['Date'] >= pd.Timestamp(start_date)) & (rd['Date'] <= pd.Timestamp(end_date))]

            maps_with_site = sorted(rd['Map'].dropna().unique())
            if maps_with_site:
                selected_map_site = st.selectbox(
                    "Select map for site breakdown:", maps_with_site, key="site_breakdown_map"
                )
                site_rd = rd[(rd['Map'] == selected_map_site) & (rd['Planted'] == True)]

                rows = []
                for site in ['A', 'B', 'C']:
                    atk_rounds = site_rd[(site_rd['Site'] == site) & (site_rd['Side'] == 'Attack')]
                    def_rounds = site_rd[(site_rd['Site'] == site) & (site_rd['Side'] == 'Defence')]

                    atk_n = len(atk_rounds)
                    def_n = len(def_rounds)
                    atk_wr = round((atk_rounds['Result'].str.lower() == 'win').sum() / atk_n * 100, 1) if atk_n > 0 else None
                    def_wr = round((def_rounds['Result'].str.lower() == 'win').sum() / def_n * 100, 1) if def_n > 0 else None

                    if atk_n > 0 or def_n > 0:
                        rows.append({
                            'Site': f'Site {site}',
                            'Post Plant (Atk)': atk_wr,
                            'Retake (Def)': def_wr,
                            'Atk Plants': atk_n,
                            'Def Plants': def_n,
                        })

                if rows:
                    site_summary = pd.DataFrame(rows)
                    site_long = site_summary.melt(
                        id_vars=['Site', 'Atk Plants', 'Def Plants'],
                        value_vars=['Post Plant (Atk)', 'Retake (Def)'],
                        var_name='Type', value_name='Win Rate (%)'
                    ).dropna(subset=['Win Rate (%)'])

                    def make_label(row):
                        n = row['Atk Plants'] if row['Type'] == 'Post Plant (Atk)' else row['Def Plants']
                        return f"{row['Win Rate (%)']:.0f}% (n={n})"

                    site_long['Label'] = site_long.apply(make_label, axis=1)
                    fig_site = px.bar(
                        site_long, x='Site', y='Win Rate (%)', color='Type', barmode='group',
                        text='Label',
                        color_discrete_map={'Post Plant (Atk)': '#E63946', 'Retake (Def)': '#60a5fa'},
                        title=f"Post-Plant Win Rate by Site — {selected_map_site}",
                        category_orders={'Site': ['Site A', 'Site B', 'Site C']}
                    )
                    fig_site.update_traces(textposition='outside', marker_line_color='#333', marker_line_width=1)
                    fig_site.add_hline(y=50, line_dash='dash', line_color='#666',
                        annotation_text='50%', annotation_font_color='#aaa')
                    fig_site.update_layout(
                        plot_bgcolor='#000000', paper_bgcolor='#000000',
                        font=dict(family='Rajdhani', color='#E63946'),
                        title_font=dict(size=18, color='#E63946'),
                        xaxis=dict(tickfont=dict(color='#fff'), gridcolor='#333'),
                        yaxis=dict(range=[0, 115], tickfont=dict(color='#fff'), gridcolor='#333', title='Win Rate (%)'),
                        legend=dict(font=dict(color='#fff')),
                        bargap=0.25
                    )
                    st.plotly_chart(fig_site, use_container_width=True)

                    display_site = site_summary.copy()
                    for col in ['Post Plant (Atk)', 'Retake (Def)']:
                        display_site[col] = display_site[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
                    st.dataframe(display_site, use_container_width=True, hide_index=True)
                else:
                    st.info(f"No site-level plant data for {selected_map_site} in selected filters.")

        # ── Attack Tempo Analysis ─────────────────────────────────────────────
        st.markdown("### ⏱️ Attack Tempo & Win Rate")
        st.markdown(
            "Rounds bucketed by time of first engagement on attack. "
            "Round starts at **1:40** — lower time remaining = earlier/more aggressive entry."
        )

        if not rounds_df.empty:
            tempo_rd = rounds_df[rounds_df['Tier'].fillna(1).astype(int).isin(selected_tiers)].copy() if 'Tier' in rounds_df.columns else rounds_df.copy()
            tempo_rd = tempo_rd[tempo_rd['Side'] == 'Attack'].copy()
            if selected_map != "All":
                tempo_rd = tempo_rd[tempo_rd['Map'] == selected_map]
            if start_date and end_date:
                tempo_rd = tempo_rd[(tempo_rd['Date'] >= pd.Timestamp(start_date)) & (tempo_rd['Date'] <= pd.Timestamp(end_date))]

            def time_to_seconds(t):
                try:
                    parts = str(t).strip().split(':')
                    return int(parts[0]) * 60 + int(parts[1])
                except:
                    return None

            tempo_rd['engage_secs'] = tempo_rd['Time to engagement'].apply(time_to_seconds)
            tempo_rd = tempo_rd.dropna(subset=['engage_secs'])

            bins   = [0,    40,           60,             75,           100]
            labels = ['Very Early (≤0:40)', 'Early (0:41–1:00)', 'Mid (1:01–1:15)', 'Late (1:16–1:40)']
            tempo_rd['Tempo'] = pd.cut(tempo_rd['engage_secs'], bins=bins, labels=labels)

            if not tempo_rd.empty:
                # ── Overall tempo bar chart ───────────────────────────────────
                tempo_overall = tempo_rd.groupby('Tempo', observed=True).agg(
                    Rounds=('Result', 'count'),
                    Wins=('Result', lambda x: (x.str.lower() == 'win').sum())
                ).reset_index()
                tempo_overall['Win Rate %'] = (tempo_overall['Wins'] / tempo_overall['Rounds'] * 100).round(1)
                tempo_overall['Label'] = tempo_overall.apply(
                    lambda r: f"{r['Win Rate %']:.0f}%\n(n={r['Rounds']})", axis=1
                )

                TEMPO_COLORS = {
                    'Very Early (≤0:40)':   '#60a5fa',
                    'Early (0:41–1:00)':    '#34d399',
                    'Mid (1:01–1:15)':      '#E63946',
                    'Late (1:16–1:40)':     '#f97316',
                }

                fig_tempo = go.Figure()
                for _, row in tempo_overall.iterrows():
                    fig_tempo.add_trace(go.Bar(
                        x=[row['Tempo']], y=[row['Win Rate %']],
                        name=str(row['Tempo']),
                        marker_color=TEMPO_COLORS.get(str(row['Tempo']), '#aaa'),
                        text=f"{row['Win Rate %']:.0f}%<br><span style='font-size:11px'>n={row['Rounds']}</span>",
                        textposition='outside',
                        showlegend=False,
                    ))
                fig_tempo.add_hline(y=50, line_dash='dash', line_color='#666',
                    annotation_text='50%', annotation_font_color='#aaa')
                fig_tempo.update_layout(
                    title='Attack Win Rate by Engagement Tempo',
                    plot_bgcolor='#000000', paper_bgcolor='#000000',
                    font=dict(family='Rajdhani', color='#E63946'),
                    title_font=dict(size=18, color='#E63946'),
                    xaxis=dict(tickfont=dict(color='#fff', size=13), gridcolor='#333',
                               categoryorder='array', categoryarray=labels),
                    yaxis=dict(range=[0, 115], tickfont=dict(color='#fff'), gridcolor='#333', title='Win Rate (%)'),
                    bargap=0.35,
                )
                st.plotly_chart(fig_tempo, use_container_width=True)

                # ── Per-map tempo heatmap ─────────────────────────────────────
                st.markdown("#### 🗺️ Tempo Win Rate by Map")
                map_tempo = tempo_rd.groupby(['Map', 'Tempo'], observed=True).agg(
                    Rounds=('Result', 'count'),
                    Wins=('Result', lambda x: (x.str.lower() == 'win').sum())
                ).reset_index()
                map_tempo['Win Rate %'] = (map_tempo['Wins'] / map_tempo['Rounds'] * 100).round(1)

                # Pivot for heatmap
                pivot = map_tempo.pivot(index='Map', columns='Tempo', values='Win Rate %')
                pivot_n = map_tempo.pivot(index='Map', columns='Tempo', values='Rounds')
                pivot = pivot.reindex(columns=labels)
                pivot_n = pivot_n.reindex(columns=labels)

                z = pivot.values.tolist()
                maps_list = pivot.index.tolist()
                customdata = []
                for map_name in maps_list:
                    row_custom = []
                    for tempo in labels:
                        wr = pivot.loc[map_name, tempo] if tempo in pivot.columns else None
                        n  = pivot_n.loc[map_name, tempo] if tempo in pivot_n.columns else 0
                        if pd.isna(wr):
                            row_custom.append("No data")
                        else:
                            row_custom.append(f"{wr:.0f}% (n={int(n)})")
                    customdata.append(row_custom)

                text_vals = []
                for map_name in maps_list:
                    row_text = []
                    for tempo in labels:
                        wr = pivot.loc[map_name, tempo] if tempo in pivot.columns else None
                        row_text.append(f"{wr:.0f}%" if pd.notna(wr) else "")
                    text_vals.append(row_text)

                fig_heat_tempo = go.Figure(data=go.Heatmap(
                    z=z,
                    x=labels,
                    y=maps_list,
                    customdata=customdata,
                    colorscale=[[0, '#7f1d1d'], [0.5, '#fef08a'], [1, '#14532d']],
                    zmid=50,
                    zmin=0, zmax=100,
                    text=text_vals,
                    texttemplate='%{text}',
                    textfont=dict(family='Rajdhani', size=13, color='white'),
                    hovertemplate='Map: %{y}<br>Tempo: %{x}<br>%{customdata}<extra></extra>',
                ))
                fig_heat_tempo.update_layout(
                    title='Attack Win Rate % by Map & Tempo',
                    plot_bgcolor='#000000', paper_bgcolor='#000000',
                    font=dict(family='Rajdhani', color='#E63946'),
                    title_font=dict(size=18, color='#E63946'),
                    xaxis=dict(tickfont=dict(color='#fff', size=12), side='bottom'),
                    yaxis=dict(tickfont=dict(color='#fff'), autorange='reversed'),
                    height=max(300, 55 * len(maps_list) + 120),
                )
                st.plotly_chart(fig_heat_tempo, use_container_width=True)

                # ── Summary table ─────────────────────────────────────────────
                st.markdown("#### 📋 Tempo Summary Table")
                tempo_table = tempo_overall[['Tempo', 'Rounds', 'Wins', 'Win Rate %']].copy()
                tempo_table['Losses'] = tempo_table['Rounds'] - tempo_table['Wins']
                tempo_table['Win Rate %'] = tempo_table['Win Rate %'].apply(lambda x: f"{x:.1f}%")
                st.dataframe(tempo_table[['Tempo', 'Rounds', 'Wins', 'Losses', 'Win Rate %']],
                             use_container_width=True, hide_index=True)
            else:
                st.info("No attack tempo data for selected filters.")
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
            "Select Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date
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
            color='Pistol Win Rate (%)', color_continuous_scale=['#450a0a', '#E63946'],
            title="Pistol Win Rates by Map"
        )
        fig_pistol.update_traces(textposition='outside', marker_line_color='#000000', marker_line_width=1.2)
        fig_pistol.update_layout(
            plot_bgcolor='#000000', paper_bgcolor='#000000',
            font=dict(family='Rajdhani', size=14, color='#E63946'),
            title_font=dict(size=20, color='#E63946'),
            xaxis=dict(tickfont=dict(color='#ffffff'), gridcolor='#333333'),
            yaxis=dict(range=[0,100], title='Win Rate (%)', title_font=dict(color='#E63946'), tickfont=dict(color='#ffffff'), gridcolor='#333333')
        )
        st.plotly_chart(fig_pistol, use_container_width=True)

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
                        color_discrete_map={'WW': '#E63946', 'WL': '#666666'}, hole=0.4)
                    fig_pie_win.update_traces(textinfo='label+percent', marker_line_color='#000000', marker_line_width=1.5)
                    fig_pie_win.update_layout(plot_bgcolor='#000000', paper_bgcolor='#000000',
                        font=dict(family='Rajdhani', size=14, color='#E63946'),
                        title_font=dict(size=18, color='#E63946'), legend=dict(font=dict(color='#ffffff')))
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
                        font=dict(family='Rajdhani', size=14, color='#E63946'),
                        title_font=dict(size=18, color='#E63946'), legend=dict(font=dict(color='#ffffff')))
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
        all_maps    = sorted(player_df['Column 1'].dropna().unique())
        min_date = player_df['Date'].min().date()
        max_date = player_df['Date'].max().date()
        col1, col2 = st.columns(2)
        selected_player = col1.selectbox("Select a player:", all_players)
        start_date      = col1.date_input("Start date:", min_value=min_date, max_value=max_date, value=min_date)
        end_date        = col2.date_input("End date:",   min_value=min_date, max_value=max_date, value=max_date)
        selected_map    = col2.selectbox("Filter by Map:", ["All"] + all_maps)
        filtered = player_df[
            (player_df['Player'] == selected_player) &
            (player_df['Date'].dt.date >= start_date) &
            (player_df['Date'].dt.date <= end_date)
        ]
        if selected_map != "All":
            filtered = filtered[filtered['Column 1'] == selected_map]
        if not filtered.empty:
            agent_stats = filtered.groupby('Agent').agg(
                Rounds=('Rounds','sum'), Kills=('Kills','sum'), Deaths=('Deaths','sum'),
                Assists=('Assists','sum'), ACS=('ACS','mean'), FK=('FK','sum'),
                Plants=('Plants','sum'), FD=('FD','sum'), FD_Def=('FD Def','sum') if 'FD Def' in filtered.columns else ('FD','sum')
            ).reset_index()
            agent_stats['K/D Ratio']     = agent_stats['Kills'] / agent_stats['Deaths'].replace(0, float('nan'))
            agent_stats['K+A per Round'] = (agent_stats['Kills'] + agent_stats['Assists']) / agent_stats['Rounds'].replace(0, float('nan'))
            agent_stats['FK-FD']         = agent_stats['FK'] - agent_stats['FD']
            display_df = agent_stats.round(2)[['Agent','Rounds','Kills','Deaths','Assists','ACS','FK-FD','Plants','K/D Ratio','K+A per Round']]
            st.markdown(f"### 🔍 Agent Performance for {selected_player} ({start_date} → {end_date})")
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No data for this player in the selected filters.")
    else:
        st.warning("No player stats found in form.csv")

    with st.expander("🐝 Player ACS Beeswarm Plot"):
        import seaborn as sns
        import matplotlib.pyplot as plt
        df_bee = pd.read_csv("foracs.csv")
        df_bee['Date'] = pd.to_datetime(df_bee['Date'], errors='coerce')
        df_bee['ACS']  = pd.to_numeric(df_bee['ACS'], errors='coerce')
        players_bee = sorted(df_bee['Player'].dropna().unique())
        agents_bee  = sorted(df_bee['Agent'].dropna().unique())
        maps_bee    = sorted(df_bee['Map'].dropna().unique())
        dates_bee   = sorted(df_bee['Date'].dropna().dt.date.unique())
        col1, col2 = st.columns(2)
        selected_player_bee = col1.selectbox("Select Player", players_bee, key='bee_player')
        selected_agents_bee = col2.multiselect("Filter by Agent(s)", agents_bee, default=agents_bee)
        selected_maps_bee   = st.multiselect("Filter by Map(s)", maps_bee, default=maps_bee)
        start_date_bee = st.date_input("Start Date", value=min(dates_bee), min_value=min(dates_bee), max_value=max(dates_bee), key='bee_start')
        end_date_bee   = st.date_input("End Date",   value=max(dates_bee), min_value=min(dates_bee), max_value=max(dates_bee), key='bee_end')
        filtered_bee = df_bee[
            (df_bee['Player'] == selected_player_bee) &
            (df_bee['Agent'].isin(selected_agents_bee)) &
            (df_bee['Map'].isin(selected_maps_bee)) &
            (df_bee['Date'].dt.date >= start_date_bee) &
            (df_bee['Date'].dt.date <= end_date_bee)
        ]
        if not filtered_bee.empty:
            avg_acs = filtered_bee['ACS'].mean()
            fig_bee, ax = plt.subplots(figsize=(10, 5))
            fig_bee.patch.set_facecolor('#000000')
            ax.set_facecolor('#000000')
            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#ffffff'); ax.spines['bottom'].set_color('#ffffff')
            palette = sns.color_palette("husl", len(filtered_bee['Agent'].unique()))
            sns.swarmplot(data=filtered_bee, x='Map', y='ACS', hue='Agent', palette=palette, ax=ax)
            ax.axhline(avg_acs, color='#E63946', linestyle='--', linewidth=1.5)
            ax.text(x=0.5, y=avg_acs+2, s=f"Avg ACS: {avg_acs:.1f}", color='#E63946', fontsize=10)
            ax.set_title(f"{selected_player_bee}'s ACS by Agent & Map", color='#E63946', fontsize=14)
            ax.set_ylabel("ACS", color='white'); ax.set_xlabel("Map", color='white')
            ax.tick_params(colors='white')
            ax.legend(title="Agent", loc='best', facecolor='#1a1a1a', labelcolor='white', title_fontsize=10, fontsize=9)
            st.pyplot(fig_bee)
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
        all_maps    = sorted(player_df['Column 1'].dropna().unique())
        min_date = player_df['Date'].min().date()
        max_date = player_df['Date'].max().date()
        col1, col2 = st.columns(2)
        selected_player = col1.selectbox("Select a player:", all_players, key='compare_player')
        start_date      = col1.date_input("Start date:", value=min_date, min_value=min_date, max_value=max_date, key='compare_start')
        end_date        = col2.date_input("End date:",   value=max_date, min_value=min_date, max_value=max_date, key='compare_end')
        selected_map    = col2.selectbox("Filter by Map:", ["All"] + all_maps, key='compare_map')

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
            for col in ['Rounds','Kills','Deaths','Assists','ACS','FK','FBSR','FKPR','KPR','Atk_Entry','FD','Multi_Kills']:
                if col in filtered.columns:
                    filtered[col] = pd.to_numeric(filtered[col].astype(str).str.replace('%','',regex=False), errors='coerce')

            agent_stats = filtered.groupby('Agent').agg(
                Rounds=('Rounds','sum'), Kills=('Kills','sum'), Deaths=('Deaths','sum'),
                Multi_Kills=('Multi_Kills','mean'), Assists=('Assists','mean'),
                ACS=('ACS','mean'), FK=('FK','sum'), FBSR=('FBSR','mean'),
                FKPR=('FKPR','mean'), KPR=('KPR','mean'), Atk_Entry=('Atk_Entry','mean'),
                FD=('FD','mean'), Anchor_Time=('Anchor_Time','mean')
            ).reset_index()
            agent_stats['K/D Ratio']     = agent_stats['Kills'] / agent_stats['Deaths'].replace(0, float('nan'))
            agent_stats['K+A per Round'] = (agent_stats['Kills'] + agent_stats['Assists']) / agent_stats['Rounds'].replace(0, float('nan'))
            agent_stats['Role']          = agent_stats['Agent'].map(agent_roles)

            selected_role = st.selectbox("Select Role:", sorted(vct_benchmarks.keys()), key='compare_role')
            role_agents   = agent_stats[agent_stats['Role'] == selected_role]

            if not role_agents.empty:
                benchmark  = vct_benchmarks[selected_role]
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

                norm_base  = {'ACS':300,'K/D Ratio':2.0,'FK':0.3,'K+A per Round':1.2,'KPR':1.2,'FBSR':1.0,'FKPR':0.3,'Atk_Entry':1.0,'FD':20.0,'Assists':20.0,'Multi_Kills':0.3,'Anchor_Time':80.0}
                categories       = list(benchmark.keys())
                player_values    = [player_avg.get(s,0) / norm_base[s] for s in categories]
                benchmark_values = [benchmark.get(s,0) / norm_base[s] for s in categories]

                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(r=player_values,    theta=categories, fill='toself', name=selected_player,          line=dict(color="#E63946")))
                fig_radar.add_trace(go.Scatterpolar(r=benchmark_values, theta=categories, fill='toself', name=f"VCT {selected_role} Avg", line=dict(color="#444444")))

                raw_values = []
                for stat in categories:
                    val   = player_avg[stat]
                    bmark = benchmark[stat]
                    diff  = val - bmark
                    sign  = '+' if diff >= 0 else ''
                    color = "#14532d" if diff >= 0 else "#7f1d1d"
                    if stat in ['FBSR','FKPR','Atk_Entry']:
                        raw_values.append(f"<span style='color:{color}'><b>{stat}</b>: {sign}{diff*100:.1f}%</span>")
                    else:
                        raw_values.append(f"<span style='color:{color}'><b>{stat}</b>: {sign}{diff:.2f}</span>")

                fig_radar.add_annotation(
                    text="<br>".join(raw_values), showarrow=False, align="left",
                    x=0.95, y=0.95, xref="paper", yref="paper",
                    bordercolor="#666", borderwidth=1, bgcolor="rgba(0,0,0,0.85)",
                    font=dict(color="white", size=12)
                )
                fig_radar.update_layout(
                    polar=dict(
                        bgcolor="#000000",
                        radialaxis=dict(visible=False, showticklabels=False, ticks='', showline=False, gridcolor="#333333"),
                        angularaxis=dict(tickfont=dict(color="#E63946"))
                    ),
                    showlegend=True, legend=dict(font=dict(color="#ffffff")),
                    plot_bgcolor='#000000', paper_bgcolor='#000000',
                    font=dict(family='Rajdhani', color='#E63946'),
                    title=dict(text=f"{selected_role} Stats vs VCT Benchmark", font=dict(size=16, color='#E63946')),
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                st.plotly_chart(fig_radar, use_container_width=True)
            else:
                st.info("No agents played in the selected role during this period.")
        else:
            st.info("No data found for this player in selected filters.")
    else:
        st.warning("No player stats found in form.csv")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
    <style>
        .footer { position:fixed; bottom:0; left:0; width:100%; background-color:#000000; color:#E63946;
            text-align:center; font-size:13px; font-family:Rajdhani,sans-serif; padding:0.5rem 0; opacity:0.8; z-index:9999; }
    </style>
    <div class="footer">
        Made by: <b>Ominous</b> | X:
        <a href="https://x.com/_SushantJha" target="_blank" style="color:#E63946;text-decoration:none;">@_SushantJha</a>
    </div>
""", unsafe_allow_html=True)
