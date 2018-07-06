import re


bindings = None
layouts = None

def init(_bindings, _layouts):
    bindings = _bindings
    layouts = _layouts

main_path = 'https://filedn.com/lauJi07EfsyumvwxE9TXUmh/_PREPA/'

def pos(*args):
    try:
        tag = next( [x for x in tags if re.match(r'chapitre_', x)] )
        path = bindings[tag][9:]
        return '&lt;a href="{}{}#page={}>" source &gt;' % main_path, path, args[0] # TODO reformater la metadata
    except StopIteration:
        return 'Warning : no chapter found here'