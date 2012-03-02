import sys

import kate
import pep8

from PyQt4 import QtCore

from pyte_plugins.check_plugins import commons
from utils import is_mymetype_python


class StoreErrorsChecker(pep8.Checker):

    def __init__(self, *args, **kwargs):
        super(StoreErrorsChecker, self).__init__(*args, **kwargs)
        self.error_list = []

    def report_error(self, line_number, offset, text, check):
        """
        Store the error
        """
        self.file_errors += 1
        self.error_list.append([line_number, offset, text[0:4], text])

    def get_errors(self):
        """
        Get the errors, and reset the checker
        """
        result, self.error_list = self.error_list, []
        self.file_errors = 0
        return result


@kate.action('pep8', shortcut='Alt+8', menu='Edit')
def check_pep8(currentDocument=None):
    if not commons.canCheckDocument(currentDocument):
        return
    currentDocument = currentDocument or kate.activeDocument()
    path = unicode(currentDocument.url().path())

    # Check the file for errors with PEP8
    sys.argv = [path]
    pep8.process_options([path])
    checker = StoreErrorsChecker(path)
    checker.check_all()
    errors = checker.get_errors()

    if len(errors) == 0:
        commons.showOk('Pep8 Ok')
        return

    errors_to_show = []

    # Paint errors found
    for error in errors:
        errors_to_show.append({
            "line": error[0],
            "column": error[1],
            "filename": path,
            "message": error[3],
            })

    commons.showErrors(errors_to_show, '%s-pep8' % path, currentDocument)


def createSignalCheckDocument(view, *args, **kwargs):
    doc = view.document()
    doc.modifiedChanged.connect(check_pep8)

windowInterface = kate.application.activeMainWindow()
windowInterface.connect(windowInterface,
                QtCore.SIGNAL('viewCreated(KTextEditor::View*)'),
                createSignalCheckDocument)