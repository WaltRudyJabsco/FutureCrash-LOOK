import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('memory_store_test', ROOT/'core'/'memory_store.py')
mem=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(mem)


class FabricMemoryTests(unittest.TestCase):
    def test_scopes_and_relevance(self):
        with tempfile.TemporaryDirectory() as td:
            store=mem.FabricMemory(Path(td)/'memory.json')
            store.add('shared','The Fabric has three trusted compute nodes.',80,source_node='a')
            store.add('persona:oracle','Prefer compact dry answers in Future Crash.',70,source_node='a')
            store.add('persona:pirate','Use restrained nautical phrasing.',70,source_node='a')
            rows=store.relevant(persona='oracle',query='Future Crash Fabric',limit=8,include_local=False)
            texts=' '.join(x['text'] for x in rows)
            self.assertIn('three trusted compute nodes',texts)
            self.assertIn('compact dry answers',texts)
            self.assertNotIn('nautical',texts)

    def test_merge_never_imports_remote_node_scope(self):
        with tempfile.TemporaryDirectory() as td:
            store=mem.FabricMemory(Path(td)/'memory.json')
            result=store.merge([
                {'scope':'shared','text':'shared fact','importance':60,'updated_at':10,'created_at':10,'source_node':'peer'},
                {'scope':'node:other','text':'private node fact','importance':60,'updated_at':10,'created_at':10,'source_node':'peer'},
            ])
            self.assertEqual(result['count'],1)
            items=store.public(include_local=True)['items']
            self.assertEqual(items[0]['scope'],'shared')

    def test_duplicate_add_is_stable(self):
        with tempfile.TemporaryDirectory() as td:
            store=mem.FabricMemory(Path(td)/'memory.json')
            a=store.add('shared','Same fact',40,source_node='a')
            b=store.add('shared','Same fact',80,source_node='b')
            self.assertEqual(a['id'],b['id'])
            self.assertEqual(len(store.public()['items']),1)
            self.assertEqual(store.public()['items'][0]['importance'],80)

if __name__=='__main__': unittest.main()
