set shortmess+=W
vmap <silent> <F5> :call Py3c()<CR>

python3 << EOF
_g_round = 0
_g_routs = []
def _on_rout(_round, lineno, *out):
	# TODO: keep last N (5?) rounds
	if _round != _g_round:
		return
	_g_routs[lineno].process_outp(*out)


class LineOutput(object):
	def __init__(self, lineno, line):
		self.lineno = lineno
		self.line = line
		self.outp = []

	def process_outp(self, *v): 
		self.outp.append(v)

	def __repr__(self):
		return str(self)

	def __str__(self):
		rs = '{0:3}:'.format(self.lineno)
		if self.line.strip():
			rs += ' {}'.format(self.line)
		if self.outp:
			rs += '	{}'.format(self.outp)
		return rs


def _parse_expr(tokenizer):
	lineno, line = tokenizer.current()
	kwords = line.lstrip().split(' ')
	indent = line[:line.find(kwords[0])]

	# star expr with or without assignment
	
	eq_sign_endings = [w[-1:] for w in kwords]
	if '=' in eq_sign_endings:
		# Case 1: assignment
		# usual form: <dot_name> = <expr>
		eq_sign_index = eq_sign_endings.index('=')
		wrapped_stmt = []
		wrapped_stmt.append(line)
		wrapped_stmt.append(indent + '_on_rout({}, {}, {})'.format(_g_round, lineno, ' '.join(kwords[:eq_sign_index])))
		return wrapped_stmt
	elif'(' in line and ')' in line:
		# Case 2: call without capturing return value
		opening_par_index = line.find('(')
		closing_par_index = line.rfind(')')
		wrapped_stmt = []
		wrapped_stmt.append(indent + '_exec_rv = ' + ' '.join(kwords))
		wrapped_stmt.append(indent + '_on_rout({}, {}, {})'.format(_g_round, lineno, '_exec_rv'))
		return wrapped_stmt

	print('expr not recognized: {}'.format(line.strip()))
	return [line]


def _parse_simple_stmt(tokenizer):
	lineno, line = tokenizer.current()
	kwords = line.lstrip().split(' ')
	indent = line[:line.find(kwords[0])]
	if kwords[0] in ['global', 'nonlocal']:
		kwords = kwords[1:]

	if kwords[0] in ['del', 'pass', 'break', 'continue', 'import']:
		return [line]

	if kwords[0] in ['from']:
		return [line]

	if kwords[0] in ['return', 'yield']:
		wrapped_stmt = []
		wrapped_stmt.append(indent + '_exec_rv = ' + ' '.join(kwords[1:]))
		wrapped_stmt.append(indent + '_on_rout({}, {}, {})'.format(_g_round, lineno, '_exec_rv'))
		wrapped_stmt.append(indent + kwords[0] + ' _exec_rv')
		return wrapped_stmt

	if kwords[0].startswith('assert'):
		wrapped_stmt = []
		wrapped_stmt.append(indent + '_exec_rv = ' + ' '.join(kwords[1:]))
		wrapped_stmt.append(indent + '_on_rout({}, {}, {})'.format(_g_round, lineno, '_exec_rv'))
		wrapped_stmt.append(indent + kwords[0] + ' _exec_rv')
		return [wrapped_stmt]

	# expr_stmt
	return _parse_expr(tokenizer)


def _is_compound_stmt(tokenizer):
	lineno, line = tokenizer.current()
	kwords = line.lstrip().split(' ')
	if kwords[0] in ['ASYNC']:
		kwords = kwords[1:]
		return True
	if kwords[0].startswith('@'):
		return True
	if kwords[0] in ['if', 'elif', 'else', 'while', 'for', 'try', 'with', 'def', 'class']:
		return True
	return False


def _parse_compound_stmt(tokenizer):
	# TODO: print basics for compound statements (loops and logic)
	# TODO: print calls (arguments, rv) to defined functions
	return [tokenizer.current()[1]]


def _normalize_multiline(raw):
	# TODO: work around ';' for now won't work if ';' is present
	# TODO: adjust for multiline definitions
	lines = ['']
	c_quotation = None
	c_opt_extended_quotation = None
	for i, c in enumerate(raw):
		if c_opt_extended_quotation is not None:
			if c == c_opt_extended_quotation:
				c_opt_extended_quotation = None
		elif c_quotation is not None:
			if c == c_quotation:
				c_quotation = None
		elif c == '\n':
			if c_opt_extended_quotation is not None or c_quotation in ['"""', "'''"]:
				pass # multiline string
			else:
				lines.append('')
				continue # don't append new line
		elif raw[i:i+2] in ['"""', "'''"]:
			c_quotation = raw[i:i+2]
		elif c in ["'", '"']:
			if i > 1 and raw[i-1] == 'r':
				c_opt_extended_quotation = c
			else:
				c_quotation = c
		# TODO: elif c in ['(', '{', '['] ...

		lines[-1] += c
	return lines


