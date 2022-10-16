
import sys

from ..parityobject import *

@jsclass('store')
class TableStore(ParityObject):
	
	def __init__(self,*obs):
		t = {}
		for a in obs:
			for k,v in a.items():
				t[k] = v
		self._table = t
	
	@jsfunc.args('key')
	def get(self,ob):
		print('get',ob,self._table,file=sys.stderr)
		try:
			return {
				'key':ob['key'],
				'value':self._table[ob['key']],
				'status':'success'
			}
		except KeyError:
			return {'status':'keyerror'}
		except Exception:
			return {'status':'exception'}
	
	@jsfunc.args('key','value')
	def set(self,ob):
		try:
			k = ob['key']
			val = ob['value']
			old = self._table[k] if k in self._table else '[:unassigned:]'
			self._table[k] = val
			return {
				'key':k,
				'value':val,
				'oldvalue':old,
				'status':'success'}
		except Exception:
			return {'status':'error'}
	
	@jsfunc.args('key')
	def rem(self,ob):
		try:
			k = ob['key']
			old = self._table[k] if k in self._table else '[:unassigned:]'
			del self._table[k]
			return {
				'key':k,
				'oldvalue':old,
				'status':'success'}
		except Exception:
			return {'status':'error'}
	
	@jsfunc
	def table(self,ob):
		try:
			return {
				'value':json.loads(json.dumps(self._table)),
				'status':'success'}
		except Exception:
			return {'status':'error'}

@jsclass('store')
class ListStore(TableStore):
	
	def __init__(self,*obs):
		def iterate(r):
			return r.values() if r is dict else r
		t = {}
		x = 0
		for a in obs:
			for v in iterate(a):
				t[x] = v
				x += 1
		super().__init__(t)
	
	def _kr(self):
		return sorted(self._table.keys())
	
	@jsfunc.args('key')
	def get(self,ob):
		return super().get(ob)
	
	@jsfunc.args('key','value')
	def set(self,ob):
		return super().set(ob)
	
	@jsfunc.args('key')
	def rem(self,ob):
		return super().rem(ob)

	@jsfunc.args('value')
	def push(self,ob):
		k = self._kr()[-1]+1
		a = dict(ob.items())
		a['key'] = k
		return super().set(a)
	
	@jsfunc
	def pop(self,ob):
		a = self.top(ob)
		del self._table[a['key']]
		return a
	
	@jsfunc
	def top(self,ob):
		k = self._kr()[-1]
		val = self._table[k]
		return {
			'key':k,
			'value':val,
			'status':'success'}
	
	@jsfunc
	def list(self,ob):
		return {
			'value':[self._table[k] for k in self._kr()],
			'status':'success'}
	
	@jsfunc
	def size(self,ob):
		val = len(self._table)
		return {
			'value':val,
			'status':'success'}

class TableManager(ParityManager):
	
	def __init__(self,table_table):
		super().__init__()
		self.table = {}
		x = 0
		for k,v in table_table.items():
			self.table[k] = (x,v)
			x += 1
	
	def pair(self,ob):
		k = ob['param']['key']
		id,pob = self.table[k]
		print(self.pairs,file=sys.stderr)
		return ({'id':id},pob)

