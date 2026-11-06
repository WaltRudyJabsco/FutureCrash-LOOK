import io,json
from unittest.mock import Mock
import pytest
from PIL import Image
import print_design as designs
import printing
from core import cognition
from test_media_request_regressions import lk

def artwork(size=(800,500)):
    out=io.BytesIO();Image.new('RGB',size,'gray').save(out,format='PNG')
    return out.getvalue(),{'id':'aic-1','title':'Test Landscape','artist':'A Painter','date':'1900','museum':'Test Museum'}

def test_lettering_fonts_and_no_shell():
    for font in designs.FONTS:
        result=designs.banner('HAPPY DAY',font)
        assert '\n' in result and len(result)>9
    for text,font in [('x','../../font'),('\x1b[31mx','small'),('x'*121,'small')]:
        with pytest.raises(ValueError):designs.banner(text,font)

@pytest.mark.parametrize('size,rotation',[((800,500),90),((500,800),0)])
def test_fortune_compact_upright_text_lucky_numbers_and_art(size,rotation):
    payload,detail=designs.render('A small kindness will find its way back to you.',kind='fortune',artwork=artwork(size))
    image=Image.open(io.BytesIO(payload))
    assert image.width==384 and image.height<2438
    assert 1<=len(detail['lines'])<=3
    assert len(set(detail['lucky_numbers']))==6 and all(1<=n<=49 for n in detail['lucky_numbers'])
    assert detail['artwork_rotation']==rotation and detail['artwork']['artist']=='A Painter'
    with pytest.raises(ValueError):designs.render('A'*140,kind='fortune')

def test_banner_uses_full_width_along_roll():
    payload,detail=designs.render('HAPPY BIRTHDAY',font_name='small')
    image=Image.open(io.BytesIO(payload))
    assert image.width==384 and image.height>image.width
    assert detail['kind']=='banner' and 'ascii_preview' in detail


def test_assistant_registry_profiles_and_routing(lk,monkeypatch):
    monkeypatch.setattr(lk,'_cognition_module',lambda:cognition)
    assert 'banner_render' in {t['function']['name'] for t in lk._lo_tools('conservative')}
    assert 'print_design' not in {t['function']['name'] for t in lk._lo_tools('conservative')}
    assert 'print_design' in {t['function']['name'] for t in lk._lo_tools('workspace')}
    assert cognition.analyze('print fortune cookie',use_openjev=False).primary=='printing'

@pytest.mark.parametrize('prompt',['How do I print a fortune on Tiny Printer?','Do not print a fortune on Tiny Printer','Preview a fortune on Tiny Printer','Print a fortune'])
def test_design_cannot_send_without_named_explicit_request(prompt,tmp_path,monkeypatch):
    render=Mock();monkeypatch.setattr(printing,'design',render)
    with pytest.raises(ValueError):printing.run_tool('print_design',{'kind':'fortune','text':'Kindness travels.','queue':'Tiny Printer','send':True},tmp_path,prompt,{})
    render.assert_not_called()

def test_explicit_fortune_single_attempt_and_preview(tmp_path,monkeypatch):
    plan={'id':'a'*32,'node':'owner','destination':'Tiny Printer','design':{'kind':'fortune'}}
    monkeypatch.setattr(printing,'design',Mock(return_value=plan));send=Mock(return_value={'state':'queued'});monkeypatch.setattr(printing,'request',send)
    args={'kind':'fortune','text':'Kindness travels.','queue':'Tiny Printer'}
    printing.run_tool('print_design',args,tmp_path,'Preview a fortune',{});send.assert_not_called()
    turn={};printing.run_tool('print_design',dict(args,send=True),tmp_path,'Print a fortune on Tiny Printer',turn)
    with pytest.raises(ValueError):printing.run_tool('print_design',dict(args,send=True),tmp_path,'Print a fortune on Tiny Printer',turn)
    assert send.call_count==1

def test_design_prepares_real_render_with_pinned_route(monkeypatch):
    monkeypatch.setattr(designs,'museum_artwork',artwork)
    monkeypatch.setattr(printing,'destinations',lambda:{'local_node':'desk','printers':[{'id':'p','label':'Tiny Printer','routes':[{'name':'tiny','node':'owner','status':'idle','profile':{'kind':'escpos','width':384}}]}]})
    request=Mock(return_value={'id':'a'*32,'node':'owner'});monkeypatch.setattr(printing,'_request',request)
    result=printing.design('Kindness travels.',kind='fortune',queue='Tiny Printer')
    assert result['design']['artwork']['id']=='aic-1'
    assert request.call_args.args==('prepare','owner')
    assert request.call_args.kwargs['kind']=='receipt-image'


def test_interactive_banner_picker_preserves_text_and_confirms_once(monkeypatch):
    from unittest.mock import Mock
    import printing, print_desk, look_renderer
    for stream in (printing.sys.stdin,printing.sys.stdout):
        monkeypatch.setattr(stream,'isatty',lambda:True)
    answers=iter([('p',False),('yes',False)])
    monkeypatch.setattr(look_renderer,'prompt_line',lambda prompt:next(answers))
    monkeypatch.setattr(print_desk,'pick',lambda ui,prefer_receipt:{'id':'tiny'})
    plan=Mock(return_value={'id':'abc','node':'owner','destination':'Tiny Printer','design':{'kind':'banner'}})
    monkeypatch.setattr(printing,'design',plan)
    send=Mock(return_value={'state':'queued','id':'abc'})
    monkeypatch.setattr(printing,'request',send)
    assert printing.main(['banner','hello','--font','small'])==0
    plan.assert_called_once_with('hello',kind='banner',font='small',queue='tiny',paper_limit_mm=304.8)
    send.assert_called_once_with('send','owner',ident='abc',confirm=True)
