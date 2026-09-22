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
        '_weather_direct_followup', '_weather_verify_nws', '_weather_verification_answer',
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
        self.assertEqual(self.w['_lo_weather_location']('weather in Portland Oregon'),'Portland Oregon')

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

    def test_missing_location_has_distinct_host_path(self):
        text=LOOK.read_text()
        self.assertIn('Which location should I use for the weather?',text)
        self.assertIn('weather_location_required',text)
        self.assertIn('weather_location_source="session"',text)
        self.assertIn('weather_discourse=',text)


if __name__=='__main__':
    unittest.main()
