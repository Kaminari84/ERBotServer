import logging
import os
import json
import requests
import base64
import hashlib
import re
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

@app.route('/er_bot_orig')
def er_bot_orig():
	return render_template('er_bot_orig.html')

@app.route('/er_bot')
def er_bot():
	return render_template('er_bot.html')

@app.route('/uploadToRedCap')
def upload_to_redcap():
	logging.info("Uploading to Redcap...")

	conv_id = request.args.get('conv_id')
	p_id = request.args.get('p_id')
	q_answers = request.args.get('q_answers')
	conv_complete = request.args.get('conv_complete')

	if conv_complete is None:
		conv_complete = 0

	if conv_id is not None and p_id is not None:
		logging.info("Conversation ID is not empty: "+str(conv_id)+", q_answers:"+str(q_answers))

		#####----- Start constructing new REDCap compatible JSON -----#####
		logging.info("Start constructing RedCap upload...")
		r_id = hashlib.sha1().hexdigest()[:16]
		logging.info("Generated RID:" + str(r_id))

		redcap_json = json.loads("{}")
		redcap_json['conv_id'] = str(conv_id)
		redcap_json['record_id'] = str(conv_id) #str(r_id)

		event_list = []
		events = EventLog.query.filter_by(conv_id=conv_id).order_by(sqlalchemy.asc(EventLog.timestamp)).limit(1000)
		for event in events:
			event_list.append({'server_time':event.timestamp.isoformat(' '), 'data':json.loads(event.event)})

		#RedCap log entry
		conv_events_text = json.dumps(event_list)
		redcap_json['conv_log'] = conv_events_text
		redcap_json['harbor_conv_log_complete'] = conv_complete #0-Incomplete, 1-Unverified, 2-Complere

		#RedCap question-answers entry
		redcap_json['q_answers'] = q_answers #"q:'What is your best...?', a:'4567'\nq:'Are you safe?',a:'No'"
		redcap_json['answer_time'] = pstnow().strftime('%d-%m-%Y %H:%M:%S')
		redcap_json['p_id'] = p_id
		redcap_json['harbor_conv_answers_complete'] = conv_complete

		redcap_text = json.dumps(redcap_json)
		logging.info("RedCap json text:" + str(redcap_text));

		#####--------------- Start REDCap event logging --------------#####
		data = {
			'token': 'C585B6F067E9AEEE18C399D77960693A',
			'content': 'record',
			'format': 'json',
			'type': 'flat',
			'overwriteBehavior': 'normal',
			'forceAutoNumber': 'false',
			'data': '['+redcap_text+']',
			'returnContent': 'count', #'auto_ids',
			'returnFormat': 'json',
			'record_id': str(r_id)
		}
		r = requests.post('https://redcap.iths.org/api/', data)
		logging.info("****Resp from REDCap:" +str(r.text))

		####----------------- End REDCap event logging ----------------####

		json_resp = json.dumps({'status': 'OK', 'conv_id':conv_id})
	else:
		json_resp = json.dumps({'status': "error", 'message':'Missing conv_id argument'})

	return make_response(json_resp, 200, {"content_type":"application/json"})

#@app.route('/d1_bot')
#def d1_bot():
#        return render_template('D1_bot.html')

#@app.route('/d2_bot')
#def d2_bot():
#        return render_template('D2_bot.html')

#@app.route('/d3_bot')
#def d3_bot():
#        return render_template('D3_bot.html')

#@app.route('/d4_bot')
#def d4_bot():
#        return render_template('D4_bot.html')

#@app.route('/d5_bot')
#def d5_bot():
#        return render_template('D5_bot.html')

#@app.route('/d6_bot')
#def d6_bot():
#        return render_template('D6_bot.html')

#@app.route('/er_bot_balanced')
#def er_bot_balanced():
#        return render_template('er_bot_balanced.html')

