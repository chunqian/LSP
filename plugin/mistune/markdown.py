from .block_parser import BlockParser, expand_leading_tab, cleanup_lines
from .inline_parser import InlineParser


class Markdown(object):
    def __init__(self, renderer, block=None, inline=None, plugins=None):
        if block is None:
            block = BlockParser()

        if inline is None:
            inline = InlineParser(renderer)

        self.block = block
        self.inline = inline
        self.renderer = inline.renderer
        self.before_parse_hooks = []
        self.before_render_hooks = []
        self.after_render_hooks = []

        if plugins:
            for plugin in plugins:
                plugin(self)

    def use(self, plugin):
        plugin(self)

    def before_parse(self, s, state):
        s, state = preprocess(s, state)
        for hook in self.before_parse_hooks:
            s, state = hook(self, s, state)
        return s, state

    def before_render(self, tokens, state):
        for hook in self.before_render_hooks:
            tokens = hook(self, tokens, state)
        return tokens

    def after_render(self, result, state):
        for hook in self.after_render_hooks:
            result = hook(self, result, state)
        return result

    def internal_parse(self, token, block_code_tokens):
        params = token.get("params")
        if params is None:
            return block_code_tokens
        for item in params:
            if isinstance(item, str) and item == "rust":
                if len(block_code_tokens) == 1:
                    # rust 多次合并
                    block_code_tokens[0]["raw"] += "\n" + token["raw"]
                else:
                    block_code_tokens.append(token)
            else:
                block_code_tokens.append(token)
                # 取一次
                break
        return block_code_tokens

    def parse(self, s, state=None):
        if state is None:
            state = {}

        s, state = self.before_parse(s, state)
        tokens = self.block.parse(s, state)
        tokens = self.before_render(tokens, state)

        # only block_code
        block_code_tokens = []
        for v in tokens:
            if v["type"] == "block_code":
                block_code_tokens = self.internal_parse(v, block_code_tokens)

        result = self.block.render(tokens, self.inline, state)
        result = self.after_render(result, state)
        return result

    def read(self, filepath, state=None):
        if state is None:
            state = {}

        state['__file__'] = filepath
        with open(filepath, 'rb') as f:
            s = f.read()

        return self.parse(s.decode('utf-8'), state)

    def __call__(self, s):
        return self.parse(s)


def preprocess(s, state):
    state.update({
        'def_links': {},
        'def_footnotes': {},
        'footnotes': [],
    })

    if s is None:
        s = '\n'
    else:
        s = s.replace('\u2424', '\n')
        s = cleanup_lines(s)
        s = expand_leading_tab(s)
        if not s.endswith('\n'):
            s += '\n'

    return s, state
