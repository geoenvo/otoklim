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
