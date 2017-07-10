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
import resources
import os.path
import qgis.utils
import csv
import os
import time
import processing
import math
import shutil

from otoklim_dialog import OtoklimDialog
from osgeo import gdal, ogr, osr
from gdalconst import GA_ReadOnly
from qgis.analysis import QgsZonalStatistics
from qgis.gui import QgsMapCanvas, QgsLayerTreeMapCanvasBridge
from qgis.core import (
            QgsVectorLayer,
            QgsRasterLayer,
            QgsMapLayerRegistry,
            QgsRasterShader,
            QgsColorRampShader,
            QgsSingleBandPseudoColorRenderer,
            QgsProject,
            QgsComposition,
            QgsFillSymbolV2,
            QgsPalLayerSettings,
            QgsExpression,
            QgsFeatureRequest,
            QgsVectorFileWriter,
            QgsCategorizedSymbolRendererV2,
            QgsRendererCategoryV2,
            QgsRasterFileWriter,
            QgsRasterPipe
        )
from PyQt4 import QtGui
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFileInfo
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QInputDialog, QListWidgetItem
from PyQt4.QtXml import QDomDocument


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
        parent=None
    ):
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
        self.dlg = OtoklimDialog()

        # GEO 03062017: Add method to browse input file while browse button is clicked
        self.dlg.Input_CH_CSV.clear()
        self.dlg.Browse_CH_CSV.clicked.connect(self.select_input_ch_csv)

        # GEO 08062017: Add method to trigger enabled optional frame while radio button toggled
        self.dlg.mode_1.toggled.connect(self.enabled_optioanl_frame)
        self.dlg.mode_2.toggled.connect(self.enabled_optioanl_frame)
        self.dlg.mode_3.toggled.connect(self.enabled_optioanl_frame)
        self.dlg.mode_4.toggled.connect(self.enabled_optioanl_frame)

        # GEO 08062017: Add method to listing kabupaten\kota or kecamatan from administration shapefile
        plugin_dir = os.path.dirname(os.path.realpath(__file__))
        kab_file = os.path.join(plugin_dir, 'static\jatim_kabupaten_kota.shp')
        layer_kab = QgsVectorLayer(kab_file, 'kabupaten', 'ogr')
        kec_file = os.path.join(plugin_dir, 'static\jatim_kecamatan.shp')
        layer_kec = QgsVectorLayer(kec_file, 'kecamatan', 'ogr')
        for feature_kab in layer_kab.getFeatures():
            item = QListWidgetItem('- Kabupaten ' + feature_kab['KABUPATEN'].capitalize())
            item.setWhatsThis(str(feature_kab['ID_KAB_CLE']))
            self.dlg.listWidget_option.addItem(item)
            for feature_kec in layer_kec.getFeatures():
                if feature_kec['ID_KAB_CLE'] == feature_kab['ID_KAB_CLE']:
                    item = QListWidgetItem('--- Kecamatan ' + feature_kec['KECAMATAN'].capitalize())
                    item.setWhatsThis(str(feature_kec['ID_KEC_CLE']))
                    self.dlg.listWidget_option.addItem(item)

        # GEO 09062017: Add method to trigger move button
        self.dlg.addSelected.clicked.connect(self.add_to_selected)
        self.dlg.deleteUnselected.clicked.connect(self.delete_from_selected)

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
            text=self.tr(u'Otoklim Generate..'),
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

    # GEO 08062017: Add Costum Functions
    def select_input_ch_csv(self):
        filename_csv = QFileDialog.getOpenFileName(self.dlg, "", "", "*.csv")
        self.dlg.Input_CH_CSV.setText(filename_csv)

    def enabled_optioanl_frame(self):
        if self.dlg.mode_4.isChecked():
            self.dlg.frame_optional.setEnabled(True)
        else:
            self.dlg.frame_optional.setEnabled(False)

    def add_to_selected(self):
        items = []
        for index in xrange(self.dlg.listWidget_selected.count()):
            items.append(self.dlg.listWidget_selected.item(index))
        selected_items = [i.text() for i in items]

        for item in self.dlg.listWidget_option.selectedItems():
            if item.text() not in selected_items:
                newitem = QListWidgetItem(item.text())
                newitem.setWhatsThis(item.whatsThis())
                self.dlg.listWidget_selected.addItem(newitem)
            else:
                pass

    def delete_from_selected(self):
        for item in self.dlg.listWidget_selected.selectedItems():
            self.dlg.listWidget_selected.takeItem(
                self.dlg.listWidget_selected.row(item)
            )

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # Static File
        plugin_dir = os.path.dirname(os.path.realpath(__file__))
        provinsi_polygon_file = os.path.join(plugin_dir, 'static\jatim_provinsi.shp')
        kabupaten_kota_polygon_file = os.path.join(plugin_dir, 'static\jatim_kabupaten_kota.shp')
        kecamatan_polygon_file = os.path.join(plugin_dir, 'static\jatim_kecamatan.shp')
        desa_polygon_file = os.path.join(plugin_dir, 'static\jatim_desa.shp')
        jawa_bali_file = os.path.join(plugin_dir, 'static\jawa_bali.shp')
        map_template = os.path.join(plugin_dir, 'static\map_template.qpt')
        map_template2 = os.path.join(plugin_dir, 'static\map_template2.qpt')
        bathymetry_file = os.path.join(plugin_dir, 'static\byth_gebco.tif')
        rule_file_ch = os.path.join(plugin_dir, 'static\rule_ch.txt')
        rule_file_sh = os.path.join(plugin_dir, 'static\rule_sh.txt')
        # See if OK was pressed
        if result:
            # GEO 03062017 Insert Otoklim Main Logic
            '''
            filename_1 = self.dlg.Input_CH_CSV.text()
            filename_2 = self.dlg.Delimiter.text()
            filename_3 = self.dlg.Year.text()
            filename_4 = self.dlg.Select_Months.currentText()
            print filename_1
            print filename_2
            print filename_3
            print filename_4
            '''
            file_input = self.dlg.Input_CH_CSV.text()
            csv_delimiter = self.dlg.Delimiter.text()
            file_directory = str(os.path.dirname(os.path.realpath(file_input)))

            map_directory = os.path.join(file_directory, 'map')
            try:
                shutil.rmtree(map_directory)
                os.mkdir(os.path.join(file_directory, 'map'))
            except:
                os.mkdir(os.path.join(file_directory, 'map'))

            temp_directory = os.path.join(file_directory, 'temp')
            try:
                shutil.rmtree(temp_directory)
                os.mkdir(os.path.join(file_directory, 'temp'))
            except:
                os.mkdir(os.path.join(file_directory, 'temp'))

            csv_directory = os.path.join(file_directory, 'csv')
            try:
                shutil.rmtree(csv_directory)
                os.mkdir(os.path.join(file_directory, 'csv'))
            except:
                os.mkdir(os.path.join(file_directory, 'csv'))

            def select_date_now():
                mth = self.dlg.Select_Months.currentText()
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

                yrs = int(float(self.dlg.Year.text()))
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
            print select_date_now()
            print file_input
            print csv_delimiter
            items = []
            for index in xrange(self.dlg.listWidget_selected.count()):
                items.append(self.dlg.listWidget_selected.item(index))
            selected_adm = [i.whatsThis() for i in items]
            print selected_adm
            pass
