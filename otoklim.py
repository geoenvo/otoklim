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
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QListWidgetItem, QCloseEvent, QColor
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from otoklim_dialog import (
    OtoklimDialog,
    NewProjectDialog,
    AskProjectDialog,
    CreateProjectDialog,
    ProjectProgressDialog,
    DirectoryConfirmDialog,
    SaveAsProjectDialog,
    EditDelimiterDialog,
    ErrorMessageDialog
)
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsMapLayerRegistry
from osgeo import gdal, ogr, osr
from gdalconst import GA_ReadOnly
import os.path
import os
import shutil
import csv
import json
import subprocess


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
        self.projectprogressdlg = ProjectProgressDialog()
        self.dirconfirmdlg = DirectoryConfirmDialog()
        self.saveasprodlg = SaveAsProjectDialog()
        self.editdelimiterdlg = EditDelimiterDialog()
        self.errormessagedlg = ErrorMessageDialog()

        # Default Main Window
        self.otoklimdlg.actionSave_As.setEnabled(False)
        self.otoklimdlg.projectparamPanel.setEnabled(False)
        self.otoklimdlg.projectparamPanel.hide()
        self.otoklimdlg.projectparamPanelAccord.setEnabled(False)
        self.otoklimdlg.projectparamPanelAccord.hide()

        # Add Menu Trigger Logic
        self.otoklimdlg.actionNew.triggered.connect(self.ask_project_name)
        self.otoklimdlg.actionOpen.triggered.connect(self.open_existing_project)
        self.otoklimdlg.actionSave.triggered.connect(self.save_change)
        self.otoklimdlg.actionSave_As.triggered.connect(self.save_as_new)
        self.otoklimdlg.actionExit.triggered.connect(self.otoklimdlg.close)

        # Add Panel Accordion Button Logic
        self.otoklimdlg.projectparamPanelAccord.clicked.connect(self.project_param_accord)

        # Add New Project Input Trigger Logic
        self.newprojectdlg.csv_delimiter.textChanged.connect(
            self.enable_create_button
        )
        self.newprojectdlg.Input_prj_folder.clear()
        self.newprojectdlg.Input_prj_folder.textChanged.connect(
            self.enable_create_button
        )
        self.newprojectdlg.Browse_prj_folder.clicked.connect(
            self.select_input_prj_folder
        )
        self.newprojectdlg.Input_province.clear()
        self.newprojectdlg.Input_province.textChanged.connect(
            self.enable_create_button
        )
        self.newprojectdlg.Browse_province.clicked.connect(
            self.select_input_province
        )
        self.newprojectdlg.Input_districts.clear()
        self.newprojectdlg.Input_districts.textChanged.connect(
            self.enable_create_button
        )
        self.newprojectdlg.Browse_districts.clicked.connect(
            self.select_input_districts
        )
        self.newprojectdlg.Input_subdistricts.clear()
        self.newprojectdlg.Input_subdistricts.textChanged.connect(
            self.enable_create_button
        )
        self.newprojectdlg.Browse_subdistricts.clicked.connect(
            self.select_input_subdistricts
        )
        self.newprojectdlg.Input_village.clear()
        self.newprojectdlg.Input_village.textChanged.connect(
            self.enable_create_button
        )
        self.newprojectdlg.Browse_village.clicked.connect(
            self.select_input_village
        )
        self.newprojectdlg.Input_bathymetry.clear()
        self.newprojectdlg.Input_bathymetry.textChanged.connect(
            self.enable_create_button
        )
        self.newprojectdlg.Browse_bathymetry.clicked.connect(
            self.select_input_bathymetry
        )
        self.newprojectdlg.Input_rainpost.clear()
        self.newprojectdlg.Input_rainpost.textChanged.connect(
            self.enable_create_button
        )
        self.newprojectdlg.Browse_rainpost.clicked.connect(
            self.select_input_rainpost
        )
        self.newprojectdlg.Input_logo.clear()
        self.newprojectdlg.Input_logo.textChanged.connect(
            self.enable_create_button
        )
        self.newprojectdlg.Browse_logo.clicked.connect(
            self.select_input_logo
        )
        self.newprojectdlg.Input_rainfall_class.clear()
        self.newprojectdlg.Input_rainfall_class.textChanged.connect(
            self.enable_create_button
        )
        self.newprojectdlg.Browse_rainfall_class.clicked.connect(
            self.select_input_rainfall_class
        )
        self.newprojectdlg.Input_normalrain_class.clear()
        self.newprojectdlg.Input_normalrain_class.textChanged.connect(
            self.enable_create_button
        )
        self.newprojectdlg.Browse_normalrain_class.clicked.connect(
            self.select_input_normalrain_class
        )
        self.newprojectdlg.Input_map_template.clear()
        self.newprojectdlg.Input_map_template.textChanged.connect(
            self.enable_create_button
        )
        self.newprojectdlg.Browse_map_template.clicked.connect(
            self.select_input_map_template
        )

        # Add New Project Next Trigger
        self.newprojectdlg.ProjectCreate.clicked.connect(
            self.select_project_create
        )

        # Add Edit Project Logic
        self.otoklimdlg.Edit_csvdelimiter.clicked.connect(
            self.edit_csv_delimiter
        )
        self.otoklimdlg.Edit_province.clicked.connect(
            self.edit_province
        )
        self.otoklimdlg.Edit_districts.clicked.connect(
            self.edit_districts
        )
        self.otoklimdlg.Edit_subdistricts.clicked.connect(
            self.edit_subdistricts
        )
        self.otoklimdlg.Edit_village.clicked.connect(
            self.edit_village
        )
        self.otoklimdlg.Edit_bathymetry.clicked.connect(
            self.edit_bathymetry
        )
        self.otoklimdlg.Edit_rainpost.clicked.connect(
            self.edit_rainpost
        )
        self.otoklimdlg.Edit_logo.clicked.connect(
            self.edit_logo
        )
        self.otoklimdlg.Edit_rainfall_class.clicked.connect(
            self.edit_rainfall_class
        )
        self.otoklimdlg.Edit_normalrain_class.clicked.connect(
            self.edit_normalrain_class
        )
        self.otoklimdlg.Edit_map_template.clicked.connect(
            self.edit_map_template
        )

        # Add Show Folder Trigger Logic
        self.otoklimdlg.showFolder.clicked.connect(
            self.show_folder
        )

        # Add Show Layer in Canvas
        self.otoklimdlg.Add_province.clicked.connect(
            self.add_shapefile_province
        )
        self.otoklimdlg.Add_districts.clicked.connect(
            self.add_shapefile_districts
        )
        self.otoklimdlg.Add_subdistricts.clicked.connect(
            self.add_shapefile_subdistricts
        )
        self.otoklimdlg.Add_village.clicked.connect(
            self.add_shapefile_village
        )
        self.otoklimdlg.Add_bathymetry.clicked.connect(
            self.add_raster_bathymetry
        )
        self.otoklimdlg.View_rainpost.clicked.connect(
            self.view_rainpost
        )
        self.otoklimdlg.View_rainfall_class.clicked.connect(
            self.view_rainfall_class
        )
        self.otoklimdlg.View_normalrain_class.clicked.connect(
            self.view_normalrain_class
        )

        # Add Save As Project Workspace Trigger Logic
        self.saveasprodlg.Browse_prj_folder.clicked.connect(
            self.select_input_prj_folder_saveas
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
        result = self.askprojectdlg.exec_()
        if result:
            self.otoklimdlg.province.setWhatsThis('')
            self.otoklimdlg.province.setStyleSheet('color: black')
            self.otoklimdlg.districts.setWhatsThis('')
            self.otoklimdlg.districts.setStyleSheet('color: black')
            self.otoklimdlg.subdistricts.setWhatsThis('')
            self.otoklimdlg.subdistricts.setStyleSheet('color: black')
            self.otoklimdlg.villages.setWhatsThis('')
            self.otoklimdlg.villages.setStyleSheet('color: black')
            self.otoklimdlg.bathymetry.setWhatsThis('')
            self.otoklimdlg.bathymetry.setStyleSheet('color: black')
            self.otoklimdlg.rainpostfile.setWhatsThis('')
            self.otoklimdlg.rainpostfile.setStyleSheet('color: black')
            self.otoklimdlg.logofile.setWhatsThis('')
            self.otoklimdlg.logofile.setStyleSheet('color: black')
            self.otoklimdlg.rainfallfile.setWhatsThis('')
            self.otoklimdlg.rainfallfile.setStyleSheet('color: black')
            self.otoklimdlg.normalrainfile.setWhatsThis('')
            self.otoklimdlg.normalrainfile.setStyleSheet('color: black')
            self.otoklimdlg.maptemplate.setWhatsThis('')
            self.otoklimdlg.maptemplate.setStyleSheet('color: black')
            project_name = self.askprojectdlg.ProjectName.text()
            self.askprojectdlg.ProjectName.clear()
            self.newprojectdlg.Input_prj_name.setText(project_name)
            self.newprojectdlg.show()
            # clear input line if window closed
            if not self.newprojectdlg.exec_():
                self.newprojectdlg.csv_delimiter.clear()
                self.newprojectdlg.Input_prj_name.clear()
                self.newprojectdlg.Input_prj_file_name.clear()
                self.newprojectdlg.Input_prj_folder.clear()
                self.newprojectdlg.Input_province.clear()
                self.newprojectdlg.Input_districts.clear()
                self.newprojectdlg.Input_subdistricts.clear()
                self.newprojectdlg.Input_village.clear()
                self.newprojectdlg.Input_bathymetry.clear()
                # self.newprojectdlg.Input_islands.clear()
                self.newprojectdlg.Input_rainpost.clear()
                self.newprojectdlg.Input_logo.clear()
                self.newprojectdlg.Input_rainfall_class.clear()
                self.newprojectdlg.Input_normalrain_class.clear()
                self.newprojectdlg.Input_map_template.clear()
        else:
            self.askprojectdlg.ProjectName.clear()

    def read_otoklim_file(self, json):
        """Read JSON structure from .otoklim file"""
        project_name = json['PRJ_NAME']
        self.otoklimdlg.projectname.setText(project_name)
        delimiter = json['FILE']['CSV_DELIMITER']
        self.otoklimdlg.csvdelimiter.setText(delimiter)
        project_directory = json['LOCATION']['PRJ_FILE_LOC']
        self.otoklimdlg.projectworkspace.setText(project_directory)
        project_filename = json['FILE']['PRJ_FILE']['NAME']
        self.otoklimdlg.projectfilename.setText(project_filename)
        shp_prov = os.path.join(
            json['LOCATION'][json['FILE']['PROV_FILE']['LOCATION']],
            json['FILE']['PROV_FILE']['NAME']
        )
        self.otoklimdlg.province.setText(shp_prov)
        shp_dis = os.path.join(
            json['LOCATION'][json['FILE']['CITY_DIST_FILE']['LOCATION']],
            json['FILE']['CITY_DIST_FILE']['NAME']
        )
        self.otoklimdlg.districts.setText(shp_dis)
        shp_subdis = os.path.join(
            json['LOCATION'][json['FILE']['SUB_DIST_FILE']['LOCATION']],
            json['FILE']['SUB_DIST_FILE']['NAME']
        )
        self.otoklimdlg.subdistricts.setText(shp_subdis)
        shp_vil = os.path.join(
            json['LOCATION'][json['FILE']['VILLAGE_FILE']['LOCATION']],
            json['FILE']['VILLAGE_FILE']['NAME']
        )
        self.otoklimdlg.villages.setText(shp_vil)
        raster_bat = os.path.join(
            json['LOCATION'][json['FILE']['BAYTH_FILE']['LOCATION']],
            json['FILE']['BAYTH_FILE']['NAME']
        )
        self.otoklimdlg.bathymetry.setText(raster_bat)
        csv_rainpost = os.path.join(
            json['LOCATION'][json['FILE']['RAINPOST_FILE']['LOCATION']],
            json['FILE']['RAINPOST_FILE']['NAME']
        )
        self.otoklimdlg.rainpostfile.setText(csv_rainpost)
        logo = os.path.join(
            json['LOCATION'][json['FILE']['LOGO_FILE']['LOCATION']],
            json['FILE']['LOGO_FILE']['NAME']
        )
        self.otoklimdlg.logofile.setText(logo)
        csv_rainfall = os.path.join(
            json['LOCATION'][json['FILE']['RAINFALL_FILE']['LOCATION']],
            json['FILE']['RAINFALL_FILE']['NAME']
        )
        self.otoklimdlg.rainfallfile.setText(csv_rainfall)
        csv_normalrain = os.path.join(
            json['LOCATION'][json['FILE']['NORMALRAIN_FILE']['LOCATION']],
            json['FILE']['NORMALRAIN_FILE']['NAME']
        )
        self.otoklimdlg.normalrainfile.setText(csv_normalrain)
        map_template = os.path.join(
            json['LOCATION'][json['FILE']['MAP_TEMP']['LOCATION']],
            json['FILE']['MAP_TEMP']['NAME']
        )
        self.otoklimdlg.maptemplate.setText(map_template)
        self.otoklimdlg.projectparamPanel.setEnabled(True)
        self.otoklimdlg.projectparamPanel.show()
        self.otoklimdlg.projectparamPanelAccord.setEnabled(True)
        self.otoklimdlg.projectparamPanelAccord.show()
        self.otoklimdlg.actionSave_As.setEnabled(True)

    def open_existing_project(self):
        """Open existing project """
        open_project = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.otoklim"
        )

        if open_project:
            self.otoklimdlg.province.setWhatsThis('')
            self.otoklimdlg.province.setStyleSheet('color: black')
            self.otoklimdlg.districts.setWhatsThis('')
            self.otoklimdlg.districts.setStyleSheet('color: black')
            self.otoklimdlg.subdistricts.setWhatsThis('')
            self.otoklimdlg.subdistricts.setStyleSheet('color: black')
            self.otoklimdlg.villages.setWhatsThis('')
            self.otoklimdlg.villages.setStyleSheet('color: black')
            self.otoklimdlg.bathymetry.setWhatsThis('')
            self.otoklimdlg.bathymetry.setStyleSheet('color: black')
            self.otoklimdlg.rainpostfile.setWhatsThis('')
            self.otoklimdlg.rainpostfile.setStyleSheet('color: black')
            self.otoklimdlg.logofile.setWhatsThis('')
            self.otoklimdlg.logofile.setStyleSheet('color: black')
            self.otoklimdlg.rainfallfile.setWhatsThis('')
            self.otoklimdlg.rainfallfile.setStyleSheet('color: black')
            self.otoklimdlg.normalrainfile.setWhatsThis('')
            self.otoklimdlg.normalrainfile.setStyleSheet('color: black')
            self.otoklimdlg.maptemplate.setWhatsThis('')
            self.otoklimdlg.maptemplate.setStyleSheet('color: black')
            with open(open_project) as jsonfile:
                otoklim_project = json.load(jsonfile)
            self.read_otoklim_file(otoklim_project)

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

    def select_input_districts(self):
        """Select Cities / Distircts Vector File """
        districts_file = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.shp"
        )
        self.newprojectdlg.Input_districts.setText(districts_file)

    def select_input_subdistricts(self):
        """Select Sub-Districts Vector File """
        subdistricts_file = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.shp"
        )
        self.newprojectdlg.Input_subdistricts.setText(subdistricts_file)

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
            "*.csv"
        )
        self.newprojectdlg.Input_rainfall_class.setText(rainfallclass_file)

    def select_input_normalrain_class(self):
        """Select Normal Rain Classification file"""
        normalrainclass_file = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.csv"
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

    # Project Parameter Edit Function
    def edit_csv_delimiter(self):
        """Edit CSV Delimiter """
        result = self.editdelimiterdlg.exec_()
        csv_delimiter = self.editdelimiterdlg.CSVDelimiter.text()
        if result and csv_delimiter:
            self.otoklimdlg.csvdelimiter.setText(csv_delimiter)
            self.otoklimdlg.csvdelimiter.setWhatsThis('edited')
            self.otoklimdlg.csvdelimiter.setStyleSheet('color: red')

    def edit_province(self):
        """Edit Province Vector File """
        province_file = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.shp"
        )
        if province_file:
            self.otoklimdlg.province.setText(province_file)
            self.otoklimdlg.province.setWhatsThis('edited')
            self.otoklimdlg.province.setStyleSheet('color: red')

    def edit_districts(self):
        """Edit Cities / Distircts Vector File """
        districts_file = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.shp"
        )
        if districts_file:
            self.otoklimdlg.districts.setText(districts_file)
            self.otoklimdlg.districts.setWhatsThis('edited')
            self.otoklimdlg.districts.setStyleSheet('color: red')

    def edit_subdistricts(self):
        """Edit Sub-Districts Vector File """
        subdistricts_file = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.shp"
        )
        if subdistricts_file:
            self.otoklimdlg.subdistricts.setText(subdistricts_file)
            self.otoklimdlg.subdistricts.setWhatsThis('edited')
            self.otoklimdlg.subdistricts.setStyleSheet('color: red')

    def edit_village(self):
        """Edit Village Vector File """
        village_file = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.shp"
        )
        if village_file:
            self.otoklimdlg.villages.setText(village_file)
            self.otoklimdlg.villages.setWhatsThis('edited')
            self.otoklimdlg.villages.setStyleSheet('color: red')

    def edit_bathymetry(self):
        """Edit Bathymetry Raster File """
        bathymetry_file = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.tif"
        )
        if bathymetry_file:
            self.otoklimdlg.bathymetry.setText(bathymetry_file)
            self.otoklimdlg.bathymetry.setWhatsThis('edited')
            self.otoklimdlg.bathymetry.setStyleSheet('color: red')

    def edit_rainpost(self):
        """Edit Rainpost CSV File """
        rainpost_file = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.csv"
        )
        if rainpost_file:
            self.otoklimdlg.rainpostfile.setText(rainpost_file)
            self.otoklimdlg.rainpostfile.setWhatsThis('edited')
            self.otoklimdlg.rainpostfile.setStyleSheet('color: red')

    def edit_logo(self):
        """Edit Logo PNG File """
        logo_file = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.png *.jpg"
        )
        if logo_file:
            self.otoklimdlg.logofile.setText(logo_file)
            self.otoklimdlg.logofile.setWhatsThis('edited')
            self.otoklimdlg.logofile.setStyleSheet('color: red')

    def edit_rainfall_class(self):
        """Edit Rainfall Classification file"""
        rainfallclass_file = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.csv"
        )
        if rainfallclass_file:
            self.otoklimdlg.rainfallfile.setText(rainfallclass_file)
            self.otoklimdlg.rainfallfile.setWhatsThis('edited')
            self.otoklimdlg.rainfallfile.setStyleSheet('color: red')

    def edit_normalrain_class(self):
        """Edit Normal Rain Classification file"""
        normalrainclass_file = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.csv"
        )
        if normalrainclass_file:
            self.otoklimdlg.normalrainfile.setText(normalrainclass_file)
            self.otoklimdlg.normalrainfile.setWhatsThis('edited')
            self.otoklimdlg.normalrainfile.setStyleSheet('color: red')

    def edit_map_template(self):
        """Edit QGIS Map Template file"""
        maptemplate_file = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.qpt"
        )
        if maptemplate_file:
            self.otoklimdlg.maptemplate.setText(maptemplate_file)
            self.otoklimdlg.maptemplate.setWhatsThis('edited')
            self.otoklimdlg.maptemplate.setStyleSheet('color: red')

    # Workspace Show In Folder
    def show_folder(self):
        """Workspace Show In Folder """
        project_workspace = self.otoklimdlg.projectworkspace.text()
        process_var = 'explorer ' + project_workspace
        subprocess.Popen(process_var)

    # Add Vector\Raster Parameter To Canvas
    def add_shapefile_province(self):
        """Add province shapefile layer to canvas"""
        province = self.otoklimdlg.province.text()
        layer = QgsVectorLayer(province, 'Provinsi', 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_shapefile_districts(self):
        """Add city/districts shapefile layer to canvas"""
        districts = self.otoklimdlg.districts.text()
        layer = QgsVectorLayer(districts, 'Kabupaten_Kota', 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_shapefile_subdistricts(self):
        """Add subdistricts shapefile layer to canvas"""
        subdistricts = self.otoklimdlg.subdistricts.text()
        layer = QgsVectorLayer(subdistricts, 'Kecamatan', 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_shapefile_village(self):
        """Add village shapefile layer to canvas"""
        villages = self.otoklimdlg.villages.text()
        layer = QgsVectorLayer(villages, 'Desa', 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_raster_bathymetry(self):
        """Add Raster layer to canvas"""
        raster = self.otoklimdlg.bathymetry.text()
        layer = QgsRasterLayer(raster, 'Bathymetry')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def view_rainpost(self):
        """View Rainpost CSV"""
        rainpostfile = self.otoklimdlg.rainpostfile.text()
        print rainpostfile
        os.system(rainpostfile)

    def view_rainfall_class(self):
        """View Rainfall Classification CSV"""
        rainfallfile = self.otoklimdlg.rainfallfile.text()
        os.system(rainfallfile)

    def view_normalrain_class(self):
        """View Normal Rain Classification CSV"""
        normalrainfile = self.otoklimdlg.normalrainfile.text()
        os.system(normalrainfile)

    # Browse Project Workspace from Save As New Mode
    def select_input_prj_folder_saveas(self):
        """Select Project Working Directory From Save As Mode """
        project_folder = QFileDialog.getExistingDirectory(
            self.saveasprodlg,
            ""
        )
        self.saveasprodlg.ProjectFolder.setText(project_folder)

    def enable_create_button(self):
        """Function to enable Create Project button"""
        input_list = [
            self.newprojectdlg.csv_delimiter.text(),
            self.newprojectdlg.Input_prj_name.text(),
            self.newprojectdlg.Input_prj_file_name.text(),
            self.newprojectdlg.Input_prj_folder.text(),
            self.newprojectdlg.Input_province.text(),
            self.newprojectdlg.Input_districts.text(),
            self.newprojectdlg.Input_subdistricts.text(),
            self.newprojectdlg.Input_village.text(),
            self.newprojectdlg.Input_bathymetry.text(),
            # self.newprojectdlg.Input_islands.text(),
            self.newprojectdlg.Input_rainpost.text(),
            self.newprojectdlg.Input_logo.text(),
            self.newprojectdlg.Input_rainfall_class.text(),
            self.newprojectdlg.Input_normalrain_class.text(),
            self.newprojectdlg.Input_map_template.text()
        ]
        enable_bool = True
        for inputline in input_list:
            if not inputline:
                enable_bool = False
        self.newprojectdlg.ProjectCreate.setEnabled(enable_bool)

    def check_shp(self, file, type):
        """Checking shapefile validation function"""
        if not os.path.exists(file):
            errormessage = 'File is not exist in the path specified: ' + file
            raise Exception(errormessage)
            item = QListWidgetItem(errormessage)
            self.projectprogressdlg.ProgressList.addItem(item)
        layer = QgsVectorLayer(file, str(type), 'ogr')
        fields = layer.pendingFields()
        # CRS must be WGS '84 (ESPG=4326)
        if layer.crs().authid().split(':')[1] != '4326':
            errormessage = 'Data Coordinate Reference System must be WGS 1984 (ESPG=4326)'
            raise Exception(errormessage)
            item = QListWidgetItem(errormessage)  
            self.projectprogressdlg.ProgressList.addItem(item)
        field_names = [field.name() for field in fields]
        field_types = [field.typeName() for field in fields]
        # Field checking
        fieldlist = [
            {'ADM_REGION': 'String'}, {'PROVINSI': 'String'}, {'ID_PROV': 'Real'},
            {'KABUPATEN': 'String'}, {'ID_KAB': 'Real'}, {'KECAMATAN': 'String'},
            {'ID_KEC': 'Real'}, {'DESA': 'String'}, {'ID_DES': 'Real'}
        ]
        if type == 'province':
            checkfield = fieldlist[0:2]
        elif type == 'districts':
            checkfield = fieldlist[0:4]
        elif type == 'subdistricts':
            checkfield = fieldlist[0:6]
        else:
            checkfield = fieldlist
        for field in checkfield:
            if field.keys()[0] not in field_names:
                errormessage = field.keys()[0] + ' field is not exists on data attribute'
                raise Exception(errormessage)
                item = QListWidgetItem(errormessage)
                self.projectprogressdlg.ProgressList.addItem(item)
            else:
                idx = field_names.index(field.keys()[0])
                if field_types[idx] != field.values()[0]:
                    errormessage = field.keys()[0] + ' field type must be ' + field.values()[0] + ' value'
                    raise Exception(errormessage)     
                    item = QListWidgetItem(errormessage)
                    self.projectprogressdlg.ProgressList.addItem(item)

    def check_raster(self, file):
        """Checking raster validation function"""
        # CRS must be WGS '84 (ESPG=4326)
        read_raster = gdal.Open(file, GA_ReadOnly)
        prj = read_raster.GetProjection()
        srs=osr.SpatialReference(wkt=prj)
        if srs.IsProjected:
            espg = srs.GetAttrValue('AUTHORITY', 1)
        if espg != '4326':
            errormessage = 'Data Coordinate Reference System must be WGS 1984 (ESPG=4326)'
            raise Exception(errormessage)           
            item = QListWidgetItem(errormessage)          
            self.projectprogressdlg.ProgressList.addItem(item)

    def check_csv(self, file, delimiter, type):
        """Checking csv validation function"""
        # Check csv file header
        with open(file, 'rb') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=str(delimiter), quotechar='|')
            header = spamreader.next()
            error_field = None
            if type == 'rainpost':
                if 'post_id' not in header:
                    error_field = 'post_id'
                elif 'city_dist' not in header:
                    error_field = 'city_dist'
                elif 'name' not in header:
                    error_field = 'name'
                elif 'lat' not in header:
                    error_field = 'lat'
                elif 'lon' not in header:
                    error_field = 'lon'
            else:
                if 'lower_limit' not in header:
                    error_field = 'lower_limit'
                elif 'upper_limit' not in header:
                    error_field = 'upper_limit'
                elif 'new_value' not in header:
                    error_field = 'new_value'
                elif 'color' not in header:
                    error_field = 'color'
            if error_field:
                errormessage = error_field + ' field not exists on file header'
                raise Exception(errormessage)
                item = QListWidgetItem(errormessage)
                self.projectprogressdlg.ProgressList.addItem(item)
        # Check csv value type
        with open(file, 'rb') as csvfile:
            spamreader = csv.DictReader(csvfile, delimiter=str(delimiter), quotechar='|')
            line = 1
            for row in spamreader:
                line += 1
                if type == 'rainpost':
                    try:
                        int(row['post_id'])
                    except:
                        error_message = ': post_id [' + row['post_id'] + '] value must be integer'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                        item = QListWidgetItem(errormessage)
                        self.projectprogressdlg.ProgressList.addItem(item)
                    try:
                        float(row['lat'])
                    except:
                        error_message = ': lat [' + row['lat'] + '] value must be float'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                        item = QListWidgetItem(errormessage)
                        self.projectprogressdlg.ProgressList.addItem(item)
                    try:
                        float(row['lon'])
                    except:
                        error_message = ': lon [' + row['lon'] + '] value must be float'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                        item = QListWidgetItem(errormessage)
                        self.projectprogressdlg.ProgressList.addItem(item)
                else:
                    try:
                        int(row['lower_limit'])
                    except:
                        if row['lower_limit'] == "*":
                            pass
                        else:
                            error_message = ': lower_limit [' + row['lower_limit'] + '] value must be integer'
                            errormessage = 'error at line: ' + str(line) + error_message
                            raise Exception(errormessage)
                            item = QListWidgetItem(errormessage)
                            self.projectprogressdlg.ProgressList.addItem(item)
                    try:
                        float(row['upper_limit'])
                    except:
                        if row['upper_limit'] == "*":
                            pass
                        else:
                            error_message = ': upper_limit [' + row['upper_limit'] + '] value must be integer'
                            errormessage = 'error at line: ' + str(line) + error_message
                            raise Exception(errormessage)
                            item = QListWidgetItem(errormessage)
                            self.projectprogressdlg.ProgressList.addItem(item)
                    try:
                        float(row['new_value'])
                    except:
                        error_message = ': new_value [' + row['new_value'] + '] value must be integer'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                        item = QListWidgetItem(errormessage)
                        self.projectprogressdlg.ProgressList.addItem(item)
                    # Special case for hex color
                    if len(row['color']) != 7 or row['color'][0] != '#':
                        error_message = ': color [' + row['color'] + '] value must be color hex format'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                        item = QListWidgetItem(errormessage)
                        self.projectprogressdlg.ProgressList.addItem(item)

    def copy_file(self, sourcefile, targetdir, shp):
        """Copy file function"""
        if not os.path.exists(sourcefile):
            errormessage = 'File is not exist in the path specified: ' + sourcefile
            raise Exception(errormessage)
            item = QListWidgetItem(errormessage)
            self.projectprogressdlg.ProgressList.addItem(item)
        if shp:
            rmv_ext = os.path.splitext(sourcefile)[0]
            shp_name = os.path.split(rmv_ext)[-1]
            dir_name = os.path.dirname(rmv_ext)
            extlist = []
            for infile in os.listdir(dir_name):
                if os.path.splitext(infile)[0] == shp_name:
                    ext = os.path.splitext(infile)[1]
                    extlist.append(ext)
            if '.dbf' not in extlist:
                errormessage = '.dbf file not found in shapefile strcuture: ' + sourcefile
                raise Exception(errormessage)
                item = QListWidgetItem(errormessage)
                self.projectprogressdlg.ProgressList.addItem(item)
            if '.shx' not in extlist:
                errormessage = '.shx file not found in shapefile strcuture: ' + sourcefile
                raise Exception(errormessage)
                item = QListWidgetItem(errormessage)
                self.projectprogressdlg.ProgressList.addItem(item)
            for infile in os.listdir(dir_name):
                if os.path.splitext(infile)[0] == shp_name:
                    ext = os.path.splitext(infile)[1]
                    extlist.append(ext)
                    source_file = os.path.join(dir_name, infile)
                    target_file = os.path.join(targetdir, shp_name + ext)
                    shutil.copyfile(source_file, target_file)
        else:
            filename = os.path.basename(sourcefile)
            source_file = sourcefile
            target_file = os.path.join(targetdir, filename)
            shutil.copyfile(source_file, target_file)

    def project_param_accord(self, type):
        """Project Param Panel Accordion Clicked Show/Hide"""
        if self.otoklimdlg.projectparamPanel.isVisible():
            self.otoklimdlg.projectparamPanel.hide()
        else:
            self.otoklimdlg.projectparamPanel.show()

    def save_change(self):
        """Save Edited Parameter"""
        project = os.path.join(
            self.otoklimdlg.projectworkspace.text(),
            self.otoklimdlg.projectfilename.text()
        )
        boundary_directory = os.path.join(self.otoklimdlg.projectworkspace.text(), 'boundary')
        input_directory = os.path.join(self.otoklimdlg.projectworkspace.text(), 'input')
        try:
            change = False
            if self.otoklimdlg.csvdelimiter.whatsThis() == 'edited':
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["FILE"]["CSV_DELIMITER"] = os.path.basename(self.otoklimdlg.csvdelimiter.text())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.csvdelimiter.setStyleSheet('color: black')
                self.otoklimdlg.csvdelimiter.setWhatsThis('')
                change = True
            if self.otoklimdlg.province.whatsThis() == 'edited':
                self.check_shp(self.otoklimdlg.province.text(), 'province')
                self.copy_file(self.otoklimdlg.province.text(), boundary_directory, True)
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["FILE"]["PROV_FILE"]["NAME"] = os.path.basename(self.otoklimdlg.province.text())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.province.setStyleSheet('color: black')
                self.otoklimdlg.province.setWhatsThis('')
                change = True
            if self.otoklimdlg.districts.whatsThis() == 'edited':
                self.check_shp(self.otoklimdlg.districts.text(), 'districts')
                self.copy_file(self.otoklimdlg.districts.text(), boundary_directory, True)
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["FILE"]["CITY_DIST_FILE"]["NAME"] = os.path.basename(self.otoklimdlg.districts.text())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.districts.setStyleSheet('color: black')
                self.otoklimdlg.districts.setWhatsThis('')
                change = True
            if self.otoklimdlg.subdistricts.whatsThis() == 'edited':
                self.check_shp(self.otoklimdlg.subdistricts.text(), 'subdistricts')
                self.copy_file(self.otoklimdlg.subdistricts.text(), boundary_directory, True)
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["FILE"]["SUB_DIST_FILE"]["NAME"] = os.path.basename(self.otoklimdlg.subdistricts.text())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.subdistricts.setStyleSheet('color: black')
                self.otoklimdlg.subdistricts.setWhatsThis('')
                change = True
            if self.otoklimdlg.villages.whatsThis() == 'edited':
                print self.otoklimdlg.villages.whatsThis()
                self.check_shp(self.otoklimdlg.villages.text(), 'villages')
                self.copy_file(self.otoklimdlg.villages.text(), boundary_directory, True)
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["FILE"]["VILLAGE_FILE"]["NAME"] = os.path.basename(self.otoklimdlg.villages.text())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.villages.setStyleSheet('color: black')
                self.otoklimdlg.villages.setWhatsThis('')
                change = True
            if self.otoklimdlg.bathymetry.whatsThis() == 'edited':
                self.check_raster(self.otoklimdlg.bathymetry.text())
                self.copy_file(self.otoklimdlg.bathymetry.text(), boundary_directory, False)
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["FILE"]["BAYTH_FILE"]["NAME"] = os.path.basename(self.otoklimdlg.bathymetry.text())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.bathymetry.setStyleSheet('color: black')
                self.otoklimdlg.bathymetry.setWhatsThis('')
                change = True
            if self.otoklimdlg.rainpostfile.whatsThis() == 'edited':
                self.check_csv(self.otoklimdlg.rainpostfile.text(), self.otoklimdlg.csvdelimiter.text(), 'rainpost')
                self.copy_file(self.otoklimdlg.rainpostfile.text(), input_directory, False)
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["FILE"]["RAINPOST_FILE"]["NAME"] = os.path.basename(self.otoklimdlg.rainpostfile.text())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.rainpostfile.setStyleSheet('color: black')
                self.otoklimdlg.rainpostfile.setWhatsThis('')
                change = True
            if self.otoklimdlg.logofile.whatsThis() == 'edited':
                self.copy_file(self.otoklimdlg.logofile.text(), input_directory, False)
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["FILE"]["LOGO_FILE"]["NAME"] = os.path.basename(self.otoklimdlg.logofile.text())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.logofile.setStyleSheet('color: black')
                self.otoklimdlg.logofile.setWhatsThis('')
                change = True
            if self.otoklimdlg.rainfallfile.whatsThis() == 'edited':
                self.check_csv(self.otoklimdlg.rainfallfile.text(), self.otoklimdlg.csvdelimiter.text(), 'class')
                self.copy_file(self.otoklimdlg.rainfallfile.text(), input_directory, False)
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["FILE"]["RAINFALL_FILE"]["NAME"] = os.path.basename(self.otoklimdlg.rainfallfile.text())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.rainfallfile.setStyleSheet('color: black')
                self.otoklimdlg.rainfallfile.setWhatsThis('')
                change = True
            if self.otoklimdlg.normalrainfile.whatsThis() == 'edited':
                self.check_csv(self.otoklimdlg.normalrainfile.text(), self.otoklimdlg.csvdelimiter.text(), 'class')
                self.copy_file(self.otoklimdlg.normalrainfile.text(), input_directory, False)
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["FILE"]["NORMALRAIN_FILE"]["NAME"] = os.path.basename(self.otoklimdlg.normalrainfile.text())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.normalrainfile.setStyleSheet('color: black')
                self.otoklimdlg.normalrainfile.setWhatsThis('')
                change = True
            if self.otoklimdlg.maptemplate.whatsThis() == 'edited':
                self.copy_file(self.otoklimdlg.maptemplate.text(), input_directory, False)
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["FILE"]["MAP_TEMP"]["NAME"] = os.path.basename(self.otoklimdlg.maptemplate.text())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.maptemplate.setStyleSheet('color: black')
                self.otoklimdlg.maptemplate.setWhatsThis('')
                change = True
            if change:
                self.read_otoklim_file(otoklim_project)
        except Exception as e:
            self.errormessagedlg.ErrorMessage.setText(str(e))
            self.errormessagedlg.exec_()

    def save_as_new(self):
        """Save Existing Project As New Project"""
        result = self.saveasprodlg.exec_()
        if result:
            self.select_project_create(True)
            self.saveasprodlg.ProjectName.clear()
            self.saveasprodlg.ProjectFileName.clear()
            self.saveasprodlg.ProjectFolder.clear()
            self.otoklimdlg.province.setWhatsThis('')
            self.otoklimdlg.province.setStyleSheet('color: black')
            self.otoklimdlg.districts.setWhatsThis('')
            self.otoklimdlg.districts.setStyleSheet('color: black')
            self.otoklimdlg.subdistricts.setWhatsThis('')
            self.otoklimdlg.subdistricts.setStyleSheet('color: black')
            self.otoklimdlg.villages.setWhatsThis('')
            self.otoklimdlg.villages.setStyleSheet('color: black')
            self.otoklimdlg.bathymetry.setWhatsThis('')
            self.otoklimdlg.bathymetry.setStyleSheet('color: black')
            self.otoklimdlg.rainpostfile.setWhatsThis('')
            self.otoklimdlg.rainpostfile.setStyleSheet('color: black')
            self.otoklimdlg.logofile.setWhatsThis('')
            self.otoklimdlg.logofile.setStyleSheet('color: black')
            self.otoklimdlg.rainfallfile.setWhatsThis('')
            self.otoklimdlg.rainfallfile.setStyleSheet('color: black')
            self.otoklimdlg.normalrainfile.setWhatsThis('')
            self.otoklimdlg.normalrainfile.setStyleSheet('color: black')
            self.otoklimdlg.maptemplate.setWhatsThis('')
            self.otoklimdlg.maptemplate.setStyleSheet('color: black')
        else:
            self.saveasprodlg.ProjectName.clear()
            self.saveasprodlg.ProjectFileName.clear()
            self.saveasprodlg.ProjectFolder.clear()

    def select_project_create(self, type):
        """Create Project"""
        # Initialize Project Parameter
        if not type:
            project_directory = self.newprojectdlg.Input_prj_folder.text()
            project_file_name = self.newprojectdlg.Input_prj_file_name.text()
            delimiter = self.newprojectdlg.csv_delimiter.text()
            shp_prov = self.newprojectdlg.Input_province.text()
            shp_dis = self.newprojectdlg.Input_districts.text()
            shp_subdis = self.newprojectdlg.Input_subdistricts.text()
            shp_vil = self.newprojectdlg.Input_village.text()
            raster_bat = self.newprojectdlg.Input_bathymetry.text()
            csv_rainpost = self.newprojectdlg.Input_rainpost.text()
            logo = self.newprojectdlg.Input_logo.text()
            csv_rainfall = self.newprojectdlg.Input_rainfall_class.text()
            csv_normalrain = self.newprojectdlg.Input_normalrain_class.text()
            map_template = self.newprojectdlg.Input_map_template.text()
            project_name = self.newprojectdlg.Input_prj_name.text()
        else:
            project_directory = self.saveasprodlg.ProjectFolder.text()
            project_file_name = self.saveasprodlg.ProjectFileName.text()
            delimiter = self.otoklimdlg.csvdelimiter.text()
            shp_prov = self.otoklimdlg.province.text()
            shp_dis = self.otoklimdlg.districts.text()
            shp_subdis = self.otoklimdlg.subdistricts.text()
            shp_vil = self.otoklimdlg.villages.text()
            raster_bat = self.otoklimdlg.bathymetry.text()
            csv_rainpost = self.otoklimdlg.rainpostfile.text()
            logo = self.otoklimdlg.logofile.text()
            csv_rainfall = self.otoklimdlg.rainfallfile.text()
            csv_normalrain = self.otoklimdlg.normalrainfile.text()
            map_template = self.otoklimdlg.maptemplate.text()
            project_name = self.saveasprodlg.ProjectName.text()
        self.createprojectdlg.project_dir.setText(str(project_directory))
        result = self.createprojectdlg.exec_()
        if result:
            self.projectprogressdlg.ProgressList.clear()
            self.projectprogressdlg.setFocus(True)
            self.projectprogressdlg.show()
            finished = False
            try:
                # Create Project Directory
                message = 'Create Project Folder..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item)
                if not os.path.exists(project_directory):
                    os.mkdir(project_directory)
                else:
                    for file in os.listdir(project_directory):
                        if os.path.splitext(file)[1] == '.otoklim':
                            os.remove(os.path.join(project_directory, file))
                def replace_confirm(file):
                    if os.path.exists(file):
                        self.dirconfirmdlg.existingPath.setText(str(file))
                        result = self.dirconfirmdlg.exec_()
                        if result:
                            shutil.rmtree(file)
                            os.mkdir(file)
                        else:
                            errormessage = 'project directory has to be changed'
                            raise Exception(errormessage)
                            item = QListWidgetItem(errormessage)
                            self.projectprogressdlg.ProgressList.addItem(item)
                    else:
                        os.mkdir(file)
                item.setText(message + ' Done')
                self.projectprogressdlg.ProgressList.addItem(item)
                # Create Root Project Directory
                message = 'Create Root Project Folder..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item)
                # Processing Folder
                processing_directory = os.path.join(project_directory, 'processing')
                replace_confirm(processing_directory)
                # Boundary Folder
                boundary_directory = os.path.join(project_directory, 'boundary')
                replace_confirm(boundary_directory)
                # Input Folder
                input_directory = os.path.join(project_directory, 'input')
                replace_confirm(input_directory)
                # Output Folder
                output_directory = os.path.join(project_directory, 'output')
                replace_confirm(output_directory)
                # Map & CSV Folder
                map_directory = os.path.join(output_directory, 'map')
                csv_directory = os.path.join(output_directory, 'csv')
                replace_confirm(map_directory)
                replace_confirm(csv_directory)
                # Copy Province Shapefiles
                message = 'Checking Province Files..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item)
                self.check_shp(shp_prov, 'province')
                self.copy_file(shp_prov, boundary_directory, True)
                item.setText(message + ' Done')
                self.projectprogressdlg.ProgressList.addItem(item)
                # Copy Cities\Districts Shapefiles
                message = 'Checking Cities/Districts Files..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item)
                self.check_shp(shp_dis, 'districts')
                self.copy_file(shp_dis, boundary_directory, True)
                item.setText(message + ' Done')
                self.projectprogressdlg.ProgressList.addItem(item)
                # Copy Sub-Districts Shapefiles
                message = 'Checking Sub-Districts Files..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item)
                self.check_shp(shp_subdis, 'subdistricts')
                self.copy_file(shp_subdis, boundary_directory, True)
                item.setText(message + ' Done')
                self.projectprogressdlg.ProgressList.addItem(item)
                # Copy Villages Shapefiles
                message = 'Checking Villages Files..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item) 
                self.check_shp(shp_vil, 'villages')
                self.copy_file(shp_vil, boundary_directory, True)
                item.setText(message + ' Done')
                self.projectprogressdlg.ProgressList.addItem(item)
                # Copy Bathymetry Raster File
                message = 'Checking Bathymetry Files..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item)
                self.check_raster(raster_bat)
                self.copy_file(raster_bat, boundary_directory, False)
                item.setText(message + ' Done')
                self.projectprogressdlg.ProgressList.addItem(item)
                # Copy Rainpost CSV File
                message = 'Checking Rainpost Files..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item)
                self.check_csv(csv_rainpost, delimiter, 'rainpost')
                self.copy_file(csv_rainpost, input_directory, False)
                item.setText(message + ' Done')
                self.projectprogressdlg.ProgressList.addItem(item)
                # Copy Logo File
                message = 'Checking Logo Files..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item)
                self.copy_file(logo, input_directory, False)
                item.setText(message + ' Done')
                self.projectprogressdlg.ProgressList.addItem(item)
                # Copy Rainfall Classification File
                message = 'Checking Rainfall Classification Files..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item)
                self.check_csv(csv_rainfall, delimiter, 'class')
                self.copy_file(csv_rainfall, input_directory, False)
                item.setText(message + ' Done')
                self.projectprogressdlg.ProgressList.addItem(item)
                # Copy Normal Rain Classification File
                message = 'Checking Normal Rain Classification Files..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item)
                self.check_csv(csv_normalrain, delimiter, 'class')
                self.copy_file(csv_normalrain, input_directory, False)
                item.setText(message + ' Done')
                self.projectprogressdlg.ProgressList.addItem(item)
                # Copy Map Template File
                message = 'Checking QGIS Map Template Files..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item)
                self.copy_file(map_template, input_directory, False)
                item.setText(message + ' Done')
                self.projectprogressdlg.ProgressList.addItem(item)
                # Create Project JSON File
                message = 'Create Project File..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item)
                project_meta = {
                    "PRJ_NAME": project_name,
                    "LOCATION": {
                        "PRJ_FILE_LOC": project_directory,
                        "BDR_FILE_LOC": boundary_directory,
                        "IN_FILE_LOC": input_directory,
                        "OUT_FILE_LOC": output_directory,
                        "MAP_FILE_LOC": map_directory,
                        "CSV_FILE_LOC": csv_directory,
                        "PRC_FILE_LOC": processing_directory,
                    },
                    "FILE": {
                        "CSV_DELIMITER": delimiter,
                        "PRJ_FILE": {
                            "NAME": project_file_name + '.otoklim',
                            "LOCATION": "PRJ_FILE_LOC",
                            "FORMAT": "OTOKLIM",
                        },
                        "PROV_FILE": {
                            "NAME": os.path.basename(shp_prov),
                            "LOCATION": "BDR_FILE_LOC",
                            "FORMAT": "SHP",
                        },
                        "CITY_DIST_FILE": {
                            "NAME": os.path.basename(shp_dis),
                            "LOCATION": "BDR_FILE_LOC",
                            "FORMAT": "SHP"
                        },
                        "SUB_DIST_FILE": {
                            "NAME": os.path.basename(shp_subdis),
                            "LOCATION": "BDR_FILE_LOC",
                            "FORMAT": "SHP"
                        },
                        "VILLAGE_FILE": {
                            "NAME": os.path.basename(shp_vil),
                            "LOCATION": "BDR_FILE_LOC",
                            "FORMAT": "SHP"
                        },
                        "BAYTH_FILE": {
                            "NAME": os.path.basename(raster_bat),
                            "LOCATION": "BDR_FILE_LOC",
                            "FORMAT": "TIF",
                        },
                        "RAINPOST_FILE": {
                            "NAME": os.path.basename(csv_rainpost),
                            "LOCATION": "IN_FILE_LOC",
                            "FORMAT": "CSV",
                        },
                        "LOGO_FILE": {
                            "NAME": os.path.basename(logo),
                            "LOCATION": "IN_FILE_LOC",
                            "FORMAT": "PNG/JPG",
                        },
                        "RAINFALL_FILE": {
                            "NAME": os.path.basename(csv_rainfall),
                            "LOCATION": "IN_FILE_LOC",
                            "FORMAT": "CSV",
                        },
                        "NORMALRAIN_FILE": {
                            "NAME": os.path.basename(csv_normalrain),
                            "LOCATION": "IN_FILE_LOC",
                            "FORMAT": "CSV",
                        },
                        "MAP_TEMP": {
                            "NAME": os.path.basename(map_template),
                            "LOCATION": "IN_FILE_LOC",
                            "FORMAT": "QPT",
                        },
                    }
                }
                otoklim_file = os.path.join(
                    project_meta['LOCATION']['PRJ_FILE_LOC'],
                    project_meta['FILE']['PRJ_FILE']['NAME']
                )
                # Write Project File (.otoklim)
                with open(otoklim_file, 'w') as outfile:
                    json.dump(project_meta, outfile, indent=4)
                item.setText(message + ' Done')
                self.projectprogressdlg.ProgressList.addItem(item)
                finished = True
            except Exception as errormessage:
                item.setText(message + ' Error')
                self.projectprogressdlg.ProgressList.addItem(item)
                item = QListWidgetItem(str(errormessage))
                self.projectprogressdlg.ProgressList.addItem(item)
                print errormessage
            # Clear if progress dialog closed
            if not self.projectprogressdlg.exec_():
                self.projectprogressdlg.ProgressList.clear()
                # Open recent created project
                if finished:
                    self.newprojectdlg.close()
                    with open(otoklim_file) as jsonfile:
                        otoklim_project = json.load(jsonfile)
                    self.read_otoklim_file(otoklim_project)

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
