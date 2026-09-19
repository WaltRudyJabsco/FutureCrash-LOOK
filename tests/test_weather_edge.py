import ast
import os
import re
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
    }
    body=[]
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names=[t.id for t in node.targets if isinstance(t,ast.Name)]
            if '_US_STATE_ABBREVIATIONS' in names:
                body.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted:
            body.append(node)
    ns={'re':re,'os':os}
    exec(compile(ast.Module(body=body,type_ignores=[]),str(LOOK),'exec'),ns)
    return ns


class WeatherEdge512Tests(unittest.TestCase):
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

    def test_operator_default_location(self):
        with patch.dict(os.environ,{'LOOK_WEATHER_LOCATION':'Portland OR'},clear=False):
            self.assertEqual(self.w['_lo_weather_default_location'](),'Portland, Oregon')

    def test_missing_location_has_distinct_host_path(self):
        text=LOOK.read_text()
        self.assertIn('Which location should I use for the weather?',text)
        self.assertIn('weather_location_required',text)
        self.assertIn('weather_location_source="session"',text)


if __name__=='__main__':
    unittest.main()
