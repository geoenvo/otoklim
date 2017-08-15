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
from PyQt4.QtCore import Qt, QSettings, QTranslator, qVersion, QCoreApplication
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
    ErrorMessageDialog,
    SaveConfrimDialog,
    ReplaceConfrimDialog
)
from qgis.core import (
    QgsVectorLayer,
    QgsRasterLayer,
    QgsMapLayerRegistry,
    QgsFeatureRequest,
    QgsExpression,
    QgsVectorFileWriter
)
from osgeo import gdal, ogr, osr
from gdalconst import GA_ReadOnly
import os.path
import os
import shutil
import csv
import json
import subprocess
import datetime
import processing
import csv


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
        self.saveconfirmdlg = SaveConfrimDialog()
        self.replaceconfirmdlg = ReplaceConfrimDialog() 

        # Default Main Window
        self.otoklimdlg.actionSave_As.setEnabled(False)
        self.otoklimdlg.projectparamPanel.setEnabled(False)
        self.otoklimdlg.projectparamPanel.hide()
        self.otoklimdlg.projectparamPanelAccord.setEnabled(False)
        self.otoklimdlg.projectparamPanelAccord.hide()
        self.otoklimdlg.idwinterpolationPanel.setEnabled(False)
        self.otoklimdlg.idwinterpolationPanel.hide()
        self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(False)
        self.otoklimdlg.idwinterpolationPanelAccord.hide()
        self.otoklimdlg.classificationPanel.hide()
        self.otoklimdlg.classificationPanelAccord.setEnabled(False)
        self.otoklimdlg.classificationPanelAccord.hide()
        self.otoklimdlg.generatemapPanel.setEnabled(False)
        self.otoklimdlg.generatemapPanel.hide()
        self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
        self.otoklimdlg.generatemapPanelAccord.hide()
        self.otoklimdlg.generatecsvPanel.hide()
        self.otoklimdlg.generatecsvPanelAccord.setEnabled(False)
        self.otoklimdlg.generatecsvPanelAccord.hide()

        # Add Menu Trigger Logic
        self.otoklimdlg.actionNew.triggered.connect(self.ask_project_name)
        self.otoklimdlg.actionOpen.triggered.connect(self.open_existing_project)
        self.otoklimdlg.actionSave.triggered.connect(self.save_change)
        self.otoklimdlg.actionSave_As.triggered.connect(self.save_as_new)
        self.otoklimdlg.actionExit.triggered.connect(self.otoklimdlg.close)

        # Add Panel Accordion Button Logic
        self.otoklimdlg.projectparamPanelAccord.clicked.connect(self.project_param_accord)
        self.otoklimdlg.idwinterpolationPanelAccord.clicked.connect(self.idw_interpolation_accord)
        self.otoklimdlg.classificationPanelAccord.clicked.connect(self.classification_accord)
        self.otoklimdlg.generatemapPanelAccord.clicked.connect(self.generate_map_accord)
        self.otoklimdlg.generatecsvPanelAccord.clicked.connect(self.generate_csv_accord)

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
        self.otoklimdlg.View_Value_CSV.clicked.connect(
            self.view_value_csv
        )

        # Add Save As Project Workspace Trigger Logic
        self.saveasprodlg.Browse_prj_folder.clicked.connect(
            self.select_input_prj_folder_saveas
        )

        # Add Input Value IDW Trigger Logic
        self.otoklimdlg.Browse_Value_CSV.clicked.connect(
            self.select_input_value_csv
        )
        self.otoklimdlg.Input_Value_CSV.clear()
        self.otoklimdlg.Input_Value_CSV.textChanged.connect(
            self.enable_test_parameter_button
        )
        self.otoklimdlg.Input_Value_CSV.textChanged.connect(
            self.input_value_csv_edited
        )

        # Add Year Enable Logic
        self.otoklimdlg.Select_Year.textChanged.connect(
            self.enable_test_parameter_button
        )
        self.otoklimdlg.Select_Year.textChanged.connect(
            self.year_now_edited
        )

        # Add Province and Month Edited Trigger
        self.otoklimdlg.Select_Province.currentIndexChanged.connect(
            self.province_edited
        )
        self.otoklimdlg.Select_Month.currentIndexChanged.connect(
            self.month_edited
        )

        # Add Select All Chcekbox
        self.otoklimdlg.check_all.stateChanged.connect(
            self.select_all_type
        )
        self.otoklimdlg.check_all_class.stateChanged.connect(
            self.select_all_type
        )
        self.otoklimdlg.check_all_map.stateChanged.connect(
            self.select_all_type
        )
        self.otoklimdlg.check_all_csv.stateChanged.connect(
            self.select_all_type
        )

        # Add Interpolate Trigger Logic
        self.otoklimdlg.testParameter.clicked.connect(
            self.pra_interpolate
        )
        self.otoklimdlg.interpolateButton.clicked.connect(
            self.interpolate_idw
        )

        # Add Raster Interpolated Logic
        self.otoklimdlg.addach_1.clicked.connect(
            self.add_ach_1
        )
        self.otoklimdlg.addash_1.clicked.connect(
            self.add_ash_1
        )
        self.otoklimdlg.addpch_1.clicked.connect(
            self.add_pch_1
        )
        self.otoklimdlg.addpsh_1.clicked.connect(
            self.add_psh_1
        )
        self.otoklimdlg.addpch_2.clicked.connect(
            self.add_pch_2
        )
        self.otoklimdlg.addpsh_2.clicked.connect(
            self.add_psh_2
        )
        self.otoklimdlg.addpch_3.clicked.connect(
            self.add_pch_3
        )
        self.otoklimdlg.addpsh_3.clicked.connect(
            self.add_psh_3
        )

        # Add Classification Trigger Logic
        self.otoklimdlg.classifyButton.clicked.connect(
            self.raster_classify
        )

        # Add Raster Classified Logic
        self.otoklimdlg.addach_1_class.clicked.connect(
            self.add_ach_1_class
        )
        self.otoklimdlg.addash_1_class.clicked.connect(
            self.add_ash_1_class
        )
        self.otoklimdlg.addpch_1_class.clicked.connect(
            self.add_pch_1_class
        )
        self.otoklimdlg.addpsh_1_class.clicked.connect(
            self.add_psh_1_class
        )
        self.otoklimdlg.addpch_2_class.clicked.connect(
            self.add_pch_2_class
        )
        self.otoklimdlg.addpsh_2_class.clicked.connect(
            self.add_psh_2_class
        )
        self.otoklimdlg.addpch_3_class.clicked.connect(
            self.add_pch_3_class
        )
        self.otoklimdlg.addpsh_3_class.clicked.connect(
            self.add_psh_3_class
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
            self.otoklimdlg.hide()
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
        # Special case for province
        self.otoklimdlg.Select_Province.clear()
        layer = QgsVectorLayer(self.otoklimdlg.province.text(), 'Provinsi', 'ogr')
        provinsi_list = []
        for field in layer.getFeatures():
            provinsi_list.append(field['PROVINSI'])
        self.otoklimdlg.Select_Province.addItems(provinsi_list)
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
        try:
            value_csv = os.path.join(
                json['LOCATION'][json['PROCESSING']['IDW_INTERPOLATION']['INPUT_VALUE_FILE']['LOCATION']],
                json['PROCESSING']['IDW_INTERPOLATION']['INPUT_VALUE_FILE']['NAME']
            )
        except:
            value_csv = ""
        self.otoklimdlg.Input_Value_CSV.setText(value_csv)
        province_id = json['PROCESSING']['IDW_INTERPOLATION']['ID_PROV']
        layer = QgsVectorLayer(self.otoklimdlg.province.text(), 'Provinsi', 'ogr')
        for value in layer.getFeatures():
            if str(value['ID_PROV']) == province_id:
                index = self.otoklimdlg.Select_Province.findText(str(value['PROVINSI']), Qt.MatchFixedString)
                self.otoklimdlg.Select_Province.setCurrentIndex(index)
        month = json['PROCESSING']['IDW_INTERPOLATION']['THIS_MONTH']
        index = self.otoklimdlg.Select_Month.findText(str(month), Qt.MatchFixedString)
        self.otoklimdlg.Select_Month.setCurrentIndex(index)
        year = json['PROCESSING']['IDW_INTERPOLATION']['THIS_YEAR']
        self.otoklimdlg.Select_Year.setText(year)
        idw_interpolate_prc = json['PROCESSING']['IDW_INTERPOLATION']['PROCESSED']
        if idw_interpolate_prc:
            self.otoklimdlg.classificationPanelAccord.setEnabled(True)
            self.otoklimdlg.groupBox_3.setEnabled(True)
            self.otoklimdlg.interpolateButton.setEnabled(True)
            ach_1 = json['PROCESSING']['IDW_INTERPOLATION']['RASTER_ACH_1']["NAME"]
            if ach_1:
                self.otoklimdlg.ach_1.setEnabled(True)
                self.otoklimdlg.ach_1.setChecked(True)
                self.otoklimdlg.addach_1.setEnabled(True)
                self.otoklimdlg.addach_1.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['IDW_INTERPOLATION']['RASTER_ACH_1']['LOCATION']], ach_1)
                )
            ash_1 = json['PROCESSING']['IDW_INTERPOLATION']['RASTER_ASH_1']["NAME"]
            if ash_1:
                self.otoklimdlg.ash_1.setEnabled(True)
                self.otoklimdlg.ash_1.setChecked(True)
                self.otoklimdlg.addash_1.setEnabled(True)
                self.otoklimdlg.addash_1.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['IDW_INTERPOLATION']['RASTER_ASH_1']['LOCATION']], ash_1)
                )
            pch_1 = json['PROCESSING']['IDW_INTERPOLATION']['RASTER_PCH_1']["NAME"]
            if pch_1:
                self.otoklimdlg.pch_1.setEnabled(True)
                self.otoklimdlg.pch_1.setChecked(True)
                self.otoklimdlg.addpch_1.setEnabled(True)
                self.otoklimdlg.addpch_1.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['IDW_INTERPOLATION']['RASTER_PCH_1']['LOCATION']], pch_1)
                )
            psh_1 = json['PROCESSING']['IDW_INTERPOLATION']['RASTER_PSH_1']["NAME"]
            if psh_1:
                self.otoklimdlg.psh_1.setEnabled(True)
                self.otoklimdlg.psh_1.setChecked(True)
                self.otoklimdlg.addpsh_1.setEnabled(True)
                self.otoklimdlg.addpsh_1.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['IDW_INTERPOLATION']['RASTER_PSH_1']['LOCATION']], psh_1)
                )
            pch_2 = json['PROCESSING']['IDW_INTERPOLATION']['RASTER_PCH_2']["NAME"]
            if pch_2:
                self.otoklimdlg.pch_2.setEnabled(True)
                self.otoklimdlg.pch_2.setChecked(True)
                self.otoklimdlg.addpch_2.setEnabled(True)
                self.otoklimdlg.addpch_2.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['IDW_INTERPOLATION']['RASTER_PCH_2']['LOCATION']], pch_2)
                )
            psh_2 = json['PROCESSING']['IDW_INTERPOLATION']['RASTER_PSH_2']["NAME"]
            if psh_2:
                self.otoklimdlg.psh_2.setEnabled(True)
                self.otoklimdlg.psh_2.setChecked(True)
                self.otoklimdlg.addpsh_2.setEnabled(True)
                self.otoklimdlg.addpsh_2.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['IDW_INTERPOLATION']['RASTER_PSH_2']['LOCATION']], psh_2)
                )
            pch_3 = json['PROCESSING']['IDW_INTERPOLATION']['RASTER_PCH_3']["NAME"]
            if pch_3:
                self.otoklimdlg.pch_3.setEnabled(True)
                self.otoklimdlg.pch_3.setChecked(True)
                self.otoklimdlg.addpch_3.setEnabled(True)
                self.otoklimdlg.addpch_3.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['IDW_INTERPOLATION']['RASTER_PCH_3']['LOCATION']], pch_3)
                )
            psh_3 = json['PROCESSING']['IDW_INTERPOLATION']['RASTER_PSH_3']["NAME"]
            if psh_3:
                self.otoklimdlg.psh_3.setEnabled(True)
                self.otoklimdlg.psh_3.setChecked(True)
                self.otoklimdlg.addpsh_3.setEnabled(True)
                self.otoklimdlg.addpsh_3.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['IDW_INTERPOLATION']['RASTER_PSH_3']['LOCATION']], psh_3)
                )
        classification_prc = json['PROCESSING']['CLASSIFICATION']['PROCESSED']
        if classification_prc:
            self.otoklimdlg.generatemapPanelAccord.setEnabled(True)
            self.otoklimdlg.classificationPanel.show()
            self.otoklimdlg.classifyButton.setEnabled(True)
            ach_1 = json['PROCESSING']['CLASSIFICATION']['RASTER_ACH_1']["NAME"]
            if ach_1:
                self.otoklimdlg.ach_1_class.setEnabled(True)
                self.otoklimdlg.ach_1_class.setChecked(True)
                self.otoklimdlg.addach_1_class.setEnabled(True)
                self.otoklimdlg.addach_1_class.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['CLASSIFICATION']['RASTER_ACH_1']['LOCATION']], ach_1)
                )
            ash_1 = json['PROCESSING']['CLASSIFICATION']['RASTER_ASH_1']["NAME"]
            if ash_1:
                self.otoklimdlg.ash_1_class.setEnabled(True)
                self.otoklimdlg.ash_1_class.setChecked(True)
                self.otoklimdlg.addash_1_class.setEnabled(True)
                self.otoklimdlg.addash_1_class.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['CLASSIFICATION']['RASTER_ASH_1']['LOCATION']], ash_1)
                )
            pch_1 = json['PROCESSING']['CLASSIFICATION']['RASTER_PCH_1']["NAME"]
            if pch_1:
                self.otoklimdlg.pch_1_class.setEnabled(True)
                self.otoklimdlg.pch_1_class.setChecked(True)
                self.otoklimdlg.addpch_1_class.setEnabled(True)
                self.otoklimdlg.addpch_1_class.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['CLASSIFICATION']['RASTER_PCH_1']['LOCATION']], pch_1)
                )
            psh_1 = json['PROCESSING']['CLASSIFICATION']['RASTER_PSH_1']["NAME"]
            if psh_1:
                self.otoklimdlg.psh_1_class.setEnabled(True)
                self.otoklimdlg.psh_1_class.setChecked(True)
                self.otoklimdlg.addpsh_1_class.setEnabled(True)
                self.otoklimdlg.addpsh_1_class.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['CLASSIFICATION']['RASTER_PSH_1']['LOCATION']], psh_1)
                )
            pch_2 = json['PROCESSING']['CLASSIFICATION']['RASTER_PCH_2']["NAME"]
            if pch_2:
                self.otoklimdlg.pch_2_class.setEnabled(True)
                self.otoklimdlg.pch_2_class.setChecked(True)
                self.otoklimdlg.addpch_2_class.setEnabled(True)
                self.otoklimdlg.addpch_2_class.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['CLASSIFICATION']['RASTER_PCH_2']['LOCATION']], pch_2)
                )
            psh_2 = json['PROCESSING']['CLASSIFICATION']['RASTER_PSH_2']["NAME"]
            if psh_2:
                self.otoklimdlg.psh_2_class.setEnabled(True)
                self.otoklimdlg.psh_2_class.setChecked(True)
                self.otoklimdlg.addpsh_2_class.setEnabled(True)
                self.otoklimdlg.addpsh_2_class.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['CLASSIFICATION']['RASTER_PSH_2']['LOCATION']], psh_2)
                )
            pch_3 = json['PROCESSING']['CLASSIFICATION']['RASTER_PCH_3']["NAME"]
            if pch_3:
                self.otoklimdlg.pch_3_class.setEnabled(True)
                self.otoklimdlg.pch_3_class.setChecked(True)
                self.otoklimdlg.addpch_3_class.setEnabled(True)
                self.otoklimdlg.addpch_3_class.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['CLASSIFICATION']['RASTER_PCH_3']['LOCATION']], pch_3)
                )
            psh_3 = json['PROCESSING']['CLASSIFICATION']['RASTER_PSH_3']["NAME"]
            if psh_3:
                self.otoklimdlg.psh_3_class.setEnabled(True)
                self.otoklimdlg.psh_3_class.setChecked(True)
                self.otoklimdlg.addpsh_3_class.setEnabled(True)
                self.otoklimdlg.addpsh_3_class.setWhatsThis(
                    os.path.join(json['LOCATION'][json['PROCESSING']['CLASSIFICATION']['RASTER_PSH_3']['LOCATION']], psh_3)
                )

        self.otoklimdlg.Input_Value_CSV.setWhatsThis('')
        self.otoklimdlg.Select_Province.setWhatsThis('')
        self.otoklimdlg.Select_Month.setWhatsThis('')
        self.otoklimdlg.Select_Year.setWhatsThis('')

        self.otoklimdlg.projectparamPanel.setEnabled(True)
        self.otoklimdlg.projectparamPanel.show()
        self.otoklimdlg.projectparamPanelAccord.setEnabled(True)
        self.otoklimdlg.projectparamPanelAccord.show()

        self.otoklimdlg.idwinterpolationPanel.setEnabled(True)
        self.otoklimdlg.idwinterpolationPanel.show()
        self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(True)
        self.otoklimdlg.idwinterpolationPanelAccord.show()

        self.otoklimdlg.classificationPanelAccord.show()
        self.otoklimdlg.generatemapPanelAccord.show()
        self.otoklimdlg.generatecsvPanelAccord.show()
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
            self.otoklimdlg.Input_Value_CSV.setWhatsThis('')
            self.otoklimdlg.Select_Province.setWhatsThis('')
            self.otoklimdlg.Select_Month.setWhatsThis('')
            self.otoklimdlg.Select_Year.setWhatsThis('')
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
            self.otoklimdlg.idwinterpolationPanel.setEnabled(False)
            self.otoklimdlg.idwinterpolationPanel.hide()
            self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(False)

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
            self.otoklimdlg.idwinterpolationPanel.setEnabled(False)
            self.otoklimdlg.idwinterpolationPanel.hide()
            self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(False)

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
            self.otoklimdlg.idwinterpolationPanel.setEnabled(False)
            self.otoklimdlg.idwinterpolationPanel.hide()
            self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(False)

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
            self.otoklimdlg.idwinterpolationPanel.setEnabled(False)
            self.otoklimdlg.idwinterpolationPanel.hide()
            self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(False)

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
            self.otoklimdlg.idwinterpolationPanel.setEnabled(False)
            self.otoklimdlg.idwinterpolationPanel.hide()
            self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(False)

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
            self.otoklimdlg.idwinterpolationPanel.setEnabled(False)
            self.otoklimdlg.idwinterpolationPanel.hide()
            self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(False)

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
            self.otoklimdlg.idwinterpolationPanel.setEnabled(False)
            self.otoklimdlg.idwinterpolationPanel.hide()
            self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(False)

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
            self.otoklimdlg.idwinterpolationPanel.setEnabled(False)
            self.otoklimdlg.idwinterpolationPanel.hide()
            self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(False)

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
            self.otoklimdlg.idwinterpolationPanel.setEnabled(False)
            self.otoklimdlg.idwinterpolationPanel.hide()
            self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(False)

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
            self.otoklimdlg.idwinterpolationPanel.setEnabled(False)
            self.otoklimdlg.idwinterpolationPanel.hide()
            self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(False)

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
            self.otoklimdlg.idwinterpolationPanel.setEnabled(False)
            self.otoklimdlg.idwinterpolationPanel.hide()
            self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(False)

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
        os.system(rainpostfile)

    def view_rainfall_class(self):
        """View Rainfall Classification CSV"""
        rainfallfile = self.otoklimdlg.rainfallfile.text()
        os.system(rainfallfile)

    def view_normalrain_class(self):
        """View Normal Rain Classification CSV"""
        normalrainfile = self.otoklimdlg.normalrainfile.text()
        os.system(normalrainfile)

    def view_value_csv(self):
        """View Input Value CSV"""
        valuecsv = self.otoklimdlg.Input_Value_CSV.text()
        os.system(valuecsv)

    # Add Raster Interpolated To Canvas
    def add_ach_1(self):
        """Add ACH 1"""
        raster = self.otoklimdlg.addach_1.whatsThis()
        layer = QgsRasterLayer(raster, 'ach1')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_ash_1(self):
        """Add ASH 1"""
        raster = self.otoklimdlg.addash_1.whatsThis()
        layer = QgsRasterLayer(raster, 'ash1')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_pch_1(self):
        """Add PCH 1"""
        raster = self.otoklimdlg.addpch_1.whatsThis()
        layer = QgsRasterLayer(raster, 'pch1')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_psh_1(self):
        """Add PSH 1"""
        raster = self.otoklimdlg.addpsh_1.whatsThis()
        layer = QgsRasterLayer(raster, 'psh1')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_pch_2(self):
        """Add PCH 2"""
        raster = self.otoklimdlg.addpch_2.whatsThis()
        layer = QgsRasterLayer(raster, 'pch2')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_psh_2(self):
        """Add PSH 2"""
        raster = self.otoklimdlg.addpsh_2.whatsThis()
        layer = QgsRasterLayer(raster, 'psh2')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_pch_3(self):
        """Add PCH 3"""
        raster = self.otoklimdlg.addpch_3.whatsThis()
        layer = QgsRasterLayer(raster, 'pch3')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_psh_3(self):
        """Add PSH 3"""
        raster = self.otoklimdlg.addpsh_3.whatsThis()
        layer = QgsRasterLayer(raster, 'psh3')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    # Add Raster Classified To Canvas
    def add_ach_1_class(self):
        """Add ACH 1 Classified"""
        raster = self.otoklimdlg.addach_1_class.whatsThis()
        layer = QgsRasterLayer(raster, 'ach1')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_ash_1_class(self):
        """Add ASH 1 Classified"""
        raster = self.otoklimdlg.addash_1_class.whatsThis()
        layer = QgsRasterLayer(raster, 'ash1')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_pch_1_class(self):
        """Add PCH 1 Classified"""
        raster = self.otoklimdlg.addpch_1_class.whatsThis()
        layer = QgsRasterLayer(raster, 'pch1')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_psh_1_class(self):
        """Add PSH 1 Classified"""
        raster = self.otoklimdlg.addpsh_1_class.whatsThis()
        layer = QgsRasterLayer(raster, 'psh1')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_pch_2_class(self):
        """Add PCH 2 Classified"""
        raster = self.otoklimdlg.addpch_2_class.whatsThis()
        layer = QgsRasterLayer(raster, 'pch2')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_psh_2_class(self):
        """Add PSH 2 Classified"""
        raster = self.otoklimdlg.addpsh_2_class.whatsThis()
        layer = QgsRasterLayer(raster, 'psh2')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_pch_3_class(self):
        """Add PCH 3 Classified"""
        raster = self.otoklimdlg.addpch_3_class.whatsThis()
        layer = QgsRasterLayer(raster, 'pch3')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_psh_3_class(self):
        """Add PSH 3 Classified"""
        raster = self.otoklimdlg.addpsh_3_class.whatsThis()
        layer = QgsRasterLayer(raster, 'psh3')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    # Browse Project Workspace from Save As New Mode
    def select_input_prj_folder_saveas(self):
        """Select Project Working Directory From Save As Mode """
        project_folder = QFileDialog.getExistingDirectory(
            self.saveasprodlg,
            ""
        )
        self.saveasprodlg.ProjectFolder.setText(project_folder)

    # Browse Input Value CSV
    def select_input_value_csv(self):
        """Select Input Value in CSV Format and Validate it """
        input_value = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.csv"
        )
        self.otoklimdlg.Input_Value_CSV.setText(input_value)
        self.otoklimdlg.Input_Value_CSV.setWhatsThis('edited')

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

    def enable_test_parameter_button(self):
        """Funtion to enable Test Parameter Button"""
        input_list = [
            self.otoklimdlg.Input_Value_CSV.text(),
            self.otoklimdlg.Select_Year.text()
        ]
        enable_bool = True
        for inputline in input_list:
            if not inputline:
                enable_bool = False
        self.otoklimdlg.testParameter.setEnabled(enable_bool)

    def input_value_csv_edited(self):
        """Function to set input value as edited"""
        self.otoklimdlg.Input_Value_CSV.setWhatsThis('edited')
        self.otoklimdlg.groupBox_3.setEnabled(False)
        self.otoklimdlg.ach_1.setChecked(False)
        self.otoklimdlg.ash_1.setChecked(False)
        self.otoklimdlg.pch_1.setChecked(False)
        self.otoklimdlg.psh_1.setChecked(False)
        self.otoklimdlg.pch_2.setChecked(False)
        self.otoklimdlg.psh_2.setChecked(False)
        self.otoklimdlg.pch_3.setChecked(False)
        self.otoklimdlg.psh_3.setChecked(False)
        self.otoklimdlg.addach_1.setEnabled(False)
        self.otoklimdlg.addash_1.setEnabled(False)
        self.otoklimdlg.addpch_1.setEnabled(False)
        self.otoklimdlg.addpsh_1.setEnabled(False)
        self.otoklimdlg.addpch_2.setEnabled(False)
        self.otoklimdlg.addpsh_2.setEnabled(False)
        self.otoklimdlg.addpch_3.setEnabled(False)
        self.otoklimdlg.addpsh_3.setEnabled(False)

    def year_now_edited(self):
        """Function to set year nor as edited"""
        self.otoklimdlg.Select_Year.setWhatsThis('edited')
        self.otoklimdlg.groupBox_3.setEnabled(False)
        self.otoklimdlg.ach_1.setChecked(False)
        self.otoklimdlg.ash_1.setChecked(False)
        self.otoklimdlg.pch_1.setChecked(False)
        self.otoklimdlg.psh_1.setChecked(False)
        self.otoklimdlg.pch_2.setChecked(False)
        self.otoklimdlg.psh_2.setChecked(False)
        self.otoklimdlg.pch_3.setChecked(False)
        self.otoklimdlg.psh_3.setChecked(False)
        self.otoklimdlg.addach_1.setEnabled(False)
        self.otoklimdlg.addash_1.setEnabled(False)
        self.otoklimdlg.addpch_1.setEnabled(False)
        self.otoklimdlg.addpsh_1.setEnabled(False)
        self.otoklimdlg.addpch_2.setEnabled(False)
        self.otoklimdlg.addpsh_2.setEnabled(False)
        self.otoklimdlg.addpch_3.setEnabled(False)
        self.otoklimdlg.addpsh_3.setEnabled(False)

    def province_edited(self):
        """Function to set province edited"""
        self.otoklimdlg.Select_Province.setWhatsThis('edited')
        self.otoklimdlg.groupBox_3.setEnabled(False)
        self.otoklimdlg.testParameter.setEnabled(True)
        self.otoklimdlg.ach_1.setChecked(False)
        self.otoklimdlg.ash_1.setChecked(False)
        self.otoklimdlg.pch_1.setChecked(False)
        self.otoklimdlg.psh_1.setChecked(False)
        self.otoklimdlg.pch_2.setChecked(False)
        self.otoklimdlg.psh_2.setChecked(False)
        self.otoklimdlg.pch_3.setChecked(False)
        self.otoklimdlg.psh_3.setChecked(False)
        self.otoklimdlg.addach_1.setEnabled(False)
        self.otoklimdlg.addash_1.setEnabled(False)
        self.otoklimdlg.addpch_1.setEnabled(False)
        self.otoklimdlg.addpsh_1.setEnabled(False)
        self.otoklimdlg.addpch_2.setEnabled(False)
        self.otoklimdlg.addpsh_2.setEnabled(False)
        self.otoklimdlg.addpch_3.setEnabled(False)
        self.otoklimdlg.addpsh_3.setEnabled(False)


    def month_edited(self):
        """Function to set month edited"""
        self.otoklimdlg.Select_Month.setWhatsThis('edited')
        self.otoklimdlg.groupBox_3.setEnabled(False)
        self.otoklimdlg.testParameter.setEnabled(True)
        self.otoklimdlg.ach_1.setChecked(False)
        self.otoklimdlg.ash_1.setChecked(False)
        self.otoklimdlg.pch_1.setChecked(False)
        self.otoklimdlg.psh_1.setChecked(False)
        self.otoklimdlg.pch_2.setChecked(False)
        self.otoklimdlg.psh_2.setChecked(False)
        self.otoklimdlg.pch_3.setChecked(False)
        self.otoklimdlg.psh_3.setChecked(False)
        self.otoklimdlg.addach_1.setEnabled(False)
        self.otoklimdlg.addash_1.setEnabled(False)
        self.otoklimdlg.addpch_1.setEnabled(False)
        self.otoklimdlg.addpsh_1.setEnabled(False)
        self.otoklimdlg.addpch_2.setEnabled(False)
        self.otoklimdlg.addpsh_2.setEnabled(False)
        self.otoklimdlg.addpch_3.setEnabled(False)
        self.otoklimdlg.addpsh_3.setEnabled(False)

    def select_all_type(self):
        """Select All Check Box Type"""
        if self.otoklimdlg.check_all.isChecked():
            self.otoklimdlg.ach_1.setChecked(True)
            self.otoklimdlg.ash_1.setChecked(True)
            self.otoklimdlg.pch_1.setChecked(True)
            self.otoklimdlg.psh_1.setChecked(True)
            self.otoklimdlg.pch_2.setChecked(True)
            self.otoklimdlg.psh_2.setChecked(True)
            self.otoklimdlg.pch_3.setChecked(True)
            self.otoklimdlg.psh_3.setChecked(True)
        else:
            self.otoklimdlg.ach_1.setChecked(False)
            self.otoklimdlg.ash_1.setChecked(False)
            self.otoklimdlg.pch_1.setChecked(False)
            self.otoklimdlg.psh_1.setChecked(False)
            self.otoklimdlg.pch_2.setChecked(False)
            self.otoklimdlg.psh_2.setChecked(False)
            self.otoklimdlg.pch_3.setChecked(False)
            self.otoklimdlg.psh_3.setChecked(False)
        if self.otoklimdlg.check_all_class.isChecked():
            self.otoklimdlg.ach_1_class.setChecked(True)
            self.otoklimdlg.ash_1_class.setChecked(True)
            self.otoklimdlg.pch_1_class.setChecked(True)
            self.otoklimdlg.psh_1_class.setChecked(True)
            self.otoklimdlg.pch_2_class.setChecked(True)
            self.otoklimdlg.psh_2_class.setChecked(True)
            self.otoklimdlg.pch_3_class.setChecked(True)
            self.otoklimdlg.psh_3_class.setChecked(True)
        else:
            self.otoklimdlg.ach_1_class.setChecked(False)
            self.otoklimdlg.ash_1_class.setChecked(False)
            self.otoklimdlg.pch_1_class.setChecked(False)
            self.otoklimdlg.psh_1_class.setChecked(False)
            self.otoklimdlg.pch_2_class.setChecked(False)
            self.otoklimdlg.psh_2_class.setChecked(False)
            self.otoklimdlg.pch_3_class.setChecked(False)
            self.otoklimdlg.psh_3_class.setChecked(False)
        if self.otoklimdlg.check_all_map.isChecked():
            self.otoklimdlg.ach_1_map.setChecked(True)
            self.otoklimdlg.ash_1_map.setChecked(True)
            self.otoklimdlg.pch_1_map.setChecked(True)
            self.otoklimdlg.psh_1_map.setChecked(True)
            self.otoklimdlg.pch_2_map.setChecked(True)
            self.otoklimdlg.psh_2_map.setChecked(True)
            self.otoklimdlg.pch_3_map.setChecked(True)
            self.otoklimdlg.psh_3_map.setChecked(True)
        else:
            self.otoklimdlg.ach_1_map.setChecked(False)
            self.otoklimdlg.ash_1_map.setChecked(False)
            self.otoklimdlg.pch_1_map.setChecked(False)
            self.otoklimdlg.psh_1_map.setChecked(False)
            self.otoklimdlg.pch_2_map.setChecked(False)
            self.otoklimdlg.psh_2_map.setChecked(False)
            self.otoklimdlg.pch_3_map.setChecked(False)
            self.otoklimdlg.psh_3_map.setChecked(False)
        if self.otoklimdlg.check_all_csv.isChecked():
            self.otoklimdlg.ach_1_csv.setChecked(True)
            self.otoklimdlg.ash_1_csv.setChecked(True)
            self.otoklimdlg.pch_1_csv.setChecked(True)
            self.otoklimdlg.psh_1_csv.setChecked(True)
            self.otoklimdlg.pch_2_csv.setChecked(True)
            self.otoklimdlg.psh_2_csv.setChecked(True)
            self.otoklimdlg.pch_3_csv.setChecked(True)
            self.otoklimdlg.psh_3_csv.setChecked(True)
        else:
            self.otoklimdlg.ach_1_csv.setChecked(False)
            self.otoklimdlg.ash_1_csv.setChecked(False)
            self.otoklimdlg.pch_1_csv.setChecked(False)
            self.otoklimdlg.psh_1_csv.setChecked(False)
            self.otoklimdlg.pch_2_csv.setChecked(False)
            self.otoklimdlg.psh_2_csv.setChecked(False)
            self.otoklimdlg.pch_3_csv.setChecked(False)
            self.otoklimdlg.psh_3_csv.setChecked(False)

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
            elif type == 'class':
                if 'lower_limit' not in header:
                    error_field = 'lower_limit'
                elif 'upper_limit' not in header:
                    error_field = 'upper_limit'
                elif 'new_value' not in header:
                    error_field = 'new_value'
                elif 'color' not in header:
                    error_field = 'color'
            else:
                if 'post_id' not in header:
                    error_field = 'post_id'
                elif 'ACH_1' not in header:
                    error_field = 'ACH_1'
                elif 'ASH_1' not in header:
                    error_field = 'ASH_1'
                elif 'PCH_1' not in header:
                    error_field = 'PCH_1'
                elif 'PSH_1' not in header:
                    error_field = 'PSH_1'
                elif 'PCH_2' not in header:
                    error_field = 'PCH_2'
                elif 'PSH_2' not in header:
                    error_field = 'PSH_2'
                elif 'PCH_3' not in header:
                    error_field = 'PCH_3'
                elif 'PSH_3' not in header:
                    error_field = 'PSH_3'
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
                elif type == 'class':
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
                else:
                    try:
                        int(row['post_id'])
                    except:
                        error_message = ': post_id [' + row['post_id'] + '] value must be integer'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        int(row['ACH_1'])
                    except:
                        error_message = ': ACH_1 [' + row['ACH_1'] + '] value must be integer'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        int(row['ASH_1'])
                    except:
                        error_message = ': ASH_1 [' + row['ASH_1'] + '] value must be integer'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        int(row['PCH_1'])
                    except:
                        error_message = ': PCH_1 [' + row['PCH_1'] + '] value must be integer'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        int(row['PSH_1'])
                    except:
                        error_message = ': PSH_1 [' + row['PSH_1'] + '] value must be integer'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        int(row['PCH_2'])
                    except:
                        error_message = ': PCH_2 [' + row['PCH_2'] + '] value must be integer'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        int(row['PSH_2'])
                    except:
                        error_message = ': PSH_2 [' + row['PSH_2'] + '] value must be integer'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        int(row['PCH_3'])
                    except:
                        error_message = ': PCH_3 [' + row['PCH_3'] + '] value must be integer'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        int(row['PSH_3'])
                    except:
                        error_message = ': PSH_3 [' + row['PSH_3'] + '] value must be integer'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)


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
            if source_file != target_file:
                shutil.copyfile(source_file, target_file)
            else:
                pass

    def project_param_accord(self, type):
        """Project Param Panel Accordion Clicked Show/Hide"""
        if self.otoklimdlg.projectparamPanel.isVisible():
            self.otoklimdlg.projectparamPanel.hide()
        else:
            self.otoklimdlg.projectparamPanel.show()

    def idw_interpolation_accord(self, type):
        """Project IDW Interpolation Accordion Clicked Show/Hide"""
        if self.otoklimdlg.idwinterpolationPanel.isVisible():
            self.otoklimdlg.idwinterpolationPanel.hide()
        else:
            self.otoklimdlg.idwinterpolationPanel.show()

    def classification_accord(self, type):
        """Project Classification Accordion Clicked Show/Hide"""
        if self.otoklimdlg.classificationPanel.isVisible():
            self.otoklimdlg.classificationPanel.hide()
        else:
            self.otoklimdlg.classificationPanel.show()

    def generate_map_accord(self, type):
        """Project Generate Map Accordion Clicked Show/Hide"""
        if self.otoklimdlg.generatemapPanel.isVisible():
            self.otoklimdlg.generatemapPanel.hide()
        else:
            self.otoklimdlg.generatemapPanel.show()

    def generate_csv_accord(self, type):
        """Project Generate CSV Accordion Clicked Show/Hide"""
        if self.otoklimdlg.generatecsvPanel.isVisible():
            self.otoklimdlg.generatecsvPanel.hide()
        else:
            self.otoklimdlg.generatecsvPanel.show()

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
            # Special case for Input Value CSV
            if self.otoklimdlg.Input_Value_CSV.whatsThis() == 'edited':
                self.check_csv(self.otoklimdlg.Input_Value_CSV.text(), self.otoklimdlg.csvdelimiter.text(), 'input_value')
                with open(self.otoklimdlg.rainpostfile.text(), 'rb') as csvfile:
                    spamreader = csv.DictReader(csvfile, delimiter=str(self.otoklimdlg.csvdelimiter.text()), quotechar='|')
                    rainpost_id = []
                    for row in spamreader:
                        rainpost_id.append(row['post_id'])
                with open(self.otoklimdlg.Input_Value_CSV.text(), 'rb') as csvfile:
                    spamreader = csv.DictReader(csvfile, delimiter=str(self.otoklimdlg.csvdelimiter.text()), quotechar='|')
                    for row in spamreader:
                        if row['post_id'] not in rainpost_id:
                            errormessage = 'post_id ' + row['post_id'] + ' does not exists on rainpost file' 
                            raise Exception(errormessage)
                self.copy_file(self.otoklimdlg.Input_Value_CSV.text(), input_directory, False)
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]['INPUT_VALUE_FILE']["NAME"] = os.path.basename(self.otoklimdlg.Input_Value_CSV.text())
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]['INPUT_VALUE_FILE']["LOCATION"] = "IN_FILE_LOC"
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.Input_Value_CSV.setWhatsThis('')
                change = True
            if self.otoklimdlg.Select_Province.whatsThis() == 'edited':
                layer = QgsVectorLayer(self.otoklimdlg.province.text(), 'Provinsi', 'ogr')
                province_id = None
                for value in layer.getFeatures():
                    if value['PROVINSI'] == self.otoklimdlg.Select_Province.currentText():
                        province_id = value['ID_PROV']
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]['ID_PROV'] = str(province_id)
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.Select_Province.setWhatsThis('')
                change = True
            if self.otoklimdlg.Select_Month.whatsThis() == 'edited':
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]['THIS_MONTH'] = str(self.otoklimdlg.Select_Month.currentText())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.Select_Month.setWhatsThis('')
                change = True
            if self.otoklimdlg.Select_Year.whatsThis() == 'edited':
                try:
                    int(self.otoklimdlg.Select_Year.text())
                except:
                    errormessage = 'year value must be four digit integer'
                    raise Exception(errormessage)
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]['THIS_YEAR'] = str(self.otoklimdlg.Select_Year.text())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.Select_Year.setWhatsThis('')
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
                def month_name(index):
                    if index == 1:
                        monthname = 'Januari'
                    elif index == 2:
                        monthname = 'Februari'
                    elif index == 3:
                        monthname = 'Maret'
                    elif index == 4:
                        monthname = 'April'
                    elif index == 5:
                        monthname = 'Mei'
                    elif index == 6:
                        monthname = 'Juni'
                    elif index == 7:
                        monthname = 'Juli'
                    elif index == 8:
                        monthname = 'Agustus'
                    elif index == 9:
                        monthname = 'September'
                    elif index == 10:
                        monthname = 'Oktober'
                    elif index == 11:
                        monthname = 'November'
                    else:
                        monthname = 'Desember'
                    return monthname
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
                    },
                    "PROCESSING": {
                        "IDW_INTERPOLATION": {
                            "PROCESSED": 0,
                            "INPUT_VALUE_FILE": {
                                "NAME": "",
                                "LOCATION": "",
                                "FORMAT": "CSV"
                            },
                            "ID_PROV": "",
                            "THIS_MONTH": month_name(datetime.datetime.now().month),
                            "THIS_YEAR": str(datetime.datetime.now().year),
                            "RASTER_ACH_1": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_ASH_1": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PCH_1": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PSH_1": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PCH_2": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PSH_2": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PCH_3": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PSH_3": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            }
                        },
                        "CLASSIFICATION": {
                            "PROCESSED": 0,
                            "RASTER_ACH_1": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_ASH_1": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PCH_1": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PSH_1": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PCH_2": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PSH_2": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PCH_3": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PSH_3": {
                                "NAME": "",
                                "LOCATION": "PRC_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                        },
                        "GENERATE_MAP": {},
                        "GENERATE_CSV": {}
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
                    self.otoklimdlg.show()
    
    def check_all_edited_parameter(self):
        """Make sure all param is not edited"""
        all_param = [
            self.otoklimdlg.province.whatsThis(),
            self.otoklimdlg.districts.whatsThis(),
            self.otoklimdlg.subdistricts.whatsThis(),
            self.otoklimdlg.villages.whatsThis(),
            self.otoklimdlg.bathymetry.whatsThis(),
            self.otoklimdlg.rainpostfile.whatsThis(),
            self.otoklimdlg.logofile.whatsThis(),
            self.otoklimdlg.rainfallfile.whatsThis(),
            self.otoklimdlg.normalrainfile.whatsThis(),
            self.otoklimdlg.maptemplate.whatsThis(),
            self.otoklimdlg.Input_Value_CSV.whatsThis(),
            self.otoklimdlg.Select_Province.whatsThis(),
            self.otoklimdlg.Select_Month.whatsThis(),
            self.otoklimdlg.Select_Year.whatsThis()
        ]
        if 'edited' in all_param:
            result = self.saveconfirmdlg.exec_()
            if result:
                self.save_change()
                return True
            else:
                return False
        else:
            return True

    def select_date_now(self):
        mth = self.otoklimdlg.Select_Month.currentText()
        if mth == 'Januari':
            mth = 1
        elif mth == 'Februari':
            mth = 2
        elif mth == 'Maret':
            mth = 3
        elif mth == 'April':
            mth = 4
        elif mth == 'Mei':
            mth = 5
        elif mth == 'Juni':
            mth = 6
        elif mth == 'Juli':
            mth = 7
        elif mth == 'Agustus':
            mth = 8
        elif mth == 'September':
            mth = 9
        elif mth == 'Oktober':
            mth = 0
        elif mth == 'November':
            mth = 11
        else:
            mth = 12

        month_dict = {
            0: ['DES', 'DESEMBER'],
            1: ['JAN', 'JANUARI'],
            2: ['FEB', 'FEBRUARI'],
            3: ['MAR', 'MARET'],
            4: ['APR', 'APRIL'],
            5: ['MEI', 'MEI'],
            6: ['JUN', 'JUNI'],
            7: ['JUL', 'JULI'],
            8: ['AGT', 'AGUSTUS'],
            9: ['SEP', 'SEPTEMBER'],
            10: ['OKT', 'OKTOBER'],
            11: ['NOV', 'NOVEMBER'],
            12: ['DES', 'DESEMBER'],
            13: ['JAN', 'JANUARI'],
            14: ['FEB', 'FEBRUARI'],
            15: ['MAR', 'MARET'],
            16: ['APR', 'APRIL']
        }
        amth = month_dict[mth-1]
        pmth_1 = month_dict[mth+1]
        pmth_2 = month_dict[mth+2]
        pmth_3 = month_dict[mth+3]
        month_header = [amth, pmth_1, pmth_2, pmth_3]

        yrs = int(self.otoklimdlg.Select_Year.text())
        ayrs = yrs
        pyrs_1 = pyrs_2 = pyrs_3 = yrs
        if mth == 12:
            pyrs_1 = yrs + 1
            pyrs_2 = yrs + 1
            pyrs_3 = yrs + 1
        elif mth == 11:
            pyrs_2 = yrs + 1
            pyrs_3 = yrs + 1
        elif mth == 10:
            pyrs_3 = yrs + 1
        elif mth == 1:
            ayrs = yrs - 1
        years_header = [ayrs, pyrs_1, pyrs_2, pyrs_3]
        return month_header, years_header
    
    def interpolate_idw(self):
        """Function To Run IDW Interpolation"""
        prcs_directory = os.path.join(self.otoklimdlg.projectworkspace.text(), 'processing')
        provinsi_polygon_file = os.path.join(prcs_directory, 'provinsi_polygon.shp')
        filename_shp = os.path.join(prcs_directory, 'rainpost_point.shp')
        temp = os.path.join(prcs_directory, 'tmp_' + '{:%Y%m%d_%H%M%S}'.format(datetime.datetime.now()))
        os.mkdir(temp)
        self.copy_file(filename_shp, temp, True)
        filename_shp_tmp = os.path.join(temp, 'rainpost_point.shp')
        layer = QgsVectorLayer(filename_shp_tmp, 'layer', 'ogr')
        layer_provinsi = QgsVectorLayer(provinsi_polygon_file, 'layer', 'ogr')
        fields = layer.pendingFields()
        field_names = [field.name() for field in fields]
        idw_params = field_names[5:]
        project = os.path.join(
            self.otoklimdlg.projectworkspace.text(),
            self.otoklimdlg.projectfilename.text()
        )
        try:
            prc_list = []
            if self.otoklimdlg.ach_1.isChecked():
                prc_list.append(idw_params[0])
                self.otoklimdlg.addach_1.setEnabled(True)
                self.otoklimdlg.addach_1.setWhatsThis(
                    os.path.join(prcs_directory, 'interpolated_' + str(idw_params[0]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_ACH_1"]["NAME"] = 'interpolated_' + str(idw_params[0]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
            if self.otoklimdlg.ash_1.isChecked():
                prc_list.append(idw_params[1])
                self.otoklimdlg.addash_1.setEnabled(True)
                self.otoklimdlg.addash_1.setWhatsThis(
                    os.path.join(prcs_directory, 'interpolated_' + str(idw_params[1]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_ASH_1"]["NAME"] = 'interpolated_' + str(idw_params[1]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
            if self.otoklimdlg.pch_1.isChecked():
                prc_list.append(idw_params[2])
                self.otoklimdlg.addpch_1.setEnabled(True)
                self.otoklimdlg.addpch_1.setWhatsThis(
                    os.path.join(prcs_directory, 'interpolated_' + str(idw_params[2]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_1"]["NAME"] = 'interpolated_' + str(idw_params[2]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
            if self.otoklimdlg.psh_1.isChecked():
                prc_list.append(idw_params[3])
                self.otoklimdlg.addpsh_1.setEnabled(True)
                self.otoklimdlg.addpsh_1.setWhatsThis(
                    os.path.join(prcs_directory, 'interpolated_' + str(idw_params[3]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_1"]["NAME"] = 'interpolated_' + str(idw_params[3]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
            if self.otoklimdlg.pch_2.isChecked():
                prc_list.append(idw_params[4])
                self.otoklimdlg.addpch_2.setEnabled(True)
                self.otoklimdlg.addpch_2.setWhatsThis(
                    os.path.join(prcs_directory, 'interpolated_' + str(idw_params[4]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_2"]["NAME"] = 'interpolated_' + str(idw_params[4]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
            if self.otoklimdlg.psh_2.isChecked():
                prc_list.append(idw_params[5])
                self.otoklimdlg.addpsh_2.setEnabled(True)
                self.otoklimdlg.addpsh_2.setWhatsThis(
                    os.path.join(prcs_directory, 'interpolated_' + str(idw_params[5]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_2"]["NAME"] = 'interpolated_' + str(idw_params[5]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
            if self.otoklimdlg.pch_3.isChecked():
                prc_list.append(idw_params[6])
                self.otoklimdlg.addpch_3.setEnabled(True)
                self.otoklimdlg.addpch_3.setWhatsThis(
                    os.path.join(prcs_directory, 'interpolated_' + str(idw_params[6]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_3"]["NAME"] = 'interpolated_' + str(idw_params[6]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
            if self.otoklimdlg.psh_3.isChecked():
                prc_list.append(idw_params[7])
                self.otoklimdlg.addpsh_3.setEnabled(True)
                self.otoklimdlg.addpsh_3.setWhatsThis(
                    os.path.join(prcs_directory, 'interpolated_' + str(idw_params[7]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_3"]["NAME"] = 'interpolated_' + str(idw_params[7]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))

            for param in prc_list:
                raster_interpolated = os.path.join(temp, param + '_raster_idw.tif')
                raster_cropped = os.path.join(prcs_directory, 'interpolated_' + str(param).lower() + '.tif')
                if os.path.exists(raster_cropped):
                    self.replaceconfirmdlg.var.setText(raster_cropped)
                    result = self.replaceconfirmdlg.exec_()
                    if result:
                        os.remove(raster_cropped)
                    else:
                        raise Exception('Skip ' + raster_cropped)

                extent = layer_provinsi.extent()
                processing.runalg(
                    'grass7:v.surf.idw',
                    layer, 8.0, 5.0, param, False,
                    "%f,%f,%f,%f" % (extent.xMinimum(), extent.xMaximum(), extent.yMinimum(), extent.yMaximum()), 0.001, -1.0, 0.0001,
                    raster_interpolated
                )
                processing.runalg(
                    "gdalogr:cliprasterbymasklayer", 
                    raster_interpolated,
                    provinsi_polygon_file,
                    -1, False, False, False, 6, 0, 75, 1, 1, False, 0, False, "", 
                    raster_cropped
                )
            with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["PROCESSED"] = 1
            with open(project, 'w') as jsonfile:
                jsonfile.write(json.dumps(otoklim_project, indent=4))
            self.otoklimdlg.testParameter.setEnabled(False)
            self.otoklimdlg.classificationPanelAccord.setEnabled(True)
            self.otoklimdlg.classificationPanel.setEnabled(True)
            self.otoklimdlg.classificationPanel.show()
        except Exception as e:
            self.errormessagedlg.ErrorMessage.setText(str(e))
            self.errormessagedlg.exec_()

    def pra_interpolate(self):
        """Checking Before Interpolate IDW Function"""
        confirm = self.check_all_edited_parameter()
        if confirm:
            driver = ogr.GetDriverByName("ESRI Shapefile")
            file_directory = os.path.join(self.otoklimdlg.projectworkspace.text(), 'processing')
            filelist = [f for f in os.listdir(file_directory) if os.path.isfile(os.path.join(file_directory, f))]
            for file in filelist:
                os.remove(os.path.join(file_directory, file))
            file_input = self.otoklimdlg.Input_Value_CSV.text()
            rainpost_file = self.otoklimdlg.rainpostfile.text()
            combine_file = os.path.join(file_directory, 'combine.csv')
            delimiter = self.otoklimdlg.csvdelimiter.text()
            date = self.select_date_now()
            months = date[0]
            years = date[1]
            try:
                # Combine CSV
                dict_input = {}
                dict_station = {}
                with open(file_input, 'rb') as csvfile:
                    spamreader = csv.reader(csvfile, delimiter=str(delimiter), quotechar='|')
                    n = 0
                    for row in spamreader:
                        if n != 0:
                            dict_input.update({int(row[0]): row[1:]})
                        else:
                            idw_params = row[1:]
                            for month in months:
                                idw_params[n] = idw_params[n].split('_')[0] + '_' + str(month[0])
                                idw_params[n+1] = idw_params[n+1].split('_')[0] + '_' + str(month[0])
                                n += 2
                            header_input = idw_params
                        n += 1
                with open(rainpost_file, 'rb') as csvfile:
                    spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
                    n = 0
                    for row in spamreader:
                        if n != 0:
                            dict_station.update({int(row[0]): row})
                        else:
                            header_station = row
                        n += 1
                try:
                    combine = {k: dict_station.get(k, []) + dict_input.get(k, []) for k in (dict_station.keys() | dict_input.keys())}
                except:
                    combine = {k: dict_station.get(k, []) + dict_input.get(k, []) for k in (dict_station.viewkeys() | dict_input.viewkeys())}
                with open(combine_file, "wb+") as csvfile:
                    csv_writer = csv.writer(csvfile, delimiter=str(delimiter))
                    csv_writer.writerow(header_station + header_input)
                    for row in combine.values():
                        csv_writer.writerow(row)
                
                # CSV To Shapefile
                csv_file = combine_file
                filename_shp = os.path.join(file_directory, 'rainpost_point.shp')
                filename_prj = os.path.join(file_directory, 'rainpost_point.prj')
                data_source = driver.CreateDataSource(filename_shp)
                srs = osr.SpatialReference()
                srs.ImportFromEPSG(4326)
                srs.MorphToESRI()
                prj_file = open(filename_prj, 'w')
                prj_file.write(srs.ExportToWkt())
                prj_file.close()
                filename_shp = filename_shp.encode('utf-8')
                layer = data_source.CreateLayer(filename_shp, srs, ogr.wkbPoint)
                with open(csv_file, 'rb') as csvfile:
                    reader = csv.reader(csvfile)
                    headers = reader.next()
                    n = 0
                    for h in headers:
                        if n <= 2:
                            layer.CreateField(ogr.FieldDefn(h, ogr.OFTString))
                        else:
                            layer.CreateField(ogr.FieldDefn(h, ogr.OFTReal))
                        n += 1
                with open(csv_file, 'rb') as csvfile:
                    spamreader = csv.DictReader(csvfile, delimiter=str(delimiter), quotechar='|')
                    for row in spamreader:
                        point = ogr.Geometry(ogr.wkbPoint)
                        feature = ogr.Feature(layer.GetLayerDefn())
                        point.AddPoint(float(row['lon']), float(row['lat']))
                        for h in headers:
                            feature.SetField(h, row[h])
                        feature.SetGeometry(point)
                        layer.CreateFeature(feature)
                
                # Province Polygon Querry
                provinsi_polygon = os.path.join(file_directory, 'provinsi_polygon.shp')
                layer = QgsVectorLayer(self.otoklimdlg.province.text(), 'provinsi', 'ogr')
                exp = "\"PROVINSI\"='{}'".format(self.otoklimdlg.Select_Province.currentText())
                it = layer.getFeatures(QgsFeatureRequest(QgsExpression(exp)))
                ids = [i.id() for i in it]
                layer.setSelectedFeatures(ids)
                QgsVectorFileWriter.writeAsVectorFormat(layer, provinsi_polygon, "utf-8", layer.crs(), "ESRI Shapefile", 1)
                layer_poly = QgsVectorLayer(provinsi_polygon, "lyr", "ogr")
                self.otoklimdlg.groupBox_3.setEnabled(True)
                self.otoklimdlg.interpolateButton.setEnabled(True)
                project = os.path.join(
                    self.otoklimdlg.projectworkspace.text(),
                    self.otoklimdlg.projectfilename.text()
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]['PROCESSED'] = 0
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_ACH_1"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_ASH_1"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_1"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_1"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_2"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_2"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_3"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_3"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]['PROCESSED'] = 0
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_ACH_1"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_ASH_1"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_1"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_1"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_2"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_2"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_3"]["NAME"] = ""
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_3"]["NAME"] = ""
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.ach_1.setChecked(False)
                self.otoklimdlg.ash_1.setChecked(False)
                self.otoklimdlg.pch_1.setChecked(False)
                self.otoklimdlg.psh_1.setChecked(False)
                self.otoklimdlg.pch_2.setChecked(False)
                self.otoklimdlg.psh_2.setChecked(False)
                self.otoklimdlg.pch_3.setChecked(False)
                self.otoklimdlg.psh_3.setChecked(False)
                self.otoklimdlg.addach_1.setEnabled(False)
                self.otoklimdlg.addash_1.setEnabled(False)
                self.otoklimdlg.addpch_1.setEnabled(False)
                self.otoklimdlg.addpsh_1.setEnabled(False)
                self.otoklimdlg.addpch_2.setEnabled(False)
                self.otoklimdlg.addpsh_2.setEnabled(False)
                self.otoklimdlg.addpch_3.setEnabled(False)
                self.otoklimdlg.addpsh_3.setEnabled(False)
                self.otoklimdlg.classificationPanelAccord.setEnabled(False)
                self.otoklimdlg.classificationPanel.hide()
                self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
                self.otoklimdlg.generatemapPanel.hide()
            except Exception as e:
                print e
                self.errormessagedlg.ErrorMessage.setText(str(e))
                self.errormessagedlg.exec_()

    def raster_classify(self):
        """Function To Classify Raster Interpolated"""
        prcs_directory = os.path.join(self.otoklimdlg.projectworkspace.text(), 'processing')
        provinsi_polygon_file = os.path.join(prcs_directory, 'provinsi_polygon.shp')
        layer_provinsi = QgsVectorLayer(provinsi_polygon_file, 'layer', 'ogr')
        filename_rainfall = self.otoklimdlg.rainfallfile.text()
        output_rainfall = os.path.join(prcs_directory, 'rule_ch.txt')
        if os.path.exists(output_rainfall):
            os.remove(output_rainfall)
        row_keeper = []
        with open(filename_rainfall, 'rb') as csvfile:
            spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
            data = spamreader.next()
            for row in spamreader:
                row_keeper.append([row['lower_limit'], row['upper_limit'], row['new_value']])
        with open(output_rainfall, "wb+") as txtfile:
            txt_writer = csv.writer(txtfile, delimiter=':')
            for row in row_keeper:
                txt_writer.writerow(row)
        filename_normalrain = self.otoklimdlg.normalrainfile.text()
        output_normalrain = os.path.join(prcs_directory, 'rule_sh.txt')
        if os.path.exists(output_normalrain):
            os.remove(output_normalrain)
        row_keeper = []
        with open(filename_normalrain, 'rb') as csvfile:
            spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
            data = spamreader.next()
            for row in spamreader:
                row_keeper.append([row['lower_limit'], row['upper_limit'], row['new_value']])
        with open(output_normalrain, "wb+") as txtfile:
            txt_writer = csv.writer(txtfile, delimiter=':')
            for row in row_keeper:
                txt_writer.writerow(row)
        project = os.path.join(
            self.otoklimdlg.projectworkspace.text(),
            self.otoklimdlg.projectfilename.text()
        )
        try:
            prc_list = []
            if self.otoklimdlg.ach_1_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_ach_1 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_ACH_1"]["NAME"]
                    param = os.path.splitext(raster_ach_1)[0].split('_')[1] + '_' + os.path.splitext(raster_ach_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_ACH_1"]["NAME"] = 'classified_' + str(param) + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_ach_1])
                self.otoklimdlg.addach_1_class.setEnabled(True)
                self.otoklimdlg.addach_1_class.setWhatsThis(
                    os.path.join(prcs_directory, 'classified_' + str(param) + '.tif')
                )
            if self.otoklimdlg.ash_1_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_ash_1 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_ASH_1"]["NAME"]
                    param = os.path.splitext(raster_ash_1)[0].split('_')[1] + '_' + os.path.splitext(raster_ash_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_ASH_1"]["NAME"] = 'classified_' + str(param) + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_ash_1])
                self.otoklimdlg.addash_1_class.setEnabled(True)
                self.otoklimdlg.addash_1_class.setWhatsThis(
                    os.path.join(prcs_directory, 'classified_' + str(param) + '.tif')
                )
            if self.otoklimdlg.pch_1_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_pch_1 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_1"]["NAME"]
                    param = os.path.splitext(raster_pch_1)[0].split('_')[1] + '_' + os.path.splitext(raster_pch_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_1"]["NAME"] = 'classified_' + str(param) + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_pch_1])
                self.otoklimdlg.addpch_1_class.setEnabled(True)
                self.otoklimdlg.addpch_1_class.setWhatsThis(
                    os.path.join(prcs_directory, 'classified_' + str(param) + '.tif')
                )
            if self.otoklimdlg.psh_1_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_psh_1 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_1"]["NAME"]
                    param = os.path.splitext(raster_psh_1)[0].split('_')[1] + '_' + os.path.splitext(raster_psh_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_1"]["NAME"] = 'classified_' + str(param) + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_psh_1])
                self.otoklimdlg.addpsh_1_class.setEnabled(True)
                self.otoklimdlg.addpsh_1_class.setWhatsThis(
                    os.path.join(prcs_directory, 'classified_' + str(param) + '.tif')
                )
            if self.otoklimdlg.pch_2_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_pch_2 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_2"]["NAME"]
                    param = os.path.splitext(raster_pch_2)[0].split('_')[1] + '_' + os.path.splitext(raster_pch_2)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_2"]["NAME"] = 'classified_' + str(param) + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_pch_2])
                self.otoklimdlg.addpch_2_class.setEnabled(True)
                self.otoklimdlg.addpch_2_class.setWhatsThis(
                    os.path.join(prcs_directory, 'classified_' + str(param) + '.tif')
                )
            if self.otoklimdlg.psh_2_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_psh_2 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_2"]["NAME"]
                    param = os.path.splitext(raster_psh_2)[0].split('_')[1] + '_' + os.path.splitext(raster_psh_2)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_2"]["NAME"] = 'classified_' + str(param) + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_psh_2])
                self.otoklimdlg.addpsh_2_class.setEnabled(True)
                self.otoklimdlg.addpsh_2_class.setWhatsThis(
                    os.path.join(prcs_directory, 'classified_' + str(param) + '.tif')
                )
            if self.otoklimdlg.pch_3_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_pch_3 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_3"]["NAME"]
                    param = os.path.splitext(raster_pch_3)[0].split('_')[1] + '_' + os.path.splitext(raster_pch_3)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_3"]["NAME"] = 'classified_' + str(param) + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_pch_3])
                self.otoklimdlg.addpch_3_class.setEnabled(True)
                self.otoklimdlg.addpch_3_class.setWhatsThis(
                    os.path.join(prcs_directory, 'classified_' + str(param) + '.tif')
                )
            if self.otoklimdlg.psh_3_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_psh_3 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_3"]["NAME"]
                    param = os.path.splitext(raster_psh_3)[0].split('_')[1] + '_' + os.path.splitext(raster_psh_3)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_3"]["NAME"] = 'classified_' + str(param) + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_psh_3])
                self.otoklimdlg.addpsh_3_class.setEnabled(True)
                self.otoklimdlg.addpsh_3_class.setWhatsThis(
                    os.path.join(prcs_directory, 'classified_' + str(param) + '.tif')
                )

            for value in prc_list:
                raster_classified = os.path.join(prcs_directory, 'classified_' + str(value[0]) + '.tif')
                rasterinterpolated = os.path.join(prcs_directory, value[1])
                if os.path.exists(raster_classified):
                    self.replaceconfirmdlg.var.setText(raster_classified)
                    result = self.replaceconfirmdlg.exec_()
                    if result:
                        os.remove(raster_classified)
                    else:
                        raise Exception('Skip ' + raster_classified)
                extent = layer_provinsi.extent()
                if value[0][0:3] == 'ach' or value[0][0:3] == 'pch':
                    processing.runalg('grass7:r.recode', rasterinterpolated, output_rainfall, False, "%f,%f,%f,%f" % (extent.xMinimum(), extent.xMaximum(), extent.yMinimum(), extent.yMaximum()), 0.001, raster_classified)
                else:
                    processing.runalg('grass7:r.recode', rasterinterpolated, output_normalrain, False, "%f,%f,%f,%f" % (extent.xMinimum(), extent.xMaximum(), extent.yMinimum(), extent.yMaximum()), 0.001, raster_classified)

            with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["PROCESSED"] = 1
            with open(project, 'w') as jsonfile:
                jsonfile.write(json.dumps(otoklim_project, indent=4))
            self.otoklimdlg.testParameter.setEnabled(False)
            self.otoklimdlg.classificationPanelAccord.setEnabled(True)
            self.otoklimdlg.classificationPanel.setEnabled(True)
        except Exception as e:
            self.errormessagedlg.ErrorMessage.setText(str(e))
            self.errormessagedlg.exec_()

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
