from ..core.tinylog import tinylog as log
import re

class Scanner(re.Scanner):
    def iter(self, string, state, parse_text):
        sc = self.scanner.scanner(string)

        pos = 0
        for match in iter(sc.search, None):
            name, method = self.lexicon[match.lastindex - 1][1]
            hole = string[pos:match.start()]
            if hole:
                yield parse_text(hole, state)

            yield method(match, state)
            pos = match.end()

        hole = string[pos:]
        if hole:
            yield parse_text(hole, state)


class ScannerParser(object):
    scanner_cls = Scanner
    RULE_NAMES = tuple()

    def __init__(self):
        self.rules = list(self.RULE_NAMES)
        self.rule_methods = {}
        self._cached_sc = {}

    def register_rule(self, name, pattern, method):
        self.rule_methods[name] = (pattern, lambda m, state: method(self, m, state))

    def get_rule_pattern(self, name):
        if name not in self.RULE_NAMES:
            return self.rule_methods[name][0]
        return getattr(self, name.upper())

    def get_rule_method(self, name):
        if name not in self.RULE_NAMES:
            return self.rule_methods[name][1]
        return getattr(self, 'parse_' + name)

    def parse_text(self, text, state):
        raise NotImplementedError

    def _scan(self, s, state, rules):
        sc = self._create_scanner(rules)
        for tok in sc.iter(s, state, self.parse_text):
            if isinstance(tok, list):
                for t in tok:
                    yield t
            elif tok:
                yield tok

    def _create_scanner(self, rules):
        sc_key = '|'.join(rules)
        sc = self._cached_sc.get(sc_key)
        if sc:
            return sc

        lexicon = [
            (self.get_rule_pattern(n), (n, self.get_rule_method(n)))
            for n in rules
        ]
        sc = self.scanner_cls(lexicon)
        self._cached_sc[sc_key] = sc
        return sc


class Matcher(object):
    PARAGRAPH_END = re.compile(
        r'(?:\n{2,})|'
        r'(?:\n {0,3}#{1,6})|'  # axt heading
        r'(?:\n {0,3}(?:`{3,}|~{3,}))|'  # fenced code
        r'(?:\n {0,3}>)|'  # blockquote
        r'(?:\n {0,3}(?:[\*\+-]|1[.)]))|'  # list
        r'(?:\n {0,3}<)'  # block html
    )

    def __init__(self, lexicon):
        self.lexicon = lexicon

    def search_pos(self, string, pos):
        m = self.PARAGRAPH_END.search(string, pos)
        if not m:
            return None
        if set(m.group(0)) == {'\n'}:
            return m.end()
        return m.start() + 1

    def iter(self, string, state, parse_text):
        # 获取language
        language_pattern = r"```([\w-]*)\s*\n.+?\n```\n"
        language_match = re.search(language_pattern, string, re.DOTALL)
        language_name = ""
        if language_match:
            language_name = language_match.group(1)

        # 匹配代码段
        code_pattern = r"```[\w-]*,?[\w-]*\s*\n(.+?\n)```\n"
        code_matches = re.findall(code_pattern, string, re.DOTALL)

        # 合并匹配到的内容
        string = '\n'.join(code_matches) if code_matches else string
        string = "```{}\n{}```\n".format(language_name, string)
        
        pos = 0
        endpos = len(string)
        last_end = 0
        while 1:
            if pos >= endpos:
                break
            for rule, (name, method) in self.lexicon:
                match = rule.match(string, pos)
                if match is not None:
                    start, end = match.span()
                    if start > last_end:
                        yield parse_text(string[last_end:start], state)

                    if name.endswith('_start'):
                        token = method(match, state, string)
                        yield token[0]
                        end = token[1]
                    else:
                        yield method(match, state)
                    last_end = pos = end
                    break
            else:
                found = self.search_pos(string, pos)
                if found is None:
                    break
                pos = found

        if last_end < endpos:
            yield parse_text(string[last_end:], state)
