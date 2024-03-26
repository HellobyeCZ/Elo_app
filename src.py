from datetime import datetime
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from statistics import mean
import math

"""
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

#creds = ServiceAccountCredentials.from_json_keyfile_name('.streamlit/elo-calculation-418217-a802da65488a.json', scope)
creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets.gsheets.creds))

client = gspread.authorize(creds)

 
sh = client.open('Elo_calculation').worksheet('Players')  
#row = [1,2,3]
#sh.append_row(row)

"""


players_dict = {}

def get_or_create_player(name):
    if name in players_dict:
        return players_dict[name]
    else:
        player = Player(name)
        players_dict[name] = player
        return player
    
    
teams_dict = {}

def get_or_create_team(players: list):
    id = "-".join(sorted(players))
    
    if id in teams_dict:
        return teams_dict[id]
    else:
        team = Team([get_or_create_player(i) for i in players if i != ''])
        teams_dict[id] = team
        return team
    

class Player:
    def __init__(self, name):
        self.name = name
        self.elo_history = [1000]
        self.elo = 1000
        self.goals_scored = 0
        self.goals_conceded = 0
        self.matches_played = 0
        self.matches_won = 0
        self.matches_lost = 0
        self.matches_drawn = 0
        self.teammates = {}
        self.opponents = {}
        self.teammates_history = {}
        self.opponents_history = {}
        self.teammates_win_rate = {}
        self.opponents_win_rate = {}
        
        
    def update_elo(self, elo):
        self.elo_history.append(elo)
        self.elo = self.elo_history[-1]

    def get_current_elo(self):
        return self.elo_history[-1]

    def add_match_details(self, match):
        # Store relevant information from the match
        # such as goals, opponents, teammates, etc.
        pass
    def __lt__(self, other):
        return self.name < other.name
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def to_dict(self):
        return {
            "name": self.name,
            "elo": self.elo,
            "elo_history": self.elo_history,
            "goals_scored": self.goals_scored,
            "goals_conceded": self.goals_conceded,
            "matches_played": self.matches_played,
            "matches_won": self.matches_won,
            "matches_lost": self.matches_lost,
            "matches_drawn": self.matches_drawn
        }





class Team:
    def __init__(self, players: list[Player]):
        
        self.players = sorted(players) # Sort players by name
        self.id = "-".join([player.name for player in self.players])

    def get_team_elo(self, elo_against:list[float]):
        
        elo_lst = []
        for i in self.players:
            p_elo = i.get_current_elo()
            temp_list = []
            for l in elo_against:
                temp_list.append(1/(1 + 10**((l - p_elo)/500)))

            elo_lst.append(mean(temp_list))
        
        return elo_lst
    
    def __str__(self) -> str:
        return " & ".join([player.name for player in self.players]) if len(self.players) > 1 else self.players[0].name
    def __repr__(self) -> str:
        return self.__str__()
    


class Match:
    def __init__(self, team1:Team, team2:Team, team1_goals:int, team2_goals:int, date:datetime):
        self.team1 = team1
        self.team2 = team2
        self.team1_goals = team1_goals
        self.team2_goals = team2_goals
        self.date = date
        
        self.pre_elo_T1 = [x.get_current_elo() for x in self.team1.players]
        self.pre_elo_T2 = [x.get_current_elo() for x in self.team2.players]
        
        self.post_elo_T1 = []
        self.post_elo_T2 = []
        

    def calculate_elo(self):
        # Perform Elo calculation based on match result
        # and update the players' Elo history
        
        self.preT1 = self.team1.get_team_elo([x.get_current_elo() for x in self.team2.players])
        self.preT2 = self.team2.get_team_elo([x.get_current_elo() for x in self.team1.players])
        
        self.point_factor = 2 + (math.log(abs(self.team1_goals-self.team2_goals) + 1) / math.log(10)) ** 3
        
        if self.team1_goals > self.team2_goals:
            team1_actual_score = 1
            team2_actual_score = 0

        elif self.team1_goals < self.team2_goals:
            team1_actual_score = 0
            team2_actual_score = 1
            
        else:
            team1_actual_score = 0.5
            team2_actual_score = 0.5
        
        # Dynamic K-Value
        
        # Team1
        for p in self.team1.players:
            p.goals_scored += self.team1_goals
            p.goals_conceded += self.team2_goals
            if team1_actual_score == 1:
                p.matches_won += 1
            elif team1_actual_score == 0:
                p.matches_lost += 1
            else:
                p.matches_drawn += 1
            k = 50 / (1 + p.matches_played / 300)
            p.matches_played += 1
            new_elo = round(p.get_current_elo() + k * self.point_factor * (team1_actual_score - self.preT1[self.team1.players.index(p)]), 2)
            p.update_elo(new_elo)
            self.post_elo_T1.append(new_elo)
            
        # Team2
        for p in self.team2.players:
            p.goals_scored += self.team2_goals
            p.goals_conceded += self.team1_goals
            if team2_actual_score == 1:
                p.matches_won += 1
            elif team2_actual_score == 0:
                p.matches_lost += 1
            else:
                p.matches_drawn += 1
            k = 50 / (1 + p.matches_played / 300)
            p.matches_played += 1
            new_elo = round(p.get_current_elo() + k * self.point_factor * (team2_actual_score - self.preT2[self.team2.players.index(p)]),2)
            p.update_elo(new_elo) 
            self.post_elo_T2.append(new_elo)
            
            
        
        
        return self.preT1, self.preT2
    
    def __str__(self) -> str:
        return f"{self.team1} {self.team1_goals} - {self.team2_goals} {self.team2}"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def to_dict(self):
        return {
            "team1": self.team1,
            "team2": self.team2,
            "team1_goals": self.team1_goals,
            "team2_goals": self.team2_goals,
            "date": self.date,
            "pre_elo_T1": self.pre_elo_T1,
            "pre_elo_T2": self.pre_elo_T2,
            "post_elo_T1": self.post_elo_T1,
            "post_elo_T2": self.post_elo_T2
        }
    
    