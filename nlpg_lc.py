from typing import List, Dict, Any, Iterator, NamedTuple, Optional
from nlpg import Parser, rule, terminal, l, slot
from pprint import pprint
from collections import defaultdict

# https://github.com/ssarkar2/LeftCornerParser/blob/master/LCParser.py

def remove_embedded_tokens(rules: List[rule]) -> List[rule]:
	out = []

	for old_rule in rules:
		# If the rule is a terminal rule, just forward it
		if len(old_rule.tokens) == 1 and isinstance(old_rule.tokens[0], terminal):
			out.append(old_rule)

		# If the rule has no terminals, also just forward it
		elif not any(isinstance(token, terminal) for token in old_rule.tokens):
			out.append(old_rule)
		
		# The rule has one or more terminals
		else:
			new_rule_tokens = []

			for token in old_rule.tokens:
				if isinstance(token, terminal):
					# Make up a name (preferably static/consistent) for the terminal rule
					if isinstance(token, l):
						terminal_name = 't_{}'.format(token.word)
					else:
						terminal_name = 't_{}'.format(hash(token))

					# Create a new rule for the terminal (if there isnt already one)
					if not any(rule.name == terminal_name for rule in out):
						out.append(rule(terminal_name, [token], slot(0)))

					# 'Update' the rule that contained to terminal to refer to 
					# the new terminal rule
					new_rule_tokens.append(terminal_name)
				else:
					new_rule_tokens.append(token)

			# Instead of the original rule add a copy that refers to the terminals
			# using the terminal rules.
			out.append(rule(old_rule.name, new_rule_tokens, old_rule.template))

	return out


def find_nullables(rules: List[rule]) -> Dict[str, rule]:
	"""
	Based on https://github.com/jeffreykegler/kollos/blob/master/notes/misc/loup2.md
	"""
	rules_lhs = defaultdict(list)
	rules_rhs = defaultdict(list)

	# An array of booleans, indexed by symbol ID. The boolean is ON, if the symbol has
	# been marked "nullable", OFF otherwise.
	nullable = dict()

	for rule in rules:
		try:
			if len(rule.tokens) == 1 and isinstance(rule.tokens[0], terminal):
				continue
			
			rules_lhs[rule.name].append(rule)
			if len(rule.tokens) == 0:
				# Initialize the nullable array, by marking as nullable the LHS of every empty rule.
				nullable[rule.name] = rule
			else:
				for token in rule.tokens:
					assert isinstance(token, str), "Expected str as token, found {!r}".format(token)
					rules_rhs[token].append(rule)
		except:
			raise Exception("Error while processing {!r}".format(rule))

	# Create a "work stack", which will contain those symbols which still need to be
	# worked on in order to find all nullable symbols. Initialize it by pushing all the
	# symbols initially marked as nullable in the nullable array.
	stack = list(nullable)

	# Symbol loop: While symbols remain on the "work stack", do the following:
	while len(stack) > 0:
		symbol = stack.pop()

		# For every rule with the work symbol on its RHS, call it the "work rule"
		for work_rule in rules_rhs[symbol]:
			# For every rule with the work symbol on its RHS, call it the "work rule"
			if work_rule.name in nullable:
				continue

			# For every RHS symbol of the work rule, if it is not marked nullable,
			# continue with the next rule of the rule loop.
			if any(token not in nullable for token in work_rule.tokens):
				continue

			# If we reach this point, the LHS of the work rule is nullable, but is not marked nullable.
			nullable[work_rule.name] = work_rule

			# Push the LHS of the work rule onto the "work stack".
			stack.append(work_rule.name)

	return nullable



def print_chart(chart):
	for config in chart:
		print_config(config)


def print_config(config):
	print("Chart#{} (progress: {})".format(id(config), config.index))
	for n, frame in enumerate(config.stack):
		print("\t Frame {}: {}".format(n, frame))


class Frame(NamedTuple):
	"""
	A frame is a partial or complete rule, to be combined with other
	frames into a complete parse. Frames live on the stack of a Config
	(a potential partial parse). And if everything pans out, a Config
	with a single frame that is complete (the index == len(rule.tokens))
	the parse is complete.
	"""
	rule: rule
	index: int # progress of the token in rule.tokens
	match: Any

	@property
	def complete(self):
		return len(self.rule.tokens) == self.index

	def __repr__(self):
		return "Frame<{}>({})=({!r})".format(self.rule.name,
			" ".join(map(str, self.rule.tokens[0:self.index] + ['*'] + self.rule.tokens[self.index:])),
			self.match)


