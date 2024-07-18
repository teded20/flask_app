import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3 as sql
from datetime import datetime,timedelta
from flask import Flask, request, session, g, redirect, url_for,render_template, flash
from apitest import fetch_leaderboard_data, insert_data_into_database, can_call_api, get_last_call_timestamp, update_last_call_timestamp
from dateutil import parser

golive = datetime(2024,7,18,5,0)

app = Flask(__name__)

#app.config["DEBUG"] = True

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flask_app.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))


def connect_db():
    """Connects to the specific database."""
    rv = sql.connect(app.config['DATABASE'],timeout=1)
    rv.row_factory = sql.Row
    return rv

def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.route('/',methods=["GET", "POST"])
def index():
    if datetime.now() > golive:
        # Check if API can be called based on last call timestamp
        last_call_timestamp = get_last_call_timestamp("flask_app.db")
        if can_call_api(last_call_timestamp):
            # Fetch data from the API
            headers = {
                "X-RapidAPI-Key": "ec34e27eb0mshc4a776c20e717bfp127602jsn97ffbe5d0d3a",
                "X-RapidAPI-Host": "golf-leaderboard-data.p.rapidapi.com"
            }
            data = fetch_leaderboard_data("https://golf-leaderboard-data.p.rapidapi.com/leaderboard/668", headers)
            if data:
                # Insert data into SQLite database
                insert_data_into_database("flask_app.db", data)
                # Update last API call timestamp
                current_datetime = datetime.now()
                formatted_datetime = current_datetime.strftime("%Y-%m-%dT%H:%M:%S")
                update_last_call_timestamp("flask_app.db",formatted_datetime)
                print('Leaderboard updated successfully!')
            else:
                print('Failed to update leaderboard.')
        else:
            print('API can only be called once every 5 minutes.')
        db = get_db()
        df=pd.read_sql_query('select * from leaderboard_array',db)
        df=df[['position','first_name','last_name','status','holes_played','total_to_par']]
        df.loc[df['status'] == 'cut', 'total_to_par'] = 'CUT'
        df.loc[df['status'] == 'withdrawn', 'total_to_par'] = 'WD'
        df['PLAYER'] = df['first_name'].str.cat(df['last_name'], sep=' ')
        df = df.rename(columns={"position": "POS","total_to_par":"TO_PAR","holes_played":"THRU"})
        df = df[['POS','PLAYER','TO_PAR','THRU']]
        df = df.sort_values(by='POS').reset_index(drop=True)

        new_row = {"POS": 157,"PLAYER": "Sebastian Soderberg ", "TO_PAR": "WD", "THRU": 0}
        df= df.append(new_row, ignore_index=True)

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

        #COMMENT THIS OUT
        #df = df[~df['THRU'].isnull()]


        df.to_sql('raw_scores',db,if_exists ='replace') #comment this in once espn link works
        #df['POS'] = df['POS'].str.replace('T','')
        df['PLAYER'] = df['PLAYER'].str.replace(r" \(.*\)","")
        df['TO_PAR'] = df.apply(lambda x: x['THRU'] if x['THRU']=='WD' else x['TO_PAR'], axis=1)
        df['PLAYER'] = df['PLAYER'].str.replace('-','')
        df.loc[(df.PLAYER == 'Cam Davis'),'PLAYER']='Cameron Davis'
        df.loc[(df.PLAYER == 'K.H. Lee'),'PLAYER']='Kyoung-Hoon Lee'
        df.loc[(df.PLAYER == 'Sebastián Muñoz'),'PLAYER']='Sebastian Munoz'
        df.loc[(df.PLAYER == 'Nicolai Højgaard'),'PLAYER']='Nicolai Hojgaard'
        df.loc[(df.PLAYER == 'Min-gyu Cho'),'PLAYER']='Mingyu Cho'
        df.loc[(df.PLAYER == 'Pablo Larrazábal'),'PLAYER']='Pablo Larrazabal'
        df.loc[(df.PLAYER == 'Si Woo Kim'),'PLAYER']='Siwoo Kim'
        df.loc[(df.PLAYER == 'Séamus Power'),'PLAYER']='Seamus Power'
        df.loc[(df.PLAYER == 'José María Olazábal'),'PLAYER']='Jose Maria Olazabal'
        df.loc[(df.PLAYER == 'Alex Noren'),'PLAYER']='Alexander Noren'
        df.loc[(df.PLAYER == 'Augusto Núñez'),'PLAYER']='Augusto Nunez'
        #df.loc[(df.PLAYER == 'Byeong Hun An'),'PLAYER']='Byeong-Hun An'
        df.loc[(df.PLAYER == 'Matti Schmid'),'PLAYER']='Matthias Schmid'
        df.loc[(df.PLAYER == 'Nico Echavarria'),'PLAYER']='Nicolas Echavarria'
        df.loc[(df.PLAYER == 'Paul Haley II'),'PLAYER']='Paul Haley'
        df.loc[(df.PLAYER == 'Roberto Díaz'),'PLAYER']='Roberto Diaz'
        df.loc[(df.PLAYER == 'Harold Varner III'),'PLAYER']='Harold Varner'
        df.loc[(df.PLAYER == 'Rasmus Højgaard'),'PLAYER']='Rasmus Hojgaard'
        df.loc[(df.PLAYER == 'Jordan Smith'),'PLAYER']='Jordan L. Smith'
        df.loc[(df.PLAYER == 'Brandon Robinson Thompson'),'PLAYER']='Brandon Robinson-Thompson'
        df.loc[(df.PLAYER == 'Alexander Björk'),'PLAYER']='Alexander Bjork'
        df.loc[(df.PLAYER == 'Thorbjørn Olesen'),'PLAYER']='Thorbjorn Olesen'
        df.loc[(df.PLAYER == 'Joaquín Niemann'),'PLAYER']='Joaquin Niemann'
        df.loc[(df.PLAYER == 'Ludvig Åberg'),'PLAYER']='Ludvig Aberg'
        df.loc[(df.PLAYER == 'Byeong Hun An'),'PLAYER']='Byeong-Hun An'
        df.loc[(df.PLAYER == 'Matthew Fitzpatrick'),'PLAYER']='Matt Fitzpatrick'
        df.loc[(df.PLAYER == 'Cam Smith'),'PLAYER']='Cameron Smith'
        df.loc[(df.PLAYER == 'Altin Van Der'),'PLAYER']='Altin Van Der Merwe'
        df.loc[(df.PLAYER == 'Sebastian Söderberg'),'PLAYER']='Sebastian Soderberg'


        df['TO_PAR']=df['TO_PAR'].str.replace('E','0')

        # if (datetime.today().weekday() > 4 or datetime.today().weekday() < 3):
        #if datetime.now() > datetime(2023,5,19,5,0):
        if df['TO_PAR'].str.contains('CUT').any():
            #df_cut = df.sort_values('POS',ascending=False)
            df = df[~df['PLAYER'].isnull()]
            not_cut = df[(df['TO_PAR'] != 'CUT') & (df['TO_PAR'] != 'WD')]
            cut_score = int(not_cut['TO_PAR'][not_cut.index[-1]])+2
            df['TO_PAR'] = df['TO_PAR'].replace('CUT',cut_score)
            df['TO_PAR'] = df['TO_PAR'].replace('WD',cut_score)
            df['TO_PAR'] = df['TO_PAR'].replace('DQ',cut_score)
        else:
            df['TO_PAR']=df['TO_PAR'].str.replace('WD','0')
            df['TO_PAR']=df['TO_PAR'].str.replace('DQ','0')

        #df['TO_PAR'] = df['TO_PAR'].str.replace('-','0')
        df['TO_PAR'] = df['TO_PAR'].astype('float',errors='ignore')


        if (df.loc[0,'POS'] != df.loc[1,'POS']) and (df.loc[0,'TO_PAR'] != df.loc[1,'TO_PAR']): #this substracts 3 if the leader is solo in the lead
            df.loc[0,'TO_PAR']=df.loc[0,'TO_PAR']-3

        # if df.loc[4,'POS'] != df.loc[5,'POS']: #this substracts 3 if the leader is solo in the lead
        #     df.loc[4,'TO_PAR']=df.loc[4,'TO_PAR']-3


        df = df.drop(['POS','THRU'],1)
        df.to_sql('scores',db,if_exists ='replace')
        db.execute('update datetime set last_run = ?',(datetime.today(),))

        df_scores = pd.read_sql_query('select * from scores',db)
        df_scores['PLAYER'] = df_scores['PLAYER'].str.split('[(]').str[0]
        df_scores['COMPARE'] = df_scores['PLAYER'].str.lower()
        df_scores['COMPARE'] = df_scores['COMPARE'].str.replace(' ','')
        df_scores['TO_PAR'] = df_scores['TO_PAR'].fillna(max(df_scores.TO_PAR))
        my_dict = dict(zip(df_scores.COMPARE,df_scores.TO_PAR))

        df_entries = pd.read_sql_query('select * from inputs',db)

        df_entries['golfer1c'] = df_entries.golfer1.str.replace(' ','')
        df_entries['golfer1c'] = df_entries.golfer1c.str.lower()
        df_entries['golfer2c'] = df_entries.golfer2.str.replace(' ','')
        df_entries['golfer2c'] = df_entries.golfer2c.str.replace('-','')
        df_entries['golfer2c'] = df_entries.golfer2c.str.lower()
        df_entries['golfer3c'] = df_entries.golfer3.str.replace(' ','')
        df_entries['golfer3c'] = df_entries.golfer3c.str.lower()
        df_entries['golfer4c'] = df_entries.golfer4.str.replace(' ','')
        df_entries['golfer4c'] = df_entries.golfer4c.str.lower()
        df_entries['golfer5c'] = df_entries.golfer5.str.replace(' ','')
        df_entries['golfer5c'] = df_entries.golfer5c.str.lower()
        df_entries['golfer6c'] = df_entries.golfer6.str.replace(' ','')
        df_entries['golfer6c'] = df_entries.golfer6c.str.lower()

        df_entries['score1'] = df_entries.golfer1c.map(my_dict)
        df_entries['score2'] = df_entries.golfer2c.map(my_dict)
        df_entries['score3'] = df_entries.golfer3c.map(my_dict)
        df_entries['score4'] = df_entries.golfer4c.map(my_dict)
        df_entries['score5'] = df_entries.golfer5c.map(my_dict)
        df_entries['score6'] = df_entries.golfer6c.map(my_dict)
        df_entries = df_entries[['name','golfer1','score1','golfer2','score2','golfer3','score3','golfer4','score4','golfer5','score5','golfer6','score6','birdies']]
        df_entries['raw_total']= int()
        # df_entries['score1']= int()
        # df_entries['score2']= int()
        # df_entries['score3']= int()
        # df_entries['score4']= int()
        # df_entries['score5']= int()
        # df_entries['score6']= int()
        for x in range(0,len(df_entries)):
        	scores = []
        	scores.extend((df_entries['score1'][x],df_entries['score2'][x],df_entries['score3'][x],df_entries['score4'][x],df_entries['score5'][x],df_entries['score6'][x]))
        	scores.sort()
        	total = sum(scores[:5])
        	df_entries['raw_total'][x]=int(total)
        print(df_entries)
        df_entries['pos']=df_entries['raw_total'].rank(ascending=1,method='min')
        df_entries.to_sql('leaderboard',db,if_exists='replace')
        cur = db.execute('select * from leaderboard order by raw_total asc')
        entries = [dict(Name=row[1],
        				Golfer1=row[2],
        				Score1=int(row[3]),
        				Golfer2=row[4],
        				Score2=int(row[5]),
        				Golfer3=row[6],
        				Score3=int(row[7]),
        				Golfer4=row[8],
        				Score4=int(row[9]),
        				Golfer5=row[10],
        				Score5=int(row[11]),
        				Golfer6=row[12],
        				Score6=int(row[13]),
        				Birdies=int(row[14]),
        				raw_total=row[15],
        				position=int(row[16])) for row in cur.fetchall()]

        db.commit()

    else:
        db = get_db()
        entries = db.execute('select name from inputs')
        flash('Full picks will be displayed once tournament begins.')

    return render_template('show_entries.html', entries=entries)


# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     error = None
#     if request.method == 'POST':
#         if request.form['username'] != app.config['USERNAME']:
#             error = 'Invalid username'
#         elif request.form['password'] != app.config['PASSWORD']:
#             error = 'Invalid password'
#         else:
#             session['logged_in'] = True
#             # flash('You were logged in')
#             return redirect(url_for('admin'))
#     return render_template('login.html', error=error)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
	print("Hi")
	db = get_db()
	df_entries = pd.read_sql_query("select name from inputs where paid = 'N'",db)
	if df_entries.empty:
		flash('There are no unpaid entries.')
	unpaid = df_entries['name'].values.tolist()
	if request.method == 'POST':
		tid = request.form.get('tid')
		paid = request.form.getlist('paid')
		db = get_db()
# 		if request.form.get('tid') != '':
# 		    print(request.form.get('tid'))
# 		    db.execute("update tournament set tournamentid = ?",[request.form.get('tid')])
# 		    db.commit()
		for x in paid:
		    db.execute("update inputs set paid = 'Y' where name = ?",(x,))
		    db.commit()
		return redirect(url_for('admin'))
	cur2 = db.execute('select * from inputs')
	num = db.execute('select count(*) from inputs').fetchone()[0]
	entries = [dict(Name=row[0],
            Golfer1=row[1],
            Golfer2=row[3],
            Golfer3=row[5],
            Golfer4=row[7],
            Golfer5=row[9],
            Golfer6=row[11],
            Birdies=int(row[13]),
            paid=row[14]) for row in cur2.fetchall()]
	return render_template('admin.html',unpaid=unpaid, entries=entries, num=num)


