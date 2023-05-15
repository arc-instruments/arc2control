# arc2control.modules
import re
import json
import importlib
import importlib.resources as resources


def moduleClassFromJson(fname):
    modname = json.loads(open(fname, 'r').read())['modname']
    return moduleClassFromModName(modname)


def moduleClassFromModName(modname):
    klsparts = modname.split('.')
    pkgname = '.'.join(klsparts[:-1])

    mod = importlib.import_module(pkgname)
    return getattr(mod, klsparts[-1])


def uiToModule(src, name):
    """
    Compile a Qt Designer UI file into a Python module using pyuic6. This
    function allows for on-the-fly parsing and importing of a UI file into a
    Python module so that an external compilation step is not necessary.

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


def allUisToModules(uis, prefix='Ui_'):
    """
    Compile all Qt Designer UI files listed in ``uis`` into Python modules
    using pyuic6. This function is similar to
    `:meth:~arc2control.modules.uiToModule` but will create a single object
    that holds the types for all compiled UIs.  This function will only look
    for classes that start with ``prefix`` and attach them as attributes to the
    returned object. However, the returned object has a flat namespace so if
    there are two identical class names in the list of the provided UIs an
    exception will be raised.

    .. code-block:: python

        from arc2control.modules import compileUisToModules
        from arc2control.modules.base import BaseModule, BaseOperation
        from . import MOD_NAME, MOD_TAG, MOD_DESCRIPTION

        uis = ['/path/to/iface01.ui', 'path/to/iface02.ui']
        generated = compileUisToModules(uis)

        # now this can be used as base class as usual
        class Iface(BaseModule, generated.Ui_IfaceWidget):
            def __init__(self, parent):
                generated.Ui_IfaceWidget.__init__(self)
                BaseModule.__init__(self, arc, arcconf, vread, store,
                    MOD_NAME, MOD_TAG, cells, mapper, parent=parent)
                # proceed as normal

        :param list uis: A list of paths with Qt UI files
        :param str prefix: Prefix of classes to look for, default is ``Ui_``

        :returns: An object holding all the compiled UI classes as attributes

        :raises ValueError: If two identical UI classes are found in the list
                            of provided files

    """

    # Create a placeholder type to hold the generated Ui classes
    # as atributes
    generated = type('GeneratedElements', (), {})()

    for ui in uis:
        _compileAndAttach(ui, generated, prefix)

    return generated


def _uisFromModuleResources(m, match='.*.ui', prefix='Ui_'):
    # Internal function to compile uis from package resources

    generated = type('GeneratedElements', (), {})()
    for res in resources.contents(m):
        if not re.match(match, res):
            continue
        with resources.path(m, res) as ui:
            _compileAndAttach(ui, generated, prefix)

    return generated


def _compileAndAttach(ui, parent, prefix):
    # Internal function to compile and attach a UI class
    # to a holder object (``parent``)

    # compile the UI file with uic
    compiled = uiToModule(ui, 'compiled')

    # traverse its members
    for item in dir(compiled):
        # check if the member name matches the prefix
        if not item.startswith(prefix):
            continue
        # we found a "<prefix>_XXXX" thing; check if it's actually a type
        obj = getattr(compiled, item)
        if isinstance(obj, type):
            # check if a type with the same name already exists in parent
            if hasattr(parent, item):
                raise ValueError('UI class ' + item + ' exists')
            setattr(parent, item, obj)
