from pathlib import Path
import ast, json, importlib.util, unittest, asyncio, sys, types
root=Path(__file__).resolve().parents[1] / 'custom_components/enable_banking'
for path in root.glob('*.py'): ast.parse(path.read_text(),filename=str(path))
for path in root.rglob('*.json'): json.loads(path.read_text())
def load(name):
    spec=importlib.util.spec_from_file_location(name,root/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
counting=load('counting')
from datetime import date
start,end=date(2026,11,1),date(2026,11,30)
def row(text,**kw):
    return dict(status='BOOK',credit_debit_indicator='DBIT',booking_date='2026-11-02',remittance_information=[text],**kw)
class CountingTests(unittest.TestCase):
    def test_card(self): self.assertEqual(counting.classify(row('Płatność kartą')), 'card')
    def test_blik(self): self.assertEqual(counting.classify(row('Płatność BLIK')), 'blik')
    def test_phone(self): self.assertEqual(counting.classify(row('Przelew na telefon BLIK')), 'excluded')
    def test_cash(self): self.assertEqual(counting.classify(row('Wypłata BLIK bankomat')), 'excluded')
    def test_unknown(self): self.assertEqual(counting.classify(row('BLIK')), 'unknown')
    def test_fee(self): self.assertEqual(counting.classify(row('Opłata za kartę')), 'excluded')
    def test_refund(self): self.assertEqual(counting.classify(row('Zwrot płatności kartą')), 'excluded')
    def test_duplicates(self):
        a=row('Płatność kartą',transaction_id='1'); b=row('Płatność kartą',transaction_id='2')
        self.assertEqual(counting.count([a,a,b],start,end)['card'],2)
    def test_identical_without_id_preserved(self):
        a=row('Płatność kartą');self.assertEqual(counting.count([a,a],start,end)['card'],2)
    def test_status_and_dates(self):
        rows=[]
        for field,value in [('booking_date','2026-10-31'),('credit_debit_indicator','CRDT'),('status','PDNG')]:
            a=row('Płatność kartą');a[field]=value;rows.append(a)
        self.assertEqual(counting.count(rows,start,end)['total'],0)
    def test_total(self):
        result=counting.count([row('Płatność kartą'),row('Płatność BLIK'),row('nieznane')],start,end)
        self.assertEqual((result['total'],result['unknown']),(2,1))
    def test_bad_date(self):
        a=row('Płatność kartą');a['booking_date']='bad'
        with self.assertRaises(ValueError): counting.count([a],start,end)
# The environment has no HA or PyJWT. Stub only JWT import for isolated pagination tests.
sys.modules.setdefault('jwt',types.ModuleType('jwt'))
api=load('api')
class PaginationTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_pages(self):
        client=api.Client(None,None,'','');calls=[]
        async def request(*args,**kw):
            calls.append(dict(kw['params']))
            return {'transactions':[1],'continuation_key':'next'} if len(calls)==1 else {'transactions':[2]}
        client.request=request
        self.assertEqual(await client.transactions('x','2026-11-01','2026-11-02'),[1,2])
        self.assertEqual(calls[1]['continuation_key'],'next')
    async def test_cycle_fails(self):
        client=api.Client(None,None,'','')
        async def request(*args,**kw): return {'transactions':[], 'continuation_key':'same'}
        client.request=request
        with self.assertRaises(ValueError): await client.transactions('x','','')
    async def test_partial_failure_not_returned(self):
        client=api.Client(None,None,'','');calls=[]
        async def request(*args,**kw):
            if calls: raise api.ApiError(429)
            calls.append(1);return {'transactions':[1],'continuation_key':'next'}
        client.request=request
        with self.assertRaises(api.ApiError): await client.transactions('x','','')
if __name__ == "__main__":
    unittest.main()
