import ast
import json
import os
import re
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
LOOK=ROOT/'look'/'lk'


def weather_namespace():
    tree=ast.parse(LOOK.read_text())
    wanted={
        '_lo_requires_weather', '_normalize_weather_location', '_lo_weather_location',
        '_lo_weather_history_location', '_lo_weather_default_location',
        '_lo_weather_context', '_lo_weather_followup', '_lo_weather_followup_location',
        '_lo_weather_verification_requested', '_weather_payload',
        '_lo_home_location_declaration', '_lo_learned_home_location', '_lo_weather_pending_location',
        '_weather_direct_followup', '_weather_code_text', '_weather_direct_summary', '_weather_verify_nws', '_weather_verification_answer',
    }
    body=[]
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names=[t.id for t in node.targets if isinstance(t,ast.Name)]
            if '_US_STATE_ABBREVIATIONS' in names:
                body.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted:
            body.append(node)
    ns={'re':re,'os':os,'json':json,'time':time}
    exec(compile(ast.Module(body=body,type_ignores=[]),str(LOOK),'exec'),ns)
    return ns


class WeatherEdge514Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w=weather_namespace()

    def test_state_shorthand_is_canonicalized(self):
        self.assertEqual(self.w['_lo_weather_location']('weather in portland or'),'portland, Oregon')
        self.assertEqual(self.w['_lo_weather_location']('weather in Portland, OR'),'Portland, Oregon')
        self.assertEqual(self.w['_lo_weather_location']('weather in Portland Oregon'),'Portland, Oregon')
        self.assertEqual(self.w['_normalize_weather_location']('portland oregon'),'portland, Oregon')

    def test_session_location_reused_for_implicit_weather(self):
        history=[
            {'role':'user','content':'weather in portland'},
            {'role':'assistant','content':'Current conditions...'},
            {'role':'user','content':'thanks'},
        ]
        self.assertEqual(self.w['_lo_weather_history_location'](history),'portland')

    def test_location_changing_followup_becomes_active_weather_place(self):
        history=[
            {'role':'user','content':'weather in portland'},
            {'role':'assistant','content':'Portland conditions...'},
            {'role':'user','content':'how about beaverton or'},
            {'role':'assistant','content':'Beaverton conditions...'},
            {'role':'user','content':'what is high and low today'},
        ]
        self.assertEqual(self.w['_lo_weather_history_location'](history),'beaverton, Oregon')

    def test_operator_default_location(self):
        with patch.dict(os.environ,{'LOOK_WEATHER_LOCATION':'Portland OR'},clear=False):
            self.assertEqual(self.w['_lo_weather_default_location'](),'Portland, Oregon')

    def test_weather_followup_recognizes_location_and_scalar_queries(self):
        history=[
            {'role':'user','content':'how is the weather today in portland'},
            {'role':'assistant','content':'67 degrees'},
        ]
        self.assertTrue(self.w['_lo_weather_followup']('how about beaverton or',history))
        self.assertEqual(self.w['_lo_weather_followup_location']('how about beaverton or',history),'beaverton, Oregon')
        self.assertTrue(self.w['_lo_weather_followup']('what is high and low today',history))
        self.assertTrue(self.w['_lo_weather_followup']('is that accurate?',history))
        self.assertTrue(self.w['_lo_weather_verification_requested']('is that accurate?'))

    def test_direct_high_low_reads_one_typed_receipt(self):
        receipt={
            'edge':'WEATHER','source':'Open-Meteo',
            'location':{'name':'Beaverton','region':'Oregon, United States'},
            'current':{'temperature_2m':65.5},
            'forecast':[{'date':'2026-09-19','high_f':69.0,'low_f':50.0},
                        {'date':'2026-09-20','high_f':73.0,'low_f':51.0}],
        }
        answer=self.w['_weather_direct_followup']('what is high and low today',json.dumps(receipt))
        self.assertEqual(answer,'The high today in Beaverton, Oregon, United States is 69.0°F, and the low is 50.0°F.')
        tomorrow=self.w['_weather_direct_followup']('high and low tomorrow',json.dumps(receipt))
        self.assertIn('73.0°F',tomorrow)
        self.assertIn('51.0°F',tomorrow)

    def test_nws_verification_is_independent_and_numeric(self):
        receipt={
            'edge':'WEATHER','source':'Open-Meteo',
            'location':{'name':'Beaverton','latitude':45.49,'longitude':-122.80},
            'current':{'temperature_2m':65.5,'relative_humidity_2m':78},
            'forecast':[],
        }
        calls=[]
        def fake_http(url, timeout=12):
            calls.append(url)
            if '/points/' in url:
                return {'properties':{'observationStations':'https://api.weather.gov/gridpoints/PQR/obs/stations'}}
            if url.endswith('/stations'):
                return {'features':[{'id':'https://api.weather.gov/stations/KHIO','properties':{'stationIdentifier':'KHIO'}}]}
            if url.endswith('/observations/latest'):
                return {'properties':{
                    'timestamp':'2026-09-19T23:00:00+00:00',
                    'temperature':{'value':20.0},
                    'relativeHumidity':{'value':65.0},
                    'windSpeed':{'value':1.5},
                    'textDescription':'Partly Cloudy',
                }}
            raise AssertionError(url)
        self.w['_http_json']=fake_http
        verification=self.w['_weather_verify_nws'](json.dumps(receipt))
        row=json.loads(verification)
        self.assertEqual(row['source'],'National Weather Service')
        self.assertEqual(row['temperature_f'],68.0)
        answer=self.w['_weather_verification_answer'](json.dumps(receipt),verification)
        self.assertIn('Open-Meteo 65.5°F',answer)
        self.assertIn('NWS 68.0°F',answer)
        self.assertIn('difference 2.5°F',answer)
        self.assertGreaterEqual(len(calls),3)


    def test_home_declaration_is_operator_state_not_geocoder_guess(self):
        self.assertEqual(self.w['_lo_home_location_declaration']('my home is portland oregon'),'portland, Oregon')
        self.assertEqual(self.w['_lo_home_location_declaration']('no home is Portland OR'),'Portland, Oregon')
        self.assertEqual(self.w['_lo_home_location_declaration']('my home is portland what is the weather'),'portland')
        self.assertEqual(self.w['_lo_home_location_declaration']('remember that i live in portland oregon'),'portland, Oregon')
        self.assertEqual(self.w['_lo_home_location_declaration']('I live in Portland OR'),'Portland, Oregon')

    def test_pending_weather_location_resolves_home_atom_or_bare_place(self):
        memory={'atoms':[{'k':'preference','s':'home','r':'weather_location','v':'Portland, Oregon','c':100,'u':1,'t':1}]}
        self.assertEqual(self.w['_lo_learned_home_location'](memory),'Portland, Oregon')
        self.assertEqual(self.w['_lo_weather_pending_location']('home',memory),'Portland, Oregon')
        self.assertEqual(self.w['_lo_weather_pending_location']('portland',memory),'portland')
        self.assertEqual(self.w['_lo_weather_pending_location']('weather in portland oregon',memory),'portland, Oregon')
        self.assertIsNone(self.w['_lo_weather_pending_location']('what is the time',memory))
        self.assertIsNone(self.w['_lo_weather_pending_location']('lo what is the date',memory))
        self.assertIsNone(self.w['_lo_weather_pending_location']('open the browser',memory))
        self.assertIsNone(self.w['_lo_weather_pending_location']('home',{'atoms':[]}))

    def test_current_weather_has_deterministic_final_answer(self):
        receipt={
            'edge':'WEATHER','source':'Open-Meteo',
            'location':{'name':'Portland','admin1':'Oregon','country':'United States'},
            'current':{'temperature_2m':61.2,'apparent_temperature':60.0,'relative_humidity_2m':70,'wind_speed_10m':4.5,'weather_code':1},
            'forecast':[{'date':'2026-09-25','high_f':72.0,'low_f':51.0,'precip_probability_pct':10}],
        }
        answer=self.w['_weather_direct_summary'](json.dumps(receipt))
        self.assertIn('Portland, Oregon:',answer)
        self.assertIn('61.2°F',answer)
        self.assertIn('today 72.0°/51.0°',answer)
        self.assertIn('rain 10%',answer)

    def test_weather_lookup_normalizes_every_entry_path(self):
        text=LOOK.read_text()
        self.assertIn('location=_normalize_weather_location(location)',text)

    def test_missing_location_has_distinct_host_path(self):
        text=LOOK.read_text()
        self.assertIn('Which location should I use for the weather?',text)
        self.assertIn('weather_location_required',text)
        self.assertIn('weather_location_source="session"',text)
        self.assertIn('weather_discourse=',text)


if __name__=='__main__':
    unittest.main()
