import logging
import os
import time
import datetime
import pytz

from datetime import datetime, timedelta
from pytz import timezone
from pytz import common_timezones
from pytz import country_timezones

from flask import Flask, request, make_response, render_template
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy

from flask_cors import CORS

logging.basicConfig( filename='/var/www/testapp/logs/app_'+time.strftime('%d-%m-%Y-%H-%M-%S')+'.log', level=logging.INFO)

logging.info("Server loading...")

app = Flask(__name__)
UPLOAD_FOLDER = '/static/audio'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:root@127.0.0.1:3306/test"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_RECYCLE'] = 1

db = SQLAlchemy(app)

def setup_app(app):
	'''
	f = open('./logs/test.txt', 'w+')
	f.write('hello world')
	f.close()
	'''

	logging.info("Instance path:"+os.path.join(app.instance_path))
	logging.info('Creating all database tables...')
	db.create_all()
	logging.info('Done!')

	logging.info("Start the actual server...")


setup_app(app)

@app.route('/')
def hello_world():
	return 'Hello, World!'

@app.route('/er_bot')
def er_bot():
	return render_template('er_bot.html')

@app.route('/er_bot_conversations')
def list_er_bot_conversations():
	er_conversations = []

	conv_path = "/var/www/testapp/static/log_er_conversations"
	logging.info("Final path: "+conv_path)
	files_path = [x for x in os.listdir(conv_path)]
	for fname in files_path:
		fpath = os.path.join(conv_path,fname)
		fdate = time.ctime(creation_date(fpath))
		er_conv = []
		if os.path.exists(fpath):
			with open(fpath, 'r') as fp:
				try: 
					er_conv = json.load(fp)
				except ValueError:
					logging.warn("Error decoding past conversation JSON for: "+fpath)


		flen = len(er_conv)

		logging.info("Path:" + fpath)
		logging.info("Datetime: " + fdate)
		logging.info("Len: " + str(flen))

		er_conversations.append({'datetime': fdate,'filepath': fpath,'len': flen})

	return render_template('list_er_conversations.html',
		conversations = er_conversations
	)
