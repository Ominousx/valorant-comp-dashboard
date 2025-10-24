import streamlit as st
import pandas as pd
from PIL import Image
import os
import plotly.express as px
from data_cleaner import clean_scrim_form
import base64

# Hardcoded credentials
USERNAME = "admin"
PASSWORD = "wolves123"

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
    body {{
        background-image: url("data:image/jpg;base64,{encoded_bg}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
        color: #ffffff;
    }}

    .stApp {{
        background-color: rgba(0, 0, 0, 0.85);
    }}

    .block-container {{
        padding: 2rem;
        border-radius: 12px;
    }}

    h1, h2, h3, .stTabs, .stButton {{
        font-family: 'Inter', sans-serif;
        color: #FDB913;
    }}

    .stDataFrame, .stTable {{
        background-color: #1a1a1a;
    }}
    </style>
""", unsafe_allow_html=True)

st.title("Valorant Scrim Dashboard")
st.image("wolves_logo.png", width=100)


# Load form.csv for overview and map comps
try:
    form_df = pd.read_csv("form.csv")
    form_df = form_df[['Column 1', 'Agent', 'Result']].dropna().reset_index(drop=True)
except Exception as e:
    form_df = pd.DataFrame()
    st.warning(f"⚠️ Couldn't load form.csv: {e}")

# Load cleaned_score.csv for Round Insights
try:
    score_df = pd.read_csv("cleaned_score.csv")
except Exception as e:
    score_df = pd.DataFrame()
    st.warning(f"⚠️ Couldn't load cleaned_score.csv: {e}")

tabs = st.tabs(["📊 Overview", "🧩 Map Composition Win Rates", "📈 Round Insights","🔫 Pistol Insights","🔢 Player Stats","🆚 Player Comparison"])

# 📊 OVERVIEW TAB
with tabs[0]:
    st.markdown("### 📅 Filter by Date Range")
    overview_dates = sorted(score_df['Date'].dropna().unique())
    date_col1, date_col2 = st.columns(2)
    start_date_overview = date_col1.selectbox("Start Date (Overview)", overview_dates, key="overview_start")
    end_date_overview = date_col2.selectbox("End Date (Overview)", overview_dates, index=len(overview_dates)-1, key="overview_end")

    filtered_score = score_df[(score_df['Date'] >= start_date_overview) & (score_df['Date'] <= end_date_overview)]

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
        # 📊 Map Win Rate Horizontal Bar Chart
        st.markdown("### 🗺️ Map Win Rates")

        winrate_df = summary[['Map', 'Win Rate']].dropna().copy()
        winrate_df['Win Rate %'] = winrate_df['Win Rate'] * 100
        winrate_df = winrate_df.sort_values(by='Win Rate %', ascending=False)

        fig_map_wr = px.bar(
            winrate_df,
            x='Win Rate %',
            y='Map',
            orientation='h',
            text=winrate_df['Win Rate %'].apply(lambda x: f"{x:.1f}%"),
            title="Map Win Rates",
            labels={'Win Rate %': 'Win Rate (%)', 'Map': 'Map'},
            color='Win Rate %',
            color_continuous_scale=['#ff0000', '#FDB913']
        )

        fig_map_wr.update_traces(
            textposition='outside',
            marker_line_color='#000000',
            marker_line_width=1.2
        )

        fig_map_wr.update_layout(
            plot_bgcolor='#000000',
            paper_bgcolor='#000000',
            font=dict(family='Inter', size=14, color='#FDB913'),
            title_font=dict(size=20, color='#FDB913'),
            yaxis=dict(
                tickfont=dict(color='#ffffff'),
                categoryorder='total ascending',
                gridcolor='#333333'
            ),
            xaxis=dict(
                title='Win Rate (%)',
                title_font=dict(color='#FDB913'),
                tickfont=dict(color='#ffffff'),
                gridcolor='#333333',
                range=[0, 100]
            )
        )

        st.plotly_chart(fig_map_wr, use_container_width=True)

    else:
        st.info("No scrim data in this date range.")

### --- Composition Win Rate Chart (Styled like rib.gg) ---

# This block should only be inside the Map Composition tab
with tabs[1]:
    st.subheader("Top 5-agent Composition Win Rates by Map")
    if not form_df.empty:
        valid_maps = []
        for i in range(0, len(form_df) - 4, 5):
            block = form_df.iloc[i:i+5]
            if len(block) == 5 and block['Column 1'].nunique() == 1 and block['Result'].nunique() == 1:
                valid_maps.append(block['Column 1'].iloc[0])

        valid_maps = sorted(set(valid_maps))
        selected_map = st.selectbox("Select a map:", valid_maps)

        teams = []
        filtered_dates = set(score_df['Date'])
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
                    (score_df['Map'] == map_match) &
                    (score_df['Outcome'].str.lower() == result_match.lower()) &
                    (score_df['Date'].isin(filtered_dates))
                )
                if not score_df[match_filter].empty:
                    agents = tuple(sorted(block['Agent'].tolist()))
                    teams.append({
                        'Composition': agents,
                        'Result': result_match
                    })

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

        def get_agent_icon(agent_name):
            path = f"assets/{agent_name}.png"
            if os.path.exists(path):
                return Image.open(path)
            return None

        # Add a column with the first agent's icon
        grouped['Win Rate %'] = grouped['wins'] / grouped['games'] * 100
        grouped['Comp String'] = grouped['Composition'].apply(lambda x: '-'.join(x))
        grouped = grouped.sort_values(by='Win Rate %', ascending=False).head(15)

        # 👇 Add this directly below — no extra indentation
        grouped['First Agent'] = grouped['Composition'].apply(lambda x: x[0])
        grouped['Icon Path'] = grouped['First Agent'].apply(lambda agent: f"assets/{agent}.png" if os.path.exists(f"assets/{agent}.png") else None)

# Agent Icons Display with Bar Chart (rib.gg style)
        if not grouped.empty:
            # Custom CSS for rib.gg style layout
            st.markdown("""
            <style>
            .composition-container {
                margin: 4px 0;
            }
            .composition-bar {
                display: flex;
                align-items: center;
                background: #2a2a2a;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 8px;
                margin: 3px 0;
                min-height: 45px;
                position: relative;
                overflow: hidden;
            }
            .bar-background {
                position: absolute;
                left: 180px;
                top: 0;
                height: 100%;
                background: #FDB913;
                border-radius: 0 4px 4px 0;
                z-index: 1;
            }
            .agents-container {
                display: flex;
                gap: 4px;
                align-items: center;
                min-width: 170px;
                z-index: 2;
                position: relative;
            }
            .agent-icon-img {
                width: 28px;
                height: 28px;
                border-radius: 3px;
                border: 1px solid rgba(255,255,255,0.2);
            }
            .win-rate-info {
                margin-left: auto;
                z-index: 2;
                position: relative;
                color: white;
                font-weight: bold;
                text-align: right;
                padding-right: 12px;
            }
            .win-percentage {
                font-size: 16px;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
            }
            .game-count {
                font-size: 11px;
                color: #ccc;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown(f"### Top Compositions on {selected_map}")
            
            # Calculate max width for bar scaling
            max_win_rate = grouped['Win Rate %'].max()
            
            for idx, row in grouped.iterrows():
                composition = row['Composition']
                win_rate = row['Win Rate %']
                games = row['games']
                wins = row['wins']
                losses = row['losses']
                draws = row['draws']
                
                # Calculate bar width percentage (scale to fit remaining space)
                bar_width_percent = (win_rate / max_win_rate * 80) if max_win_rate > 0 else 0
                
                # Create agent icons HTML
                icons_html = ""
                for agent in composition:
                    icon_name = agent.lower().replace('/', '_').replace(' ', '_')
                    icon_path = f"assets/agents/{icon_name}.png"
                    
                    if os.path.exists(icon_path):
                        # Convert to base64 for HTML embedding
                        import base64
                        try:
                            with open(icon_path, "rb") as img_file:
                                img_data = base64.b64encode(img_file.read()).decode()
                            icons_html += f'<img src="data:image/png;base64,{img_data}" class="agent-icon-img" title="{agent}" />'
                        except:
                            icons_html += f'<div class="agent-icon-img" style="background:#666;color:white;display:flex;align-items:center;justify-content:center;font-size:10px;" title="{agent}">{agent[:2]}</div>'
                    else:
                        icons_html += f'<div class="agent-icon-img" style="background:#666;color:white;display:flex;align-items:center;justify-content:center;font-size:10px;" title="{agent}">{agent[:2]}</div>'
                
                # Create the complete composition bar (rib.gg style)
                composition_html = f"""
                <div class="composition-container">
                    <div class="composition-bar">
                        <div class="bar-background" style="width: {bar_width_percent}%;"></div>
                        <div class="agents-container">
                            {icons_html}
                        </div>
                        <div class="win-rate-info">
                            <div class="win-percentage">{win_rate:.1f}%</div>
                            <div class="game-count">({games} games)</div>
                        </div>
                    </div>
                </div>
                """
                
                st.markdown(composition_html, unsafe_allow_html=True)
        else:
            st.info(f"No composition data available for {selected_map}")

# 📈 ROUND INSIGHTS TAB
with tabs[2]:
    st.subheader("📈 Round Insights from cleaned_score.csv")
    if not score_df.empty:
        maps = sorted(score_df['Map'].dropna().unique())
        dates = sorted(score_df['Date'].dropna().unique())

        col1, col2 = st.columns(2)
        selected_map = col1.selectbox("Filter by Map", ["All"] + maps)
        start_date = col1.selectbox("Start Date", dates, key="insight_start")
        end_date = col2.selectbox("End Date", dates, index=len(dates)-1, key="insight_end")

        filtered_df = score_df.copy()
        if selected_map != "All":
            filtered_df = filtered_df[filtered_df['Map'] == selected_map]

        if start_date and end_date:
            filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]

        # Derive Atk/Def WR based on Star Side
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
            'Avg_Atk_WR': ('Atk WR Derived', lambda x: pd.to_numeric(x.astype(str).str.replace('%','', regex=False), errors='coerce').mean()),
            'Avg_Def_WR': ('Def WR Derived', lambda x: pd.to_numeric(x.astype(str).str.replace('%','', regex=False), errors='coerce').mean()),

        }

        if 'Atk PP %' in filtered_df.columns:
            agg_dict['Atk_PP_Success'] = (
                'Atk PP %',
                lambda x: pd.to_numeric(x.fillna('0').str.replace('%', ''), errors='coerce').mean()
            )

        if 'Def PP %' in filtered_df.columns:
            agg_dict['Def_PP_Success'] = (
                'Def PP %',
                lambda x: pd.to_numeric(x.fillna('0').str.replace('%', ''), errors='coerce').mean()
            )


        summary = filtered_df.groupby('Map').agg(**agg_dict).reset_index()
        # Calculate Round Win Rate using (Atk + Def) / 2
        summary['Raw_Round_WR'] = (summary['Avg_Atk_WR'] + summary['Avg_Def_WR']) / 2
        summary['Round WR'] = summary['Raw_Round_WR'].apply(lambda x: f"{x * 100:.1f}%" if pd.notnull(x) else "-")


        # Optional: Format WRs as percentages
        # Save raw numeric values for chart use (before formatting to %)
        summary['Raw_Atk_WR'] = summary['Avg_Atk_WR']
        summary['Raw_Def_WR'] = summary['Avg_Def_WR']
        summary['Raw_Round_WR'] = (summary['Raw_Atk_WR'] + summary['Raw_Def_WR']) / 2
        summary['Round WR'] = summary['Raw_Round_WR'].apply(lambda x: f"{x * 100:.1f}%" if pd.notnull(x) else "-")



        summary['Avg_Atk_WR'] = summary['Avg_Atk_WR'].apply(lambda x: f"{x * 100:.1f}%" if pd.notnull(x) else "-")
        summary['Avg_Def_WR'] = summary['Avg_Def_WR'].apply(lambda x: f"{x * 100:.1f}%" if pd.notnull(x) else "-")
        display_cols = ['Map', 'Games', 'Wins', 'Draws', 'Losses', 'Avg_Atk_WR', 'Avg_Def_WR','Round WR']

        def highlight_win_rates(val, threshold_low=40, threshold_high=60):
            try:
                val = float(val.replace('%', ''))
            except:
                return ''
            if val >= threshold_high:
                return 'background-color: #14532d; color: white;'  # green
            elif val < threshold_low:
                return 'background-color: #7f1d1d; color: white;'  # red
            else:
                return 'background-color: #78350f; color: white;'  # amber

        styled_df = summary[display_cols].style\
            .applymap(highlight_win_rates, subset=['Avg_Atk_WR', 'Avg_Def_WR','Round WR'])\
            .set_properties(**{'text-align': 'center'})\
            .set_table_styles([{
                'selector': 'th',
                'props': [('background-color', '#1a1a1a'), ('color', '#FDB913'), ('text-align', 'center')]
            }])

        # Only show selected columns in the summary table (hide raw WRs)
        display_cols = ['Map', 'Games', 'Wins', 'Draws', 'Losses', 'Avg_Atk_WR', 'Avg_Def_WR','Round WR']
        st.dataframe(styled_df, use_container_width=True)

        # Visualize Attack vs Defense Win Rates
        # Prepare data
        plot_df = summary[['Map', 'Raw_Atk_WR', 'Raw_Def_WR']].copy()
        plot_df.rename(columns={'Raw_Atk_WR': 'Attack', 'Raw_Def_WR': 'Defense'}, inplace=True)
        plot_df['Attack'] *= 100
        plot_df['Defense'] *= 100

        # Melt for plotting
        plot_df = plot_df.melt(id_vars='Map', var_name='Side', value_name='Win Rate (%)')
        plot_df['Map'] = pd.Categorical(plot_df['Map'], categories=plot_df.groupby('Map')['Win Rate (%)'].mean().sort_values(ascending=False).index, ordered=True)

        # Wolves color map
        color_map = {
            'Attack': '#FDB913',   # Gold
            'Defense': '#ffffff'   # White
        }

        fig = px.bar(
            plot_df,
            x='Map',
            y='Win Rate (%)',
            color='Side',
            color_discrete_map=color_map,
            barmode='group',
            text=plot_df['Win Rate (%)'].apply(lambda x: f"{x:.1f}%"),
            title="Attack vs Defense Win Rates by Map"
        )

        fig.update_traces(
            textposition='outside',
            marker_line_color='#333333',
            marker_line_width=1.2,
            width=0.4
        )

        fig.update_layout(
            plot_bgcolor='#000000',
            paper_bgcolor='#000000',
            font=dict(color='#FDB913', family='Inter'),
            title_font=dict(color='#FDB913', size=20),
            legend_title_text='Side',
            xaxis=dict(tickangle=-25, gridcolor='#333333'),
            yaxis=dict(range=[0, 100], gridcolor='#333333')
        )

        st.plotly_chart(fig, use_container_width=True)

        #--- Post-Plant Success Rate Bar Chart ---
        if 'Atk_PP_Success' in score_df.columns and 'Def_PP_Success' in score_df.columns:
            st.markdown("### 📊 Post-Plant Success Rate by Map")

            # Fresh aggregation directly from original score_df
            pp_df = score_df.groupby('Map').agg({
                'Atk_PP_Success': lambda x: pd.to_numeric(x.astype(str).str.replace('%','', regex=False), errors='coerce').mean(),
                'Def_PP_Success': lambda x: pd.to_numeric(x.astype(str).str.replace('%','', regex=False), errors='coerce').mean()
            }).reset_index()

            label_map = {
                "Atk_PP_Success": "Post Plant",
                "Def_PP_Success": "Retakes"
            }

            sort_label = st.selectbox("Sort by", list(label_map.values()), index=0)
            sort_col = [k for k, v in label_map.items() if v == sort_label][0]
            sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True)
            ascending = sort_order == "Ascending"

            # Optional: convert to 0–100 range if needed
            if pp_df['Atk_PP_Success'].max() <= 1.0:
                pp_df['Atk_PP_Success'] *= 100
                pp_df['Def_PP_Success'] *= 100

            pp_df = pp_df.sort_values(by=sort_col, ascending=ascending)
            pp_df['Map'] = pd.Categorical(pp_df['Map'], categories=pp_df['Map'], ordered=True)

            pp_df.rename(columns=label_map, inplace=True)
            pp_df_long = pp_df.melt(id_vars='Map', var_name='Side', value_name='Post-Plant Success (%)')

            fig_pp = px.bar(
                pp_df_long,
                x='Map',
                y='Post-Plant Success (%)',
                color='Side',
                barmode='stack',
                text=pp_df_long['Post-Plant Success (%)'].apply(lambda x: f"{x:.1f}%"),
                title="Post-Plant Success Rate (Stacked Atk + Def)",
                color_discrete_map={
                    'Post Plant': '#FDB913',
                    'Retakes': '#ffffff'
                }
            )

            fig_pp.update_traces(
                textposition='inside',
                marker_line_color='#333333',
                marker_line_width=1.2
            )

            fig_pp.update_layout(
                plot_bgcolor='#000000',
                paper_bgcolor='#000000',
                font=dict(family='Inter, sans-serif', size=14, color='#FDB913'),
                title_font=dict(size=20, color='#FDB913'),
                xaxis=dict(
                    title='Map',
                    title_font=dict(size=16, color='#FDB913'),
                    tickfont=dict(size=14, color='#ffffff'),
                    tickangle=-25,
                    gridcolor='#333333'
                ),
                yaxis=dict(
                    title='Post-Plant Success (%)',
                    title_font=dict(size=16, color='#FDB913'),
                    tickfont=dict(size=14, color='#ffffff'),
                    gridcolor='#333333',
                    range=[0, 100]
                ),
                legend=dict(
                    font=dict(size=13, color='#ffffff')
                )
            )

            st.plotly_chart(fig_pp, use_container_width=True)



