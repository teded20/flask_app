import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3 as sql
from datetime import datetime,timedelta
from flask_mail import Mail, Message
from flask import Flask, request, session, g, redirect, url_for,render_template, flash

db = sql.connect('flask_app.db')
db.execute('delete from inputs') # for when starting new tournament
db.execute('delete from golfers')
db.execute('delete from leaderboard')
db.execute('delete from raw_scores')
db.commit()


tid = db.execute('select tournamentid from tournament').fetchone()[0]
url = "https://www.espn.com/golf/leaderboard/_/tournamentId/"+tid
page = requests.get(url)
soup = BeautifulSoup(page.content,'html.parser')
rows = soup.find_all('tr')
rows = rows[3:]
column_headers = ['POS','PLAYER','TO_PAR','THRU']
cells = rows[10].find_all('td')
leaderboard = []
if len(cells[0].get_text()) > 5:
    for x in range(0,len(rows)):
        if len(rows[x]) == 1:
            continue
        cells = rows[x].find_all('td')
        leaderboard.append(['-',cells[0].get_text(),'-',cells[1].get_text()])
elif len(cells[1].get_text()) > 5:
    for x in range(0,len(rows)):
        if len(rows[x]) == 1:
            continue
        cells = rows[x].find_all('td')
        leaderboard.append([cells[0].get_text(),cells[1].get_text(),cells[2].get_text(),cells[4].get_text()])
elif len(cells[2].get_text()) > 5:
    for x in range(0,len(rows)):
        if len(rows[x]) == 1:
            continue
        cells = rows[x].find_all('td')
        leaderboard.append([cells[0].get_text(),cells[2].get_text(),cells[3].get_text(),cells[5].get_text()])
else:
    for x in range(0,len(rows)):
        if len(rows[x]) == 1:
            continue
        cells = rows[x].find_all('td')
        leaderboard.append([cells[0].get_text(),cells[1].get_text(),cells[2].get_text(),'F'])

for x in range(0,len(leaderboard)):
    if leaderboard[x][2]=='-' and len(leaderboard[x][2])==1:
        leaderboard[x][2] = '0'

df=pd.DataFrame(leaderboard,columns = column_headers)

df_e = pd.read_sql_query('select * from inputs',db)
total = len(df_e)
df_e = df_e[['golfer1','golfer2','golfer3','golfer4','golfer5','golfer6']]
df5 = df_e
df2 = pd.concat([df5.golfer1, df5.golfer2,df5.golfer3,df5.golfer4,df5.golfer5,df5.golfer6], ignore_index=True)
df3 = pd.DataFrame(df2,columns=['golfers'])
df4 = df3['golfers'].value_counts()/total*100
owners = dict(df4)
df['OWNED']=0
df['OWNED'] = df.PLAYER.map(owners)
df.OWNED = df.OWNED.round(0)
df.OWNED=df.OWNED.fillna(0)
df['OWNED']=df.OWNED.astype(int).astype(str)+'%'

df.to_sql('raw_scores',db,if_exists ='replace')

top20url = 'http://www.owgr.com/ranking'
top20page = requests.get(top20url)
top20soup = BeautifulSoup(top20page.content,'html.parser')
names = top20soup.findAll('td',{'class':'name'})
rankings = []
for x in range(0,len(names)):
    rankings.append([str(names[x].getText()),int(x+1)])

column_headers = ['PLAYER','RANK']
field = pd.DataFrame(rankings,columns=column_headers)
field['PLAYER'] = field['PLAYER'].str.split('[(]').str[0]
field = field.sort_values('RANK',ascending=True)
field = pd.DataFrame(rankings,columns=column_headers)
field['PLAYER'] = field['PLAYER'].str.split('[(]').str[0]
field = field.sort_values('RANK',ascending=True)

df = df.drop(['POS','THRU','TO_PAR'],1)
df['RANK']=''
my_dict = dict(zip(field.PLAYER,field.RANK))
df['RANK'] = df.PLAYER.map(my_dict)
df = df.sort_values('RANK',ascending=True)
df.to_sql('golfers',db,if_exists = 'replace')

db.close()