from urllib.parse import quote
from html.parser import HTMLParser
import html


PUNCTUATION = r'''\\!"#$%&'()*+,./:;<=>?@\[\]^`{}|_~-'''
ESCAPE_TEXT = r'\\[' + PUNCTUATION + ']'


def escape(s, quote=True):
    s = s.replace("&", "&amp;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
    return s


def escape_url(link):
    safe = (
        ':/?#@'           # gen-delims - '[]' (rfc3986)
        '!$&()*+,;='      # sub-delims - "'" (rfc3986)
        '%'               # leave already-encoded octets alone
    )

    if html is None:
        return quote(link.encode('utf-8'), safe=safe)
    # return html.escape(quote(html.unescape(link), safe=safe))
    return html.escape(quote(HTMLParser().unescape(link), safe=safe))


def escape_html(s):
    if html is not None:
        # return html.escape(html.unescape(s)).replace('&#x27;', "'")
        return html.escape(HTMLParser().unescape(s)).replace('&#x27;', "'")
    return escape(s)


def url_encode(s, quote=True):
    s = s.replace("&", "%26")
    s = s.replace("<", "%3C")
    s = s.replace(">", "%3E")
    if quote:
        s = s.replace('"', "%22")
    return s


def unikey(s):
    return ' '.join(s.split()).lower()
