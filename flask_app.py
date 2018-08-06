
# A very simple Flask Hello World app for you to get started with...

import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3 as sql
from datetime import datetime,timedelta
from flask import Flask, request, session, g, redirect, url_for,render_template, flash
import sys

#with app.app_context():

app = Flask(__name__)
app.config["DEBUG"] = True

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flask_app.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))

# SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
#     username="tsedwards17",
#     password="comments",
#     hostname="tsedwards17.mysql.pythonanywhere-services.com",
#     databasename="tsedwards17$comments",
# )
# app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
# app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# db = SQLAlchemy(app)

# class Comment(db.Model):

#     __tablename__ = "comments"

#     id = db.Column(db.Integer, primary_key=True)
#     content = db.Column(db.String(4096))


def connect_db():
    """Connects to the specific database."""
    rv = sql.connect(app.config['DATABASE'])
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

@app.route('/',methods=["GET", "POST"])
def index():
    golive = datetime(2018,8,9,5,0)

    if datetime.now() > golive:
        db = get_db()

        # db.execute('delete from inputs') # for when starting new tournament
        # db.execute('delete from golfers')
        # db.execute('delete from leaderboard')
        # db.commit()

        lasttime = db.execute('select * from datetime').fetchone()[0]
        lasttime = datetime.strptime(lasttime,'%Y-%m-%d %H:%M:%S.%f')
        nowtime = datetime.today()
        delt = nowtime - lasttime

        if delt > timedelta(0,10):
            url = "http://www.espn.com/golf/leaderboard?tournamentId=401025263" #PGA Championship
            page = requests.get(url)
            soup = BeautifulSoup(page.content,'html.parser')
            names = soup.findAll('a',{'class':'full-name'})
            thru = soup.findAll('td',{'class':'thru in'})
            pos = soup.findAll('td',{'class':'position'})
            to_par = soup.findAll('td',{'class':'relativeScore'})
            column_headers = ['POS','PLAYER','TO_PAR','THRU']
            leaderboard = []
            for x in range(0,len(to_par)):
                leaderboard.append([pos[x].getText(),names[x].getText(),to_par[x].getText(),thru[x].getText()])
            for x in range(0,len(leaderboard)):
                if leaderboard[x][1]=='Alexander Noren':
                    leaderboard[x][1] = 'Alex Noren'
            df=pd.DataFrame(leaderboard,columns = column_headers)
            df.to_sql('raw_scores',db,if_exists ='replace')
            df['POS'] = df['POS'].str.replace('T','')


            df['TO_PAR']=df['TO_PAR'].str.replace('E','0')
            df['TO_PAR'] = df['TO_PAR'].astype('float',errors='ignore')
            # df['TO_PAR'].apply(pd.to_numeric, errors='ignore', downcast='integer')
            if df.loc[0,'POS'] != df.loc[1,'POS']:
                df.loc[0,'TO_PAR']=df.loc[0,'TO_PAR']-3
            if (datetime.today().weekday() > 4 or datetime.today().weekday() < 3):
                df_cut = df.sort_values('POS',ascending=False)
                df_cut = df_cut[pd.notnull(df_cut['TO_PAR'])]
                cut_score = int(df_cut.iloc[0]['TO_PAR'] + 2)
                df['TO_PAR'] = df['TO_PAR'].fillna(cut_score)
            df = df.drop(['POS','THRU'],1)
            df.to_sql('scores',db,if_exists ='replace')
            db.execute('update datetime set last_run = ?',(datetime.today(),))

        df_scores = pd.read_sql_query('select * from scores',db)
        df_scores['TO_PAR'] = df_scores['TO_PAR'].fillna(max(df_scores.TO_PAR))
        my_dict = dict(zip(df_scores.PLAYER,df_scores.TO_PAR))
        df_entries = pd.read_sql_query('select * from inputs',db)
        df_entries['score1'] = df_entries.golfer1.map(my_dict)
        df_entries['score2'] = df_entries.golfer2.map(my_dict)
        df_entries['score3'] = df_entries.golfer3.map(my_dict)
        df_entries['score4'] = df_entries.golfer4.map(my_dict)
        df_entries['score5'] = df_entries.golfer5.map(my_dict)
        df_entries['score6'] = df_entries.golfer6.map(my_dict)
        df_entries = df_entries[['name','golfer1','score1','golfer2','score2','golfer3','score3','golfer4','score4','golfer5','score5','golfer6','score6','birdies']]
        df_entries['raw_total']= int()
        for x in range(0,len(df_entries)):
        	scores = []
        	scores.extend((df_entries['score1'][x],df_entries['score2'][x],df_entries['score3'][x],df_entries['score4'][x],df_entries['score5'][x],df_entries['score6'][x]))
        	scores.sort()
        	total = sum(scores[:5])
        	df_entries['raw_total'][x]=int(total)
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            # flash('You were logged in')
            return redirect(url_for('admin'))
    return render_template('login.html', error=error)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
	db = get_db()
	df_entries = pd.read_sql_query("select * from inputs where paid = 'N'",db)
	if df_entries.empty:
		flash('There are no unpaid entries.')
	unpaid = df_entries['name'].values.tolist()
	if request.method == 'POST':
		paid = request.form.getlist('paid')
		db = get_db()
		for x in paid:
		    db.execute("update inputs set paid = 'Y' where name = ?",(x,))
		    db.commit()
		return redirect(url_for('admin'))
	cur2 = db.execute('select * from inputs')
	entries = [dict(Name=row[0],
            Golfer1=row[1],
            Golfer2=row[3],
            Golfer3=row[5],
            Golfer4=row[7],
            Golfer5=row[9],
            Golfer6=row[11],
            Birdies=int(row[13]),
            paid=row[14]) for row in cur2.fetchall()]
	return render_template('admin.html',unpaid=unpaid, entries=entries)


@app.route('/add', methods=['GET', 'POST'])
def add_entry():
    godown = datetime(2018,8,9,5,0)
    if datetime.today() < godown:
    	db = get_db()
    	
    	top20url = 'http://www.owgr.com/en/Events/EventResult.aspx?eventid=7125'
    	top20page = requests.get(top20url)
    	top20soup = BeautifulSoup(top20page.content,'html.parser')
    	names = top20soup.findAll('td',{'class':'name'})
    	rankings = []
    	for x in range(0,len(names)):
    		rankings.append([str(names[x].getText()),int(x+1)])
    	column_headers = ['PLAYER','RANK']
    	field = pd.DataFrame(rankings,columns=column_headers)
    	field = field.sort_values('RANK',ascending=True)
    	field.to_sql('golfers',db,if_exists = 'replace')
    	
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
    				db.execute('insert into inputs (name, email, golfer1, golfer2, golfer3, golfer4, golfer5, golfer6, paid, birdies) values (?, ?, ?, ?, ?, ?, ?, ?, ?,?)',[request.form.get('name'), request.form.get('email'), request.form.get('golfer1'), request.form.get('golfer2'),request.form.get('golfer3'),request.form.get('golfer4'),request.form.get('golfer5'),request.form.get('golfer6'),'N',request.form.get('birdies')])
    				db.commit()
    				flash('New entry was successfully posted!')
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
	scores = [dict(pos=row[1],player=row[2],to_par=row[3],thru=row[4]) for row in cur.fetchall()]
	return render_template('scoreboard.html',scores=scores)