#@app.route('/er_bot_issue_focused')
#def er_bot_issue_focused():
#        return render_template('er_bot_issue_focused.html')

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

	allEvents = EventLog.query.order_by(sqlalchemy.desc(EventLog.timestamp)).limit(1000)
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

		#####----- Start constructing new REDCap compatible JSON -----#####

		#r_id = hashlib.sha1().hexdigest()[:16]
		#logging.info("Generated RID:" + str(r_id))

		#redcap_json = json.loads("{}")
		#redcap_json['conv_id'] = str(conv_id)
		#redcap_json['record_id'] = str(r_id)

		#field_map = {
		#	"event-type": "event_type",
		#	"timestamp": "timestamp",
		#	"q-id": "q_id",
		#	"q-text": "q_text",
		#	"q-alt": "q_alt",
		#	"dialogue-position": "dialogue_position",
		#	"audio-id": "audio_id",
		#	"lang": "lang",
		#	"voice": "voice",
		#	"speech-speed": "speech_speed",
		#	"audio-file": "audio_file",
		#	"date": "date",
		#	"time": "time",
		#	"q-answer-type": "q_answer_type",
		#	"q-answer": "q_answer"
		#}

		#for s_field, d_field in field_map.items():
		#	if s_field in event_data:
		#		redcap_json[d_field] = event_data[s_field]


		## The redcap entry complete statu checks
		#event_fields = {
		#	"q-audio-stopped":['conv_id','timestamp','q_id','q_text','q_alt',
		#			'dialogue_position','audio_id'],
               	#	"q-audio-play":['conv_id','timestamp','q_id','q_text','q_alt',
		#			'dialogue_position','audio_id','lang','voice',
		#			'speech_speed','audio_file'],
               	#	"q-audio-paused":['conv_id','timestamp','q_id','q_text','q_alt',
		#			'dialogue_position','audio_id','audio_file'],
              	#	"q-asked":['conv_id','timestamp','q_id','q_text','q_alt','lang','q_answer_type'],
               	#	"q-answered":['conv_id','timestamp','q_id','lang','q_answer_type','q_answer'],
               	#	"start-conversation":['conv_id','timestamp','date','time'],
               	#	"end-conversation":['conv_id','timestamp','date','time']
		#	}

		#def check_all_fields(redcap_json, event_fields_spec):
		#	all_fields = False
		#	if 'event_type' in redcap_json:
		#		if redcap_json['event_type'] in event_fields_spec:
		#			all_fields = True
		#			for field_name in event_fields_spec[redcap_json['event_type']]:
		#				if field_name not in redcap_json:
		#					all_fields = False
		#	return all_fields

		## Indicate the completion
		#check_result = check_all_fields(redcap_json, event_fields)
		#if check_result == True:
		#	redcap_json['harbor_event_log_complete'] = 2 #0-Incomplete, 1-Unverified, 2-Complere
		#else:
		#	redcap_json['harbor_event_log_complete'] = 0

		#redcap_text = json.dumps(redcap_json)
		#logging.info("Json Text:" + str(redcap_text));


		#####--------------- Start REDCap event logging --------------#####

		#data = {
    		#	'token': 'C585B6F067E9AEEE18C399D77960693A',
    		#	'content': 'record',
    		#	'format': 'json',
    		#	'type': 'flat',
    		#	'overwriteBehavior': 'normal',
    		#	'forceAutoNumber': 'true',
    		#	'data': '['+redcap_text+']',
    		#	'returnContent': 'auto_ids',
    		#	'returnFormat': 'json',
    		#	'record_id': str(r_id)
		#}
		#r = requests.post('https://redcap.iths.org/api/', data)
		#logging.info("****Resp from REDCap:" +str(r.text))

		#####----------------- End REDCap event logging ----------------####

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

		# Construct reusable audio filename
		logging.info("Constructing reusable audio filename...")
		hash_object = hashlib.md5(text.encode())
		text_md5 = hash_object.hexdigest()
		logging.info("Hashed text:"+text_md5)

		# Encodeing voice
		p_voice = re.compile(r'\([A-Za-z_,)\- ]+')
		v_match = p_voice.findall(voice)
		v_fin = ""
		if len(v_match) > 0:
			v_fin = v_match[0].replace('(','').replace(')','').replace(',','').replace(' ','')
			v_fin = v_fin.replace(lang,'')
		logging.info("Voice info:"+v_fin)

		audio_filename = "static/audio/audio_v_"+v_fin+"_l_"+lang.replace('-','')+"_s_"+str(speed_reduction)+"_t_"+text_md5+".wav" 
		#audio_filename = "static/audio/audio_"+datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f")+".wav"

		audio_fullpath = os.path.join(app.root_path, audio_filename)
		logging.info("Audio full path:"+audio_fullpath)

		if os.path.exists(audio_fullpath):
			logging.info("Audio file already on server, not need to call TTS!")
			json_resp = json.dumps({"audio_file":audio_filename})
		else:
			logging.info("Audio file not on server, calling TTS!")


			options = {
				"http":{
				}
			}

			logging.info("-------TTS REQUEST \#1 - TOKEN--------")
			headers = {	'Ocp-Apim-Subscription-Key': str(key),
					'Content-Length': "0"}

			r = requests.post(url_token, headers=headers)#data = {'key':'value'})
			logging.info("Status Code:"+str(r.status_code))
			logging.info("Resp headers:"+str(r.headers))

			auth_token = r.content
			logging.info("Auth Token:"+str(auth_token))

			#make the request for audio synthesis

			logging.info("-------TTS REQUEST \#2 - AUDIO SYNTHESIS--------")
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

			#audio_fullpath = os.path.join(app.root_path, audio_filename)
			#logging.info("Audio full path:"+audio_fullpath)
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
