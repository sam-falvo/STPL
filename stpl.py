#!/usr/bin/env python
#
# To see recognizer state changes:
# 	python stpl.py | grep "^\["
# To see just the compiled assembly listing:
# 	python stpl.py | grep -v "^\["
# To see both interleaved:
# 	python stpl.py


src = """
declare by80;
declare ctr;
declare x,y;
declare screenbase;
declare w,h;

delay:	let ctr = ctr+65535;
	return if ctr=0;
	goto delay;

home:	let x=0; let y=0; return;

clrx:	goto clrxx if (x-w)&32768; return;
clrxx:	let !(screenbase+(by80!(y+y))+x) = 32;
	let x=x+1; goto clrx;
clry:	goto clryy if (y-h)&32768; return;
clryy:	call clrx; let x=0; let y=y+1; goto clry;
clr:	call home; call clry; return;
"""

# Token Kinds
K_SPACE = 0
K_WORD = 1
K_CHAR = 2
K_NUMBER = 3
K_KEYWORD = 4
K_EXPR = 5
K_IDLIST = 6

symbol = ''
kind = K_SPACE

keywords = [
	'let', 'goto', 'if', 'return', 'declare', 'call'
]

procs = []

nextlabel = 0
def alloclabel():
	global nextlabel
	l = nextlabel
	nextlabel = nextlabel+1
	return l

class RecognizerStack(object):
	def __init__(self):
		self.s = []
		self.t = []
		self.nextlinelabel = None
		self.context = None

	def snarf(self, starting, length):
		if len(self.s) - length <= 0:
			self.s = []
			self.t = []
		else:
			org = len(self.s)+starting
			del self.s[org:org+length]
			del self.t[org:org+length]

	def reducestep(self):
		print self.s, self.t

		# let word =
		if (len(self.s) > 2) and (self.t[-3] == K_KEYWORD) and (self.s[-3] == 'let') and (self.t[-2] == K_WORD) and (self.t[-1] == K_CHAR) and (self.s[-1] == '='):
			self.context = None

		# let word = expr ;
		if (len(self.s) > 4) and (self.t[-5] == K_KEYWORD) and (self.s[-5] == 'let') and (self.t[-4] == K_WORD) and (self.t[-3] == K_CHAR) and (self.s[-3] == '=') and (self.t[-2] == K_EXPR) and (self.t[-1] == K_CHAR) and (self.s[-1] == ';'):
			print "  lit " + self.s[-4]
			print "  swm"
			self.snarf(-5, 5)
			return True

		# let ! -- change context back, so that we can properly evaluate the target lvalue.
		if (len(self.s) > 1) and (self.t[-2] == K_KEYWORD) and (self.s[-2] == 'let') and (self.t[-1] == K_CHAR) and (self.s[-1] == '!'):
			self.context = None
			return False

		# let ! expr = expr ;
		if (len(self.s) > 5) and (self.t[-6] == K_KEYWORD) and (self.s[-6] == 'let') and (self.t[-5] == K_CHAR) and (self.s[-5] == '!') and (self.t[-4] == K_EXPR) and (self.t[-3] == K_CHAR) and (self.s[-3] == '=') and (self.t[-2] == K_EXPR) and (self.t[-1] == K_CHAR) and (self.s[-1] == ';'):
			print "  swap"
			print "  swm"
			self.snarf(-6, 6)
			return True

		# !! expr op expr
		if (len(self.s) > 3) and ((self.t[-4] != K_CHAR) or (self.s[-4] != '!')) and (self.t[-3] == K_EXPR) and (self.t[-2] == K_CHAR) and (self.t[-1] == K_EXPR):
			if self.s[-2] == '+':
				print "  add"
				self.snarf(-3, 2)
			elif self.s[-2] == '&':
				print "  and"
				self.snarf(-3, 2)
			elif self.s[-2] == '~':
				print "  cpl"
				self.snarf(-3, 2)
			elif self.s[-2] == '^':
				print "  xor"
				self.snarf(-3, 2)
			elif self.s[-2] == '!':
				print "  add"
				print "  fwm"
				self.snarf(-3, 2)
			elif self.s[-2] == "-":
				print "  neg"
				self.snarf(-3, 2)
			elif self.s[-2] == '=':
				print "  xor"
				l1 = alloclabel()
				l2 = alloclabel()
				print "  zgo L%d" % l1
				print "  lit 0"
				print "  go  L%d\n  go" % l2
				print "L%d:" % l1
				print "  lit $FFFF"
				print "L%d:" % l2
				self.snarf(-3, 2)
			elif self.s[-2] == '#':
				print "  xor"
				l1 = alloclabel()
				l2 = alloclabel()
				print "  zgo L%d" % l1
				print "  lit $FFFF"
				print "  go  L%d\n  go" % l2
				print "L%d:" % l1
				print "  lit 0"
				print "L%d:" % l2
				self.snarf(-3, 2)
			else:
				print "SYNTAX ERROR: unsupported operator?"

		# ( expr )
		if (len(self.s) > 2) and (self.t[-3] == K_CHAR) and (self.s[-3] == '(') and (self.t[-2] == K_EXPR) and (self.t[-1] == K_CHAR) and (self.s[-1] == ')'):
			self.snarf(-3, 1)
			self.snarf(-1, 1)
			return True

		# (!expr && !let) ! expr
		if (len(self.s) > 2) and (self.t[-3] != K_EXPR) and ((self.t[-3] != K_KEYWORD) or (self.s[-3] != 'let')) and (self.t[-2] == K_CHAR) and (self.s[-2] == '!') and (self.t[-1] == K_EXPR):
			print "  fwm"
			self.snarf(-2, 1)
			return True

		# number
		elif (len(self.s) >= 1) and (self.t[-1] == K_NUMBER):
			print "  lit " + self.s[-1]
			self.t[-1] = K_EXPR
			return True

		# !let/\!declare word
		elif (len(self.s) > 1) and (self.context == None) and ((self.t[-2] != K_KEYWORD) or (self.t[-2] == K_KEYWORD and self.s[-2] not in ['let', 'declare'])) and (self.t[-1] == K_WORD):
			print "  lit "+self.s[-1]
			print "  fwm"
			self.t[-1] = K_EXPR
			return True

		# sub word
		elif (len(self.s) > 1) and (self.t[-2] == K_WORD) and (self.t[-1] == K_CHAR) and (self.s[-1] == ':'):
			l = alloclabel()
			print "L%d:" % l
			procs.append((self.s[-2], l))
			self.snarf(-2,2)
			return True

		# goto expr ;
		elif (len(self.s) > 2) and (self.t[-3] == K_KEYWORD) and (self.s[-3] == 'goto') and (self.t[-2] == K_EXPR) and (self.t[-1] == K_CHAR) and (self.s[-1] == ';'):
			print "  go"
			self.snarf(-3, 3)
			return True

		# ... if expr ;
		elif (len(self.s) > 2) and (self.t[-3] == K_KEYWORD) and (self.s[-3] == 'if') and (self.t[-2] == K_EXPR) and (self.t[-1] == K_CHAR) and (self.s[-1] == ';'):
			l1 = alloclabel()
			print "  lit L%d\n  zgo" % l1
			self.nextlinelabel = l1
			self.snarf(-3, 2)
			return True

		# return ;
		elif (len(self.s) > 1) and (self.t[-2] == K_KEYWORD) and (self.s[-2] == 'return') and (self.t[-1] == K_CHAR) and (self.s[-1] == ';'):
			print "  rfs"
			self.snarf(-2, 2)
			return True

		# delcare idlist , word
		elif (len(self.s) > 3) and (self.context == 'declare') and (self.t[-2] == K_CHAR) and (self.s[-2] == ',') and (self.t[-1] == K_WORD):
			self.vardecls.append(self.s[-1])
			self.snarf(-2,2)
			return True

		# declare word (declare context)
		elif (len(self.s) >= 1) and (self.context == 'declare') and (self.t[-1] == K_WORD):
			self.vardecls = [self.s[-1]]
			self.t[-1] = K_IDLIST
			return True

		# declare idlist ;
		elif (len(self.s) > 2) and (self.t[-3] == K_KEYWORD) and (self.s[-3] == 'declare') and (self.t[-2] == K_IDLIST) and (self.t[-1] == K_CHAR) and (self.s[-1] == ';'):
			self.snarf(-3, 3)
			for v in self.vardecls:
				print "%s:  dcw 0" % v
			self.context = None
			return True

		# declare context
		elif (len(self.s) > 0) and (self.t[-1] == K_KEYWORD) and (self.s[-1] == 'declare') and (self.context == None):
			self.context = 'declare'

		# let context
		elif (len(self.s) > 0) and (self.t[-1] == K_KEYWORD) and (self.s[-1] == 'let') and (self.context == None):
			self.context = 'let'

		# call expr ;
		elif (len(self.s) > 2) and (self.t[-3] == K_KEYWORD) and (self.s[-3] == 'call') and (self.t[-2] == K_EXPR) and (self.t[-1] == K_CHAR) and (self.s[-1] == ';'):
			print "  call"
			self.snarf(-3, 3)
			return True

		return False

	def reduce(self):
		reduced = True
		while reduced:
			reduced = self.reducestep()
		if self.nextlinelabel:
			print "L%d: " % self.nextlinelabel
			self.nextlinelabel = None

	def push(self, s, t):
		self.s.append(s)
		self.t.append(t)
		self.reduce()

