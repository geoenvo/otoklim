# -*- coding: utf-8 -*-
"""
/***************************************************************************
 OtoklimDialog
                                 A QGIS plugin
 Lorem ipsum dolor sit amet
                             -------------------
        begin                : 2017-07-03
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Geo Enviro Omega
        email                : faizalprbw@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic

BASE, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'otoklim_dialog_base.ui'))

ASK_PROJECT, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'otoklim_dialog_ask_project.ui'))

NEW_PROJECT, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'otoklim_dialog_new_project.ui'))

CREATE_PROJECT, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'otoklim_dialog_create_project.ui'))

PROJECT_PROGRESS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'otoklim_dialog_project_progress.ui'))

DIR_CONFIRM, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'otoklim_dialog_directory_confirm.ui'))

SAVE_AS_PRO, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'otoklim_dialog_save_as_project.ui'))

EDIT_CSV, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'otoklim_dialog_edit_delimiter.ui'))

ERROR_MSG, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'otoklim_dialog_error_message.ui'))

SAVE_CONFIRM, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'otoklim_dialog_save_confirm.ui'))

REPLACE_CONFIRM, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'otoklim_dialog_replace_confirm.ui'))


class OtoklimDialog(QtGui.QMainWindow, BASE):
    def __init__(self, parent=None):
        """Constructor."""
        super(OtoklimDialog, self).__init__(parent)
        self.setupUi(self)

class AskProjectDialog(QtGui.QDialog, ASK_PROJECT):
    def __init__(self, parent=None):
        """Constructor."""
        super(AskProjectDialog, self).__init__(parent)
        self.setupUi(self)

class NewProjectDialog(QtGui.QDialog, NEW_PROJECT):
    def __init__(self, parent=None):
        """Constructor."""
        super(NewProjectDialog, self).__init__(parent)
        self.setupUi(self)

class CreateProjectDialog(QtGui.QDialog, CREATE_PROJECT):
    def __init__(self, parent=None):
        """Constructor."""
        super(CreateProjectDialog, self).__init__(parent)
        self.setupUi(self)

class ProjectProgressDialog(QtGui.QDialog, PROJECT_PROGRESS):
    def __init__(self, parent=None):
        """Constructor."""
        super(ProjectProgressDialog, self).__init__(parent)
        self.setupUi(self)

class DirectoryConfirmDialog(QtGui.QDialog, DIR_CONFIRM):
    def __init__(self, parent=None):
        """Constructor."""
        super(DirectoryConfirmDialog, self).__init__(parent)
        self.setupUi(self)

class SaveAsProjectDialog(QtGui.QDialog, SAVE_AS_PRO):
    def __init__(self, parent=None):
        """Constructor."""
        super(SaveAsProjectDialog, self).__init__(parent)
        self.setupUi(self)

class EditDelimiterDialog(QtGui.QDialog, EDIT_CSV):
    def __init__(self, parent=None):
        """Constructor."""
        super(EditDelimiterDialog, self).__init__(parent)
        self.setupUi(self)

class ErrorMessageDialog(QtGui.QDialog, ERROR_MSG):
    def __init__(self, parent=None):
        """Constructor."""
        super(ErrorMessageDialog, self).__init__(parent)
        self.setupUi(self)

class SaveConfrimDialog(QtGui.QDialog, SAVE_CONFIRM):
    def __init__(self, parent=None):
        """Constructor."""
        super(SaveConfrimDialog, self).__init__(parent)
        self.setupUi(self)

class ReplaceConfrimDialog(QtGui.QDialog, REPLACE_CONFIRM):
    def __init__(self, parent=None):
        """Constructor."""
        super(ReplaceConfrimDialog, self).__init__(parent)
        self.setupUi(self)
