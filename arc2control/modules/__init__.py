# arc2control.modules
import json
import importlib


def moduleClassFromJson(fname):
    modname = json.loads(open(fname, 'r').read())['modname']
    klsparts = modname.split('.')
    pkgname = '.'.join(klsparts[:-1])

    mod = importlib.import_module(pkgname)
    return getattr(mod, klsparts[-1])


def uiToModule(src, name):
    """
    Compile a Qt Designer UI file into a Python module using pyuic6. This
    function allows for on-the-fly parsing and importing of a UI file into a
    Python module so that an external compilation step is not necessary.
    Although built-in modules will always have their UIs precompiled (as pyuic
    migh not always be available) UI auto-compilation expediates the turnaround
    for UI changes when developing a 3rd party module.

    .. code-block:: python

        from arc2control.modules import uiToModule
        from arc2control.modules.base import BaseModule, BaseOperation
        from . import MOD_NAME, MOD_TAG, MOD_DESCRIPTION

        # this effectively does
        # >>> from generated import Ui_IfaceWidget
        generated = uiToModule('/path/to/iface.ui', 'generated')
        Ui_IfaceWidget = generated.Ui_IfaceWidget

        # now this can be used as base class as usual
        class Iface(BaseModule, Ui_IfaceWidget):
            def __init__(self, parent):
                Ui_IfaceWidget.__init__(self)
                BaseModule.__init__(self, arc, arcconf, vread, store,
                    MOD_NAME, MOD_TAG, cells, mapper, parent=parent)
                # proceed as normal

    :param str src: Path to Qt UI file
    :param str name: Name of the auto-generated module
    """

    import PyQt6.uic as uic
    from io import StringIO
    import importlib.util

    f = StringIO()
    uic.compileUi(src, f, execute=False)
    code = f.getvalue()
    f.close()

    spec = importlib.util.spec_from_loader(name, loader=None)
    mod = importlib.util.module_from_spec(spec)
    exec(code, mod.__dict__)

    return mod
