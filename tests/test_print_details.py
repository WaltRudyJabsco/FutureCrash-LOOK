import json
import re
import pytest
import print_details as details
import print_destinations as physical
import print_core
from notebook_markdown import cell_width

UUID='e3248000-80ce-11db-8000-d80f9909e292'
UUID2='cfe92100-67c4-11d4-a45f-dccd2fc9fd8b'


def test_linux_implicit_route_uses_only_unique_observed_service_uuid():
    observed=[{'uri':'dnssd://Brother%20MFC-9130CW._ipp._tcp.local/?uuid='+UUID,'uuid':UUID,'label':'Brother MFC-9130CW'}]
    result=physical.device('implicitclass://Brother_MFC_9130CW/',observed)
    assert result['keys']==['uuid:'+UUID] and result['source']=='unique-discovered-service'
    # An arbitrary queue with a model-looking name is not evidence.
    assert not physical.device('file:///dev/null',observed)['keys']
    assert not physical.device('implicitclass://Office_Cluster/',observed)['keys']
    observed.append(dict(observed[0],uuid=UUID2))
    assert not physical.device('implicitclass://Brother_MFC_9130CW/',observed)['keys']


def test_minimal_linux_discovery_falls_back_to_observed_lpinfo_uuid(monkeypatch):
    monkeypatch.setattr(print_core,'_DEVICE_CACHE',(0,[]))
    monkeypatch.setattr(print_core.shutil,'which',lambda command:None)
    monkeypatch.setattr(print_core,'run',lambda args:'network dnssd://Brother%20MFC-9130CW._ipp._tcp.local/?uuid='+UUID)
    rows=print_core.discovered_devices()
    assert rows[0]['uuid']==UUID and rows[0]['label']=='Brother MFC-9130CW'


def test_linux_and_macos_routes_consolidate_without_name_guessing():
    observed=[{'uri':'ipp://printer.local/ipp/print','uuid':UUID,'label':'Brother MFC-9130CW'}]
    rows=[{'name':'Brother_MFC_9130CW','node':'linux','device':physical.device('implicitclass://Brother_MFC_9130CW/',observed)},
          {'name':'Brother_MFC_9130CW','node':'mac','device':physical.device('dnssd://Brother%20MFC-9130CW._ipp._tcp.local/?uuid='+UUID,observed)}]
    assert len(physical.consolidate(rows))==1


OPTIONS='PageSize/Media Size: A4 *Letter Legal\nsides/Two-sided printing: *one-sided two-sided-long-edge two-sided-short-edge\nInk/Ink & color: *Color Grayscale'


def test_options_parse_defaults_and_keep_keywords():
    rows=details.option_rows(OPTIONS)
    assert rows[0]=={'key':'PageSize','label':'Media Size','default':'Letter','choices':['A4','Letter','Legal']}
    assert rows[1]['default']=='one-sided'


@pytest.mark.parametrize('width',[24,40,80,120])
def test_aligned_details_wrap_without_losing_choices_or_using_json(width):
    lines=details.render('options',{'queue':'epson','node':'owner','options':OPTIONS},width)
    assert all(sum(cell_width(c) for c in line)<=width for line in lines)
    output='\n'.join(lines)
    assert 'Media Size' in output and 'Letter' in output and 'Available:' in output
    assert '{' not in output and '*Letter' not in output


def test_detail_inks_separate_labels_values_and_choices():
    colors={'WHITE':'\033[97m'}
    output='\n'.join(details.render('options',{'options':OPTIONS},80,colors))
    assert '\033[38;2;95;175;255mMedia Size' in output
    assert '\033[97mLetter' in output
    assert '\033[38;2;160;160;160m  Available:' in output


def test_jobs_and_routes_are_labeled_not_json():
    jobs=details.render('jobs',{'routes':[{'node':'tower','queue':'receipt','jobs':'receipt-12 me 1024 Mon 02 Nov 2026'}]},80)
    assert 'Job' in '\n'.join(jobs) and 'receipt-12' in '\n'.join(jobs) and '{' not in '\n'.join(jobs)
    routes=details.render('routes',{'routes':[{'node':'tower','name':'receipt','status':'idle','profile':{'kind':'escpos'}}]},80)
    assert 'Computer' in '\n'.join(routes) and 'escpos' in '\n'.join(routes)