class Tokenizer(object):
	# TODO: work around ';' for now won't work if ';' is present
	# TODO: adjust for multiline definitions

	def __init__(self, raw):
		self.index = -1
		self.lines = _normalize_multiline(raw)
		ls_line = self.lines[0].lstrip()
		self.orig_indent = self.lines[0][:self.lines[0].find(ls_line)]

	def parse(self):
		parsed = []
		stmt = self.next()
		while stmt is not None:
			_g_routs.append(LineOutput(self.index, stmt))
			strip_stmt = stmt.strip()
			if not strip_stmt:
				parsed.append('')
			elif strip_stmt.startswith('#'):
				parsed.append(stmt)
			else:
				if _is_compound_stmt(self):
					parsed.extend(_parse_compound_stmt(self))
				else:
					parsed.extend(_parse_simple_stmt(self))
			stmt = self.next()
		return parsed
		
	def current(self):
		return self.index, self.lines[self.index]
		
	def next(self):
		if self.index + 1 >= len(self.lines):
			return None
		self.index += 1
		return self.lines[self.index]
EOF

python3 << EOF
import vim

EXEC_BUFFER_NR_KEY = 'pyex_buf'
EXEC_BUFFER_VAR_KEY = 'is_pyex_buf'


def get_cached_buf(cbuf_nr):
	if EXEC_BUFFER_NR_KEY not in vim.buffers[cbuf_nr].vars:
		return None

	buf_nr = int(vim.current.buffer.vars[EXEC_BUFFER_NR_KEY])

	if buf_nr > len(vim.buffers):
		del vim.buffers[cbuf_nr].vars[EXEC_BUFFER_NR_KEY]
		return None

	bwn = vim.eval('bufwinnr({})'.format(buf_nr))
	if int(vim.eval('bufwinnr({})'.format(buf_nr))) < 0:
		del vim.buffers[cbuf_nr].vars[EXEC_BUFFER_NR_KEY]
		return None

	cbuf = vim.buffers[buf_nr]
	if not cbuf.valid or cbuf.name != '' or EXEC_BUFFER_VAR_KEY not in cbuf.vars:
		del vim.buffers[cbuf_nr].vars[EXEC_BUFFER_NR_KEY]
		return None

	return cbuf

def cache_buf(cbuf_nr, nbuf):
	vim.buffers[cbuf_nr].vars[EXEC_BUFFER_NR_KEY] = str(nbuf.number)

def new_buf():
	vim.command('vnew')
	nbuf = vim.buffers[vim.current.buffer.number]
	nbuf.vars[EXEC_BUFFER_VAR_KEY] = 'y'
	return nbuf

def get_buf(cbuf):
	cached_buf = get_cached_buf(cbuf.number)
	if cached_buf is not None:
		return cached_buf

	nbuf = new_buf()
	cache_buf(cbuf.number, nbuf)
	return nbuf
EOF

function! Py3c() range
python3 << EOF
(lnum1, col1) = vim.current.buffer.mark('<')
(lnum2, col2) = vim.current.buffer.mark('>')
lines = vim.eval('getline({}, {})'.format(lnum1, lnum2))
lines[0] = lines[0][col1:]
lines[-1] = lines[-1][:col2+1]

ebuf = get_buf(vim.current.buffer)

# TODO: save previous rounds?
_g_round +=1
_g_routs = []
t = Tokenizer('\n'.join(lines))
exec_cmd = '\n'.join(t.parse())

output_buf = ['Running:']
# debug output (actual command ran)
# for line in exec_cmd.split('\n'):
# 	output_buf.append('> '+line)

try:
	command_output = exec(exec_cmd)
except BaseException as e:
	msg = 'Exception {} was thrown: {}'.format(type(e), e)
	command_output = msg

for out in _g_routs:
	output_buf.extend(str(out).split('\n'))

output_buf.append('')
if command_output is not None:
	# for line in command_output.split('\n'):
	output_buf.extend(str(command_output).split('\n'))

output_buf.append('')
output_buf.append('############')

ebuf[len(output_buf):] = ebuf[0:]
ebuf[0:len(output_buf)] = output_buf

EOF
endfunction
