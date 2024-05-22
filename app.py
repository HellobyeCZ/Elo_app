import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from src import Player, Team, Match
import numpy as np
import datetime as dt
import plotly.express as px

st.set_page_config(
    page_title="Fifa Elo app",
    page_icon="⚽",
    layout="centered",
)
st.title("Fifa Elo app ⚽")

tabs = st.tabs(["Home", "Form", "Players", "Matches"])

    
players_list_whisp = sorted(st.secrets.players.player_names)

players_dict = {}
teams_dict = {}


def get_or_create_player(name):
    "Get or create player by name"
    if name in players_dict:
        return players_dict[name]
    else:
        player = Player(name)
        players_dict[name] = player
        return player
    
def get_or_create_team(players: list):
    "Get or create team by list of players"
    id = "-".join(sorted(players))
    
    if id in teams_dict:
        return teams_dict[id]
    else:
        team = Team([get_or_create_player(i) for i in players if i != ''])
        teams_dict[id] = team
        return team


def get_sheet():
    
    #scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets.gsheets.creds))
    client = gspread.authorize(creds)
    sh = client.open('Elo_calculation').worksheet('Players')  
    return sh

sh = get_sheet()

data = pd.DataFrame(sh.get_all_records())
players_dict = {}
lst = []

# create players of all unique players in P1, P2, P3, P4
_ = [get_or_create_player(x) for x in np.unique(data[["P1", "P2", "P3", "P4"]]) if x != '']

for i, row in data.iterrows():
    match = Match(
            get_or_create_team([row['P1'], row['P2']]),
            get_or_create_team([row['P3'], row['P4']]),
            row['score_1'],
            row['score_2'],
            row['date']
        )
    match.calculate_elo()
    # Update all players that are not in the match
    for player in players_dict.values():
        if player not in match.team1.players and player not in match.team2.players:
            player.update_elo(player.get_current_elo())
    lst.append(match)
        

elo_history_dict = {player.to_dict()["name"]: player.to_dict()["elo_history"] for player in players_dict.values()}
player_df_data = pd.DataFrame([player.to_dict() for player in players_dict.values()])
matches_df_data = pd.DataFrame([match.to_dict() for match in lst])




with tabs[0]:
    st.write("Welcome to the Elo App! This app allows you to track and calculate Elo ratings for players in a game or sport.")
    st.write("Here are some features you can find in this app:")

    st.write("- Form: Use the form on the tab to input match results and update the Elo ratings.")
    st.write("- Players: View the Elo ratings and history of individual players.")
    st.write("- Matches: View the details and results of past matches.")
    st.write("You can navigate to the different tabs using the tabs above.")
    st.write("Below is a summary of the current Elo ratings of all players:")




    #st.line_chart(pd.DataFrame(elo_history_dict))
    st.subheader("Elo Ratings over time:")
    #st.json(elo_history_dict)
    st.plotly_chart(px.line(elo_history_dict))
    
    st.subheader("Current standings:")
    #st.dataframe(player_df_data.drop(columns=["elo_history"]).sort_values(by="elo", ascending=False).reset_index(drop=True))
    flat_list = [x for xs in player_df_data["elo_history"] for x in xs]
    ymax, ymin = np.max(flat_list), np.min(flat_list)
    st.dataframe(player_df_data.sort_values(by="elo", ascending=False).reset_index(drop=True), column_config={"elo_history": st.column_config.LineChartColumn("Elo history", y_min = ymin, y_max = ymax)})

    st.subheader("Last 10 matches:")
    st.dataframe(matches_df_data.tail(10).sort_index(ascending=False))


with tabs[1]:        

    with st.form("my_form"):
        st.header("Input form")
        
        st.subheader("Team 1")
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            p1 = st.selectbox("Player 1", key="p1", options=players_list_whisp, index=None)
        with col2:
            p2 = st.selectbox("Player 2", key="p2", options=players_list_whisp, index=None)
        with col3:
            score_1 = st.number_input("Score Team 1", key="score_1", step=1, min_value=0, format="%d", value=0)

            
        st.subheader("Team 2")
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            p3 = st.selectbox("Player 3", key="p3", options=players_list_whisp, index=None)
        with col2:
            p4 = st.selectbox("Player 4", key="p4", options=players_list_whisp, index=None)
        with col3:
            score_2 = st.number_input("Score Team 2", key="score_2", step=1, min_value=0, format="%d", value=0)
        
        date = st.date_input("Date", key="date", value=dt.datetime.now())
        
    
        submitted = st.form_submit_button("Submit")
        
        if submitted and p1 != None and p3 != None:
            sh.append_row([p1, p2, p3, p4, score_1, score_2, str(date)])
            st.success('This is a success message!', icon="✅")
            st.rerun()
        

with tabs[2]:
    st.subheader("Players")
    st.write("Here you can view the Elo ratings and history of individual players.")
    player = st.selectbox("Select a player:", options=players_list_whisp, index=players_list_whisp.index(list(players_dict.keys())[0]))
    
    try:
        interested = players_dict[player]
        player_data = interested.to_dict()
        
        cols = st.columns(3)
        with cols[0]:
            st.metric("Current Elo", player_data["elo"])
        with cols[1]:
            st.metric("Max Elo", max(player_data["elo_history"]))
        with cols[2]:
            st.metric("Min Elo", min(player_data["elo_history"]))
        
        cols =  st.columns(5)
        with cols[0]:
            st.metric("Total Matches", player_data["matches_played"])
        with cols[1]:
            st.metric("Wins", player_data["matches_won"])
        with cols[2]:
            st.metric("Losses", player_data["matches_lost"])
        with cols[3]:
            st.metric("Draws", player_data["matches_drawn"])
        with cols[4]:
            st.metric("Win Rate", f"{player_data['matches_won']/player_data['matches_played']*100:.1f}%")
        st.subheader("Elo Ratings over time:")
        fig = px.line(player_data["elo_history"], title=f"Elo ratings for {player}", labels={"index": "index", "value": "Elo"})
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig)
        st.json(player_data, expanded=False)
    except KeyError:
        st.write("Player not found :(")
    except Exception as e:
        st.write(f"An error occurred: {e}")


with tabs[3]:
    st.subheader("Matches")
    st.dataframe(matches_df_data)
    