@app.route('/add', methods=['GET', 'POST'])
def add_entry():
    if datetime.today() < golive:
        db = get_db()

        cur = db.execute('select PLAYER from golfers')
        df_top20 = pd.DataFrame(cur.fetchall(),columns=['name'])
        top20 = df_top20['name'].tolist()[:20]
        not20 = sorted(df_top20['name'].tolist()[20:])
        if request.method == 'POST':
            if ((request.form.get('golfer1') != request.form.get('golfer2'))
                and (request.form.get('golfer1') != request.form.get('golfer3'))
                and (request.form.get('golfer2') != request.form.get('golfer3'))
                and (request.form.get('golfer4') != request.form.get('golfer5'))
                and (request.form.get('golfer4') != request.form.get('golfer6'))
                and (request.form.get('golfer5') != request.form.get('golfer6'))
                and (request.form.get('golfer1') != '')
                and (request.form.get('golfer2') != '')
                and (request.form.get('golfer3') != '')
                and (request.form.get('golfer4') != '')
                and (request.form.get('golfer5') != '')
                and (request.form.get('golfer6') != '')
                and (request.form.get('name') != '')
                and (request.form.get('birdies') != '')
                and (request.form.get('email') != '')):
                    df_rankings = pd.read_sql_query('select * from golfers',db)
                    my_dict = dict(zip(df_rankings.PLAYER,df_rankings.RANK))
                    d = {'PLAYER':[request.form.get('golfer1'),request.form.get('golfer2'),request.form.get('golfer3'),request.form.get('golfer4'),request.form.get('golfer5'),request.form.get('golfer6')]}
                    print(d)
                    df = pd.DataFrame(data=d)
                    print(df.to_string())
                    df['RANK']=df.PLAYER.map(my_dict)
                    print(df.to_string())
                    df = df.sort_values('RANK').reset_index(drop=True)
                    print(df.to_string())
                    print(df.PLAYER[0],df.PLAYER[1])
                    db.execute('insert into inputs (name, email, golfer1, golfer2, golfer3, golfer4, golfer5, golfer6, paid, birdies) values (?, ?, ?, ?, ?, ?, ?, ?, ?,?)',[request.form.get('name').title(), request.form.get('email'), df.PLAYER[0], df.PLAYER[1],df.PLAYER[2],df.PLAYER[3],df.PLAYER[4],df.PLAYER[5],'N',request.form.get('birdies')])
                    db.commit()
                    flash('Your entry was successfully posted')
            elif ((request.form.get('golfer1') == request.form.get('golfer2')) or (request.form.get('golfer1') == request.form.get('golfer3')) or (request.form.get('golfer2') == request.form.get('golfer3')) or (request.form.get('golfer4') == request.form.get('golfer5')) or (request.form.get('golfer4') == request.form.get('golfer6')) or (request.form.get('golfer5') == request.form.get('golfer6'))):
                flash('You cannot pick two of the same golfers.')
            elif ((request.form.get('golfer1') == '') or (request.form.get('golfer2') == '') or (request.form.get('golfer3') == '') or (request.form.get('golfer4') == '') or (request.form.get('golfer5') == '') or (request.form.get('golfer6') == '')):
                flash('One of your golfer slots is blank.')
            elif request.form.get('name') == '':
                flash('Enter your name.')
            elif request.form.get('email') == '':
                flash('Enter your email.')
            elif request.form.get('birdies') == '':
                flash('Enter your birdie number.')
            else:
                flash('Fix your entry below.')
        return render_template('add.html', top20=top20, not20=not20)
    else:
        flash('The entry window has closed.')
        return render_template('add.html')


@app.route('/scoreboard', methods=['GET', 'POST'])
def scoreboard():
    db = get_db()
    cur = db.execute('select * from raw_scores')
    scores = [dict(pos=row[1],player=row[2],to_par=row[3],thru=row[4],owned=row[5]) for row in cur.fetchall()]
    return render_template('scoreboard.html',scores=scores)

@app.route('/rules', methods=['GET'])
def rules():
    return render_template('rules.html')

