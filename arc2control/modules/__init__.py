# arc2control.modules
import json
import importlib

def moduleClassFromJson(fname):
    modname = json.loads(open(fname, 'r').read())['modname']
    klsparts = modname.split('.')
    pkgname = '.'.join(klsparts[:-1])

    mod = importlib.import_module(pkgname)
    return getattr(mod, klsparts[-1])