from datetime import datetime

from datetime import datetime

# 📊 GRAPH INSIGHTS TAB
with tabs[3]:
    st.subheader("🔫 Pistol Round Win Rate by Map")

    if not score_df.empty:
        # Ensure date column is in datetime format
        score_df['Date'] = pd.to_datetime(score_df['Date'], errors='coerce')

        # Date filter
        min_date = score_df['Date'].min()
        max_date = score_df['Date'].max()

        start_date, end_date = st.date_input(
            "Select Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        # Filter dataframe by date range
        filtered_df = score_df[(score_df['Date'] >= pd.to_datetime(start_date)) & (score_df['Date'] <= pd.to_datetime(end_date))]

        # Calculate pistol stats
        filtered_df['Total Pistols Won'] = filtered_df['First Pistol'] + filtered_df['Second Pistol']
        grouped = filtered_df.groupby('Map').agg(
            Total_Pistols_Won=('Total Pistols Won', 'sum'),
            Total_Pistols_Played=('Map', 'count')
        ).reset_index()

        grouped['Total_Pistols_Played'] *= 2  # 2 pistol rounds per map
        grouped['Pistol Win Rate (%)'] = (grouped['Total_Pistols_Won'] / grouped['Total_Pistols_Played']) * 100

        grouped = grouped.sort_values(by='Pistol Win Rate (%)', ascending=False)

        # Plotly bar chart
        fig_pistol = px.bar(
            grouped,
            x='Map',
            y='Pistol Win Rate (%)',
            text=grouped['Pistol Win Rate (%)'].apply(lambda x: f"{x:.1f}%"),
            color='Pistol Win Rate (%)',
            color_continuous_scale=['#ff0000', '#FDB913'],
            title="Pistol Win Rates by Map"
        )

        fig_pistol.update_traces(
            textposition='outside',
            marker_line_color='#000000',
            marker_line_width=1.2
        )

        fig_pistol.update_layout(
            plot_bgcolor='#000000',
            paper_bgcolor='#000000',
            font=dict(family='Inter', size=14, color='#FDB913'),
            title_font=dict(size=20, color='#FDB913'),
            xaxis=dict(tickfont=dict(color='#ffffff'), gridcolor='#333333'),
            yaxis=dict(range=[0, 100], title='Win Rate (%)', title_font=dict(color='#FDB913'), tickfont=dict(color='#ffffff'), gridcolor='#333333')
        )

        st.plotly_chart(fig_pistol, use_container_width=True)

        # --- 2nd Round Conversion Pie Charts (WW/WL and LL/LW) ---
        # --- 2nd Round Conversion Pie Charts (WW/WL and LL/LW) ---
        st.markdown("### 🍰 2nd Round Outcomes by Map")

        if 'Atk 2nd' in filtered_df.columns and 'Def 2nd' in filtered_df.columns:

             conversion_data = pd.concat([
                 filtered_df[['Map', 'Atk 2nd']].rename(columns={'Atk 2nd': 'Conversion'}),
                 filtered_df[['Map', 'Def 2nd']].rename(columns={'Def 2nd': 'Conversion'})
             ])

             map_list = conversion_data['Map'].dropna().unique()
             selected_map = st.selectbox("Select a map to view 2nd round breakdown:", sorted(map_list))

             map_conversions = conversion_data[conversion_data['Map'] == selected_map]

             col1, col2 = st.columns(2)

             with col1:
                 st.markdown("#### 🔁 After Winning Pistol (WW/WL)")
                 filtered_win = map_conversions[map_conversions['Conversion'].isin(['WW', 'WL'])]

                 if filtered_win.empty:
                     st.info("No conversion attempts found for pistol round wins on this map.")
                 else:
                     pie_data_win = filtered_win['Conversion'].value_counts(normalize=True).reset_index()
                     pie_data_win.columns = ['Conversion', 'Percentage']
                     pie_data_win['Percentage'] *= 100

                     fig_pie_win = px.pie(
                         pie_data_win,
                         names='Conversion',
                         values='Percentage',
                         title=f"Pistol Conversion - {selected_map}",
                         color='Conversion',
                         color_discrete_map={
                             'WW': '#FDB913',
                             'WL': '#666666'
                         },
                         hole=0.4
                     )

                     fig_pie_win.update_traces(
                         textinfo='label+percent',
                         marker_line_color='#000000',
                         marker_line_width=1.5
                     )

                     fig_pie_win.update_layout(
                         plot_bgcolor='#000000',
                         paper_bgcolor='#000000',
                         font=dict(family='Inter', size=14, color='#FDB913'),
                         title_font=dict(size=18, color='#FDB913'),
                         legend=dict(font=dict(color='#ffffff'))
                     )

                     st.plotly_chart(fig_pie_win, use_container_width=True)

             with col2:
                 st.markdown("#### 🔁 After Losing Pistol (LL/LW)")
                 filtered_loss = map_conversions[map_conversions['Conversion'].isin(['LL', 'LW'])]

                 if filtered_loss.empty:
                     st.info("No eco round outcomes found for pistol round losses on this map.")
                 else:
                     pie_data_loss = filtered_loss['Conversion'].value_counts(normalize=True).reset_index()
                     pie_data_loss.columns = ['Conversion', 'Percentage']
                     pie_data_loss['Percentage'] *= 100

                     fig_pie_loss = px.pie(
                         pie_data_loss,
                         names='Conversion',
                         values='Percentage',
                         title=f"Eco Round Outcomes - {selected_map}",
                         color='Conversion',
                         color_discrete_map={
                             'LL': '#444444',
                             'LW': '#3b82f6'
                         },
                         hole=0.4
                     )

                     fig_pie_loss.update_traces(
                         textinfo='label+percent',
                         marker_line_color='#000000',
                         marker_line_width=1.5
                     )

                     fig_pie_loss.update_layout(
                         plot_bgcolor='#000000',
                         paper_bgcolor='#000000',
                         font=dict(family='Inter', size=14, color='#FDB913'),
                         title_font=dict(size=18, color='#FDB913'),
                         legend=dict(font=dict(color='#ffffff'))
                     )

                     st.plotly_chart(fig_pie_loss, use_container_width=True)

    else:
         st.info("No data available for pistol or 2nd round conversion insights.")


## 🔢 PLAYER STATS TAB
with tabs[4]:
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
                Plants=('Plants', 'sum')
            ).reset_index()

            agent_stats['K/D Ratio'] = agent_stats['Kills'] / agent_stats['Deaths'].replace(0, float('nan'))
            agent_stats['K+A per Round'] = (agent_stats['Kills'] + agent_stats['Assists']) / agent_stats['Rounds'].replace(0, float('nan'))

            display_df = agent_stats.round(2)[['Agent', 'Rounds', 'Kills', 'Deaths', 'Assists', 'ACS', 'FK', 'Plants', 'K/D Ratio', 'K+A per Round']]

            st.markdown(f"### 🔍 Agent Performance for {selected_player} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            st.dataframe(display_df, use_container_width=True)

        else:
            st.info("No data for this player in the selected filters.")

    else:
        st.warning("No player stats found in form.csv")

     # 🐝 PLAYER ACS BEESWARM PLOT
    with st.expander("🐝 Player ACS Beeswarm Plot"):
        import seaborn as sns
        import matplotlib.pyplot as plt

        st.subheader("🐝 Player ACS Beeswarm Plot")

        # Clean + convert
        df = pd.read_csv("foracs.csv")
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['ACS'] = pd.to_numeric(df['ACS'], errors='coerce')

        players = sorted(df['Player'].dropna().unique())
        agents = sorted(df['Agent'].dropna().unique())
        maps = sorted(df['Map'].dropna().unique())
        dates = sorted(df['Date'].dropna().dt.date.unique())


        # Filters
        col1, col2 = st.columns(2)
        selected_player = col1.selectbox("Select Player", players)
        selected_agents = col2.multiselect("Filter by Agent(s)", agents, default=agents)
        selected_maps = st.multiselect("Filter by Map(s)", maps, default=maps)

        start_date = st.date_input("Start Date", value=min(dates), min_value=min(dates), max_value=max(dates))
        end_date = st.date_input("End Date", value=max(dates), min_value=min(dates), max_value=max(dates))


        # Filter the data
        filtered_df = df[
            (df['Player'] == selected_player) &
            (df['Agent'].isin(selected_agents)) &
            (df['Map'].isin(selected_maps)) &
            (df['Date'].dt.date >= start_date) &
            (df['Date'].dt.date <= end_date)
        ]

        if not filtered_df.empty:
            avg_acs = filtered_df['ACS'].mean()

            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_facecolor('#000000')
            ax.set_facecolor('000000')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#ffffff')
            ax.spines['bottom'].set_color('#ffffff')

            palette = sns.color_palette("husl", len(filtered_df['Agent'].unique()))
            sns.swarmplot(data=filtered_df, x='Map', y='ACS', hue='Agent', palette=palette, ax=ax)
            ax.axhline(avg_acs, color='yellow', linestyle='--', linewidth=1.5)
            ax.text(x=0.5, y=avg_acs + 2, s=f"Avg ACS: {avg_acs:.1f}", color='yellow', fontsize=10, ha='left')

            ax.set_title(f"{selected_player}'s ACS by Agent & Map", color='#FDB913', fontsize=14)
            ax.set_ylabel("ACS", color='white')
            ax.set_xlabel("Map", color='white')
            ax.tick_params(colors='white')
            ax.legend(title="Agent", loc='best', facecolor='#1a1a1a', labelcolor='white', title_fontsize=10, fontsize=9)

            st.pyplot(fig)
        else:
            st.info("No ACS data for selected filters.")


# --- Post-Plant Success Rate Bar Chart ---

if 'Atk_PP_Success' in summary.columns and 'Def_PP_Success' in summary.columns:

    st.markdown("### 📊 Post-Plant Success Rate by Map")

    label_map = {
        "Atk_PP_Success": "Post Plant",
        "Def_PP_Success": "Retakes"
    }

    sort_label = st.selectbox("Sort by", list(label_map.values()), index=0)
    sort_col = [k for k, v in label_map.items() if v == sort_label][0]
    sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True)
    ascending = sort_order == "Ascending"

    pp_df = summary[['Map', 'Atk_PP_Success', 'Def_PP_Success']].copy()
    pp_df = pp_df.fillna(0)

    pp_df['Atk_PP_Success'] = pd.to_numeric(pp_df['Atk_PP_Success'], errors='coerce')
    pp_df['Def_PP_Success'] = pd.to_numeric(pp_df['Def_PP_Success'], errors='coerce')
    if pp_df['Atk_PP_Success'].max() <= 1.0:
        pp_df['Atk_PP_Success'] *= 100
        pp_df['Def_PP_Success'] *= 100

    # Sort before renaming columns
    pp_df = pp_df.sort_values(by=sort_col, ascending=ascending)
    pp_df['Map'] = pd.Categorical(pp_df['Map'], categories=pp_df['Map'], ordered=True)

    # Rename for nicer legend labels
    pp_df.rename(columns=label_map, inplace=True)

    pp_df_long = pp_df.melt(id_vars='Map', var_name='Side', value_name='Post-Plant Success (%)')

    # Plot
    fig_pp = px.bar(
        pp_df_long,
        x='Map',
        y='Post-Plant Success (%)',
        color='Side',
        barmode='stack',
        text=pp_df_long['Post-Plant Success (%)'].apply(lambda x: f"{x:.1f}%"),
        title="Post-Plant Success Rate (Stacked Atk + Def)",
        color_discrete_map={
            'Post Plant': '#FDB913',
            'Retakes': '#ffffff'
        }
    )

    fig_pp.update_traces(
        textposition='inside',
        marker_line_color='#333333',
        marker_line_width=1.2
    )

    fig_pp.update_layout(
        plot_bgcolor='#000000',
        paper_bgcolor='#000000',
        font=dict(family='Inter, sans-serif', size=14, color='#FDB913'),
        title_font=dict(size=20, color='#FDB913'),
        xaxis=dict(
            title='Map',
            title_font=dict(size=16, color='#FDB913'),
            tickfont=dict(size=14, color='#ffffff'),
            tickangle=-25,
            gridcolor='#333333'
        ),
        yaxis=dict(
            title='Post-Plant Success (%)',
            title_font=dict(size=16, color='#FDB913'),
            tickfont=dict(size=14, color='#ffffff'),
            gridcolor='#333333',
            range=[0, 100]
        ),
        legend=dict(
            font=dict(size=13, color='#ffffff')
        )
    )

    st.plotly_chart(fig_pp, use_container_width=True)

