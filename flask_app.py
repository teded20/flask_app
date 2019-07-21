
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3 as sql
from datetime import datetime,timedelta
from flask_mail import Mail, Message
from flask import Flask, request, session, g, redirect, url_for,render_template, flash


golive = datetime(2019,7,18,5,0)

app = Flask(__name__)
mail = Mail(app)

# app.config["DEBUG"] = True

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

# @app.errorhandler(404)
# def page_not_found(e):
#     msg = Message("Hello",sender="from@example.com",recipients=["tsedwards17@gmail.com"])
#     mail.send(msg)
#     return render_template("404.html")


@app.route('/',methods=["GET", "POST"])
def index():

    # db = get_db()
    # db.execute('delete from inputs') # for when starting new tournament
    # db.execute('delete from golfers')
    # db.execute('delete from leaderboard')
    # db.execute('delete from raw_scores')
    # db.commit()

    try:
        if datetime.now() > golive:
            db = get_db()

            lasttime = db.execute('select * from datetime').fetchone()[0]
            lasttime = datetime.strptime(lasttime,'%Y-%m-%d %H:%M:%S.%f')
            nowtime = datetime.today()
            delt = nowtime - lasttime

            if delt > timedelta(0,10):
                url = "https://www.espn.com/golf/leaderboard/_/tournamentId/401056547"
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
                #leaderboard.append([len(pos)+1,'Louis Oosthuizen','CUT','WD'])
                for x in range(0,len(leaderboard)):
                    # if leaderboard[x][1]=='Alexander Noren':
                    #     leaderboard[x][1] = 'Alex Noren'
                    # if leaderboard[x][1]=='Rafael Cabrera Bello':
                    #     leaderboard[x][1] = 'Rafa Cabrera Bello'
                    # if leaderboard[x][1]=='Alvaro Ortiz (a)':
                    #     leaderboard[x][1] = 'Alvaro Ortiz Becerra'
                    if leaderboard[x][2]=='-' and len(leaderboard[x][2])==1:
                        leaderboard[x][2] = '0'
                #    if leaderboard[x][1]=='Haotong Li':
                #        leaderboard[x][0]=len(pos)
                #        leaderboard[x][2]='CUT'
                #        leaderboard[x][3]='WD'
                df=pd.DataFrame(leaderboard,columns = column_headers)
                df.to_sql('raw_scores',db,if_exists ='replace') #comment this in once espn link works
                df['POS'] = df['POS'].str.replace('T','')
                df['PLAYER'] = df['PLAYER'].str.replace(r" \(.*\)","")
                df['PLAYER'] = df['PLAYER'].str.replace('-','')
                df['TO_PAR']=df['TO_PAR'].str.replace('E','0')
                df['TO_PAR']=df['TO_PAR'].str.replace('WD','0')

                # if (datetime.today().weekday() > 4 or datetime.today().weekday() < 3):
                if datetime.now() > datetime(2019,6,14,5,0):
                    #df_cut = df.sort_values('POS',ascending=False)
                    not_cut = df[df.POS != '-']
                    # df_cut = df_cut[pd.notnull(df_cut['TO_PAR'])]
                    cut_score = int(not_cut['TO_PAR'][not_cut.index[-1]])+2
                    df['TO_PAR'] = df['TO_PAR'].replace('CUT',cut_score)
                    df['TO_PAR'] = df['TO_PAR'].replace('WD',cut_score)

                #df['TO_PAR'] = df['TO_PAR'].str.replace('-','0')
                df['TO_PAR'] = df['TO_PAR'].astype('float',errors='ignore')
                if df.loc[0,'POS'] != df.loc[1,'POS']:
                    df.loc[0,'TO_PAR']=df.loc[0,'TO_PAR']-3
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
    except Exception as e:
        msg = Message("Hello",sender="from@example.com",recipients=["tsedwards17@gmail.com"])
        #mail.send(msg)
        return render_template('404.html')

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
	df_entries = pd.read_sql_query("select name from inputs where paid = 'N'",db)
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


        #this changed for the PGA Championship, need to update with not using the OWGR event and just using espn + the OWGR ranking site
#       top20url = 'http://www.owgr.com/ranking'
#     	top20page = requests.get(top20url)
#     	top20soup = BeautifulSoup(top20page.content,'html.parser')
#     	names = top20soup.findAll('td',{'class':'name'})
#     	rankings = []
#     	for x in range(0,len(names)):
#     		rankings.append([str(names[x].getText()),int(x+1)])
#     	column_headers = ['PLAYER','RANK']
#     	field = pd.DataFrame(rankings,columns=column_headers)
#     	field['PLAYER'] = field['PLAYER'].str.split('[(]').str[0]
#     	field = field.sort_values('RANK',ascending=True)
#     	field.to_sql('golfers',db,if_exists = 'replace')

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
	scores = [dict(pos=row[1],player=row[2],to_par=row[3],thru=row[4]) for row in cur.fetchall()]
	return render_template('scoreboard.html',scores=scores)

@app.route('/rules', methods=['GET'])
def rules():
	return render_template('rules.html')


