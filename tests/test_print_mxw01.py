"""Bluetooth receipt tests use a fake gatttool; never transmit to hardware."""
import io,json,os
from pathlib import Path
from unittest.mock import Mock
import pytest
from PIL import Image
import print_core as core
import print_mxw01 as mx

PROFILE={'kind':'escpos','transport':'mxw01-ble','address':'12:34:56:78:9A:BC','adapter':'hci1','label':'Tiny Printer','width':384,'columns':30}

@pytest.fixture
def home(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setattr(core,'discovered_devices',lambda:[])
    monkeypatch.setattr(core,'run',Mock(side_effect=RuntimeError('No CUPS')))
    return tmp_path


def test_register_preview_then_catalog_without_cups(home,monkeypatch):
    monkeypatch.setattr(core.shutil,'which',lambda _: '/test/gatttool')
    args=dict(queue='tiny',address=PROFILE['address'],adapter='hci1')
    assert not core.add_bluetooth(**args)['applied']
    assert core.profiles()=={}
    core.add_bluetooth(**args,confirm=True)
    rows=core.catalog()['printers'];assert len(rows)==1 and rows[0]['profile']['label']=='Tiny Printer'
    assert 'configured Bluetooth' in rows[0]['status']
    assert core.require_queue('Tiny Printer')=='tiny'
    assert 'Bluetooth-LE' in core.options('tiny')['options']
    with pytest.raises(ValueError,match='already'):core.add_bluetooth(**args,confirm=True)


def test_register_keeps_other_printer_profile(home,monkeypatch):
    monkeypatch.setattr(core.shutil,'which',lambda _: '/test/gatttool')
    core.update_profile('rongta',{'label':'Little Printer','kind':'escpos','width':192,'columns':48,'image_mode':'column24','max_receipt_bytes':4096})
    before=core.profiles()['rongta'].copy()
    core.add_bluetooth('tiny',PROFILE['address'],'hci1',confirm=True)
    assert core.profiles()['rongta']==before


@pytest.mark.parametrize('field,value',[('address','bad;rm'),('adapter','hci1;exit'),('width',576)])
def test_invalid_transport_settings(field,value):
    with pytest.raises(ValueError):mx.validate(dict(PROFILE,**{field:value}))


def test_raster_bit_order_padding_and_limits():
    image=Image.new('1',(384,2),1);image.putpixel((0,0),0);image.putpixel((7,1),0)
    payload,rows=mx.encode(image)
    assert rows==18 and payload[0]==1 and payload[48]==128
    assert payload[96:]==bytes(16*48)
    with pytest.raises(ValueError):mx.encode(Image.new('1',(384,512),1))
    assert mx.command(0xa9,bytes([56,0,48,0])).hex().startswith('2221a900040038003000')


def test_text_image_bounds_and_visible_ink():
    image=mx.text_image('Tiny Printer\nA short note')
    payload,rows=mx.encode(image)
    assert any(payload) and rows<mx.MAX_ROWS
    with pytest.raises(ValueError):mx.text_image('line\n'*100)
    with pytest.raises(ValueError):mx.text_image('escape\x1b')


def test_shared_spool_review_send_once_and_receipt(home,monkeypatch):
    monkeypatch.setattr(core,'require_queue',lambda _: 'tiny')
    monkeypatch.setattr(core,'profiles',lambda:{'tiny':PROFILE})
    send=Mock(return_value={'transport':'mxw01-ble','note':'Transmitted; verify physical output'})
    monkeypatch.setattr(mx,'transmit',send)
    spool=core.Spool();plan=spool.prepare('tiny',b'Hello Tiny','note.txt','receipt-text')
    assert plan['state']=='prepared' and plan['max_paper_mm']==64 and not send.called
    assert spool.send(plan['id'])['state']=='prepared' and not send.called
    result=spool.send(plan['id'],True)
    assert result['state']=='queued' and result['receipt']['transport']=='mxw01-ble'
    spool.send(plan['id'],True);assert send.call_count==1
    assert not core.run.called
    assert 'queued' in core.jobs('tiny')['jobs']
    with pytest.raises(ValueError):spool.prepare('tiny',b'note','n.txt','receipt-text',{'copies':2})
    with pytest.raises(ValueError):spool.prepare('tiny',b'%PDF-1','x.pdf','document')


def test_partial_bluetooth_send_never_retried(home,monkeypatch):
    monkeypatch.setattr(core,'require_queue',lambda _: 'tiny');monkeypatch.setattr(core,'profiles',lambda:{'tiny':PROFILE})
    send=Mock(side_effect=RuntimeError('lost link'));monkeypatch.setattr(mx,'transmit',send)
    spool=core.Spool();p=spool.prepare('tiny',b'note','n.txt','receipt-text')
    assert spool.send(p['id'],True)['state']=='uncertain'
    spool.send(p['id'],True);assert send.call_count==1


@pytest.mark.parametrize('mtu',[23,128])
def test_transport_negotiates_before_data_and_preserves_every_byte(home,monkeypatch,mtu):
    log=home/'writes.jsonl';tool=home/'gatttool'
    tool.write_text('#!/usr/bin/env python3\n'+f'''import sys,json
print('[LE]>',flush=True)
for line in sys.stdin:
 line=line.strip()
 if line=='connect':print('Connection successful',flush=True)
 elif line=='mtu 128':print('MTU was exchanged successfully: {mtu}',flush=True)
 elif line=='characteristics':
  for handle,uuid in [('0x000a','ae01'),('0x000f','ae03'),('0x0044','ae3c')]:print('char value handle = '+handle+', uuid = 0000'+uuid+'-0000-1000-8000-00805f9b34fb',flush=True)
 elif line.startswith('char-write-cmd'):
  with open({str(log)!r},'a') as out:out.write(json.dumps(line.split())+'\\n')
 elif line=='exit':break
''');tool.chmod(0o755)
    monkeypatch.setattr(mx.shutil,'which',lambda _:str(tool));monkeypatch.setattr(mx,'WRITE_DELAY',.001)
    payload=bytes(range(48))*20
    if mtu==23:
        with pytest.raises(RuntimeError,match='too small'):mx.transmit(PROFILE,payload)
        assert not log.exists()
    else:
        receipt=mx.transmit(PROFILE,payload);assert receipt['mtu']==128
        lines=[json.loads(s) for s in log.read_text().splitlines()]
        assert bytes.fromhex(''.join(s[2] for s in lines if s[1]=='0x000f'))==payload
        assert all(len(bytes.fromhex(s[2]))<=mtu-3 for s in lines)
        assert len([s for s in lines if s[1]=='0x000a'])==3