recog = RecognizerStack()

def checkkw():
	global symbol
	global kind
	if symbol in keywords:
		kind = K_KEYWORD

def sym():
	global symbol, kind
	checkkw()
	recog.push(symbol, kind)

def isstartofword(c):
	return (97 <= ord(c) < 97+26) or (65 <= ord(c) < 65+26) or (c == '_')

def isdigit(c):
	return 48 <= ord(c) < 58

def iswordchar(c):
	return isstartofword(c) or isdigit(c)

def isspace(c):
	return ord(c) < 33

def sym0():
	if kind:
		sym()

def chr(c):
	global symbol
	global kind
	if (kind != K_WORD) and isstartofword(c):
		sym0()
		kind = K_WORD
		symbol = c
	elif (kind == K_WORD) and iswordchar(c):
		symbol = symbol + c
	elif (kind != K_NUMBER) and isdigit(c):
		sym0()
		kind = K_NUMBER
		symbol = c
	elif (kind == K_NUMBER) and isdigit(c):
		symbol = symbol + c
	elif (kind != K_SPACE) and isspace(c):
		sym0()
		kind = K_SPACE
		symbol = ''
	elif (kind == K_SPACE) and isspace(c):
		pass # we ignore spaces.
	else:
		sym0()
		kind = K_CHAR
		symbol = c

def dumpprocvars():
	for pv in procs:
		print "%s: dcw L%d" % (pv[0], pv[1])

def main():
	global symbol
	symbol = ""
	for ch in src:
		chr(ch)
	dumpprocvars()

if __name__=='__main__':
	main()