class Config(NamedTuple):
	"""A possible (partial) parse"""
	stack: List[Frame]
	index: int # index of the progress word in the sentence


class Parse(object):
	def __init__(self, rules: List[rule], words: List[Any], goal: str):
		self.rules = remove_embedded_tokens(rules)
		self.words = list(words)
		self.goal = goal
		self.nullables = find_nullables(self.rules)

	def __iter__(self):
		chart = [Config([], 0)]
		self.counter = 0
		
		while len(chart) > 0:
			config = chart.pop()

			if config.index == len(self.words) \
				and len(config.stack) == 1 \
				and config.stack[0].rule.name == self.goal \
				and config.stack[0].complete:
				yield config.stack[0].match
			else:
				configs = list(self.step(config))
				chart.extend(configs)
				self.counter += len(configs)

	def step(self, config: Config):
		yield from self._advance(config)
		yield from self._scan(config)
		yield from self._predict(config)
		yield from self._complete(config)

	def _eat(self, rule: rule, match: List[Any]) -> Any:
		"""
		Tests if the match completes the rule, and if so, applies the rule's
		template to the match to finish it (e.g. converting a list into a
		structure.) (inappropriately called 'consume', like 'swallow' or 'digest')
		"""
		try:
			if len(rule.tokens) == len(match):
				match = rule.template.consume(match)
		except:
			raise Exception("Error while {!r} tries to eat {!r}".format(rule, match))
		return match

	def _scan(self, config: Config) -> Iterator[Config]:
		if config.index < len(self.words) and (len(config.stack) == 0 or not config.stack[-1].complete):
			word = self.words[config.index]
			for rule in self._find_rules(word):
				match = rule.tokens[0].consume(word)
				yield Config(config.stack + [Frame(rule, 1, match)], config.index + 1)

	def _predict(self, config: Config) -> Iterator[Config]:
		"""
		Based on the last rule on the stack, predict which higher rule could be
		positioned above the last rule.
		"""
		if len(config.stack) > 0:
			if config.stack[-1].complete:
				for rule in self._find_left_corner(config.stack[-1].rule):
					match = self._eat(rule, [config.stack[-1].match])
					yield Config(config.stack[0:-1] + [Frame(rule, 1, match)], config.index)

	def _complete(self, config: Config) -> Iterator[Config]:
		"""
		If the last rule on the stack is complete, and the second one isn't yet
		then check whether the second one can be progressed with the completed
		rule, and if this is the case, do so.
		"""
		if len(config.stack) > 1:
			first = config.stack[-1]
			second = config.stack[-2]
			if first.complete and not second.complete and first.rule.name == second.rule.tokens[second.index]:
				# Append the results of the child token to the progress so far
				match = self._eat(second.rule, second.match + [first.match])
				
				# Yield a new config where the two frames, the one with the parent and the child,
				# are replaced with one where the parent has progressed one step.
				yield Config(config.stack[:-2] + [Frame(second.rule, second.index + 1, match)], config.index)

	def _advance(self, config: Config) -> Iterator[Config]:
		"""
		Same as complete, except for nullable rules. It just adds a None to the
		match and advances the Frame. If it completes it (i.e. the nullable was 
		the rule's last token) it also consumes the match.
		"""
		if len(config.stack) > 0:
			frame = config.stack[-1]
			if not frame.complete:
				token = frame.rule.tokens[frame.index]
				if token in self.nullables:
					# Append the results of the child token to the progress so far
					match = self._eat(frame.rule, frame.match + [self.nullables[token].template.consume([])])
					yield Config(config.stack[:-1] + [Frame(frame.rule, frame.index + 1, match)], config.index)

	def _find_left_corner(self, corner: rule) -> Iterator[rule]:
		for rule in self.rules:
			if len(rule.tokens) > 0 and rule.tokens[0] == corner.name:
				yield rule

	def _find_rules(self, word: Any) -> Iterator[rule]:
		for rule in self.rules:
			if len(rule.tokens) == 1 \
				and isinstance(rule.tokens[0], terminal) \
				and rule.tokens[0].test(word):
				yield rule


