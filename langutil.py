import re

def human_join(elements):
    if len(elements) > 1:
        return "{} and {}".format(", ".join(map(str, elements[:-1])), str(elements[-1]))
    else:
        return str(elements[0])


def indefinite_article(noun_phrase):
    # algorithm adapted from CPAN package Lingua-EN-Inflect-1.891 by Damian Conway
    m = re.search('\w+', noun_phrase, re.UNICODE)
    if m:
        word = m.group(0)
    else:
        return 'an'

    wordi = word.lower()
    for anword in ('euler', 'heir', 'honest', 'hono'):
        if wordi.startswith(anword):
            return 'an'

    if wordi.startswith('hour') and not wordi.startswith('houri'):
        return 'an'

    if len(word) == 1:
        if wordi in 'aedhilmnorsx':
            return 'an'
        else:
            return 'a'

    if re.match(r'(?!FJO|[HLMNS]Y.|RY[EO]|SQU|'
                  r'(F[LR]?|[HL]|MN?|N|RH?|S[CHKLMNPTVW]?|X(YL)?)[AEIOU])'
                  r'[FHLMNRSX][A-Z]', word):
        return 'an'

    for regex in (r'^e[uw]', r'^onc?e\b',
                    r'^uni([^nmd]|mo)','^u[bcfhjkqrst][aeiou]'):
        if re.match(regex, wordi):
            return 'a'

    # original regex was /^U[NK][AIEO]?/ but that matches UK, UN, etc.
    if re.match('^U[NK][AIEO]', word):
        return 'a'
    elif word == word.upper():
        if wordi[0] in 'aedhilmnorsx':
            return 'an'
        else:
            return 'a'

    if wordi[0] in 'aeio':
        return 'an'

    if re.match(r'^y(b[lor]|cl[ea]|fere|gg|p[ios]|rou|tt)', wordi):
        return 'an'
    else:
        return 'a'