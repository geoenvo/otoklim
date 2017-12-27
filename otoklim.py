# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Otoklim
                                 A QGIS plugin
 This Plugin used to support the automation of the seasonal prediction & analysis produced by BMKG Climatological Station
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
from PyQt4.QtCore import Qt, QSettings, QTranslator, qVersion, QCoreApplication, QFileInfo, QSize, QVariant
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QListWidgetItem, QTreeWidgetItem, QCloseEvent, QColor, QPainter, QImage
from PyQt4.QtXml import QDomDocument
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
    QGis,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsMapLayerRegistry,
    QgsFeatureRequest,
    QgsExpression,
    QgsVectorFileWriter,
    QgsRasterShader,
    QgsColorRampShader,
    QgsSingleBandPseudoColorRenderer,
    QgsFillSymbolV2,
    QgsLineSymbolV2,
    QgsPalLayerSettings,
    QgsProject,
    QgsComposition,
    QgsField,
    QgsRendererCategoryV2,
    QgsCategorizedSymbolRendererV2,
    QgsDistanceArea,
)
from qgis.gui import QgsMapCanvas, QgsLayerTreeMapCanvasBridge
from qgis.analysis import QgsZonalStatistics
from osgeo import gdal, ogr, osr
from gdalconst import GA_ReadOnly
import qgis.utils
import os.path
import os
import shutil
import json
import subprocess
import datetime
import processing
import csv
import logging
import xml.etree.cElementTree as ET


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
        self.otoklimdlg.logoArea.show()
        self.otoklimdlg.scrollArea.hide()
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
        self.newprojectdlg.Input_map_template_2.clear()
        self.newprojectdlg.Input_map_template_2.textChanged.connect(
            self.enable_create_button
        )
        self.newprojectdlg.Browse_map_template_2.clicked.connect(
            self.select_input_map_template_2
        )
        self.newprojectdlg.Input_map_template_3.clear()
        self.newprojectdlg.Input_map_template_3.textChanged.connect(
            self.enable_create_button
        )
        self.newprojectdlg.Browse_map_template_3.clicked.connect(
            self.select_input_map_template_3
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
        self.otoklimdlg.Edit_rainfall_class.clicked.connect(
            self.edit_rainfall_class
        )
        self.otoklimdlg.Edit_normalrain_class.clicked.connect(
            self.edit_normalrain_class
        )
        self.otoklimdlg.Edit_map_template.clicked.connect(
            self.edit_map_template
        )
        self.otoklimdlg.Edit_map_template_2.clicked.connect(
            self.edit_map_template_2
        )
        self.otoklimdlg.Edit_map_template_3.clicked.connect(
            self.edit_map_template_3
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

        # Add Search Region Logic
        self.otoklimdlg.search_option1.textChanged.connect(
            self.search_option_1
        )
        self.otoklimdlg.search_option2.textChanged.connect(
            self.search_option_2
        )

        # Add Expand Region Listing Logic
        self.otoklimdlg.expand_1.clicked.connect(
            self.expand_option_1
        )
        self.otoklimdlg.expand_2.clicked.connect(
            self.expand_option_2
        )

        # Add Move Selected Region Button Logic
        self.otoklimdlg.addSelected_1.clicked.connect(self.add_to_selected_1)
        self.otoklimdlg.deleteUnselected_1.clicked.connect(self.delete_from_selected_1)
        self.otoklimdlg.addSelected_2.clicked.connect(self.add_to_selected_2)
        self.otoklimdlg.deleteUnselected_2.clicked.connect(self.delete_from_selected_2)

        # Add Generate Map Trigger Logic
        self.otoklimdlg.generatemapButton.clicked.connect(self.generate_map)

        # Add Generate CSV Trigger Logic
        self.otoklimdlg.generatecsvButton.clicked.connect(self.generate_csv)

        # Open Folder Trigger Logic
        self.otoklimdlg.showInterpolateFolder.clicked.connect(self.show_interpolate_folder)
        self.otoklimdlg.showClassificationFolder.clicked.connect(self.show_classification_folder)
        self.otoklimdlg.showGenerateMapFolder.clicked.connect(self.show_generatemap_folder)
        self.otoklimdlg.showGenerateCSVFolder.clicked.connect(self.show_generatecsv_folder)

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
            self.otoklimdlg.rainfallfile.setWhatsThis('')
            self.otoklimdlg.rainfallfile.setStyleSheet('color: black')
            self.otoklimdlg.normalrainfile.setWhatsThis('')
            self.otoklimdlg.normalrainfile.setStyleSheet('color: black')
            self.otoklimdlg.maptemplate.setWhatsThis('')
            self.otoklimdlg.maptemplate.setStyleSheet('color: black')
            self.otoklimdlg.maptemplate2.setWhatsThis('')
            self.otoklimdlg.maptemplate2.setStyleSheet('color: black')
            self.otoklimdlg.maptemplate3.setWhatsThis('')
            self.otoklimdlg.maptemplate3.setStyleSheet('color: black')
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
                self.newprojectdlg.Input_rainpost.clear()
                self.newprojectdlg.Input_rainfall_class.clear()
                self.newprojectdlg.Input_normalrain_class.clear()
                self.newprojectdlg.Input_map_template.clear()
                self.newprojectdlg.Input_map_template_2.clear()
                self.newprojectdlg.Input_map_template_3.clear()
        else:
            self.askprojectdlg.ProjectName.clear()

    def read_otoklim_file(self, json, save=False):
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
        map_template_2 = os.path.join(
            json['LOCATION'][json['FILE']['MAP_TEMP_2']['LOCATION']],
            json['FILE']['MAP_TEMP_2']['NAME']
        )
        self.otoklimdlg.maptemplate2.setText(map_template_2)
        map_template_3 = os.path.join(
            json['LOCATION'][json['FILE']['MAP_TEMP_3']['LOCATION']],
            json['FILE']['MAP_TEMP_3']['NAME']
        )
        self.otoklimdlg.maptemplate3.setText(map_template_3)
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
            self.otoklimdlg.showInterpolateFolder.setEnabled(True)
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
            self.otoklimdlg.generatecsvPanelAccord.setEnabled(True)
            self.otoklimdlg.classificationPanel.show()
            self.otoklimdlg.classifyButton.setEnabled(True)
            self.otoklimdlg.showClassificationFolder.setEnabled(True)
            self.otoklimdlg.classificationPanel.setEnabled(True)
            self.otoklimdlg.generatemapPanel.setEnabled(True)
            self.otoklimdlg.generatecsvPanel.setEnabled(True)
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
        generatemap_prc = json['PROCESSING']['GENERATE_MAP']['PROCESSED']
        if generatemap_prc:
            self.otoklimdlg.showGenerateMapFolder.setEnabled(True)

        generatecsv_prc = json['PROCESSING']['GENERATE_CSV']['PROCESSED']
        if generatecsv_prc:
            self.otoklimdlg.showGenerateCSVFolder.setEnabled(True)

        # Region Listing
        province_id = json['PROCESSING']['IDW_INTERPOLATION']['ID_PROV']
        region_csv = os.path.join(json["LOCATION"]["PRC_FILE_LOC"], str(province_id) +  "_regionlist.csv")
        self.region_listing(province_id, region_csv, save)

        self.otoklimdlg.Input_Value_CSV.setWhatsThis('')
        self.otoklimdlg.Select_Province.setWhatsThis('edited')
        self.otoklimdlg.Select_Month.setWhatsThis('')
        self.otoklimdlg.Select_Year.setWhatsThis('')
        self.otoklimdlg.logoArea.hide()
        self.otoklimdlg.scrollArea.show()
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
            self.otoklimdlg.rainfallfile.setWhatsThis('')
            self.otoklimdlg.rainfallfile.setStyleSheet('color: black')
            self.otoklimdlg.normalrainfile.setWhatsThis('')
            self.otoklimdlg.normalrainfile.setStyleSheet('color: black')
            self.otoklimdlg.maptemplate.setWhatsThis('')
            self.otoklimdlg.maptemplate.setStyleSheet('color: black')
            self.otoklimdlg.maptemplate2.setWhatsThis('')
            self.otoklimdlg.maptemplate2.setStyleSheet('color: black')
            self.otoklimdlg.maptemplate3.setWhatsThis('')
            self.otoklimdlg.maptemplate3.setStyleSheet('color: black')
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

    def select_input_map_template_2(self):
        """Select QGIS Map Template file"""
        maptemplate_file_2 = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.qpt"
        )
        self.newprojectdlg.Input_map_template_2.setText(maptemplate_file_2)

    def select_input_map_template_3(self):
        """Select QGIS Map Template file"""
        maptemplate_file_3 = QFileDialog.getOpenFileName(
            self.newprojectdlg,
            "",
            "",
            "*.qpt"
        )
        self.newprojectdlg.Input_map_template_3.setText(maptemplate_file_3)

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
            self.otoklimdlg.classificationPanel.hide()
            self.otoklimdlg.classificationPanelAccord.setEnabled(False)
            self.otoklimdlg.generatemapPanel.hide()
            self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.hide()
            self.otoklimdlg.generatecsvPanelAccord.setEnabled(False)

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
            self.otoklimdlg.classificationPanel.hide()
            self.otoklimdlg.classificationPanelAccord.setEnabled(False)
            self.otoklimdlg.generatemapPanel.hide()
            self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.hide()
            self.otoklimdlg.generatecsvPanelAccord.setEnabled(False)

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
            self.otoklimdlg.classificationPanel.hide()
            self.otoklimdlg.classificationPanelAccord.setEnabled(False)
            self.otoklimdlg.generatemapPanel.hide()
            self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.hide()
            self.otoklimdlg.generatecsvPanelAccord.setEnabled(False)

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
            self.otoklimdlg.classificationPanel.hide()
            self.otoklimdlg.classificationPanelAccord.setEnabled(False)
            self.otoklimdlg.generatemapPanel.hide()
            self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.hide()
            self.otoklimdlg.generatecsvPanelAccord.setEnabled(False)

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
            self.otoklimdlg.classificationPanel.hide()
            self.otoklimdlg.classificationPanelAccord.setEnabled(False)
            self.otoklimdlg.generatemapPanel.hide()
            self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.hide()
            self.otoklimdlg.generatecsvPanelAccord.setEnabled(False)

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
            self.otoklimdlg.classificationPanel.hide()
            self.otoklimdlg.classificationPanelAccord.setEnabled(False)
            self.otoklimdlg.generatemapPanel.hide()
            self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.hide()
            self.otoklimdlg.generatecsvPanelAccord.setEnabled(False)

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
            self.otoklimdlg.classificationPanel.setEnabled(False)
            self.otoklimdlg.classificationPanel.hide()
            self.otoklimdlg.classificationPanelAccord.setEnabled(False)
            self.otoklimdlg.generatemapPanel.setEnabled(False)
            self.otoklimdlg.generatemapPanel.hide()
            self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.hide()
            self.otoklimdlg.generatecsvPanelAccord.setEnabled(False)

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
            self.otoklimdlg.classificationPanel.setEnabled(False)
            self.otoklimdlg.classificationPanel.hide()
            self.otoklimdlg.classificationPanelAccord.setEnabled(False)
            self.otoklimdlg.generatemapPanel.setEnabled(False)
            self.otoklimdlg.generatemapPanel.hide()
            self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.hide()
            self.otoklimdlg.generatecsvPanelAccord.setEnabled(False)

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
            self.otoklimdlg.classificationPanel.setEnabled(False)
            self.otoklimdlg.classificationPanel.hide()
            self.otoklimdlg.classificationPanelAccord.setEnabled(False)
            self.otoklimdlg.generatemapPanel.setEnabled(False)
            self.otoklimdlg.generatemapPanel.hide()
            self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.hide()
            self.otoklimdlg.generatecsvPanelAccord.setEnabled(False)

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
            self.otoklimdlg.classificationPanel.setEnabled(False)
            self.otoklimdlg.classificationPanel.hide()
            self.otoklimdlg.classificationPanelAccord.setEnabled(False)
            self.otoklimdlg.generatemapPanel.setEnabled(False)
            self.otoklimdlg.generatemapPanel.hide()
            self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.hide()
            self.otoklimdlg.generatecsvPanelAccord.setEnabled(False)

    def edit_map_template_2(self):
        """Edit QGIS Map Template file"""
        maptemplate_file_2 = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.qpt"
        )
        if maptemplate_file_2:
            self.otoklimdlg.maptemplate2.setText(maptemplate_file_2)
            self.otoklimdlg.maptemplate2.setWhatsThis('edited')
            self.otoklimdlg.maptemplate2.setStyleSheet('color: red')
            self.otoklimdlg.idwinterpolationPanel.setEnabled(False)
            self.otoklimdlg.idwinterpolationPanel.hide()
            self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(False)
            self.otoklimdlg.classificationPanel.setEnabled(False)
            self.otoklimdlg.classificationPanel.hide()
            self.otoklimdlg.classificationPanelAccord.setEnabled(False)
            self.otoklimdlg.generatemapPanel.setEnabled(False)
            self.otoklimdlg.generatemapPanel.hide()
            self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.hide()
            self.otoklimdlg.generatecsvPanelAccord.setEnabled(False)

    def edit_map_template_3(self):
        """Edit QGIS Map Template file"""
        maptemplate_file_3 = QFileDialog.getOpenFileName(
            self.otoklimdlg,
            "",
            "",
            "*.qpt"
        )
        if maptemplate_file_3:
            self.otoklimdlg.maptemplate3.setText(maptemplate_file_3)
            self.otoklimdlg.maptemplate3.setWhatsThis('edited')
            self.otoklimdlg.maptemplate3.setStyleSheet('color: red')
            self.otoklimdlg.idwinterpolationPanel.setEnabled(False)
            self.otoklimdlg.idwinterpolationPanel.hide()
            self.otoklimdlg.idwinterpolationPanelAccord.setEnabled(False)
            self.otoklimdlg.classificationPanel.setEnabled(False)
            self.otoklimdlg.classificationPanel.hide()
            self.otoklimdlg.classificationPanelAccord.setEnabled(False)
            self.otoklimdlg.generatemapPanel.setEnabled(False)
            self.otoklimdlg.generatemapPanel.hide()
            self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.setEnabled(False)
            self.otoklimdlg.generatecsvPanel.hide()
            self.otoklimdlg.generatecsvPanelAccord.setEnabled(False)

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

    # Add vECTOR Classified To Canvas
    def add_ach_1_class(self):
        """Add ACH 1 Classified"""
        vector = self.otoklimdlg.addach_1_class.whatsThis()
        layer = QgsVectorLayer(vector, 'ach1', 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_ash_1_class(self):
        """Add ASH 1 Classified"""
        vector = self.otoklimdlg.addash_1_class.whatsThis()
        layer = QgsVectorLayer(vector, 'ash1', 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_pch_1_class(self):
        """Add PCH 1 Classified"""
        vector = self.otoklimdlg.addpch_1_class.whatsThis()
        layer = QgsVectorLayer(vector, 'pch1', 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_psh_1_class(self):
        """Add PSH 1 Classified"""
        vector = self.otoklimdlg.addpsh_1_class.whatsThis()
        layer = QgsVectorLayer(vector, 'psh1', 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_pch_2_class(self):
        """Add PCH 2 Classified"""
        vector = self.otoklimdlg.addpch_2_class.whatsThis()
        layer = QgsVectorLayer(vector, 'pch2', 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_psh_2_class(self):
        """Add PSH 2 Classified"""
        vector = self.otoklimdlg.addpsh_2_class.whatsThis()
        layer = QgsVectorLayer(vector, 'psh2', 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_pch_3_class(self):
        """Add PCH 3 Classified"""
        vector = self.otoklimdlg.addpch_3_class.whatsThis()
        layer = QgsRasterLayer(vector, 'pch3')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

    def add_psh_3_class(self):
        """Add PSH 3 Classified"""
        vector = self.otoklimdlg.addpsh_3_class.whatsThis()
        layer = QgsRasterLayer(vector, 'psh3')
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
            self.newprojectdlg.Input_rainpost.text(),
            self.newprojectdlg.Input_rainfall_class.text(),
            self.newprojectdlg.Input_normalrain_class.text(),
            self.newprojectdlg.Input_map_template.text(),
            self.newprojectdlg.Input_map_template_2.text(),
            self.newprojectdlg.Input_map_template_3.text()
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
            error_field_param = None
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
                if len(header) < 2:
                    error_field = "interpolation's parameters"
                else:
                    for param in header[1:]:
                        if param not in ['ACH_1', 'ASH_1', 'PCH_1', 'PSH_1', 'PCH_2', 'PSH_2', 'PCH_3', 'PSH_3']:
                            error_field_param = str(param) + ' unknown parameter' 
            if error_field:
                errormessage = error_field + ' field not exists on file header'
                raise Exception(errormessage)
                item = QListWidgetItem(errormessage)
                self.projectprogressdlg.ProgressList.addItem(item)
            if error_field_param:
                errormessage = error_field_param
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
                        if 'ACH_1' in row:
                            if row['ACH_1'].strip() == '':
                                pass
                            else:
                                float(row['ACH_1'])
                    except:
                        error_message = ': ACH_1 [' + row['ACH_1'] + '] value must be float'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        if 'ASH_1' in row:
                            if row['ASH_1'].strip() == '':
                                pass
                            else:
                                float(row['ASH_1'])
                    except:
                        error_message = ': ASH_1 [' + row['ASH_1'] + '] value must be float'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        if 'PCH_1' in row:
                            if row['PCH_1'].strip() == '':
                                pass
                            else:
                                float(row['PCH_1'])
                    except:
                        error_message = ': PCH_1 [' + row['PCH_1'] + '] value must be float'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        if 'PSH_1' in row:
                            if row['PSH_1'].strip() == '':
                                pass
                            else:
                                float(row['PSH_1'])
                    except:
                        error_message = ': PSH_1 [' + row['PSH_1'] + '] value must be float'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        if 'PCH_2' in row:
                            if row['PCH_2'].strip() == '':
                                pass
                            else:
                                float(row['PCH_2'])
                    except:
                        error_message = ': PCH_2 [' + row['PCH_2'] + '] value must be float'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        if 'PSH_2' in row:
                            if row['PSH_2'].strip() == '':
                                pass
                            else:
                                float(row['PSH_2'])
                    except:
                        error_message = ': PSH_2 [' + row['PSH_2'] + '] value must be float'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        if 'PCH_3' in row:
                            if row['PCH_3'].strip() == '':
                                pass
                            else:
                                float(row['PCH_3'])
                    except:
                        error_message = ': PCH_3 [' + row['PCH_3'] + '] value must be float'
                        errormessage = 'error at line: ' + str(line) + error_message
                        raise Exception(errormessage)
                    try:
                        if 'PSH_3' in row:
                            if row['PSH_3'].strip() == '':
                                pass
                            else:
                                float(row['PSH_3'])
                    except:
                        error_message = ': PSH_3 [' + row['PSH_3'] + '] value must be float'
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

    def show_interpolate_folder(self):
        """Show Interpolate file folder"""
        project = os.path.join(
            self.otoklimdlg.projectworkspace.text(),
            self.otoklimdlg.projectfilename.text()
        )
        with open(project, 'r') as jsonfile:
            otoklim_project = json.load(jsonfile)
            interpolate_workspace = otoklim_project["LOCATION"]["INTER_FILE_LOC"]
        process_var = 'explorer ' + interpolate_workspace
        subprocess.Popen(process_var)

    def show_classification_folder(self):
        """Show Classification file folder"""
        project = os.path.join(
            self.otoklimdlg.projectworkspace.text(),
            self.otoklimdlg.projectfilename.text()
        )
        with open(project, 'r') as jsonfile:
            otoklim_project = json.load(jsonfile)
            interpolate_workspace = otoklim_project["LOCATION"]["CLASS_FILE_LOC"]
        process_var = 'explorer ' + interpolate_workspace
        subprocess.Popen(process_var)

    def show_generatemap_folder(self):
        """Show Generated Map Folder"""
        project = os.path.join(
            self.otoklimdlg.projectworkspace.text(),
            self.otoklimdlg.projectfilename.text()
        )
        with open(project, 'r') as jsonfile:
            otoklim_project = json.load(jsonfile)
            interpolate_workspace = otoklim_project["LOCATION"]["MAP_FILE_LOC"]
        process_var = 'explorer ' + interpolate_workspace
        subprocess.Popen(process_var)

    def show_generatecsv_folder(self):
        """Show Generated CSV Folder"""
        project = os.path.join(
            self.otoklimdlg.projectworkspace.text(),
            self.otoklimdlg.projectfilename.text()
        )
        with open(project, 'r') as jsonfile:
            otoklim_project = json.load(jsonfile)
            interpolate_workspace = otoklim_project["LOCATION"]["CSV_FILE_LOC"]
        process_var = 'explorer ' + interpolate_workspace
        subprocess.Popen(process_var)

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
            if self.otoklimdlg.maptemplate2.whatsThis() == 'edited':
                self.copy_file(self.otoklimdlg.maptemplate2.text(), input_directory, False)
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["FILE"]["MAP_TEMP_2"]["NAME"] = os.path.basename(self.otoklimdlg.maptemplate2.text())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.maptemplate2.setStyleSheet('color: black')
                self.otoklimdlg.maptemplate2.setWhatsThis('')
                change = True
            if self.otoklimdlg.maptemplate3.whatsThis() == 'edited':
                self.copy_file(self.otoklimdlg.maptemplate3.text(), input_directory, False)
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["FILE"]["MAP_TEMP_3"]["NAME"] = os.path.basename(self.otoklimdlg.maptemplate3.text())
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                self.otoklimdlg.maptemplate3.setStyleSheet('color: black')
                self.otoklimdlg.maptemplate3.setWhatsThis('')
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
                self.read_otoklim_file(otoklim_project, True)
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
            self.otoklimdlg.rainfallfile.setWhatsThis('')
            self.otoklimdlg.rainfallfile.setStyleSheet('color: black')
            self.otoklimdlg.normalrainfile.setWhatsThis('')
            self.otoklimdlg.normalrainfile.setStyleSheet('color: black')
            self.otoklimdlg.maptemplate.setWhatsThis('')
            self.otoklimdlg.maptemplate.setStyleSheet('color: black')
            self.otoklimdlg.maptemplate2.setWhatsThis('')
            self.otoklimdlg.maptemplate2.setStyleSheet('color: black')
            self.otoklimdlg.maptemplate3.setWhatsThis('')
            self.otoklimdlg.maptemplate3.setStyleSheet('color: black')
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
            csv_rainfall = self.newprojectdlg.Input_rainfall_class.text()
            csv_normalrain = self.newprojectdlg.Input_normalrain_class.text()
            map_template = self.newprojectdlg.Input_map_template.text()
            map_template_2 = self.newprojectdlg.Input_map_template_2.text()
            map_template_3 = self.newprojectdlg.Input_map_template_3.text()
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
            csv_rainfall = self.otoklimdlg.rainfallfile.text()
            csv_normalrain = self.otoklimdlg.normalrainfile.text()
            map_template = self.otoklimdlg.maptemplate.text()
            map_template_2 = self.otoklimdlg.maptemplate2.text()
            map_template_3 = self.otoklimdlg.maptemplate3.text()
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
                # Log Folder
                log_directory = os.path.join(processing_directory, 'log')
                replace_confirm(log_directory)
                # Interpolated & Classified Folder
                interpolated_directory = os.path.join(processing_directory, 'interpolated')
                replace_confirm(interpolated_directory)
                classified_directory = os.path.join(processing_directory, 'classified')
                replace_confirm(classified_directory)
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
                # Copy Map Template 2 File
                message = 'Checking QGIS Map Template 2 Files..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item)
                self.copy_file(map_template_2, input_directory, False)
                item.setText(message + ' Done')
                self.projectprogressdlg.ProgressList.addItem(item)
                # Copy Map Template 3 File
                message = 'Checking QGIS Map Template 3 Files..'
                item = QListWidgetItem(message)
                self.projectprogressdlg.ProgressList.addItem(item)
                self.copy_file(map_template_3, input_directory, False)
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
                        "INTER_FILE_LOC": interpolated_directory,
                        "CLASS_FILE_LOC": classified_directory,
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
                        "MAP_TEMP_2": {
                            "NAME": os.path.basename(map_template_2),
                            "LOCATION": "IN_FILE_LOC",
                            "FORMAT": "QPT",
                        },
                        "MAP_TEMP_3": {
                            "NAME": os.path.basename(map_template_3),
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
                                "LOCATION": "INTER_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_ASH_1": {
                                "NAME": "",
                                "LOCATION": "INTER_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PCH_1": {
                                "NAME": "",
                                "LOCATION": "INTER_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PSH_1": {
                                "NAME": "",
                                "LOCATION": "INTER_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PCH_2": {
                                "NAME": "",
                                "LOCATION": "INTER_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PSH_2": {
                                "NAME": "",
                                "LOCATION": "INTER_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PCH_3": {
                                "NAME": "",
                                "LOCATION": "INTER_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PSH_3": {
                                "NAME": "",
                                "LOCATION": "INTER_FILE_LOC",
                                "FORMAT": "TIF"
                            }
                        },
                        "CLASSIFICATION": {
                            "PROCESSED": 0,
                            "RASTER_ACH_1": {
                                "NAME": "",
                                "LOCATION": "CLASS_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_ASH_1": {
                                "NAME": "",
                                "LOCATION": "CLASS_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PCH_1": {
                                "NAME": "",
                                "LOCATION": "CLASS_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PSH_1": {
                                "NAME": "",
                                "LOCATION": "CLASS_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PCH_2": {
                                "NAME": "",
                                "LOCATION": "CLASS_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PSH_2": {
                                "NAME": "",
                                "LOCATION": "CLASS_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PCH_3": {
                                "NAME": "",
                                "LOCATION": "CLASS_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                            "RASTER_PSH_3": {
                                "NAME": "",
                                "LOCATION": "CLASS_FILE_LOC",
                                "FORMAT": "TIF"
                            },
                        },
                        "GENERATE_MAP": {
                            "PROCESSED": 0,
                            "RASTER_ACH_1": {
                                "REGION_LIST": "",
                                "LOCATION": "MAP_FILE_LOC",
                                "FORMAT": "PDF"
                            },
                            "RASTER_ASH_1": {
                                "REGION_LIST": "",
                                "LOCATION": "MAP_FILE_LOC",
                                "FORMAT": "PDF"
                            },
                            "RASTER_PCH_1": {
                                "REGION_LIST": "",
                                "LOCATION": "MAP_FILE_LOC",
                                "FORMAT": "PDF"
                            },
                            "RASTER_PSH_1": {
                                "REGION_LIST": "",
                                "LOCATION": "MAP_FILE_LOC",
                                "FORMAT": "PDF"
                            },
                            "RASTER_PCH_2": {
                                "REGION_LIST": "",
                                "LOCATION": "MAP_FILE_LOC",
                                "FORMAT": "PDF"
                            },
                            "RASTER_PSH_2": {
                                "REGION_LIST": "",
                                "LOCATION": "MAP_FILE_LOC",
                                "FORMAT": "PDF"
                            },
                            "RASTER_PCH_3": {
                                "REGION_LIST": "",
                                "LOCATION": "MAP_FILE_LOC",
                                "FORMAT": "PDF"
                            },
                            "RASTER_PSH_3": {
                                "REGION_LIST": "",
                                "LOCATION": "MAP_FILE_LOC",
                                "FORMAT": "PDF"
                            },
                        },
                        "GENERATE_CSV": {
                            "PROCESSED": 0,
                            "RASTER_ACH_1": {
                                "REGION_LIST": "",
                                "LOCATION": "CSV_FILE_LOC",
                                "FORMAT": "CSV"
                            },
                            "RASTER_ASH_1": {
                                "REGION_LIST": "",
                                "LOCATION": "CSV_FILE_LOC",
                                "FORMAT": "CSV"
                            },
                            "RASTER_PCH_1": {
                                "REGION_LIST": "",
                                "LOCATION": "CSV_FILE_LOC",
                                "FORMAT": "CSV"
                            },
                            "RASTER_PSH_1": {
                                "REGION_LIST": "",
                                "LOCATION": "CSV_FILE_LOC",
                                "FORMAT": "CSV"
                            },
                            "RASTER_PCH_2": {
                                "REGION_LIST": "",
                                "LOCATION": "CSV_FILE_LOC",
                                "FORMAT": "CSV"
                            },
                            "RASTER_PSH_2": {
                                "REGION_LIST": "",
                                "LOCATION": "CSV_FILE_LOC",
                                "FORMAT": "CSV"
                            },
                            "RASTER_PCH_3": {
                                "REGION_LIST": "",
                                "LOCATION": "CSV_FILE_LOC",
                                "FORMAT": "CSV"
                            },
                            "RASTER_PSH_3": {
                                "REGION_LIST": "",
                                "LOCATION": "CSV_FILE_LOC",
                                "FORMAT": "CSV"
                            },
                        }
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
            self.otoklimdlg.rainfallfile.whatsThis(),
            self.otoklimdlg.normalrainfile.whatsThis(),
            self.otoklimdlg.maptemplate.whatsThis(),
            self.otoklimdlg.maptemplate2.whatsThis(),
            self.otoklimdlg.maptemplate3.whatsThis(),
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
            mth_s = '01'
        elif mth == 'Februari':
            mth = 2
            mth_s = '02'
        elif mth == 'Maret':
            mth = 3
            mth_s = '03'
        elif mth == 'April':
            mth = 4
            mth_s = '04'
        elif mth == 'Mei':
            mth = 5
            mth_s = '05'
        elif mth == 'Juni':
            mth = 6
            mth_s = '06'
        elif mth == 'Juli':
            mth = 7
            mth_s = '07'
        elif mth == 'Agustus':
            mth = 8
            mth_s = '08'
        elif mth == 'September':
            mth = 9
            mth_s = '09'
        elif mth == 'Oktober':
            mth = 10
            mth_s = '10'
        elif mth == 'November':
            mth = 11
            mth_s = '11'
        else:
            mth = 12
            mth_s = '12'

        month_dict = {
            0: ['DES', 'DESEMBER', '12'],
            1: ['JAN', 'JANUARI', '01'],
            2: ['FEB', 'FEBRUARI', '02'],
            3: ['MAR', 'MARET', '03'],
            4: ['APR', 'APRIL', '04'],
            5: ['MEI', 'MEI', '05'],
            6: ['JUN', 'JUNI', '06'],
            7: ['JUL', 'JULI', '07'],
            8: ['AGT', 'AGUSTUS', '08'],
            9: ['SEP', 'SEPTEMBER', '09'],
            10: ['OKT', 'OKTOBER', '10'],
            11: ['NOV', 'NOVEMBER', '11'],
            12: ['DES', 'DESEMBER', '12'],
            13: ['JAN', 'JANUARI', '01'],
            14: ['FEB', 'FEBRUARI', '02'],
            15: ['MAR', 'MARET', '03'],
            16: ['APR', 'APRIL', '04']
        }
        amth = month_dict[mth-1]
        pmth_1 = month_dict[mth+1]
        pmth_2 = month_dict[mth+2]
        pmth_3 = month_dict[mth+3]
        month_header = [amth, pmth_1, pmth_2, pmth_3, mth_s]

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
        years_header = [ayrs, pyrs_1, pyrs_2, pyrs_3, yrs]
        return month_header, years_header

    def logger(self, prc_dir):
        """Function to trigger python logging"""
        log_dir = os.path.join(prc_dir, 'log')
        log_filename = os.path.join(log_dir, 'otoklim_' + '{:%Y%m%d_%H%M%S}'.format(datetime.datetime.now()) + '.log')
        try:
            os.remove(log_filename)
        except OSError:
            pass
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        fh = logging.FileHandler(log_filename)
        formatter = logging.Formatter("%(asctime)s - [%(levelname)s] %(message)s")
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        logger.addHandler(ch)
        logger.addHandler(fh)
        logger.info('Running start at ' + '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()))
        return logger
    
    def interpolate_idw(self):
        """Function To Run IDW Interpolation"""
        prcs_directory = os.path.join(self.otoklimdlg.projectworkspace.text(), 'processing')
        logger = self.logger(prcs_directory)
        logger.info('Interpolate Stasiun Point By Using IDW Method..')
        self.iface.mainWindow().statusBar().showMessage('Interpolate Stasiun Point By Using IDW Method..')
        interpolated_directory = os.path.join(prcs_directory, 'interpolated')
        provinsi_polygon_file = os.path.join(prcs_directory, 'provinsi_polygon.shp')
        layer_provinsi = QgsVectorLayer(provinsi_polygon_file, 'layer', 'ogr')
        temp = os.path.join(prcs_directory, 'tmp_' + '{:%Y%m%d_%H%M%S}'.format(datetime.datetime.now()))
        os.mkdir(temp)
        combine_file = os.path.join(prcs_directory, 'combine.csv')
        logger.debug('- Read stasiun point data')
        with open(combine_file, "r") as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader)
            idw_params = headers[5:]
        project = os.path.join(
            self.otoklimdlg.projectworkspace.text(),
            self.otoklimdlg.projectfilename.text()
        )
        try:
            logger.debug('- Listing selected parameter to be processed')
            prc_list = []
            if self.otoklimdlg.ach_1.isChecked():
                logger.debug('-- ' + str(idw_params[0]) + ' is checked')
                prc_list.append(idw_params[0])
                self.otoklimdlg.addach_1.setEnabled(True)
                self.otoklimdlg.addach_1.setWhatsThis(
                    os.path.join(interpolated_directory, 'interpolated_' + str(idw_params[0]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_ACH_1"]["NAME"] = 'interpolated_' + str(idw_params[0]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
            if self.otoklimdlg.ash_1.isChecked():
                logger.debug('-- ' + str(idw_params[1]) + ' is checked')
                prc_list.append(idw_params[1])
                self.otoklimdlg.addash_1.setEnabled(True)
                self.otoklimdlg.addash_1.setWhatsThis(
                    os.path.join(interpolated_directory, 'interpolated_' + str(idw_params[1]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_ASH_1"]["NAME"] = 'interpolated_' + str(idw_params[1]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
            if self.otoklimdlg.pch_1.isChecked():
                logger.debug('-- ' + str(idw_params[2]) + ' is checked')
                prc_list.append(idw_params[2])
                self.otoklimdlg.addpch_1.setEnabled(True)
                self.otoklimdlg.addpch_1.setWhatsThis(
                    os.path.join(interpolated_directory, 'interpolated_' + str(idw_params[2]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_1"]["NAME"] = 'interpolated_' + str(idw_params[2]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
            if self.otoklimdlg.psh_1.isChecked():
                logger.debug('-- ' + str(idw_params[3]) + ' is checked')
                prc_list.append(idw_params[3])
                self.otoklimdlg.addpsh_1.setEnabled(True)
                self.otoklimdlg.addpsh_1.setWhatsThis(
                    os.path.join(interpolated_directory, 'interpolated_' + str(idw_params[3]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_1"]["NAME"] = 'interpolated_' + str(idw_params[3]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
            if self.otoklimdlg.pch_2.isChecked():
                logger.debug('-- ' + str(idw_params[4]) + ' is checked')
                prc_list.append(idw_params[4])
                self.otoklimdlg.addpch_2.setEnabled(True)
                self.otoklimdlg.addpch_2.setWhatsThis(
                    os.path.join(interpolated_directory, 'interpolated_' + str(idw_params[4]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_2"]["NAME"] = 'interpolated_' + str(idw_params[4]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
            if self.otoklimdlg.psh_2.isChecked():
                logger.debug('-- ' + str(idw_params[5]) + ' is checked')
                prc_list.append(idw_params[5])
                self.otoklimdlg.addpsh_2.setEnabled(True)
                self.otoklimdlg.addpsh_2.setWhatsThis(
                    os.path.join(interpolated_directory, 'interpolated_' + str(idw_params[5]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_2"]["NAME"] = 'interpolated_' + str(idw_params[5]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
            if self.otoklimdlg.pch_3.isChecked():
                logger.debug('-- ' + str(idw_params[6]) + ' is checked')
                prc_list.append(idw_params[6])
                self.otoklimdlg.addpch_3.setEnabled(True)
                self.otoklimdlg.addpch_3.setWhatsThis(
                    os.path.join(interpolated_directory, 'interpolated_' + str(idw_params[6]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_3"]["NAME"] = 'interpolated_' + str(idw_params[6]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
            if self.otoklimdlg.psh_3.isChecked():
                logger.debug('-- ' + str(idw_params[7]) + ' is checked')
                prc_list.append(idw_params[7])
                self.otoklimdlg.addpsh_3.setEnabled(True)
                self.otoklimdlg.addpsh_3.setWhatsThis(
                    os.path.join(interpolated_directory, 'interpolated_' + str(idw_params[7]).lower() + '.tif')
                )
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_3"]["NAME"] = 'interpolated_' + str(idw_params[7]).lower() + '.tif'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))

            logger.info('- Selected parameter :' + str(prc_list))
            for param in prc_list:
                logger.info('-- Field (Parameter) : ' + param)
                logger.debug('-- Interpolating in progress...')
                filename_shp = os.path.join(prcs_directory, 'rainpost_point_' + str(param) + '.shp')
                self.copy_file(filename_shp, temp, True)
                filename_shp_tmp = os.path.join(temp, 'rainpost_point_' + str(param) + '.shp')
                layer = QgsVectorLayer(filename_shp_tmp, 'layer', 'ogr')
                fields = layer.pendingFields()
                field_names = [field.name() for field in fields]
                raster_interpolated = os.path.join(temp, param + '_raster_idw.tif')
                raster_cropped = os.path.join(interpolated_directory, 'interpolated_' + str(param).lower() + '.tif')
                if os.path.exists(raster_cropped):
                    self.replaceconfirmdlg.var.setText(raster_cropped)
                    result = self.replaceconfirmdlg.exec_()
                    if result:
                        os.remove(raster_cropped)
                    else:
                        raise Exception('Skip ' + raster_cropped)

                extent = layer_provinsi.extent()
                logger.info('-- runalg v.surf.idw')
                processing.runalg(
                    'grass7:v.surf.idw',
                    layer, 8.0, 5.0, param, False,
                    "%f,%f,%f,%f" % (extent.xMinimum(), extent.xMaximum(), extent.yMinimum(), extent.yMaximum()), 0.001, -1.0, 0.0001,
                    raster_interpolated
                )
                logger.info('-- runalg saga:clipgridwithpolygon')
                processing.runalg('saga:clipgridwithpolygon', raster_interpolated, provinsi_polygon_file, raster_cropped)
                logger.info('-- Interpolating success.. Raster data has been stored on ' + str(raster_cropped))
            with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["PROCESSED"] = 1
            with open(project, 'w') as jsonfile:
                jsonfile.write(json.dumps(otoklim_project, indent=4))
            self.otoklimdlg.showInterpolateFolder.setEnabled(True)
            self.otoklimdlg.testParameter.setEnabled(False)
            self.otoklimdlg.classificationPanelAccord.setEnabled(True)
            self.otoklimdlg.classificationPanel.setEnabled(True)
            self.otoklimdlg.classificationPanel.show()
        except Exception as e:
            self.errormessagedlg.ErrorMessage.setText(str(e))
            logger.error(str(e))
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
            delimiter = self.otoklimdlg.csvdelimiter.text()
            file_input = self.otoklimdlg.Input_Value_CSV.text()
            rainpost_file = self.otoklimdlg.rainpostfile.text()
            combine_file = os.path.join(file_directory, 'combine.csv')
            date = self.select_date_now()
            months = date[0]
            years = date[1]
            try:
                self.check_csv(file_input, delimiter, 'input_value')
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
                            mo = 0
                            for month in months:
                                if mo == 4:
                                    break
                                try:
                                    idw_params[n] = idw_params[n].split('_')[0] + '_' + str(month[0])
                                except IndexError:
                                    pass
                                try:
                                    idw_params[n+1] = idw_params[n+1].split('_')[0] + '_' + str(month[0])
                                except IndexError:
                                    pass
                                n += 2
                                mo += 1
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
                for param in idw_params:
                    filename_shp = os.path.join(file_directory, 'rainpost_point_' + str(param) + '.shp')
                    filename_prj = os.path.join(file_directory, 'rainpost_point_' + str(param) + '.shp')
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
                        hdr = []
                        for h in headers:
                            if n <= 2:
                                layer.CreateField(ogr.FieldDefn(h, ogr.OFTString))
                            else:
                                if n > 4:
                                    if h == param:
                                        layer.CreateField(ogr.FieldDefn(h, ogr.OFTReal))
                                    else:
                                        hdr.append(h)
                                else:
                                    layer.CreateField(ogr.FieldDefn(h, ogr.OFTReal))
                            n += 1
                        headers = [h for h in headers if h not in hdr]
                    with open(csv_file, 'rb') as csvfile:
                        spamreader = csv.DictReader(csvfile, delimiter=str(delimiter), quotechar='|')
                        for row in spamreader:
                            create_feature = True
                            point = ogr.Geometry(ogr.wkbPoint)
                            feature = ogr.Feature(layer.GetLayerDefn())
                            point.AddPoint(float(row['lon']), float(row['lat']))
                            for h in headers:
                                if h in header_input:
                                    if row[h]:
                                        feature.SetField(h, row[h])
                                    else:
                                        create_feature = False
                                else:
                                    feature.SetField(h, row[h])
                            if create_feature:
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
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]['PROCESSED'] = 0
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_ACH_1"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_ASH_1"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_PCH_1"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_PSH_1"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_PCH_2"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_PSH_2"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_PCH_3"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_PSH_3"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]['PROCESSED'] = 0
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_ACH_1"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_ASH_1"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_PCH_1"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_PSH_1"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_PCH_2"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_PSH_2"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_PCH_3"]["REGION_LIST"] = ""
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_PSH_3"]["REGION_LIST"] = ""
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
                self.otoklimdlg.ach_1_class.setChecked(False)
                self.otoklimdlg.ash_1_class.setChecked(False)
                self.otoklimdlg.pch_1_class.setChecked(False)
                self.otoklimdlg.psh_1_class.setChecked(False)
                self.otoklimdlg.pch_2_class.setChecked(False)
                self.otoklimdlg.psh_2_class.setChecked(False)
                self.otoklimdlg.pch_3_class.setChecked(False)
                self.otoklimdlg.psh_3_class.setChecked(False)
                self.otoklimdlg.addach_1_class.setEnabled(False)
                self.otoklimdlg.addash_1_class.setEnabled(False)
                self.otoklimdlg.addpch_1_class.setEnabled(False)
                self.otoklimdlg.addpsh_1_class.setEnabled(False)
                self.otoklimdlg.addpch_2_class.setEnabled(False)
                self.otoklimdlg.addpsh_2_class.setEnabled(False)
                self.otoklimdlg.addpch_3_class.setEnabled(False)
                self.otoklimdlg.addpsh_3_class.setEnabled(False)
                self.otoklimdlg.ach_1_map.setChecked(False)
                self.otoklimdlg.ash_1_map.setChecked(False)
                self.otoklimdlg.pch_1_map.setChecked(False)
                self.otoklimdlg.psh_1_map.setChecked(False)
                self.otoklimdlg.pch_2_map.setChecked(False)
                self.otoklimdlg.psh_2_map.setChecked(False)
                self.otoklimdlg.pch_3_map.setChecked(False)
                self.otoklimdlg.psh_3_map.setChecked(False)
                self.otoklimdlg.ach_1_csv.setChecked(False)
                self.otoklimdlg.ash_1_csv.setChecked(False)
                self.otoklimdlg.pch_1_csv.setChecked(False)
                self.otoklimdlg.psh_1_csv.setChecked(False)
                self.otoklimdlg.pch_2_csv.setChecked(False)
                self.otoklimdlg.psh_2_csv.setChecked(False)
                self.otoklimdlg.pch_3_csv.setChecked(False)
                self.otoklimdlg.psh_3_csv.setChecked(False)
                self.otoklimdlg.classificationPanelAccord.setEnabled(False)
                self.otoklimdlg.classificationPanel.hide()
                self.otoklimdlg.generatemapPanelAccord.setEnabled(False)
                self.otoklimdlg.generatemapPanel.hide()
                self.otoklimdlg.generatecsvPanelAccord.setEnabled(False)
                self.otoklimdlg.generatecsvPanel.hide()
            except Exception as e:
                print e
                self.otoklimdlg.groupBox_3.setEnabled(False)
                self.errormessagedlg.ErrorMessage.setText(str(e))
                self.errormessagedlg.exec_()

    def raster_classify(self):
        """Function To Classify Raster Interpolated"""
        prcs_directory = os.path.join(self.otoklimdlg.projectworkspace.text(), 'processing')
        logger = self.logger(prcs_directory)
        logger.info('Classify Raster..')
        self.iface.mainWindow().statusBar().showMessage('Classify Raster..')
        classified_directory = os.path.join(prcs_directory, 'classified')
        interpolated_directory = os.path.join(prcs_directory, 'interpolated')
        provinsi_polygon_file = os.path.join(prcs_directory, 'provinsi_polygon.shp')
        layer_provinsi = QgsVectorLayer(provinsi_polygon_file, 'layer', 'ogr')
        filename_rainfall = self.otoklimdlg.rainfallfile.text()
        output_rainfall = os.path.join(prcs_directory, 'rule_ch.txt')
        if os.path.exists(output_rainfall):
            os.remove(output_rainfall)
        row_keeper = []
        logger.debug('- Read classification rule from ', filename_rainfall)
        with open(filename_rainfall, 'rb') as csvfile:
            spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
            for row in spamreader:
                row_keeper.append([row['lower_limit'], row['upper_limit'], row['new_value']])
        logger.debug('- Write classification rule to ', output_rainfall)
        with open(output_rainfall, "wb+") as txtfile:
            txt_writer = csv.writer(txtfile, delimiter=':')
            for row in row_keeper:
                txt_writer.writerow(row)
        filename_normalrain = self.otoklimdlg.normalrainfile.text()
        output_normalrain = os.path.join(prcs_directory, 'rule_sh.txt')
        if os.path.exists(output_normalrain):
            os.remove(output_normalrain)
        row_keeper = []
        logger.debug('- Read classification rule from ', filename_normalrain)
        with open(filename_normalrain, 'rb') as csvfile:
            spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
            for row in spamreader:
                row_keeper.append([row['lower_limit'], row['upper_limit'], row['new_value']])
        logger.debug('- Write classification rule to ', output_normalrain)
        with open(output_normalrain, "wb+") as txtfile:
            txt_writer = csv.writer(txtfile, delimiter=':')
            for row in row_keeper:
                txt_writer.writerow(row)
        project = os.path.join(
            self.otoklimdlg.projectworkspace.text(),
            self.otoklimdlg.projectfilename.text()
        )
        try:
            logger.debug('- Listing selected parameter to be processed')
            prc_list = []
            if self.otoklimdlg.ach_1_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_ach_1 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_ACH_1"]["NAME"]
                    param = os.path.splitext(raster_ach_1)[0].split('_')[1] + '_' + os.path.splitext(raster_ach_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_ACH_1"]["NAME"] = 'classified_' + str(param) + '.shp'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_ach_1])
                self.otoklimdlg.addach_1_class.setEnabled(True)
                self.otoklimdlg.addach_1_class.setWhatsThis(
                    os.path.join(classified_directory, 'classified_' + str(param) + '.shp')
                )
                logger.debug('-- ' + str(param) + ' is checked')
            if self.otoklimdlg.ash_1_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_ash_1 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_ASH_1"]["NAME"]
                    param = os.path.splitext(raster_ash_1)[0].split('_')[1] + '_' + os.path.splitext(raster_ash_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_ASH_1"]["NAME"] = 'classified_' + str(param) + '.shp'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_ash_1])
                self.otoklimdlg.addash_1_class.setEnabled(True)
                self.otoklimdlg.addash_1_class.setWhatsThis(
                    os.path.join(classified_directory, 'classified_' + str(param) + '.shp')
                )
                logger.debug('-- ' + str(param) + ' is checked')
            if self.otoklimdlg.pch_1_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_pch_1 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_1"]["NAME"]
                    param = os.path.splitext(raster_pch_1)[0].split('_')[1] + '_' + os.path.splitext(raster_pch_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_1"]["NAME"] = 'classified_' + str(param) + '.shp'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_pch_1])
                self.otoklimdlg.addpch_1_class.setEnabled(True)
                self.otoklimdlg.addpch_1_class.setWhatsThis(
                    os.path.join(classified_directory, 'classified_' + str(param) + '.shp')
                )
                logger.debug('-- ' + str(param) + ' is checked')
            if self.otoklimdlg.psh_1_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_psh_1 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_1"]["NAME"]
                    param = os.path.splitext(raster_psh_1)[0].split('_')[1] + '_' + os.path.splitext(raster_psh_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_1"]["NAME"] = 'classified_' + str(param) + '.shp'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_psh_1])
                self.otoklimdlg.addpsh_1_class.setEnabled(True)
                self.otoklimdlg.addpsh_1_class.setWhatsThis(
                    os.path.join(classified_directory, 'classified_' + str(param) + '.shp')
                )
                logger.debug('-- ' + str(param) + ' is checked')
            if self.otoklimdlg.pch_2_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_pch_2 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_2"]["NAME"]
                    param = os.path.splitext(raster_pch_2)[0].split('_')[1] + '_' + os.path.splitext(raster_pch_2)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_2"]["NAME"] = 'classified_' + str(param) + '.shp'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_pch_2])
                self.otoklimdlg.addpch_2_class.setEnabled(True)
                self.otoklimdlg.addpch_2_class.setWhatsThis(
                    os.path.join(classified_directory, 'classified_' + str(param) + '.shp')
                )
                logger.debug('-- ' + str(param) + ' is checked')
            if self.otoklimdlg.psh_2_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_psh_2 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_2"]["NAME"]
                    param = os.path.splitext(raster_psh_2)[0].split('_')[1] + '_' + os.path.splitext(raster_psh_2)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_2"]["NAME"] = 'classified_' + str(param) + '.shp'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_psh_2])
                self.otoklimdlg.addpsh_2_class.setEnabled(True)
                self.otoklimdlg.addpsh_2_class.setWhatsThis(
                    os.path.join(classified_directory, 'classified_' + str(param) + '.shp')
                )
                logger.debug(str(param) + ' is checked')
            if self.otoklimdlg.pch_3_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_pch_3 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PCH_3"]["NAME"]
                    param = os.path.splitext(raster_pch_3)[0].split('_')[1] + '_' + os.path.splitext(raster_pch_3)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_3"]["NAME"] = 'classified_' + str(param) + '.shp'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_pch_3])
                self.otoklimdlg.addpch_3_class.setEnabled(True)
                self.otoklimdlg.addpch_3_class.setWhatsThis(
                    os.path.join(classified_directory, 'classified_' + str(param) + '.shp')
                )
                logger.debug('-- ' + str(param) + ' is checked')
            if self.otoklimdlg.psh_3_class.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_psh_3 = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["RASTER_PSH_3"]["NAME"]
                    param = os.path.splitext(raster_psh_3)[0].split('_')[1] + '_' + os.path.splitext(raster_psh_3)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_3"]["NAME"] = 'classified_' + str(param) + '.shp'
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_psh_3])
                self.otoklimdlg.addpsh_3_class.setEnabled(True)
                self.otoklimdlg.addpsh_3_class.setWhatsThis(
                    os.path.join(classified_directory, 'classified_' + str(param) + '.shp')
                )
                logger.debug('-- ' + str(param) + ' is checked')

            logger.info('- Selected parameter :' + str(prc_list))
            for value in prc_list:
                logger.info('-- Field (Parameter) : ' + value[0])
                logger.debug('-- Classification In Progress in progress...')
                raster_classified = os.path.join(classified_directory, 'classified_' + str(value[0]) + '.tif')
                rasterinterpolated = os.path.join(interpolated_directory, value[1])
                if os.path.exists(raster_classified):
                    self.replaceconfirmdlg.var.setText(raster_classified)
                    result = self.replaceconfirmdlg.exec_()
                    if result:
                        os.remove(raster_classified)
                    else:
                        raise Exception('Skip ' + raster_classified)
                extent = layer_provinsi.extent()
                logger.info('-- grass7:r.recode')
                if value[0][0:3] == 'ach' or value[0][0:3] == 'pch':
                    processing.runalg(
                        'grass7:r.recode',
                        rasterinterpolated,
                        output_rainfall,
                        False,
                        "%f,%f,%f,%f" % (extent.xMinimum(), extent.xMaximum(), extent.yMinimum(), extent.yMaximum()),
                        0.001,
                        raster_classified
                    )
                else:
                    processing.runalg(
                        'grass7:r.recode',
                        rasterinterpolated,
                        output_normalrain,
                        False,
                        "%f,%f,%f,%f" % (extent.xMinimum(), extent.xMaximum(), extent.yMinimum(), extent.yMaximum()),
                        0.001,
                        raster_classified
                    )

                # Raster to Vector Conversion (Special Case)
                vector_classified = os.path.join(classified_directory, 'classified_' + str(value[0]) + '.shp')
                if os.path.exists(vector_classified):
                    QgsVectorFileWriter.deleteShapeFile(vector_classified)
                    try:
                        os.remove(os.path.splitext(vector_classified)[0] +  '.cpg')
                    except OSError:
                        pass
                # Polygonize
                logger.info('-- gdalogr:polygonize')
                processing.runalg("gdalogr:polygonize", raster_classified, "DN", vector_classified)
                logger.info('-- Classification success.. Vector data has been stored on ' + str(vector_classified))
                # Add Attribute
                logger.debug('-- Add new attribute to vector classified..')
                layer_vector_classified = QgsVectorLayer(vector_classified, 'vector_classified', 'ogr')
                res = layer_vector_classified.dataProvider().addAttributes(
                    [
                        QgsField(str(value[0])[0:3].upper(), QVariant.String),
                        QgsField('Area', QVariant.Double),
                        QgsField('Percent', QVariant.Double),
                    ]
                )
                layer_vector_classified.updateFields()
                # Record Label, Value and Color
                label_value = {}
                if str(value[0])[0:3].upper() == 'ACH' or str(value[0])[0:3].upper() == 'PCH':
                    color = []
                    label = []
                    list_value = []
                    with open(self.otoklimdlg.rainfallfile.text(), 'rb') as csvfile:
                        spamreader = csv.DictReader(csvfile, delimiter=str(self.otoklimdlg.csvdelimiter.text()), quotechar='|')
                        for row in spamreader:
                            if str(row['lower_limit']) == '*':
                                label_str = '< ' + str(row['upper_limit'])
                                label.append(label_str)
                            elif str(row['upper_limit']) == '*':
                                label_str = '> ' + str(row['lower_limit'])
                                label.append(label_str)
                            else:
                                label_str = str(row['lower_limit']) + ' - ' + str(row['upper_limit'])
                                label.append(label_str)
                            color.append(row['color'])
                            list_value.append(row['new_value'])
                            label_value.update({row['new_value']: (label_str, row['color'])})
                else:
                    color = []
                    label = []
                    list_value = []
                    with open(self.otoklimdlg.normalrainfile.text(), 'rb') as csvfile:
                        spamreader = csv.DictReader(csvfile, delimiter=str(self.otoklimdlg.csvdelimiter.text()), quotechar='|')
                        for row in spamreader:
                            if str(row['lower_limit']) == '*':
                                label_str = '< ' + str(row['upper_limit'])
                                label.append(label_str)
                            elif str(row['upper_limit']) == '*':
                                label_str = '> ' + str(row['lower_limit'])
                                label.append(label_str)
                            else:
                                label_str = str(row['lower_limit']) + ' - ' + str(row['upper_limit'])
                                label.append(label_str)
                            color.append(row['color'])
                            list_value.append(row['new_value'])
                            label_value.update({row['new_value']: (label_str, row['color'])})
                # Set Attribute
                logger.debug('-- Set attribute value to vector classified..')
                expression = QgsExpression("area(transform($geometry, 'EPSG:4326','EPSG:3857'))")
                index = layer_vector_classified.fieldNameIndex("Area")
                expression.prepare(layer_vector_classified.pendingFields())
                area_all = 0
                features = layer_vector_classified.getFeatures()
                for i in features:
                    area_all += expression.evaluate(i)
                layer_vector_classified.startEditing()
                features = layer_vector_classified.getFeatures()
                for i in features:
                    layer_vector_classified.changeAttributeValue(
                        i.id(),
                        layer_vector_classified.fieldNameIndex(str(value[0])[0:3].upper()), 
                        str(label_value[str(i['DN'])][0])
                    )
                    layer_vector_classified.changeAttributeValue(
                        i.id(),
                        layer_vector_classified.fieldNameIndex('Area'), 
                        expression.evaluate(i)
                    )
                    layer_vector_classified.changeAttributeValue(
                        i.id(),
                        layer_vector_classified.fieldNameIndex('Percent'), 
                        (expression.evaluate(i) / float(area_all)) * 100
                    )
                layer_vector_classified.commitChanges()
                # Render Vector Style
                logger.debug('-- Vector classified rendering..')
                style_file = os.path.join(classified_directory, 'classified_' + str(value[0]) + '.qml')
                categories = []
                for dn, (label, color) in label_value.items():
                    symbol = QgsFillSymbolV2.createSimple({'color': color, 'outline_color': '0,0,0,0', 'outline_width': '0'})
                    category = QgsRendererCategoryV2(dn, symbol, label)
                    categories.append(category)
                expression = 'DN'
                renderer = QgsCategorizedSymbolRendererV2(expression, categories)
                layer_vector_classified.setRendererV2(renderer)
                layer_vector_classified.saveNamedStyle(style_file)
                logger.info('-- Rendering success.. Rendering file has been stored on ' + str(style_file))

            with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    otoklim_project["PROCESSING"]["CLASSIFICATION"]["PROCESSED"] = 1
            with open(project, 'w') as jsonfile:
                jsonfile.write(json.dumps(otoklim_project, indent=4))
            self.otoklimdlg.showClassificationFolder.setEnabled(True)
            self.otoklimdlg.testParameter.setEnabled(False)
            self.otoklimdlg.generatemapPanelAccord.setEnabled(True)
            self.otoklimdlg.generatecsvPanelAccord.setEnabled(True)
            self.otoklimdlg.generatemapPanel.setEnabled(True)
            self.otoklimdlg.generatecsvPanel.setEnabled(True)
            self.otoklimdlg.generatemapPanel.show()
            self.otoklimdlg.generatecsvPanel.show()
            with open(project, 'r') as jsonfile:
                otoklim_project = json.load(jsonfile)
                province_id = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["ID_PROV"]
                region_csv = os.path.join(otoklim_project["LOCATION"]["PRC_FILE_LOC"], str(province_id) +  "_regionlist.csv")
            self.region_listing(province_id, region_csv, False)
        except Exception as e:
            self.errormessagedlg.ErrorMessage.setText(str(e))
            logger.error(str(e))
            self.errormessagedlg.exec_()

    def region_listing(self, province_id, region_csv, save):
        """Function to listing region to tree widget"""
        self.otoklimdlg.treeWidget_option_1.clear()
        self.otoklimdlg.treeWidget_option_2.clear()
        self.otoklimdlg.treeWidget_selected_1.clear()
        self.otoklimdlg.treeWidget_selected_2.clear()
        if province_id:
            all_regions = []
            layer = QgsVectorLayer(self.otoklimdlg.province.text(), 'Provinsi', 'ogr')
            layer_kab = QgsVectorLayer(self.otoklimdlg.districts.text(), 'Provinsi', 'ogr')
            layer_kec = QgsVectorLayer(self.otoklimdlg.subdistricts.text(), 'Provinsi', 'ogr')
            exp = "\"ID_PROV\"='{}'".format(province_id)
            layer.setSubsetString(exp)
            fields = layer.pendingFields()
            if not os.path.exists(region_csv) or save:
                try:
                    os.remove(region_csv)
                except OSError:
                    pass
                with open(region_csv, "wb+") as csvfile:
                    csv_writer = csv.writer(csvfile, delimiter=",")
                    # Single Province Listing
                    for feature in layer.getFeatures():
                        csv_writer.writerow([feature['PROVINSI'].capitalize(), feature['ADM_REGION'].capitalize(), feature['ID_PROV']])
                    district_list = []
                    layer_kab.setSubsetString(exp)
                    # City \ District Listing
                    for feature in layer_kab.getFeatures():
                        district_list.append((
                            feature['KABUPATEN'].capitalize(),
                            feature['ADM_REGION'].capitalize(),
                            feature['ID_KAB'],
                            feature['PROVINSI'].capitalize()
                        ))
                    for kab in sorted(district_list, key=lambda x: x[0]):
                        csv_writer.writerow(kab)
                        subdistrict_list = []
                        exp = "\"ID_KAB\"='{}'".format(kab[2])
                        layer_kec.setSubsetString(exp)
                        # Sub-District Listing
                        for feature in layer_kec.getFeatures():
                            subdistrict_list.append((
                                feature['KECAMATAN'].capitalize(),
                                feature['ADM_REGION'].capitalize(),
                                feature['ID_KEC'],
                                feature['KABUPATEN'].capitalize(),
                                feature['PROVINSI'].capitalize(),
                            ))
                        for kec in sorted(subdistrict_list, key=lambda x: x[0]):
                            csv_writer.writerow(kec)
            with open(region_csv, 'rb') as csvfile:
                spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
                region_list = [row for row in spamreader]
            for region in region_list:
                item = QTreeWidgetItem([region[1] + ' ' + region[0]])
                if str(region[1]) == "Provinsi":
                    item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ str(region[1]) + ' '+ str(region[0]))
                elif str(region[1]) == "Kabupaten":
                    item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KAB. ' + str(region[0]) + ', PROV. ' + str(region[3]))
                elif str(region[1]) == "Kota":
                    item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KOTA ' + str(region[0]) + ', PROV. ' + str(region[3]))
                else:
                    item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KEC. ' + str(region[0]) + ', KAB. ' + str(region[3]) + ', PROV. ' + str(region[4]))
                if len(str(int(float(region[2])))) == 2:
                    parent_1 = item
                    self.otoklimdlg.treeWidget_option_1.addTopLevelItem(item)
                elif len(str(int(float(region[2])))) == 4:
                    parent_1.addChild(item)
                    child_1 = item
                else:
                    child_1.addChild(item)
                self.otoklimdlg.treeWidget_option_1.expandToDepth(0)
                item2 = QTreeWidgetItem([region[1] + ' ' + region[0]])
                if str(region[1]) == "Provinsi":
                    item2.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ str(region[1]) + ' '+ str(region[0]))
                elif str(region[1]) == "Kabupaten":
                    item2.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KAB. ' + str(region[0]) + ', PROV. ' + str(region[3]))
                elif str(region[1]) == "Kota":
                    item2.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KOTA ' + str(region[0]) + ', PROV. ' + str(region[3]))
                else:
                    item2.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KEC. ' + str(region[0]) + ', KAB. ' + str(region[3]) + ', PROV. ' + str(region[4]))
                if len(str(int(float(region[2])))) == 2:
                    parent_2 = item2
                    self.otoklimdlg.treeWidget_option_2.addTopLevelItem(item2)
                elif len(str(int(float(region[2])))) == 4:
                    parent_2.addChild(item2)
                    child_2 = item2
                else:
                    child_2.addChild(item2)
                self.otoklimdlg.treeWidget_option_2.expandToDepth(0)

    def expand_option_1(self):
        self.search_option_1(expand=True)

    def expand_option_2(self):
        self.search_option_2(expand=True)

    def search_option_1(self, expand=False):
        """Function to search region"""
        key = self.otoklimdlg.search_option1.text()
        project = os.path.join(
            self.otoklimdlg.projectworkspace.text(),
            self.otoklimdlg.projectfilename.text()
        )
        with open(project, 'r') as jsonfile:
            otoklim_project = json.load(jsonfile)
            province_id = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["ID_PROV"]
            region_csv = os.path.join(otoklim_project["LOCATION"]["PRC_FILE_LOC"], str(province_id) +  "_regionlist.csv")
        with open(region_csv, 'rb') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
            region_list = [row for row in spamreader]
        filter_list = [row for row in region_list if str(key).upper() in row[0].upper()]
        default = (filter_list == region_list)
        self.otoklimdlg.treeWidget_option_1.clear()
        for region in filter_list:
            item = QTreeWidgetItem([region[1] + ' ' + region[0]])
            if str(region[1]) == "Provinsi":
                item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ str(region[1]) + ' '+ str(region[0]))
            elif str(region[1]) == "Kabupaten":
                item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KAB. ' + str(region[0]) + ', PROV. ' + str(region[3]))
            elif str(region[1]) == "Kota":
                item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KOTA ' + str(region[0]) + ', PROV. ' + str(region[3]))
            else:
                item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KEC. ' + str(region[0]) + ', KAB. ' + str(region[3]) + ', PROV. ' + str(region[4]))
            if len(str(int(float(region[2])))) == 2 or default:
                parent = item
                self.otoklimdlg.treeWidget_option_1.addTopLevelItem(item)
                parent_code = str(int(float(region[2])))
                for region in region_list:
                    item = QTreeWidgetItem([region[1] + ' ' + region[0]])
                    if str(region[1]) == "Provinsi":
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ str(region[1]) + ' '+ str(region[0]))
                    elif str(region[1]) == "Kabupaten":
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KAB. ' + str(region[0]) + ', PROV. ' + str(region[3]))
                    elif str(region[1]) == "Kota":
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KOTA ' + str(region[0]) + ', PROV. ' + str(region[3]))
                    else:
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KEC. ' + str(region[0]) + ', KAB. ' + str(region[3]) + ', PROV. ' + str(region[4]))
                    if len(str(int(float(region[2])))) == 4 and str(region[2][:2]) == parent_code:
                        parent.addChild(item)
                        child = item
                    elif len(str(int(float(region[2])))) > 4 and str(region[2][:2]) == parent_code:
                        child.addChild(item)
                if default:
                    if expand:
                        self.otoklimdlg.treeWidget_option_1.expandToDepth(1)
                    else:
                        self.otoklimdlg.treeWidget_option_1.expandToDepth(0)
                    break
            elif len(str(int(float(region[2])))) == 4:
                parent = item
                self.otoklimdlg.treeWidget_option_1.addTopLevelItem(item)
                parent_code = str(int(float(region[2])))
                for region in region_list:
                    item = QTreeWidgetItem([region[1] + ' ' + region[0]])
                    if str(region[1]) == "Provinsi":
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ str(region[1]) + ' '+ str(region[0]))
                    elif str(region[1]) == "Kabupaten":
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KAB. ' + str(region[0]) + ', PROV. ' + str(region[3]))
                    elif str(region[1]) == "Kota":
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KOTA ' + str(region[0]) + ', PROV. ' + str(region[3]))
                    else:
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KEC. ' + str(region[0]) + ', KAB. ' + str(region[3]) + ', PROV. ' + str(region[4]))
                    if len(str(int(float(region[2])))) > 4 and str(region[2][:4]) == parent_code:
                        parent.addChild(item)
            else:
                self.otoklimdlg.treeWidget_option_1.addTopLevelItem(item)
    
    def search_option_2(self, expand=False):
        """Function to search region"""
        key = self.otoklimdlg.search_option2.text()
        project = os.path.join(
            self.otoklimdlg.projectworkspace.text(),
            self.otoklimdlg.projectfilename.text()
        )
        with open(project, 'r') as jsonfile:
            otoklim_project = json.load(jsonfile)
            province_id = otoklim_project["PROCESSING"]["IDW_INTERPOLATION"]["ID_PROV"]
            region_csv = os.path.join(otoklim_project["LOCATION"]["PRC_FILE_LOC"], str(province_id) +  "_regionlist.csv")
        with open(region_csv, 'rb') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
            region_list = [row for row in spamreader]
        filter_list = [row for row in region_list if str(key).upper() in row[0].upper()]
        default = (filter_list == region_list)
        self.otoklimdlg.treeWidget_option_2.clear()
        for region in filter_list:
            item = QTreeWidgetItem([region[1] + ' ' + region[0]])
            if str(region[1]) == "Provinsi":
                item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ str(region[1]) + ' '+ str(region[0]))
            elif str(region[1]) == "Kabupaten":
                item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KAB. ' + str(region[0]) + ', PROV. ' + str(region[3]))
            elif str(region[1]) == "Kota":
                item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KOTA ' + str(region[0]) + ', PROV. ' + str(region[3]))
            else:
                item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KEC. ' + str(region[0]) + ', KAB. ' + str(region[3]) + ', PROV. ' + str(region[4]))
            if len(str(int(float(region[2])))) == 2 or default:
                parent = item
                self.otoklimdlg.treeWidget_option_2.addTopLevelItem(item)
                parent_code = str(int(float(region[2])))
                for region in region_list:
                    item = QTreeWidgetItem([region[1] + ' ' + region[0]])
                    if str(region[1]) == "Provinsi":
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ str(region[1]) + ' '+ str(region[0]))
                    elif str(region[1]) == "Kabupaten":
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KAB. ' + str(region[0]) + ', PROV. ' + str(region[3]))
                    elif str(region[1]) == "Kota":
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KOTA ' + str(region[0]) + ', PROV. ' + str(region[3]))
                    else:
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KEC. ' + str(region[0]) + ', KAB. ' + str(region[3]) + ', PROV. ' + str(region[4]))
                    if len(str(int(float(region[2])))) == 4 and str(region[2][:2]) == parent_code:
                        parent.addChild(item)
                        child = item
                    elif len(str(int(float(region[2])))) > 4 and str(region[2][:2]) == parent_code:
                        child.addChild(item)
                if default:
                    if expand:
                        self.otoklimdlg.treeWidget_option_2.expandToDepth(1)
                    else:
                        self.otoklimdlg.treeWidget_option_2.expandToDepth(0)
                    break
            elif len(str(int(float(region[2])))) == 4:
                parent = item
                self.otoklimdlg.treeWidget_option_2.addTopLevelItem(item)
                parent_code = str(int(float(region[2])))
                for region in region_list:
                    item = QTreeWidgetItem([region[1] + ' ' + region[0]])
                    if str(region[1]) == "Provinsi":
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ str(region[1]) + ' '+ str(region[0]))
                    elif str(region[1]) == "Kabupaten":
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KAB. ' + str(region[0]) + ', PROV. ' + str(region[3]))
                    elif str(region[1]) == "Kota":
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KOTA ' + str(region[0]) + ', PROV. ' + str(region[3]))
                    else:
                        item.setWhatsThis(1, str(region[0]) + '|' + str(region[2]) + '|'+ 'KEC. ' + str(region[0]) + ', KAB. ' + str(region[3]) + ', PROV. ' + str(region[4]))
                    if len(str(int(float(region[2])))) > 4 and str(region[2][:4]) == parent_code:
                        parent.addChild(item)
            else:
                self.otoklimdlg.treeWidget_option_2.addTopLevelItem(item)

    def add_to_selected_1(self):
        """Function to move selected region"""
        items = []
        for index in xrange(self.otoklimdlg.treeWidget_selected_1.topLevelItemCount()):
            items.append(self.otoklimdlg.treeWidget_selected_1.topLevelItem(index))
        selected_items = [i.text(0) for i in items]

        for item in self.otoklimdlg.treeWidget_option_1.selectedItems():
            if item.text(0) not in selected_items:
                newitem = QTreeWidgetItem([item.text(0)])
                newitem.setWhatsThis(0, item.whatsThis(1))
                self.otoklimdlg.treeWidget_selected_1.addTopLevelItem(newitem)
            else:
                pass
    
    def add_to_selected_2(self):
        """Function to move selected region"""
        items = []
        for index in xrange(self.otoklimdlg.treeWidget_selected_2.topLevelItemCount()):
            items.append(self.otoklimdlg.treeWidget_selected_2.topLevelItem(index))
        selected_items = [i.text(0) for i in items]

        for item in self.otoklimdlg.treeWidget_option_2.selectedItems():
            if item.text(0) not in selected_items:
                newitem = QTreeWidgetItem([item.text(0)])
                newitem.setWhatsThis(0, item.whatsThis(1))
                self.otoklimdlg.treeWidget_selected_2.addTopLevelItem(newitem)
            else:
                pass

    def delete_from_selected_1(self):
        """Function to remove selected region"""
        for item in self.otoklimdlg.treeWidget_selected_1.selectedItems():
            self.otoklimdlg.treeWidget_selected_1.takeTopLevelItem(
                self.otoklimdlg.treeWidget_selected_1.indexOfTopLevelItem(item)
            )
    
    def delete_from_selected_2(self):
        """Function to remove selected region"""
        for item in self.otoklimdlg.treeWidget_selected_2.selectedItems():
            self.otoklimdlg.treeWidget_selected_2.takeTopLevelItem(
                self.otoklimdlg.treeWidget_selected_2.indexOfTopLevelItem(item)
            )

    def generate_map(self):
        """Function to generate map"""
        prcs_directory = os.path.join(self.otoklimdlg.projectworkspace.text(), 'processing')
        logger = self.logger(prcs_directory)
        logger.info('Generate Map..')
        self.iface.mainWindow().statusBar().showMessage('Generate Map..')
        out_directory = os.path.join(self.otoklimdlg.projectworkspace.text(), 'output')
        map_directory = os.path.join(out_directory, 'map')
        filename_xml = os.path.join(map_directory, 'phb.xml')
        classified_directory = os.path.join(prcs_directory, 'classified')
        date = self.select_date_now()
        date_produced = self.otoklimdlg.Date_Produced.text()
        months = date[0]
        years = date[1]
        items = []
        for index in xrange(self.otoklimdlg.treeWidget_selected_1.topLevelItemCount()):
            items.append(self.otoklimdlg.treeWidget_selected_1.topLevelItem(index))
        slc_id_list = [int(float(i.whatsThis(0).split('|')[1])) for i in items]
        slc_name_list = [str(i.whatsThis(0).split('|')[0]) for i in items]
        slc_nametitle_list = [str(i.whatsThis(0).split('|')[2]) for i in items]
        project = os.path.join(
            self.otoklimdlg.projectworkspace.text(),
            self.otoklimdlg.projectfilename.text()
        )
        try:
            logger.debug('- Listing selected parameter to be processed')
            prc_list = []
            date_list = []
            curah_hujan = ET.Element("curah_hujan")
            forecast = ET.SubElement(curah_hujan, "forecast")
            params = ET.SubElement(curah_hujan, "params")
            # set forecast
            issue = ET.SubElement(forecast, "issue")
            ET.SubElement(issue, "timestamp").text = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
            ET.SubElement(issue, "year").text = str(years[4])
            ET.SubElement(issue, "month").text = str(months[4])
            # set params
            if self.otoklimdlg.ach_1_map.isChecked():
                data = ET.SubElement(params, "data")
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_ach_1 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_ACH_1"]["NAME"]
                    param = os.path.splitext(raster_ach_1)[0].split('_')[1] + '_' + os.path.splitext(raster_ach_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_ACH_1"]["REGION_LIST"] = str(slc_id_list)
                    ET.SubElement(data, "param").text = str(param.split('_')[0])
                    ET.SubElement(data, "month").text = str(months[0][2])
                    ET.SubElement(data, "year").text = str(years[0])
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_ach_1])
                logger.debug('-- ' + str(param) + ' is checked')
                date_list.append([months[0], years[0]])
            if self.otoklimdlg.ash_1_map.isChecked():
                data = ET.SubElement(params, "data")
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_ash_1 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_ASH_1"]["NAME"]
                    param = os.path.splitext(raster_ash_1)[0].split('_')[1] + '_' + os.path.splitext(raster_ash_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_ASH_1"]["REGION_LIST"] = str(slc_id_list)
                    ET.SubElement(data, "param").text = str(param.split('_')[0])
                    ET.SubElement(data, "month").text = str(months[0][2])
                    ET.SubElement(data, "year").text = str(years[0])
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_ash_1])
                logger.debug('-- ' + str(param) + ' is checked')
                date_list.append([months[0], years[0]])
            if self.otoklimdlg.pch_1_map.isChecked():
                data = ET.SubElement(params, "data")
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_pch_1 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_1"]["NAME"]
                    param = os.path.splitext(raster_pch_1)[0].split('_')[1] + '_' + os.path.splitext(raster_pch_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_PCH_1"]["REGION_LIST"] = str(slc_id_list)
                    ET.SubElement(data, "param").text = str(param.split('_')[0])
                    ET.SubElement(data, "month").text = str(months[1][2])
                    ET.SubElement(data, "year").text = str(years[1])
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_pch_1])
                logger.debug('-- ' + str(param) + ' is checked')
                date_list.append([months[1], years[1]])
            if self.otoklimdlg.psh_1_map.isChecked():
                data = ET.SubElement(params, "data")
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_psh_1 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_1"]["NAME"]
                    param = os.path.splitext(raster_psh_1)[0].split('_')[1] + '_' + os.path.splitext(raster_psh_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_PSH_1"]["REGION_LIST"] = str(slc_id_list)
                    ET.SubElement(data, "param").text = str(param.split('_')[0])
                    ET.SubElement(data, "month").text = str(months[1][2])
                    ET.SubElement(data, "year").text = str(years[1])
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_psh_1])
                logger.debug('-- ' + str(param) + ' is checked')
                date_list.append([months[1], years[1]])
            if self.otoklimdlg.pch_2_map.isChecked():
                data = ET.SubElement(params, "data")
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_pch_2 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_2"]["NAME"]
                    param = os.path.splitext(raster_pch_2)[0].split('_')[1] + '_' + os.path.splitext(raster_pch_2)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_PCH_2"]["REGION_LIST"] = str(slc_id_list)
                    ET.SubElement(data, "param").text = str(param.split('_')[0])
                    ET.SubElement(data, "month").text = str(months[2][2])
                    ET.SubElement(data, "year").text = str(years[2])
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_pch_2])
                logger.debug('-- ' + str(param) + ' is checked')
                date_list.append([months[2], years[2]])
            if self.otoklimdlg.psh_2_map.isChecked():
                data = ET.SubElement(params, "data")
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_psh_2 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_2"]["NAME"]
                    param = os.path.splitext(raster_psh_2)[0].split('_')[1] + '_' + os.path.splitext(raster_psh_2)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_PSH_2"]["REGION_LIST"] = str(slc_id_list)
                    ET.SubElement(data, "param").text = str(param.split('_')[0])
                    ET.SubElement(data, "month").text = str(months[2][2])
                    ET.SubElement(data, "year").text = str(years[2])
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_psh_2])
                logger.debug('-- ' + str(param) + ' is checked')
                date_list.append([months[2], years[2]])
            if self.otoklimdlg.pch_3_map.isChecked():
                data = ET.SubElement(params, "data")
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_pch_3 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_3"]["NAME"]
                    param = os.path.splitext(raster_pch_3)[0].split('_')[1] + '_' + os.path.splitext(raster_pch_3)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_PCH_3"]["REGION_LIST"] = str(slc_id_list)
                    ET.SubElement(data, "param").text = str(param.split('_')[0])
                    ET.SubElement(data, "month").text = str(months[3][2])
                    ET.SubElement(data, "year").text = str(years[3])
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_pch_3])
                logger.debug('-- ' + str(param) + ' is checked')
                date_list.append([months[3], years[3]])
            if self.otoklimdlg.psh_3_map.isChecked():
                data = ET.SubElement(params, "data")
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_psh_3 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_3"]["NAME"]
                    param = os.path.splitext(raster_psh_3)[0].split('_')[1] + '_' + os.path.splitext(raster_psh_3)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_MAP"]["RASTER_PSH_3"]["REGION_LIST"] = str(slc_id_list)
                    ET.SubElement(data, "param").text = str(param.split('_')[0])
                    ET.SubElement(data, "month").text = str(months[3][2])
                    ET.SubElement(data, "year").text = str(years[3])
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_psh_3])
                logger.debug('-- ' + str(param) + ' is checked')
                date_list.append([months[3], years[3]])
            tree = ET.ElementTree(curah_hujan)
            tree.write(filename_xml, encoding='utf-8', xml_declaration=True)
            logger.info('- Selected parameter :' + str(prc_list))
            # Polygon to Line Conversion
            provinsi_line = os.path.join(prcs_directory, 'provinsi_line.shp')
            if not os.path.exists(provinsi_line):
                logger.debug('- Convert Province Boundary..')
                logger.info('- polygonstolines')
                processing.runandload("qgis:polygonstolines", self.otoklimdlg.province.text(), provinsi_line)
                lineprovince = QgsMapLayerRegistry.instance().mapLayersByName('Lines from polygons')[0]
                QgsMapLayerRegistry.instance().removeMapLayer(lineprovince.id())
            kabupaten_line = os.path.join(prcs_directory, 'kabupaten_line.shp')
            if not os.path.exists(kabupaten_line):
                logger.debug('- Convert Districts Boundary..')
                logger.info('- polygonstolines')
                processing.runandload("qgis:polygonstolines", self.otoklimdlg.districts.text(), kabupaten_line)
                linekabupaten = QgsMapLayerRegistry.instance().mapLayersByName('Lines from polygons')[0]
                QgsMapLayerRegistry.instance().removeMapLayer(linekabupaten.id())
            kecamatan_line = os.path.join(prcs_directory, 'kecamatan_line.shp')
            if not os.path.exists(kecamatan_line):
                logger.debug('- Convert Sub-Districts Boundary..')
                logger.info('- polygonstolines')
                processing.runandload("qgis:polygonstolines", self.otoklimdlg.subdistricts.text(), kecamatan_line)
                linekecamatan = QgsMapLayerRegistry.instance().mapLayersByName('Lines from polygons')[0]
                QgsMapLayerRegistry.instance().removeMapLayer(linekecamatan.id())
            desa_line = os.path.join(prcs_directory, 'desa_line.shp')
            if not os.path.exists(desa_line):
                logger.debug('- Convert Villages Boundary..')
                logger.info('- polygonstolines')
                processing.runandload("qgis:polygonstolines", self.otoklimdlg.villages.text(), desa_line)
                linedesa = QgsMapLayerRegistry.instance().mapLayersByName('Lines from polygons')[0]
                QgsMapLayerRegistry.instance().removeMapLayer(linedesa.id())
            # Start Listing
            for value, date in zip(prc_list, date_list):
                logger.info('-- Field (Parameter) : ' + value[0])
                logger.debug('-- Generate Map in progress...')
                vector_classified = os.path.join(classified_directory, value[1])
                style_file = os.path.join(classified_directory, os.path.splitext(value[1])[0] + '.qml')
                temp_raster = os.path.join(prcs_directory, 'tmp' + str(value[1]))
                if os.path.exists(temp_raster):
                    pass
                else:
                    os.mkdir(temp_raster)
                month = date[0]
                year = date[1]
                for slc_id, slc_name, slc_nametitle in zip(slc_id_list, slc_name_list, slc_nametitle_list):
                    logger.info('--- Region processed : ' + slc_name)
                    projectqgs = os.path.join(prcs_directory, str(slc_name) + '_qgisproject_' + str(value[0]) + '_' + str(slc_id) + '.qgs')
                    output_jpg = os.path.join(map_directory, str(slc_id) + '_' + str(years[4]) + str(months[4]) + '_' + str(year) + str(month[2]) + '_' + str(value[0]).split('_')[0] + '_' + str(slc_name) + '.jpg')
                    if os.path.basename(output_jpg) not in os.listdir(map_directory):
                        if len(str(slc_id)) == 2:
                            # Classified Value Styling
                            layer_vector = QgsVectorLayer(vector_classified, '', 'ogr')
                            layer_vector.loadNamedStyle(style_file)
                            # Province Styling
                            layer_provinsi = QgsVectorLayer(self.otoklimdlg.province.text(), 'Provinsi', 'ogr')
                            exp = "\"ID_PROV\"!='{}'".format(str(slc_id))
                            layer_provinsi.setSubsetString(exp)
                            symbol = QgsFillSymbolV2.createSimple({'color': '169,169,169,255', 'outline_color': '0,0,0,0', 'outline_style': 'solid', 'outline_width': '0.5'})
                            layer_provinsi.rendererV2().setSymbol(symbol)
                            layer_provinsi_line = QgsVectorLayer(provinsi_line, 'Batas Provinsi', 'ogr')
                            symbol = QgsLineSymbolV2.createSimple({'color': '0,0,0,255', 'penstyle': 'solid', 'width': '0.5'})
                            layer_provinsi_line.rendererV2().setSymbol(symbol)
                            layer_provinsi.triggerRepaint()
                            palyr = QgsPalLayerSettings()
                            palyr.readFromLayer(layer_provinsi)
                            palyr.enabled = True
                            palyr.fieldName = 'PROVINSI'
                            palyr.placement = QgsPalLayerSettings.OverPoint
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '14', '')
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferDraw, True, True, '1', '')
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferSize, True, True, '1', '')
                            palyr.writeToLayer(layer_provinsi)
                            # Districts Styling
                            layer_kabupaten = QgsVectorLayer(self.otoklimdlg.districts.text(), 'Kabupaten', 'ogr')
                            exp = "\"ID_PROV\"='{}'".format(str(slc_id))
                            layer_kabupaten.setSubsetString(exp)
                            symbol = QgsFillSymbolV2.createSimple({'color': '0,0,0,0', 'outline_color': '0,0,0,0', 'outline_style': 'dot', 'outline_width': '0.25'})
                            layer_kabupaten.rendererV2().setSymbol(symbol)
                            layer_kabupaten_line = QgsVectorLayer(kabupaten_line, 'Batas Kabupaten', 'ogr')
                            layer_kabupaten_line.setSubsetString(exp)
                            symbol = QgsLineSymbolV2.createSimple({'color': '0,0,0,255', 'penstyle': 'dot', 'width': '0.25'})
                            layer_kabupaten_line.rendererV2().setSymbol(symbol)
                            palyr = QgsPalLayerSettings()
                            palyr.readFromLayer(layer_kabupaten)
                            palyr.enabled = True
                            palyr.fieldName = 'KABUPATEN'
                            palyr.placement = QgsPalLayerSettings.OverPoint
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '8', '')
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferDraw, True, True, '1', '')
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferSize, True, True, '1', '')
                            palyr.writeToLayer(layer_kabupaten)
                            # Bathymetry
                            layer_bath = QgsRasterLayer(self.otoklimdlg.bathymetry.text(), 'Bathymetry')
                            # Add Layer To QGIS Canvas
                            canvas = qgis.utils.iface.mapCanvas()
                            QgsMapLayerRegistry.instance().addMapLayer(layer_bath)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_provinsi)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_kabupaten)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_vector)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_kabupaten_line)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_provinsi_line)
                            # Set Extent
                            canvas.setExtent(layer_kabupaten.extent())
                            canvas.refresh()
                            # Create QGIS Porject File
                            f = QFileInfo(projectqgs)
                            p = QgsProject.instance()
                            p.write(f)
                            QgsProject.instance().clear()
                            # Read Map
                            template_file = open(self.otoklimdlg.maptemplate.text())
                            template_content = template_file.read()
                            template_file.close()
                            document = QDomDocument()
                            document.setContent(template_content)
                            if str(value[0])[0:3].upper() == 'ACH' or str(value[0])[0:3].upper() == 'PCH':
                                title_type = "CURAH"
                            else:
                                title_type = "SIFAT"
                            if str(value[0])[0:3].upper().startswith('A'):
                                title_adj = "ANALISIS"
                            else:
                                title_adj = "PRAKIRAAN"
                            map_title = 'PETA ' + title_adj + ' ' + title_type + ' HUJAN BULAN ' + str(month[1]) + ' TAHUN '+ str(year) + ' ' + str(slc_nametitle).upper()
                            substitution_map = {'map_title': map_title, 'date_produced':date_produced}
                            canvas = QgsMapCanvas()
                            QgsProject.instance().read(QFileInfo(projectqgs))
                            bridge = QgsLayerTreeMapCanvasBridge(QgsProject.instance().layerTreeRoot(), canvas)
                            bridge.setCanvasLayers()
                            composition = QgsComposition(canvas.mapSettings())
                            composition.loadFromTemplate(document, substitution_map)
                            map_item = composition.getComposerItemById('map')
                            map_item.setMapCanvas(canvas)
                            # Province Polygon As Extent
                            if self.otoklimdlg.province_extent.isChecked():
                                map_item.zoomToExtent(canvas.extent())
                            legend_item = composition.getComposerItemById('legend_line')
                            legend_item.updateLegend()
                            composition.refreshItems()
                            # Save as image
                            dpi = 300
                            dpmm = dpi / 25.4
                            width = int(dpmm * composition.paperWidth())
                            height = int(dpmm * composition.paperHeight())
                            # create output image and initialize it
                            image = QImage(QSize(width, height), QImage.Format_ARGB32)
                            image.setDotsPerMeterX(dpmm * 1000)
                            image.setDotsPerMeterY(dpmm * 1000)
                            image.fill(0)
                            # render the composition
                            imagePainter = QPainter(image)
                            composition.renderPage(imagePainter, 0)
                            imagePainter.end()
                            image.save(output_jpg, "jpg")
                            logger.info('--- Image saved at : ' + output_jpg)
                            # Remove unuse file
                            vector = QgsMapLayerRegistry.instance().mapLayersByName('')[0]
                            kabupaten = QgsMapLayerRegistry.instance().mapLayersByName('Kabupaten')[0]
                            provinsi = QgsMapLayerRegistry.instance().mapLayersByName('Provinsi')[0]
                            bathymetry = QgsMapLayerRegistry.instance().mapLayersByName('Bathymetry')[0]
                            provinsiline = QgsMapLayerRegistry.instance().mapLayersByName('Batas Provinsi')[0]
                            kabupatenline = QgsMapLayerRegistry.instance().mapLayersByName('Batas Kabupaten')[0]
                            all_layer = [vector.id(), kabupaten.id(), provinsi.id(), bathymetry.id(), provinsiline.id(), kabupatenline.id()]
                            QgsMapLayerRegistry.instance().removeMapLayers(all_layer)
                        elif len(str(slc_id)) == 4:
                            # Classified Value Styling
                            layer_vector = QgsVectorLayer(vector_classified, '', 'ogr')
                            layer_vector.loadNamedStyle(style_file)
                            # Province Styling
                            layer_provinsi = QgsVectorLayer(self.otoklimdlg.province.text(), 'Provinsi', 'ogr')
                            symbol = QgsFillSymbolV2.createSimple({'color': '240,240,240,255', 'outline_color': '0,0,0,255', 'outline_style': 'solid', 'outline_width': '0.5'})
                            layer_provinsi.rendererV2().setSymbol(symbol)
                            layer_provinsi.triggerRepaint()
                            # Districts Styling
                            layer_kabupaten = QgsVectorLayer(self.otoklimdlg.districts.text(), 'Kabupaten', 'ogr')
                            exp = "\"ID_PROV\"='{}' AND \"ID_KAB\"!='{}'".format(str(slc_id)[0:2], str(slc_id))
                            layer_kabupaten.setSubsetString(exp)
                            symbol = QgsFillSymbolV2.createSimple({'color': '169,169,169,255', 'outline_color': '0,0,0,0', 'outline_style': 'solid', 'outline_width': '0.5'})
                            layer_kabupaten.rendererV2().setSymbol(symbol)
                            layer_kabupaten.triggerRepaint()
                            layer_kabupaten_line = QgsVectorLayer(kabupaten_line, 'Batas Kabupaten', 'ogr')
                            layer_kabupaten_line.setSubsetString(exp)
                            symbol = QgsLineSymbolV2.createSimple({'color': '0,0,0,255', 'penstyle': 'solid', 'width': '0.5'})
                            layer_kabupaten_line.rendererV2().setSymbol(symbol)
                            palyr = QgsPalLayerSettings()
                            palyr.readFromLayer(layer_kabupaten)
                            palyr.enabled = True
                            palyr.fieldName = 'KABUPATEN'
                            palyr.placement = QgsPalLayerSettings.OverPoint
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '14', '')
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferDraw, True, True, '1', '')
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferSize, True, True, '1', '')
                            palyr.writeToLayer(layer_kabupaten)
                            # Sub-Districts Styling
                            layer_kecamatan = QgsVectorLayer(self.otoklimdlg.subdistricts.text(), 'Kecamatan', 'ogr')
                            exp = "\"ID_KAB\"='{}'".format(str(slc_id))
                            layer_kecamatan.setSubsetString(exp)
                            symbol = QgsFillSymbolV2.createSimple({'color': '0,0,0,0', 'outline_color': '0,0,0,0', 'outline_style': 'dot', 'outline_width': '0.25'})
                            layer_kecamatan.rendererV2().setSymbol(symbol)
                            layer_kecamatan_line = QgsVectorLayer(kecamatan_line, 'Batas Kecamatan', 'ogr')
                            layer_kecamatan_line.setSubsetString(exp)
                            symbol = QgsLineSymbolV2.createSimple({'color': '0,0,0,255', 'penstyle': 'dot', 'width': '0.25'})
                            layer_kecamatan_line.rendererV2().setSymbol(symbol)
                            palyr = QgsPalLayerSettings()
                            palyr.readFromLayer(layer_kecamatan)
                            palyr.enabled = True
                            palyr.fieldName = 'KECAMATAN'
                            palyr.placement = QgsPalLayerSettings.OverPoint
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '8', '')
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferDraw, True, True, '1', '')
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferSize, True, True, '1', '')
                            palyr.writeToLayer(layer_kecamatan)
                            # Bathymetry
                            layer_bath = QgsRasterLayer(self.otoklimdlg.bathymetry.text(), 'Bathymetry')
                            # Add Layer To QGIS Canvas
                            canvas = qgis.utils.iface.mapCanvas()
                            QgsMapLayerRegistry.instance().addMapLayer(layer_bath)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_provinsi)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_vector)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_kabupaten)    
                            QgsMapLayerRegistry.instance().addMapLayer(layer_kecamatan)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_kecamatan_line)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_kabupaten_line)
                            # Set Extent
                            canvas.setExtent(layer_kecamatan.extent())
                            canvas.refresh()
                            # Create QGIS Porject File
                            f = QFileInfo(projectqgs)
                            p = QgsProject.instance()
                            p.write(f)
                            QgsProject.instance().clear()
                            QgsMapLayerRegistry.instance().removeMapLayer(layer_vector.id())
                            del layer_vector
                            # Read Map
                            template_file = open(self.otoklimdlg.maptemplate2.text())
                            template_content = template_file.read()
                            template_file.close()
                            document = QDomDocument()
                            document.setContent(template_content)
                            if str(value[0])[0:3].upper() == 'ACH' or str(value[0])[0:3].upper() == 'PCH':
                                title_type = "CURAH"
                            else:
                                title_type = "SIFAT"
                            if str(value[0])[0:3].upper().startswith('A'):
                                title_adj = "ANALISIS"
                            else:
                                title_adj = "PRAKIRAAN"
                            map_title = 'PETA ' + title_adj + ' ' + title_type + ' HUJAN BULAN ' + str(month[1]) + ' TAHUN '+ str(year) + ' ' + str(slc_nametitle).upper()
                            substitution_map = {'map_title': map_title, 'date_produced':date_produced}
                            canvas = QgsMapCanvas()
                            QgsProject.instance().read(QFileInfo(projectqgs))
                            bridge = QgsLayerTreeMapCanvasBridge(QgsProject.instance().layerTreeRoot(), canvas)
                            bridge.setCanvasLayers()
                            composition = QgsComposition(canvas.mapSettings())
                            composition.loadFromTemplate(document, substitution_map)
                            map_item = composition.getComposerItemById('map')
                            map_item.setMapCanvas(canvas)
                            map_item.zoomToExtent(canvas.extent())
                            composition.refreshItems()
                            # Save as image
                            dpi = 200
                            dpmm = dpi / 25.4
                            width = int(dpmm * composition.paperWidth())
                            height = int(dpmm * composition.paperHeight())
                            # create output image and initialize it
                            image = QImage(QSize(width, height), QImage.Format_ARGB32)
                            image.setDotsPerMeterX(dpmm * 1000)
                            image.setDotsPerMeterY(dpmm * 1000)
                            image.fill(0)
                            # render the composition
                            imagePainter = QPainter(image)
                            composition.renderPage(imagePainter, 0)
                            imagePainter.end()
                            image.save(output_jpg, "jpg")
                            logger.info('--- Image saved at : ' + output_jpg)
                            # Remove unuse file
                            vector = QgsMapLayerRegistry.instance().mapLayersByName('')[0]
                            kecamatan = QgsMapLayerRegistry.instance().mapLayersByName('Kecamatan')[0]
                            kabupaten = QgsMapLayerRegistry.instance().mapLayersByName('Kabupaten')[0]
                            provinsi = QgsMapLayerRegistry.instance().mapLayersByName('Provinsi')[0]
                            bathymetry = QgsMapLayerRegistry.instance().mapLayersByName('Bathymetry')[0]
                            kabupatenline = QgsMapLayerRegistry.instance().mapLayersByName('Batas Kabupaten')[0]
                            kecamatanline = QgsMapLayerRegistry.instance().mapLayersByName('Batas Kecamatan')[0]
                            all_layer = [vector.id(), kabupaten.id(), provinsi.id(), bathymetry.id(), kecamatan.id(), kabupatenline.id(), kecamatanline.id()]
                            QgsMapLayerRegistry.instance().removeMapLayers(all_layer)
                            del vector
                            os.remove(projectqgs)
                        else:
                            # Classified Value Styling
                            layer_vector = QgsVectorLayer(vector_classified, '', 'ogr')
                            layer_vector.loadNamedStyle(style_file)
                            # Province Styling
                            layer_provinsi = QgsVectorLayer(self.otoklimdlg.province.text(), 'Provinsi', 'ogr')
                            symbol = QgsFillSymbolV2.createSimple({'color': '240,240,240,255', 'outline_color': '0,0,0,255', 'outline_style': 'solid', 'outline_width': '0.5'})
                            layer_provinsi.rendererV2().setSymbol(symbol)
                            layer_provinsi.triggerRepaint()
                            # Districts Styling
                            layer_kabupaten = QgsVectorLayer(self.otoklimdlg.districts.text(), 'Kabupaten', 'ogr')
                            exp = "\"ID_PROV\"='{}' AND \"ID_KAB\"!='{}'".format(str(slc_id)[0:2], str(slc_id)[0:4])
                            layer_kabupaten.setSubsetString(exp)
                            symbol = QgsFillSymbolV2.createSimple({'color': '223,223,223,255', 'outline_color': '0,0,0,255', 'outline_style': 'solid', 'outline_width': '0.5'})
                            layer_kabupaten.rendererV2().setSymbol(symbol)
                            layer_kabupaten.triggerRepaint()
                            # Sub-Districts Styling
                            layer_kecamatan = QgsVectorLayer(self.otoklimdlg.subdistricts.text(), 'Kecamatan', 'ogr')
                            exp = "\"ID_KAB\"='{}' AND \"ID_KEC\"!='{}'".format(str(slc_id)[0:4], str(slc_id))
                            layer_kecamatan.setSubsetString(exp)
                            symbol = QgsFillSymbolV2.createSimple({'color': '169,169,169,255', 'outline_color': '0,0,0,0', 'outline_style': 'solid', 'outline_width': '0.5'})
                            layer_kecamatan.rendererV2().setSymbol(symbol)
                            layer_kecamatan.triggerRepaint()
                            layer_kecamatan_line = QgsVectorLayer(kecamatan_line, 'Batas Kecamatan', 'ogr')
                            layer_kecamatan_line.setSubsetString(exp)
                            symbol = QgsLineSymbolV2.createSimple({'color': '0,0,0,255', 'penstyle': 'solid', 'width': '0.5'})
                            layer_kecamatan_line.rendererV2().setSymbol(symbol)
                            palyr = QgsPalLayerSettings()
                            palyr.readFromLayer(layer_kecamatan)
                            palyr.enabled = True
                            palyr.fieldName = 'KECAMATAN'
                            palyr.placement = QgsPalLayerSettings.OverPoint
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '14', '')
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferDraw, True, True, '1', '')
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferSize, True, True, '1', '')
                            palyr.writeToLayer(layer_kecamatan)
                            # Villages Styling
                            layer_desa = QgsVectorLayer(self.otoklimdlg.villages.text(), 'Desa', 'ogr')
                            exp = "\"ID_KEC\"='{}'".format(str(slc_id))
                            layer_desa.setSubsetString(exp)
                            symbol = QgsFillSymbolV2.createSimple({'color': '0,0,0,0', 'outline_color': '0,0,0,0', 'outline_style': 'dot', 'outline_width': '0.25'})
                            layer_desa.rendererV2().setSymbol(symbol)
                            layer_desa_line = QgsVectorLayer(desa_line, 'Batas Desa', 'ogr')
                            layer_desa_line.setSubsetString(exp)
                            symbol = QgsLineSymbolV2.createSimple({'color': '0,0,0,255', 'penstyle': 'dot', 'width': '0.25'})
                            layer_desa_line.rendererV2().setSymbol(symbol)
                            palyr = QgsPalLayerSettings()
                            palyr.readFromLayer(layer_desa)
                            palyr.enabled = True
                            palyr.fieldName = 'DESA'
                            palyr.placement = QgsPalLayerSettings.OverPoint
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '8', '')
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferDraw, True, True, '1', '')
                            palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferSize, True, True, '1', '')
                            palyr.writeToLayer(layer_desa)
                            # Bathymetry
                            layer_bath = QgsRasterLayer(self.otoklimdlg.bathymetry.text(), 'Bathymetry')
                            # Add Layer To QGIS Canvas
                            canvas = qgis.utils.iface.mapCanvas()
                            QgsMapLayerRegistry.instance().addMapLayer(layer_bath)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_provinsi)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_vector)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_kabupaten)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_kecamatan)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_desa)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_desa_line)
                            QgsMapLayerRegistry.instance().addMapLayer(layer_kecamatan_line)
                            # Set Extent
                            canvas.setExtent(layer_desa.extent())
                            canvas.refresh()
                            # Create QGIS Porject File
                            f = QFileInfo(projectqgs)
                            p = QgsProject.instance()
                            p.write(f)
                            QgsProject.instance().clear()
                            QgsMapLayerRegistry.instance().removeMapLayer(layer_vector.id())
                            del layer_vector
                            # Read Map
                            template_file = open(self.otoklimdlg.maptemplate3.text())
                            template_content = template_file.read()
                            template_file.close()
                            document = QDomDocument()
                            document.setContent(template_content)
                            if str(value[0])[0:3].upper() == 'ACH' or str(value[0])[0:3].upper() == 'PCH':
                                title_type = "CURAH"
                            else:
                                title_type = "SIFAT"
                            if str(value[0])[0:3].upper().startswith('A'):
                                title_adj = "ANALISIS"
                            else:
                                title_adj = "PRAKIRAAN"
                            map_title = 'PETA ' + title_adj + ' ' + title_type + ' HUJAN BULAN ' + str(month[1]) + ' TAHUN '+ str(year) + ' ' + str(slc_nametitle).upper()
                            substitution_map = {'map_title': map_title, 'date_produced':date_produced}
                            canvas = QgsMapCanvas()
                            QgsProject.instance().read(QFileInfo(projectqgs))
                            bridge = QgsLayerTreeMapCanvasBridge(QgsProject.instance().layerTreeRoot(), canvas)
                            bridge.setCanvasLayers()
                            composition = QgsComposition(canvas.mapSettings())
                            composition.loadFromTemplate(document, substitution_map)
                            map_item = composition.getComposerItemById('map')
                            map_item.setMapCanvas(canvas)
                            map_item.zoomToExtent(canvas.extent())
                            composition.refreshItems()
                            # Save as image
                            dpi = 150
                            dpmm = dpi / 25.4
                            width = int(dpmm * composition.paperWidth())
                            height = int(dpmm * composition.paperHeight())
                            # create output image and initialize it
                            image = QImage(QSize(width, height), QImage.Format_ARGB32)
                            image.setDotsPerMeterX(dpmm * 1000)
                            image.setDotsPerMeterY(dpmm * 1000)
                            image.fill(0)
                            # render the composition
                            imagePainter = QPainter(image)
                            composition.renderPage(imagePainter, 0)
                            imagePainter.end()
                            image.save(output_jpg, "jpg")
                            logger.info('--- Image saved at : ' + output_jpg)
                            # Remove unuse file
                            vector = QgsMapLayerRegistry.instance().mapLayersByName('')[0]
                            desa = QgsMapLayerRegistry.instance().mapLayersByName('Desa')[0]
                            kecamatan = QgsMapLayerRegistry.instance().mapLayersByName('Kecamatan')[0]
                            kabupaten = QgsMapLayerRegistry.instance().mapLayersByName('Kabupaten')[0]
                            provinsi = QgsMapLayerRegistry.instance().mapLayersByName('Provinsi')[0]
                            bathymetry = QgsMapLayerRegistry.instance().mapLayersByName('Bathymetry')[0]
                            kecamatanline = QgsMapLayerRegistry.instance().mapLayersByName('Batas Kecamatan')[0]
                            desaline = QgsMapLayerRegistry.instance().mapLayersByName('Batas Desa')[0]
                            all_layer = [vector.id(), desa.id(), kabupaten.id(), provinsi.id(), bathymetry.id(), kecamatan.id(), kecamatanline.id(), desaline.id()]
                            QgsMapLayerRegistry.instance().removeMapLayers(all_layer)
                            del vector
                            os.remove(projectqgs)
                    else:
                        logger.info('--- Skip processing for ' + str(os.path.basename(output_jpg)))
                        pass
                shutil.rmtree(temp_raster)
                self.otoklimdlg.showGenerateMapFolder.setEnabled(True)
        except Exception as e:
            self.errormessagedlg.ErrorMessage.setText(str(e))
            logger.error(str(e))
            self.errormessagedlg.exec_()

    def generate_csv(self):
        """Function to generate CSV"""
        prcs_directory = os.path.join(self.otoklimdlg.projectworkspace.text(), 'processing')
        logger = self.logger(prcs_directory)
        logger.info('Generate CSV..')
        self.iface.mainWindow().statusBar().showMessage('Generate CSV..')
        classified_directory = os.path.join(prcs_directory, 'classified')
        out_directory = os.path.join(self.otoklimdlg.projectworkspace.text(), 'output')
        csv_directory = os.path.join(out_directory, 'csv')
        items = []
        for index in xrange(self.otoklimdlg.treeWidget_selected_2.topLevelItemCount()):
            items.append(self.otoklimdlg.treeWidget_selected_2.topLevelItem(index))
        slc_id_list = [int(float(i.whatsThis(0).split('|')[1])) for i in items]
        project = os.path.join(
            self.otoklimdlg.projectworkspace.text(),
            self.otoklimdlg.projectfilename.text()
        )
        try:
            logger.debug('- Listing selected parameter to be processed')
            prc_list = []
            if self.otoklimdlg.ach_1_csv.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_ach_1 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_ACH_1"]["NAME"]
                    param = os.path.splitext(raster_ach_1)[0].split('_')[1] + '_' + os.path.splitext(raster_ach_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_ACH_1"]["REGION_LIST"] = str(slc_id_list)
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_ach_1])
                logger.debug('-- ' + str(param) + ' is checked')
            if self.otoklimdlg.ash_1_csv.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_ash_1 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_ASH_1"]["NAME"]
                    param = os.path.splitext(raster_ash_1)[0].split('_')[1] + '_' + os.path.splitext(raster_ash_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_ASH_1"]["REGION_LIST"] = str(slc_id_list)
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_ash_1])
                logger.debug('-- ' + str(param) + ' is checked')
            if self.otoklimdlg.pch_1_csv.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_pch_1 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_1"]["NAME"]
                    param = os.path.splitext(raster_pch_1)[0].split('_')[1] + '_' + os.path.splitext(raster_pch_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_PCH_1"]["REGION_LIST"] = str(slc_id_list)
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_pch_1])
                logger.debug('-- ' + str(param) + ' is checked')
            if self.otoklimdlg.psh_1_csv.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_psh_1 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_1"]["NAME"]
                    param = os.path.splitext(raster_psh_1)[0].split('_')[1] + '_' + os.path.splitext(raster_psh_1)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_PSH_1"]["REGION_LIST"] = str(slc_id_list)
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_psh_1])
                logger.debug('-- ' + str(param) + ' is checked')
            if self.otoklimdlg.pch_2_csv.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_pch_2 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_2"]["NAME"]
                    param = os.path.splitext(raster_pch_2)[0].split('_')[1] + '_' + os.path.splitext(raster_pch_2)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_PCH_2"]["REGION_LIST"] = str(slc_id_list)
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_pch_2])
                logger.debug('-- ' + str(param) + ' is checked')
            if self.otoklimdlg.psh_2_csv.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_psh_2 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_2"]["NAME"]
                    param = os.path.splitext(raster_psh_2)[0].split('_')[1] + '_' + os.path.splitext(raster_psh_2)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_PSH_2"]["REGION_LIST"] = str(slc_id_list)
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_psh_2])
                logger.debug('-- ' + str(param) + ' is checked')
            if self.otoklimdlg.pch_3_csv.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_pch_3 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PCH_3"]["NAME"]
                    param = os.path.splitext(raster_pch_3)[0].split('_')[1] + '_' + os.path.splitext(raster_pch_3)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_PCH_3"]["REGION_LIST"] = str(slc_id_list)
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_pch_3])
                logger.debug('-- ' + str(param) + ' is checked')
            if self.otoklimdlg.psh_3_csv.isChecked():
                with open(project, 'r') as jsonfile:
                    otoklim_project = json.load(jsonfile)
                    raster_psh_3 = otoklim_project["PROCESSING"]["CLASSIFICATION"]["RASTER_PSH_3"]["NAME"]
                    param = os.path.splitext(raster_psh_3)[0].split('_')[1] + '_' + os.path.splitext(raster_psh_3)[0].split('_')[2]
                    otoklim_project["PROCESSING"]["GENERATE_CSV"]["RASTER_PSH_3"]["REGION_LIST"] = str(slc_id_list)
                with open(project, 'w') as jsonfile:
                    jsonfile.write(json.dumps(otoklim_project, indent=4))
                prc_list.append([param, raster_psh_3])
                logger.debug('-- ' + str(param) + ' is checked')
            logger.info('- Selected parameter :' + str(prc_list))
            # Create CSV Default File
            if len(prc_list) > 0:
                driver = ogr.GetDriverByName("ESRI Shapefile")
                kabupaten_csv = os.path.join(csv_directory, 'kabupaten.csv')
                kecamatan_csv = os.path.join(csv_directory, 'kecamatan.csv')
                desa_csv = os.path.join(csv_directory, 'desa.csv')
                kabupaten_json = os.path.join(csv_directory, 'kabupaten.json')
                kecamatan_json = os.path.join(csv_directory, 'kecamatan.json')
                desa_json = os.path.join(csv_directory, 'desa.json')
                output_csv_list = [kabupaten_csv, kecamatan_csv, desa_csv]
                output_json_list = [kabupaten_json, kecamatan_json, desa_json]
                region_id_list = [1, 2, 3]
                shp_list = [
                    self.otoklimdlg.districts.text(), 
                    self.otoklimdlg.subdistricts.text(),
                    self.otoklimdlg.villages.text()
                ]
                json_kabupaten = []
                json_kecamatan = []
                json_desa = []

                csv_edit = []
                for i in slc_id_list:
                    if len(str(i)) == 2:
                        csv_edit.append(1)
                    elif len(str(i)) == 4:
                        csv_edit.append(2)
                    else:
                        csv_edit.append(3)

                check_slc = []
                for shp, output_csv, output_json, region_id in zip(shp_list, output_csv_list, output_json_list, region_id_list):
                    logger.debug('--- Generate in progress for :' + str(output_csv))
                    n = 1
                    if region_id in csv_edit:
                        with open(output_csv, "wb+") as csvfile:
                            if region_id == 1:
                                main_header = ['No', 'Provinsi', 'ID_Kabupaten_Kota', 'Kabupaten_Kota']
                            elif region_id == 2:
                                main_header = ['No', 'Provinsi', 'ID_Kabupaten_Kota', 'Kabupaten_Kota', 'ID_Kecamatan', 'Kecamatan']
                            else:
                                main_header = ['No', 'Provinsi', 'ID_Kabupaten_Kota', 'Kabupaten_Kota', 'ID_Kecamatan', 'Kecamatan', 'ID_Desa', 'Desa']
                            header = main_header
                            param = []
                            for prc in prc_list:
                                param_header = [prc[0].upper() + '_SBK', prc[0].upper() + '_SB', prc[0].upper() + '_SBB', prc[0].upper() + '_M']
                                param.append(param_header)
                                header += param_header
                            csv_writer = csv.DictWriter(csvfile, fieldnames=header,  delimiter=';')
                            csv_writer.writeheader()
                            for slc_id in slc_id_list:
                                if slc_id not in check_slc:
                                    continue_run = True
                                    if len(str(slc_id)) == 2 and region_id == 1:
                                        check_slc.append(slc_id)
                                        logger.info('---- Region : ' + str(slc_id))
                                        layer = QgsVectorLayer(shp, "PROVINSI", "ogr")
                                        exp = "\"ID_PROV\"='{}'".format(str(slc_id))
                                        layer.setSubsetString(exp)
                                    elif len(str(slc_id)) == 4 and region_id == 2:
                                        check_slc.append(slc_id)
                                        logger.info('---- Region : ' + str(slc_id))
                                        layer = QgsVectorLayer(shp, "KABUPATEN", "ogr")
                                        exp = "\"ID_KAB\"='{}'".format(str(slc_id))
                                        layer.setSubsetString(exp)
                                    elif len(str(slc_id)) == 7 and region_id == 3:
                                        check_slc.append(slc_id)
                                        logger.info('---- Region : ' + str(slc_id))
                                        layer = QgsVectorLayer(shp, "KECAMATAN", "ogr")
                                        exp = "\"ID_KEC\"='{}'".format(str(slc_id))
                                        layer.setSubsetString(exp)
                                    else:
                                        continue_run = False
                                    if continue_run:
                                        union_list = {}
                                        temp_list = []
                                        for prc in prc_list:
                                            logger.debug('----- Union :' + str(slc_id) + ' & ' + str(prc[0]))
                                            vector_classified = os.path.join(classified_directory, prc[1])
                                            temp = os.path.join(prcs_directory, 'tmp_' + str(prc[0]))
                                            temp_list.append(temp)
                                            union = os.path.join(temp, str(slc_id) + '_' + str(prc[0]) + '_un.shp')
                                            if os.path.exists(temp):
                                                pass
                                            else:
                                                os.mkdir(temp)
                                            processing.runandload("qgis:union", vector_classified, layer, union)
                                            layer_union = QgsMapLayerRegistry.instance().mapLayersByName('Union')[0]
                                            QgsMapLayerRegistry.instance().removeMapLayer(layer_union)
                                            logger.info('----- Union success.. Vector data has been stored on ' + str(union))
                                            union_list.update({str(prc[0]):  str(union)})
                                        dataSource = driver.Open(shp, 0)
                                        layersource = dataSource.GetLayer()
                                        for feature in layersource:
                                            if (region_id == 1 and feature.GetField("ID_PROV") == slc_id) or (region_id == 2 and feature.GetField("ID_KAB") == slc_id) or (region_id == 3 and feature.GetField("ID_KEC") == slc_id):
                                                if region_id == 1:
                                                    logger.info('---- Region : ' + str(feature.GetField("ID_KAB")))
                                                    main_values = {
                                                        'No': n,
                                                        'Provinsi': feature.GetField("PROVINSI"),
                                                        'ID_Kabupaten_Kota': feature.GetField("ID_KAB"),
                                                        'Kabupaten_Kota': feature.GetField("KABUPATEN")
                                                    }
                                                    exp = "\"ID_KAB\"='{}'".format(str(feature.GetField("ID_KAB")))
                                                elif region_id == 2:
                                                    logger.info('---- Region : ' + str(feature.GetField("ID_KEC")))
                                                    main_values = {
                                                        'No': n,
                                                        'Provinsi': feature.GetField("PROVINSI"),
                                                        'ID_Kabupaten_Kota': feature.GetField("ID_KAB"),
                                                        'Kabupaten_Kota': feature.GetField("KABUPATEN"),
                                                        'ID_Kecamatan': feature.GetField("ID_KEC"),
                                                        'Kecamatan': feature.GetField("KECAMATAN")
                                                    }
                                                    exp = "\"ID_KEC\"='{}'".format(str(feature.GetField("ID_KEC")))
                                                else:
                                                    logger.info('---- Region : ' + str(feature.GetField("ID_DES")))
                                                    main_values = {
                                                        'No': n,
                                                        'Provinsi': feature.GetField("PROVINSI"),
                                                        'ID_Kabupaten_Kota': feature.GetField("ID_KAB"),
                                                        'Kabupaten_Kota': feature.GetField("KABUPATEN"),
                                                        'ID_Kecamatan': feature.GetField("ID_KEC"),
                                                        'Kecamatan': feature.GetField("KECAMATAN"),
                                                        'ID_Desa': feature.GetField("ID_DES"),
                                                        'Desa': feature.GetField("DESA")
                                                    }
                                                    exp = "\"ID_DES\"='{}'".format(str(feature.GetField("ID_DES")))
                                                param_values = {}
                                                for prc in prc_list:
                                                    # Calculate Area
                                                    logger.info('----- Calculate Area Classified: ' + str(prc[0]))
                                                    sbk = {}
                                                    sb = {}
                                                    sbb = {}
                                                    m = {}
                                                    unique_counts = {}
                                                    expression = QgsExpression("area(transform($geometry, 'EPSG:4326','EPSG:3857'))")
                                                    layer_union = QgsVectorLayer(union_list[str(prc[0])], str(prc[0]), 'ogr')
                                                    layer_union.setSubsetString(exp)
                                                    index = layer_union.fieldNameIndex("Area")
                                                    expression.prepare(layer_union.pendingFields())
                                                    area_all = 0
                                                    features = layer_union.getFeatures()
                                                    for i in features:
                                                        if expression.evaluate(i):
                                                            area_all += expression.evaluate(i)
                                                        else:
                                                            area_all += 0
                                                    layer_union.startEditing()
                                                    features = layer_union.getFeatures()
                                                    for i in features:
                                                        if i[prc[0].upper().split('_')[0]]:
                                                            if expression.evaluate(i):
                                                                area = expression.evaluate(i)
                                                            else:
                                                                area = 0
                                                            layer_union.changeAttributeValue(
                                                                i.id(),
                                                                layer_union.fieldNameIndex('Area'), 
                                                                area
                                                            )
                                                            layer_union.changeAttributeValue(
                                                                i.id(),
                                                                layer_union.fieldNameIndex('Percent'), 
                                                                (area / float(area_all)) * 100
                                                            )
                                                            if i[prc[0].upper().split('_')[0]] not in unique_counts:
                                                                unique_counts[i[prc[0].upper().split('_')[0]]] = (area / float(area_all)) * 100
                                                            else:
                                                                unique_counts[i[prc[0].upper().split('_')[0]]] += (area / float(area_all)) * 100
                                                    layer_union.commitChanges()
                                                    for key, value in zip(unique_counts.keys(), unique_counts.values()):
                                                        if value > 0 and value < 20:
                                                            sbk.update({key: value})
                                                        elif value >= 20 and value < 50:
                                                            sb.update({key: value})
                                                        elif value >= 50 and value < 100:
                                                            sbb.update({key: value})
                                                        elif value == 100:
                                                            m.update({key: value})
                                                    param_values.update({
                                                        prc[0].upper() + '_SBK': sbk,
                                                        prc[0].upper() + '_SB': sb,
                                                        prc[0].upper() + '_SBB': sbb,
                                                        prc[0].upper() + '_M': m
                                                    })
                                                # JSON Structure
                                                logger.debug('----- Write JSON')
                                                json_values = {}
                                                json_values.update({"VALUES": param_values})
                                                json_values.update(main_values)
                                                if region_id == 1:
                                                    json_kabupaten.append(json_values)
                                                elif region_id == 2:
                                                    json_kecamatan.append(json_values)
                                                else:
                                                    json_desa.append(json_values)
                                                # CSV Structure
                                                main_values.update(param_values)
                                                logger.debug('----- Write CSV')
                                                csv_writer.writerow(main_values)
                                                n += 1
                                        del layer_union    
                                        dataSource.Destroy()
                                        for temp in temp_list:
                                            shutil.rmtree(temp)
                        with open(output_json, 'w') as jsonfile:
                            if region_id == 1:
                                jsonfile.write(json.dumps(json_kabupaten, indent=4))
                            elif region_id == 2:
                                jsonfile.write(json.dumps(json_kecamatan, indent=4))
                            else:
                                jsonfile.write(json.dumps(json_desa, indent=4))     
            self.otoklimdlg.showGenerateCSVFolder.setEnabled(True)
        except Exception as e:
            self.errormessagedlg.ErrorMessage.setText(str(e))
            logger.error(str(e))
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
