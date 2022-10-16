
import re
import sys
import json

'''
Remove endpoint complexity from client-side javascript, leaving everything to
python decorators in the server source.

Now that I think about it, "parity" has nothing to do with pairs.
'''

# Every ParityObject class needs to provide a javascript class string.

# All relevant ParityObject class strings are gathered and provided at one time.

# Query url and POST body are passed to a ParityObject handler, which does
# parity logic and returns the outcome if the input is valid parity parameters,
# but does nothing if it is not.

# Authentication functions for storing multi-page session tokens locally should
# also be provided by the collective ParityObject javascript source.

# Helper funcs.

def clone(a):
	return json.loads(json.dumps(a))

# Helper classes.

class _listdict(dict):
	def add(self,k,v):
		if not k in self:
			self[k] = []
		self[k].append(v)
	def iter(self):
		for k,v in self.iteritems():
			for a in v:
				yield (k,a)

_jsclasses = {}
_jsclasstags = _listdict()

# Decorators.

def jsfunc(f):
	'''Decorator to provide filter for methods meant to have a js-equivalent.'''
	setattr(f,'jsfunc',True)
	setattr(f,'args',[])
	return f
def __args(*args):
	'''Decorator to map arguments in list to {key:val} pairs'''
	def decor(f):
		setattr(f,'jsfunc',True)
		setattr(f,'args',list(args))
		return f
	return decor
setattr(jsfunc,'args',__args)

def jsclass(*tags,extending=None):
	'''Decorator incorporating class into jsclass table, along with jsfuncs.'''
	extending = extending if extending else []
	tags = tags if len(tags) > 0 else ['default']
	def decor(cls):
		# Set up the class table object.	
		t = {
			'name':cls.__name__,
			'class':cls,
			'funcs':{k:list(f.args) \
				for k,f in cls.__dict__.items() if hasattr(f,'jsfunc')}
		}
		_jsclasses[cls.__name__] = t
		for s in extending:
			# Sometimes classes are extended client-side.  This is needed for those
			# new class names that the server otherwise wouldn't know about.
			_jsclasses[s] = t
		for tag in tags:
			# Add object to managing class table.
			_jsclasstags.add(tag,t)
		return cls
	return decor

# Class string translation.

def _jsstr(a,extends=None):
	extends = extends if extends else 'ParityObject'
	fs_pre = """\
class %s extends %s {\
""" % (a['name'],extends)
	fs = """\
	async %s(...r) {
		let x = null
		if (%s) {
			let a = {}
			let t = %s
			for (let i=0; i < r.length; ++i)
				a[t[i]] = r[i]
			x = await this.sendMethodRequest("%s",a)
		}
		else
			x = await this.sendMethodRequest("%s",r[0])
		/*
		if (!x.status)
			throw new StatusError('no x.status in result!\\n'+JSON.stringify(x))
		if (/error/.test(x.status))
			throw new StatusError('x.status contains an error!\\n'+JSON.stringify(x))
		//*/
		return x
	}\
"""
	fs_post = """\
}\
"""
	sr = [fs_pre]
	for f,args in a['funcs'].items():
		sr.append(fs % (
			f,
			'true' if len(args) else 'false',
			json.dumps(args),
			f,
			f))
	sr.append(fs_post)
	return '\n\n'.join(sr)

def _jsstr_tags(*tags,extends=None):
	print(_jsclasstags,file=sys.stderr)
	t = {}
	for tag in tags:
		for c in _jsclasstags[tag]:
			k = c['name']
			if not k in t:
				t[k] = c
	r = list(map(lambda a:_jsstr(a,extends=extends),t.values()))
	return '\n\n'.join(r)

def compile_classes(*tags,rootclass='ParityObject',endpoint=None):
	top = """\

class StatusError extends Error {}

class %s {
	constructor() {
		this.parityId = null
		this.paired = false
	}
	getId() {
		return this.parityId
	}
	endpoint() {
		%s
	}
	authenticate() {
		return null
	}
	async pair(param) {
		param = typeof param === 'undefined' ? null : param
		if (this.parityId !== null)
			throw new Exception('Attempting to re-pair a parity object.')
		let a = await this.sendRequest({
			method:'#pair',
			auth:this.authenticate(),
			class:this.constructor.name,
			param:param
		})
		if (a) {
			if (typeof a.id !== 'undefined') {
				this.parityId = a.id
				this.paired = true
			}
		}
		return this
	}
	async sendRequest(a) {
		let x = await fetch(this.endpoint(), {
			method:'POST',
			headers:{'Content-Type':'application/json'},
			body:JSON.stringify(a)
		})
		return x.json()
	}
	async sendMethodRequest(method,a) {
		let b = Object.assign(Object.assign({},a),{
			parityid:this.getId(),
			method:method,
			auth:this.authenticate(),
		})
		return this.sendRequest(b)
	}
}""" % (
		rootclass,
		('return "%s"' % (endpoint,)) if endpoint else \
			"throw new Error('abstract method called')")
	middle = _jsstr_tags(*tags,extends=rootclass)
	return '\n\n'.join([top,middle])

# Class declarations.

class ParityObject:
	pass

_default_parity = ParityObject()

class ParityManager:
	# This needs to handle pointing jsfunc calls to their respective server-side
	# parity objects.
	def __init__(self):
		# Pairing between parity objects and their ids happens solely within the
		# parity object manager.  ParityObjects have no sense of personal id.  At
		# least not in context with which clients are pointing at them.
		self.pairs = {}
	
	def pair(self,ob):
		# Must return an object to return to the client, and a reference to the
		# actual server-side ParityObject.
		return ({
			id:1
		},_default_parity)
	
	def evaluate(self,ob):
		if re.search(r'^#',ob['method']):
			# We have a special case here...
			if ob['method'] == '#pair':
				res,pob = self.pair(ob)
				if not 'id' in res:
					print('no id in res',res,file=sys.stderr)
				elif not res['id'] in self.pairs:
					# UNCERTAIN: Still not sure what to do with this table.
					self.pairs[res['id']] = pob
				return res
			else:
				return {'result':'eternal-failure'}
		else:
			if 'parityid' in ob:
				print('parityid in ob',ob,self.pairs,file=sys.stderr)
				if not ob['parityid'] in self.pairs:
					return {'result':'quintessential-annihilation'}
				pob = self.pairs[ob['parityid']]
				t = _jsclasses[type(pob).__name__]
				m = ob['method']
				res = {'result':'penultimate-failure'}
				if m in t['funcs']:
					#res = getattr(pob,m)(pob,ob)
					res = getattr(pob,m)(ob)
				return res
			else:
				return {'result':'the-end-of-all-things'}


if __name__ == '__main__':
	
	@jsclass('wood','pood')
	class A (ParityObject):
		def __init__(self):
			pass
		def heyo(self):
			print('heyo')
		@jsfunc
		def mayo(self):
			print('mayo')
	
	a = A()
	#print(dir(a))
	#print(_jsclasses)
	#print(_jsclasstags)
	print(compile_classes(
		'wood',
		rootclass='WoodPair',
		endpoint='/parity/wood'))

