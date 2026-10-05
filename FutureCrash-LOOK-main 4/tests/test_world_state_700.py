import ast
import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'core'))
import world_state

LOOK=ROOT/'look'/'lk'

class FakeGoal:
    def public(self):
        return {
            'id':'goal_test','created':1.0,'request':'move the files','primary':'files',
            'families':['files'],'steps':[{'id':'step_1','status':'pending','actions':['files.move'],'depends_on':[]}]
        }

class WorldState700Tests(unittest.TestCase):
    def test_goal_and_receipt_survive_process_state(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'world.json'
            ws=world_state.WorldState(path)
            ws.begin_goal(FakeGoal())
            r=ws.record_receipt('move_path',True,'ok','MOVE OK: a -> b',args={'source':'a','destination':'b'},duration_ms=4)
            self.assertTrue(r['ok'])
            loaded=world_state.WorldState(path).load()
            self.assertEqual(loaded['active_goal_id'],'goal_test')
            self.assertEqual(loaded['receipts'][-1]['action'],'move_path')
            ws.close_goal('goal_test',satisfied=True,reason='receipt verified')
            self.assertEqual(world_state.WorldState(path).load()['goals'][-1]['status'],'done')

    def test_failure_is_typed_and_recallable(self):
        with tempfile.TemporaryDirectory() as td:
            ws=world_state.WorldState(Path(td)/'world.json')
            ws.begin_goal(FakeGoal())
            r=ws.record_receipt('run_command',False,'internal_error',"Tool internal error: NameError: name '_looks_like_shell_file_discovery' is not defined")
            self.assertEqual(r['failure_class'],'host_bug')
            self.assertEqual(ws.latest_failure()['id'],r['id'])
            self.assertIn('_looks_like_shell_file_discovery',ws.context())

    def test_consequential_actions_have_structural_preflight_policy(self):
        self.assertTrue(world_state.execution_policy('run_command')['preflight'])
        self.assertTrue(world_state.execution_policy('move_path')['verify'])
        self.assertEqual(world_state.execution_policy('read_file')['mode'],'normal')

    def test_shell_discovery_guard_exists_and_does_not_block_asciiquarium(self):
        tree=ast.parse(LOOK.read_text())
        wanted={'_looks_like_shell_file_discovery'}
        body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
        ns={'re':__import__('re'),'shlex':__import__('shlex'),'Path':Path}
        exec(compile(ast.Module(body=body,type_ignores=[]),str(LOOK),'exec'),ns)
        f=ns['_looks_like_shell_file_discovery']
        self.assertFalse(f('asciiquarium'))
        self.assertFalse(f('echo find me'))
        self.assertTrue(f('find . -name "*.txt"'))
        self.assertTrue(f('pwd && fd report'))



    def test_explicit_terminal_intent_gets_real_tty_path(self):
        text=LOOK.read_text()
        self.assertIn('"interactive":{"type":"boolean"',text)
        self.assertIn('if _lo_terminal_interactive_intent(prompt):',text)
        self.assertIn('interactive exit 130 · launched; terminal session interrupted by user',text)
        self.assertIn('stdin=subprocess.DEVNULL',text)  # captured path remains non-interactive

    def test_installer_ships_world_state_core(self):
        install=(ROOT/'install.sh').read_text()
        self.assertIn('core/world_state.py',install)
        self.assertIn('import conductor, fabric_client, memory_store, decision, cognition, world_state',install)

    def test_tool_error_recall_bypasses_model_reconstruction(self):
        text=LOOK.read_text()
        self.assertIn('if _lo_tool_error_query(prompt):',text)
        self.assertIn('_lo_latest_tool_error_answer()',text)
        self.assertIn('an earlier failure is evidence, never a veto on retry',world_state.WorldState.__dict__['context'].__doc__ or '' if False else Path(ROOT/'core'/'world_state.py').read_text())

if __name__=='__main__': unittest.main()
