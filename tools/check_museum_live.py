"""Opt-in live smoke check: save a small public-domain exhibition, never a bulk mirror."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'core'))
import museum
out=ROOT/'artifacts/museum-live';collection=museum.Museum(out/'collection')
for ident in ('aic-27992','aic-28560','aic-80607','aic-874','met-436532','met-436535','met-435809','met-437853'):
    try:
        row=collection.save(ident,'First exhibition');print(ident,row['title'],row['bytes'],flush=True)
    except Exception as exc:print(ident,'unavailable:',str(exc),flush=True)
state=collection.snapshot();assert {x['source'] for x in state['items']}=={'met','aic'}
(out/'catalog.json').write_text(json.dumps(state,ensure_ascii=False,indent=2))
print('Live saved images:',len(state['items']))
