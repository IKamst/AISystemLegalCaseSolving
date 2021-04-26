import re
import traceback
from typing import List
from functools import reduce
from itertools import chain
from pprint import pprint
from collections import OrderedDict
import os

import flask
import spacy

import parser
from hasl1.grammar import hasl0_grammar, hasl1_grammar, Claim, Relation, Argument, Entity, Span, id
from flask import Flask, render_template, request, jsonify


def unique(iterable, key = lambda x: x):
    elements = []
    seen = set()
    for el in iterable:
        if key(el) not in seen:
            elements.append(el)
            seen.add(key(el))
    return elements


class TokenizeError(Exception):
    pass


class JSONEncoder(flask.json.JSONEncoder):
    mapping = {
        'claim': Claim,
        'relation': Relation
    }

    def ref(self, o):
        return {
            'cls': next(name for name, cls in self.mapping.items() if isinstance(o, cls)),
            'id': id(o)
        }

    def default(self, o):
        if isinstance(o, Argument):
            return {
                'cls': 'argument',
                'claims': o.claims,
                'relations': o.relations,
                'entities': frozenset(entity for entity in chain.from_iterable(claim.entities for claim in o.claims))
            }
        elif isinstance(o, Claim):
            return {
                'cls': 'claim',
                'id': id(o),
                'assumption': o.assumed,
                'text': str(o),
                'tooltip': o.tooltip
            }
        elif isinstance(o, Relation):
            return {
                'cls': 'relation',
                'id': id(o),
                'sources': [self.ref(s) for s in o.sources],
                'target': self.ref(o.target),
                'type': o.type
            }
        elif isinstance(o, Entity):
            return {
                'name': o.name,
                'noun': o.noun,
                'pronoun': o.pronoun,
                'repr': repr(o)
            }
        elif isinstance(o, Span):
            return str(o)
        elif isinstance(o, spacy.tokens.doc.Doc):
            return list(o)
        elif isinstance(o, spacy.tokens.token.Token):
            return dict(text=str(o), tag=o.tag_)
        elif isinstance(o, frozenset):
            return list(o)
        else:
            print("What to do with {}".format(o.__class__.__name__))
            return super().default(o)


nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner', 'textcat'])


app = Flask(__name__)
app.secret_key = 'Tralalala'
app.json_encoder = JSONEncoder
app.debug = True

# Load sentence files
sentence_files = [os.path.join(os.path.dirname(__file__), '../evaluation.tex')]
sentences = OrderedDict()

for sentence_file in sentence_files:
    sentences.update(parser.read_sentences(sentence_file))

grammars = {
    'HASL/0': hasl0_grammar,
    'HASL/1': hasl1_grammar
}

@app.route('/')
def hello():
    return render_template('index.html', sections=sentences, grammars=grammars)


@app.route('/api/parse', methods=['GET'])
def api_parse_sentence():
    grammar_name = request.args.get('grammar')
    tokens = nlp(request.args.get('sentence'))
    reply = dict(tokens=tokens, grammar=grammar_name)

    try:
        try:
            grammar = grammars[grammar_name]
        except:
            raise Exception('Grammar {} not available'.format(grammar_name));

        p = parser.Parser(grammar, 'sentences')
        parses = p.parse(tokens)
        reply['parses'] = unique(parses, key=lambda parse: parse['data'])

        if len(reply['parses']) > 20:
            reply['warning'] = 'There were {} parses, but cut off at {}'.format(len(reply['parses']), 20)
            reply['parses'] = reply['parses'][:20]

        return jsonify(reply)
    except Exception as error:
        traceback.print_exc()
        reply['error'] = "{}: {!s}\n{}".format(error.__class__.__name__, error, traceback.format_exc())
        response = jsonify(reply)
        response.status_code = 400
        return response

def run():
    app.run(extra_files=sentence_files)
