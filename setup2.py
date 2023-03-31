import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3 as sql
from datetime import datetime,timedelta
from flask import Flask, request, session, g, redirect, url_for,render_template, flash

conn = sql.connect('flask_app.db')

cursor = conn.cursor()

field_file = "testfiles/2023mastersfield.csv"

# for when starting new tournament
cursor.execute('delete from inputs') 
cursor.execute('delete from golfers')
cursor.execute('delete from leaderboard')
cursor.execute('delete from raw_scores')


#Set up the field the new way using the local csv ezpool file
html_file_path = field_file
with open(html_file_path, "r") as f:
    html_content = f.read()
soup = BeautifulSoup(html_content, "html.parser")
df = pd.read_csv(field_file)
df.to_sql('golfers',conn,if_exists = 'replace')

conn.commit()
conn.close()
