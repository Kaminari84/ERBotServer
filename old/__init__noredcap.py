import logging
import os
import json
import requests
import base64
import hashlib

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

#DATABASE Log class
class EventLog(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	conv_id = db.Column(db.String(80))
	event = db.Column(db.String(1024))
	timestamp = db.Column(db.DateTime())

	def __init__(self, conv_id, event):
		self.conv_id = conv_id
		self.event = event
		self.timestamp = pstnow()

#Date-Time helpers
def utcnow():
    return datetime.now(tz=pytz.utc)

def pstnow():
    utc_time = utcnow()
    pacific = timezone('US/Pacific')
    pst_time = utc_time.astimezone(pacific)
    return pst_time

#Debugging POST reqyest for TTS helper
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

#Server initial setup
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

@app.route('/test_redcap')
def test_redcap():
	return render_template('test_redcap.html')

@app.route('/er_bot')
def er_bot():
	return render_template('er_bot.html')

@app.route('/er_bot_get_conversation')
def er_bot_get_conversation():
	event_list = []
	logging.info("Viewing single conversation...")

	conv_id = request.args.get('conv_id')
	if conv_id is not None:
		logging.info("Conversation ID is not empty: "+str(conv_id))
		events = EventLog.query.filter_by(conv_id=conv_id).order_by(sqlalchemy.asc(EventLog.timestamp)).limit(1000)
		for event in events:
			logging.info("Event:"+str(event.event))
			event_list.append({'server_time':event.timestamp.isoformat(' '), 'data':json.loads(event.event)})

	json_resp = json.dumps(event_list)

	return make_response(json_resp, 200, {"content_type":"application/json"})


@app.route('/er_bot_conversations')
def list_er_bot_conversations():
	er_conversations = []
	logging.info("Rendering ER conversations...")

	conv_ids = {}

	allEvents = EventLog.query.order_by(sqlalchemy.desc(EventLog.timestamp)).limit(10000)
	for event in allEvents:
		logging.info("Conv ID:"+event.conv_id)
		if event.conv_id not in conv_ids:
			logging.info("New conversation ID, get first date:")
			no_events = EventLog.query.filter_by(conv_id=event.conv_id).order_by(sqlalchemy.asc(EventLog.timestamp)).count()
			logging.info("Number of events: "+str(no_events))
			oldest_event = EventLog.query.filter_by(conv_id=event.conv_id).order_by(sqlalchemy.asc(EventLog.timestamp)).first()
			if oldest_event:
				logging.info("Got first event" + oldest_event.timestamp.isoformat(' '))
				conv_ids[event.conv_id] = { "start_date":oldest_event.timestamp.isoformat(' '), "no_events": no_events }

	for key, value in conv_ids.items():
		er_conversations.append( { 'datetime': value["start_date"],'filepath': key,'len': value['no_events'] } )


	return render_template('list_er_conversations.html',
		conversations = er_conversations
	)

@app.route('/logErEvent')
def log_er_event():
	logging.info("Got log ER event request...")
	json_resp = json.dumps({})
	conv_id = request.args.get('conv_id')
	data = request.args.get('data')
	logging.info("Conv_id: "+str(conv_id))
	logging.info("Data: "+str(data))
	if conv_id is not None and data is not None:
		logging.info("There is data in it!")

		event_data = json.dumps({})
		try:
			event_data = json.loads(data)
		except ValueError:
			logging.info("Can't parse event data as JSON")
			json_resp = json.dumps({'status':'error', 'message':'Provided event data not JSON according to Python3 json.loads'})
			return make_response(json_resp, 200, {"content_type":"application/json"})

		eventLog = EventLog(conv_id = conv_id, event = json.dumps(event_data))

		logging.info("Adding event to log...")
		db.session.merge(eventLog)
		db.session.commit()

		# Add logging to the REDCap
		# 1) Get the next record ID to add
		#data = {
		#	'token': 'C585B6F067E9AEEE18C399D77960693A',
		#	'content': 'generateNextRecordName'
		#}
		#r = requests.post('https://redcap.iths.org/api/', data)
		#r_id = int(r.text)
		#logging.info("****New record ID:" +str(r_id))

		r_id = hashlib.sha1().hexdigest()[:16]
		print("Generated universal ID:" + str(r_id))

		data = {
    			'token': 'C585B6F067E9AEEE18C399D77960693A',
    			'content': 'record',
    			'format': 'json',
    			'type': 'flat',
    			'overwriteBehavior': 'normal',
    			'forceAutoNumber': 'true',
    			'data': '[{ "record_id": "'+str(r_id)+'", "user":"Test", "entry":599, "my_first_instrument_complete":2 }]',
    			'returnContent': 'auto_ids',
    			'returnFormat': 'json',
    			'record_id': hashlib.sha1().hexdigest()[:16]
		}
		r = requests.post('https://redcap.iths.org/api/', data)
		logging.info("****Resp from REDCap:" +str(r.text))

		json_resp = json.dumps( {'status':'OK', 'conv_id':conv_id, 'event_entry':event_data })
	else:
		logging.info("No data in event request")
		json_resp = json.dumps({'status':'error', 'message':'No data in event log request!'})

	return make_response(json_resp, 200, {"content_type":"application/json"})

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
