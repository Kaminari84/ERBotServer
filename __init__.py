import logging
import os
import json
import requests
import base64

import time
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

def pretty_print_POST(req):
	"""
	At this point it is completely built and ready
	to be fired; it is "prepared".

	However pay attention at the formatting used in 
	this function because it is programmed to be pretty 
	printed and may differ from the actual request.
	"""
	print('{}\n{}\n{}\n\n{}'.format(
		'-----------START-----------',
		req.method + ' ' + req.url,
		'\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
		req.body,
	))

def setup_app(app):
	'''
	f = open('./logs/test.txt', 'w+')
	f.write('hello world')
	f.close()
	'''

	audio_path = os.path.join(app.root_path, "static/audio/audio_test.wav")
	with open(audio_path, 'wb') as fd:
		pass

	logging.info("Instance path:"+os.path.join(app.root_path))
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

	logging.info("Rendering ER conversations...")

	return render_template('list_er_conversations.html',
		conversations = er_conversations
	)

@app.route('/ttsRequest')
def tts_request():
	logging.info("tts request...")
	json_resp = json.dumps({})
	text_call = request.args.get('text')
	voice_call = request.args.get('voice')
	lang_call = request.args.get('lang')
	speed_reduction_call = request.args.get('speed_reduction')
	if text_call is not None:

		key = "dff62f4138fa4314bcd1bf12c3e97602"
		url_token = 'https://api.cognitive.microsoft.com/sts/v1.0/issueToken'
		url_synth = 'https://speech.platform.bing.com/synthesize'

		voice = "Microsoft Server Speech Text to Speech Voice (en-US, ZiraRUS)"
		if voice_call is not None:
			voice = voice_call

		lang = "en-US"
		if lang_call is not None:
			lang = lang_call

		text = text_call

		speed_reduction = 0.0
		if speed_reduction_call is not None:
			speed_reduction = speed_reduction_call

		client_app_guid = 'e0e6613c7f7f4a5dbc06d5ad592895b4'
		instance_app_guid = '94eb5ccc71344c27ae7ab3fd2e572a52'
		app_name = 'Test_Speech_Gen'
		audio_filename = "static/audio/audio_"+datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f")+".wav"

		options = {
			"http":{
			}
		}
		
		logging.info("-------REQUEST 1--------")
		headers = {	'Ocp-Apim-Subscription-Key': str(key),
					'Content-Length': "0"}

		r = requests.post(url_token, headers=headers)#data = {'key':'value'})
		logging.info("Status Code:"+str(r.status_code))
		logging.info("Resp headers:"+str(r.headers))

		auth_token = r.content
		logging.info("Auth Token:"+str(auth_token))


		#make the request for audio synthesis

		logging.info("-------REQUEST 2--------")
		#https://stackoverflow.com/questions/45247983/urllib-urlretrieve-with-custom-header

		data = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '+ \
		'xmlns:mstts="http://www.w3.org/2001/mstts" '+ \
		'xml:lang="'+str(lang)+'">'+ \
		'<voice xml:lang="'+str(lang)+'" '+ \
		'name="'+str(voice)+'">'+ \
		'<prosody pitch="high" rate="-'+speed_reduction+'%">'+ \
		str(text)+ \
		'</prosody>' + \
		'</voice>'+ \
		'</speak>'

		token_base64 = base64.b64encode(auth_token).decode('ascii')

		headers = {	'Authorization': "Bearer "+auth_token.decode('ascii'),
					'Content-Type': "application/ssml+xml",
					'X-Microsoft-OutputFormat': "riff-8khz-8bit-mono-mulaw",
					'X-Search-AppId': client_app_guid,
					'X-Search-ClientID': instance_app_guid,
					'User-Agent': app_name,
					'Content-Length': str(len(data))}

		#r2 = requests.post(url_synth, headers=headers, data = json.dumps({'content':data}))
		req = requests.Request('POST',url_synth, headers=headers, data = data.encode('utf-8'))
		prepared = req.prepare()
		pretty_print_POST(prepared)

		s = requests.Session()
		resp = s.send(prepared)

		logging.info("Status Code:"+str(resp.status_code))
		logging.info("Resp headers:"+str(resp.headers))
		#print("Resp content:"+str(resp.content))

		audio_fullpath = os.path.join(app.root_path, audio_filename)
		logging.info("Audio full path:"+audio_fullpath)
		with open(audio_fullpath, 'wb') as fd:
			for chunk in resp.iter_content(chunk_size=128):
				fd.write(chunk)
	
		if resp.status_code == requests.codes.ok:
			logging.info("TTS request success!!!")
			json_resp = json.dumps({"audio_file":audio_filename})
		else:
			logging.warn("!!!TTS request failed")
	else:
		logging.warn("Error, text empty!!!")


	return make_response(json_resp, 200, {"content_type":"application/json"})
	#return "", 200, {'Content-Type': 'text/html; charset=utf-8'}
