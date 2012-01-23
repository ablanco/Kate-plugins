# Inspirated in http://code.google.com/p/djangode/source/browse/trunk/djangode/gui/python_editor.py#214
import compiler
import os
import glob
import pkgutil
import string
import sys

import kate

from PyQt4 import QtCore, QtGui


global modules_path
modules_path = {}


class AutoCompleter(QtGui.QCompleter):

    def __init__(self, l, view, activate_subfix):
        super(AutoCompleter, self).__init__(l, view)
        self.view = view
        self.activate_subfix = activate_subfix

    def auto_insertText(self, text):
        text = text.replace(self.completionPrefix(), '')
        self.view.insertText('%s%s'% (text, self.activate_subfix))

    @classmethod
    def get_pythonpath(self):
        return sys.path

    @classmethod
    def get_top_level_modules(self):
        # http://code.google.com/p/djangode/source/browse/trunk/djangode/data/codemodel/codemodel.py#57
        modules = []
        pythonpath = self.get_pythonpath()
        for directory in pythonpath:
            for filename in glob.glob(directory + os.sep + "*"):
                module = None
                if filename.endswith(".py"):
                    module = filename.split(os.sep)[-1][:-3]
                elif os.path.isdir(filename) and os.path.exists(filename + os.sep + "__init__.py"):
                    module = filename.split(os.sep)[-1]
                if module and not module in modules:
                    modules.append(module)
                    modules_path[module] = [filename]
        return sorted(modules)

    @classmethod
    def get_submodules(self, module_name, submodules=None, attributes=False):
        module_dir = modules_path[module_name][0]
        submodules = [submodule for submodule in submodules if submodule]
        if submodules:
            submodules = os.sep.join(submodules)
            module_dir = "%s%s%s" % (module_dir, os.sep, submodules)
        modules = []
        for loader, module_name, is_pkg in pkgutil.walk_packages([module_dir]):
            modules.append(module_name)
        if attributes:
            att_dir = os.sep.join(module_dir.split(os.sep)[:-1])
            att_module = module_dir.split(os.sep)[-1].replace('.py', '').replace('.pyc', '')
            importer = pkgutil.get_importer(att_dir)
            module = importer.find_module(att_module)
            code = module.get_code()
            for const in code.co_consts:
                if getattr(const, 'co_name', None):
                    modules.append(const.co_name)
        return sorted(modules)


class ComboBox(QtGui.QComboBox):

    def __init__(self, view, *args, **kwargs):
        super(ComboBox, self).__init__(view, *args, **kwargs)
        self.main_view = view

    def keyPressEvent(self, event, *args, **kwargs):
        key = unicode(event.text())
        insertCharacters = string.ascii_letters + string.digits + '. ;_\n'
        if key in unicode(insertCharacters):
            self.main_view.insertText(event.text())
        return super(ComboBox, self).keyPressEvent(event, *args, **kwargs)


def autocompleteDocument(document, qrange, *args, **kwargs):
    if qrange.start().line() != qrange.end().line():
        return
    line = unicode(document.line(qrange.start().line())).lstrip()
    currentDocument = kate.activeDocument()
    view = currentDocument.activeView()
    currentPosition = view.cursorPosition()
    activate_subfix = ''
    prefix = ''
    word_list = None
    if line.startswith("import ") and not '.' in line:
        prefix = line.replace('import ', '').split('.')[-1]
        prefix = prefix.split('.')[-1].strip()
        word_list = AutoCompleter.get_top_level_modules()
    elif line.startswith("from ") and not '.' in line and not 'import' in line:
        prefix = line.replace('from ', '').split('.')[-1]
        prefix = prefix.split('.')[-1].strip()
        activate_subfix = '.'
        word_list = AutoCompleter.get_top_level_modules()
    elif "from " in line or "import " in line:
        separated = '.'
        if not '.' in line:
            separated = 'import '
            prefix = line
            module = line.replace('from ', '').split(separated)[0].strip()
        else:
            prefix = line.split(separated)[-1].strip()
            module = line.replace('from ', '').replace('import ', '').split(separated)[0].strip()
        top_level_module = modules_path.get(module)
        attributes = False
        if line.startswith("from ") and not ' import ' in line:
            submodules = line.split(".")[1:-1]
        elif line.startswith("from "):
            attributes = True
            prefix = prefix.split(" import")[1].strip()
            submodules = line.split(" import")[0].split(".")[1:]
            activate_subfix = '\n'
        else:
            submodules = line.split("import ")[1].split(".")[1:-1]
        if top_level_module:
            word_list = AutoCompleter.get_submodules(module, submodules, attributes)
    elif '.' in line:
        text = unicode(document.text()).split("\n")
        raw, column = currentPosition.position()
        text_raw = text[raw]
        del text[raw]
        code = compile('\n'.join(text), "name", "exec")
        vars_file = {}
        exec code in globals(), vars_file
        module = vars_file.get(text_raw.split('.')[0], None).__name__
        submodules = text_raw.split('.')[1:-1]
        top_level_module = modules_path.get(module, None)
        attributes = True
        if top_level_module:
            word_list = AutoCompleter.get_submodules(module, submodules, attributes)

    if not word_list:
        return

    string_list = QtCore.QStringList()
    for word in word_list:
        string_list.append(word)

    completer = AutoCompleter(QtCore.QStringList(), view, activate_subfix)
    completer.setCompletionMode(QtGui.QCompleter.PopupCompletion)
    completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
    completer.setModel(QtGui.QStringListModel(string_list, completer))
    completer.setCompletionPrefix(prefix)
    completer.popup().setCurrentIndex(completer.completionModel().index(0, 0))

    point = view.cursorToCoordinate(currentPosition)
    point.setY((point.y() - 80))

    qr = QtCore.QRect(point, QtCore.QSize(100, 100))
    qr.setWidth(completer.popup().sizeHintForColumn(0)
              + completer.popup().verticalScrollBar().sizeHint().width())

    qcombo = ComboBox(view)
    completer.setWidget(qcombo)
    completer.activated.connect(completer.auto_insertText)
    completer.complete(qr)


def createSignalAutocompleteDocument(view, *args, **kwargs):
    # https://launchpad.net/ubuntu/precise/+source/pykde4
    # https://launchpad.net/ubuntu/precise/+source/pykde4/4:4.7.97-0ubuntu1/+files/pykde4_4.7.97.orig.tar.bz2
    view.document().textInserted.connect(autocompleteDocument)


windowInterface = kate.application.activeMainWindow()
windowInterface.connect(windowInterface,
                QtCore.SIGNAL('viewCreated(KTextEditor::View*)'),
                createSignalAutocompleteDocument)