class LCParser(Parser):
	def parse(self, rule_name, words):
		return Parse(self.rules, words, rule_name)


if __name__ == '__main__':
	import nlpg
	from nlpg import ruleset, rule, tlist, template, l, slot, empty
	from pprint import pprint

	class claim(NamedTuple):
		id: str

	class argument(NamedTuple):
		claim: 'claim'
		attacks: List['claim']
		supports: List['claim']

	rules = ruleset([
		rule('extended_claims',
			['extended_claim'],
			tlist(head=0)),
		rule('extended_claims',
			['extended_claim', l('and'), 'extended_claims'],
			tlist(head=0, tail=2)),
		rule('extended_claim',
			['claim', 'supports', 'attacks'],
			template(argument, claim=0, supports=1, attacks=2)),
		rule('claim',
			[l('birds'), l('can'), l('fly')],
			template(claim, id='b_can_f')),
		rule('claim',
			[l('Tweety'), l('can'), l('fly')],
			template(claim, id='t_can_f')),
		rule('claim',
			[l('Tweety'), l('has'), l('wings')],
			template(claim, id='t_has_w')),
		rule('claim',
			[l('Tweety'), l('is'), l('a'), l('bird')],
			template(claim, id='t_is_b')),
		rule('claim',
			[l('Tweety'), l('is'), l('a'), l('penguin')],
			template(claim, id='t_is_p')),
		rule('claim',
			[l('Tweety'), l('is'), l('awesome')],
			template(claim, id='t_is_a')),
		rule('supports',
			[],
			tlist()),
		rule('supports',
			['support'],
			tlist(0)),
		rule('supports',
			['support', l('and'), 'supports'],
			tlist(0, 2)),
		rule('support',
			[l('because'), 'extended_claims'],
			slot(1)),
		rule('attacks',
			[],
			tlist()),
		rule('attacks',
			['attack'],
			tlist(0)),
		rule('attacks',
			['attack', l('and'), 'attacks'],
			tlist(0, 2)),
		rule('attack',
			['attack_marker', 'extended_claims'],
			slot(1)),
		rule('attack_marker', [l('but')], empty()),
		rule('attack_marker', [l('except'), l('that')], empty())
	])

	start = 'extended_claim'

	rd_parser = Parser(rules)

	lc_parser = LCParser(rules)
	
	sentence = 'Tweety can fly because Tweety is a bird and because Tweety is a bird and birds can fly but Tweety is a penguin'

	class minarg(NamedTuple):
		claim: l
		support: Optional['minarg']
		attack: Optional['minarg']

		def __repr__(self):
			return "({}{}{})".format(
				self.claim,
				" because " + repr(self.support) if self.support else "",
				" except " + repr(self.attack) if self.attack else "")

	# rules = ruleset([
	# 	rule('S', ['t_claim', 'support', 'attack'], template(minarg, claim=0, support=1, attack=2)),
	# 	rule('support', [l('because'), 'S'], slot(1)),
	# 	rule('support', [], empty()),
	# 	rule('attack', [l('except'), 'S'], slot(1)),
	# 	rule('attack', [], empty()),
	# 	rule('t_claim', [l('A')], slot(0)),
	# 	rule('t_claim', [l('B')], slot(0)),
	# 	rule('t_claim', [l('C')], slot(0)),
	# ])

	# start = 'S'

	# parser = LCParser(rules)
	
	# sentence = 'A except B because C'

	words = sentence.split(' ')

	from timeit import timeit
	print("LC Parser: {}".format(timeit('list(rd_parser.parse(start, words))', number=100, globals={'rd_parser': rd_parser, 'start': start, 'words': words})))
	print("RD Parser: {}".format(timeit('list(lc_parser.parse(start, words))', number=100, globals={'lc_parser': lc_parser, 'start': start, 'words': words})))

	parser = lc_parser

	trees = list(parser.parse(start, words))

	# nlpg.DEBUG = True

	pprint(trees)

	for tree in trees:
		for realisation in parser.reverse(start, tree):
			print(' '.join(realisation))
