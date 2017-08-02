# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Otoklim
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from otoklim_dialog import OtoklimDialog, NewProjectDialog, AskProjectDialog, CreateProjectDialog
import os.path


class Otoklim:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Otoklim_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Otoklim')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'Otoklim')
        self.toolbar.setObjectName(u'Otoklim')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Otoklim', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        self.otoklimdlg = OtoklimDialog()
        self.newprojectdlg = NewProjectDialog()
        self.askprojectdlg = AskProjectDialog()
        self.createprojectdlg = CreateProjectDialog()

        # Add Menu Trigger Logic
        self.otoklimdlg.actionNew.triggered.connect(self.ask_project_name)
        self.otoklimdlg.actionOpen.triggered.connect(self.open_existing_project)
        self.otoklimdlg.actionExit.triggered.connect(self.otoklimdlg.close)

        # Add New Project Input Trigger Logic
        self.newprojectdlg.Input_prj_folder.clear()
        self.newprojectdlg.Browse_prj_folder.clicked.connect(
            self.select_input_prj_folder
        )
        self.newprojectdlg.Input_province.clear()
        self.newprojectdlg.Browse_province.clicked.connect(
            self.select_input_province
        )
        self.newprojectdlg.Input_cities.clear()
        self.newprojectdlg.Browse_cities.clicked.connect(
            self.select_input_cities
        )
        self.newprojectdlg.Input_village.clear()
        self.newprojectdlg.Browse_village.clicked.connect(
            self.select_input_village
        )
        self.newprojectdlg.Input_bathymetry.clear()
        self.newprojectdlg.Browse_bathymetry.clicked.connect(
            self.select_input_bathymetry
        )
        self.newprojectdlg.Input_islands.clear()
        self.newprojectdlg.Browse_islands.clicked.connect(
            self.select_input_islands
        )
        self.newprojectdlg.Input_rainpost.clear()
        self.newprojectdlg.Browse_rainpost.clicked.connect(
            self.select_input_rainpost
        )
        self.newprojectdlg.Input_logo.clear()
        self.newprojectdlg.Browse_logo.clicked.connect(
            self.select_input_logo
        )
        self.newprojectdlg.Input_rainfall_class.clear()
        self.newprojectdlg.Browse_rainfall_class.clicked.connect(
            self.select_input_rainfall_class
        )
        self.newprojectdlg.Input_normalrain_class.clear()
        self.newprojectdlg.Browse_normalrain_class.clicked.connect(
            self.select_input_normalrain_class
        )
        self.newprojectdlg.Input_map_template.clear()
        self.newprojectdlg.Browse_map_template.clicked.connect(
            self.select_input_map_template
        )

        # Add New Project Next Trigger
        self.newprojectdlg.ProjectCreate.clicked.connect(
            self.select_project_create
        )

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/Otoklim/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'otoklim'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Otoklim'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    # Main Menu Functions
    def ask_project_name(self):
        """Ask for new project name"""
        self.askprojectdlg.show()
        result = self.askprojectdlg.exec_()
        if result:
            project_name = self.askprojectdlg.ProjectName.text()
            self.newprojectdlg.Input_prj_name.setText(project_name)
            self.newprojectdlg.show()

    def open_existing_project(self):
        """Open existing project """
        open_project = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.otoklim"
        )

    # Project Parameter Input Function
    def select_input_prj_folder(self):
        """Select Project Working Directory """
        project_folder = QFileDialog.getExistingDirectory(
            self.newprojectdlg,
            ""
        )
        self.newprojectdlg.Input_prj_folder.setText(project_folder)

    def select_input_province(self):
        """Select Province Vector File """
        province_file = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.shp"
        )
        self.newprojectdlg.Input_province.setText(province_file)

    def select_input_cities(self):
        """Select Cities / Distircts Vector File """
        cities_file = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.shp"
        )
        self.newprojectdlg.Input_cities.setText(cities_file)

    def select_input_village(self):
        """Select Village Vector File """
        village_file = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.shp"
        )
        self.newprojectdlg.Input_village.setText(village_file)

    def select_input_bathymetry(self):
        """Select Bathymetry Raster File """
        bathymetry_file = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.tif"
        )
        self.newprojectdlg.Input_bathymetry.setText(bathymetry_file)

    def select_input_islands(self):
        """Select Islands Vector File """
        islands_file = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.shp"
        )
        self.newprojectdlg.Input_islands.setText(islands_file)

    def select_input_rainpost(self):
        """Select Rainpost CSV File """
        rainpost_file = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.csv"
        )
        self.newprojectdlg.Input_rainpost.setText(rainpost_file)

    def select_input_logo(self):
        """Select Logo PNG File """
        logo_file = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.png *.jpg"
        )
        self.newprojectdlg.Input_logo.setText(logo_file)

    def select_input_rainfall_class(self):
        """Select Rainfall Classification file"""
        rainfallclass_file = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.txt"
        )
        self.newprojectdlg.Input_rainfall_class.setText(rainfallclass_file)

    def select_input_normalrain_class(self):
        """Select Normal Rain Classification file"""
        normalrainclass_file = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.txt"
        )
        self.newprojectdlg.Input_normalrain_class.setText(normalrainclass_file)

    def select_input_map_template(self):
        """Select QGIS Map Template file"""
        maptemplate_file = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.qpt"
        )
        self.newprojectdlg.Input_map_template.setText(maptemplate_file)

    def select_project_create(self):
        """Create Project"""
        project_folder = self.newprojectdlg.Input_prj_folder.text()
        project_name = self.newprojectdlg.Input_prj_name.text()
        project_directory = os.path.join(project_folder, project_name)
        self.createprojectdlg.show()
        self.createprojectdlg.project_dir.setText(str(project_directory))
        result = self.createprojectdlg.exec_()
        if result:
            print self.createprojectdlg.project_dir.text()

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.otoklimdlg.show()
        # Run the dialog event loop
        '''
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
        '''