# 📊 PLAYER COMPARISON TAB
with tabs[5]:
    st.subheader("🎚 Player vs VCT Benchmark Comparison")

    try:
        player_df = pd.read_csv("form.csv")
    except Exception as e:
        st.warning(f"Could not load player data: {e}")
        player_df = pd.DataFrame()

    if not player_df.empty:
        # Convert and filter dates
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

        # Agent to role mapping
        agent_roles = {
            'Jett': 'Duelist', 'Raze': 'Duelist', 'Reyna': 'Duelist', 'Yoru': 'Duelist', 'Phoenix': 'Duelist', 'Iso': 'Duelist', 'Waylay': 'Duelist', 'Neon':'Duelist',
            'Skye': 'Initiator', 'KAY/O': 'Initiator', 'Breach': 'Initiator', 'Fade': 'Initiator', 'Sova': 'Initiator', 'Gekko': 'Initiator', 'Tejo': 'Initiator',
            'Omen': 'Controller', 'Brimstone': 'Controller', 'Astra': 'Controller', 'Viper': 'Controller', 'Harbor': 'Controller', 'Clove': 'Controller',
            'Killjoy': 'Sentinel', 'Cypher': 'Sentinel', 'Chamber': 'Sentinel', 'Sage': 'Sentinel', 'Deadlock': 'Sentinel', 'Vyse': 'Sentinel', 'Veto': 'Sentinel'
        }

        # VCT average benchmarks by role
        vct_benchmarks = {
            'Duelist':     {'ACS': 240, 'KPR': 0.90, 'FBSR': 0.55, 'FKPR': 0.18, 'Atk_Entry': 0.55},
            'Initiator':   {'ACS': 196, 'KPR': 0.90, 'FD': 2, 'K+A per Round': 1, 'Assists': 10.0},
            'Controller':  {'ACS': 203, 'KPR': 0.90, 'FD': 2, 'K+A per Round': 1, 'Multi_Kills': 0.25},
            'Sentinel':    {'ACS': 200, 'KPR': 0.90, 'FD': 2, 'Multi_Kills': 0.25, 'Anchor_Time': 48.0},
        }

        filtered = player_df[
            (player_df['Player'] == selected_player) &
            (player_df['Date'].dt.date >= start_date) &
            (player_df['Date'].dt.date <= end_date)
        ]

        if selected_map != "All":
            filtered = filtered[filtered['Column 1'] == selected_map]

        if not filtered.empty:
            # Fill missing 'Atk Entry' with 0 to ensure smooth calculations
            if 'Atk_Entry' in filtered.columns:
                filtered['Atk_Entry'] = filtered['Atk_Entry'].fillna(0)

            # Clean and convert percentage columns
            for col in ['Rounds', 'Kills', 'Deaths', 'Assists', 'ACS', 'FK', 'FBSR', 'FKPR', 'KPR', 'Atk_Entry', 'FD','Multi-Kills']:
                if col in filtered.columns:
                    filtered[col] = filtered[col].astype(str).str.replace('%', '', regex=False)
                    filtered[col] = pd.to_numeric(filtered[col], errors='coerce')

            # Compute player stats per agent
            agent_stats = filtered.groupby('Agent').agg(
                Rounds=('Rounds', 'sum'),
                Kills=('Kills', 'sum'),
                Deaths=('Deaths', 'sum'),
                Multi_Kills=('Multi_Kills','mean'),
                Assists=('Assists', 'mean'),
                ACS=('ACS', 'mean'),
                FK=('FK', 'sum'),
                FBSR=('FBSR', 'mean'),
                FKPR=('FKPR', 'mean'),
                KPR=('KPR', 'mean'),
                Atk_Entry=('Atk_Entry', 'mean'),
                FD=('FD', 'mean'),
                Anchor_Time=('Anchor_Time', 'mean')
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
                        if stat in role_agents.columns:
                            val = role_agents[stat].mean()
                            player_avg[stat] = val if pd.notna(val) else 0
                        else:
                            player_avg[stat] = 0

                # Normalize values (manual bounds)
                norm_base = {
                    'ACS': 300,
                    'K/D Ratio': 2.0,
                    'FK': 0.3,
                    'K+A per Round': 1.2,
                    'KPR': 1.2,
                    'FBSR': 1.0,
                    'FKPR': 0.3,
                    'Atk_Entry': 1.0,
                    'FD': 20.0,
                    'Assists': 20.0,
                    'Multi_Kills': 0.3,
                    'Anchor_Time':80.0
                }

                categories = list(benchmark.keys())
                player_values = [player_avg.get(stat, 0) / norm_base[stat] for stat in categories]
                benchmark_values = [benchmark.get(stat, 0) / norm_base[stat] for stat in categories]

                import plotly.graph_objects as go
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=player_values,
                    theta=categories,
                    fill='toself',
                    name=f"{selected_player}",
                    line=dict(color="#FDB913")
                ))
                fig.add_trace(go.Scatterpolar(
                    r=benchmark_values,
                    theta=categories,
                    fill='toself',
                    name=f"VCT {selected_role} Avg",
                    line=dict(color="#444444")
                ))

                raw_values = []
                for stat in categories:
                    val = player_avg[stat]
                    bmark = benchmark[stat]
                    diff = val - bmark
                    sign = '+' if diff >= 0 else ''
                    color = "#14532d" if diff >= 0 else "#7f1d1d"

                    # Use % format for relevant stats
                    if stat in ['FBSR', 'FKPR', 'Atk Entry']:
                        display_diff = f"{sign}{diff * 100:.1f}%"
                    else:
                        display_diff = f"{sign}{diff:.2f}"

                    if stat in ['FBSR', 'FKPR', 'Atk Entry']:
                        raw_values.append(f"<span style='color:{color}'><b>{stat}</b>: {sign}{diff * 100:.1f}%</span>")
                    else:
                        raw_values.append(f"<span style='color:{color}'><b>{stat}</b>: {sign}{diff:.2f}</span>")

                fig.add_annotation(
                    text="<br>".join(raw_values),
                    showarrow=False,
                    align="left",
                    x=0.95,
                    y=0.95,
                    xref="paper",
                    yref="paper",
                    bordercolor="#666",
                    borderwidth=1,
                    bgcolor="rgba(0,0,0,0.85)",
                    font=dict(color="white", size=12)
                )

                fig.update_layout(
                    polar=dict(
                        bgcolor="#000000",
                        radialaxis=dict(
                            visible=False,
                            showticklabels=False,
                            ticks='',
                            showline=False,
                            gridcolor="#333333"
                        ),
                        angularaxis=dict(tickfont=dict(color="#FDB913"))
                    ),
                    showlegend=True,
                    legend=dict(font=dict(color="#ffffff")),
                    plot_bgcolor='#000000',
                    paper_bgcolor='#000000',
                    font=dict(family='Inter', color='#FDB913'),
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

# Footer in bottom-right corner
# Full-width footer pinned to bottom
st.markdown("""
    <style>
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: #000000;
            color: #FDB913;
            text-align: center;
            font-size: 13px;
            font-family: Inter, sans-serif;
            padding: 0.5rem 0;
            opacity: 0.8;
            z-index: 9999;
        }
    </style>
    <div class="footer">
        Made by: <b>Ominous</b> | X:
        <a href="https://x.com/_SushantJha" target="_blank" style="color: #FDB913; text-decoration: none;">@_SushantJha</a>
    </div>
""", unsafe_allow_html=True)
