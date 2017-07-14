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
import datetime
import shutil
import logging
import numpy as np

from otoklim_dialog import OtoklimDialog
from osgeo import gdal, ogr, osr
from gdalconst import GA_ReadOnly
from qgis.analysis import QgsZonalStatistics
from qgis.gui import QgsMapCanvas, QgsLayerTreeMapCanvasBridge, QgsMessageBar
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
            QgsRendererCategoryV2
        )
from PyQt4 import QtGui
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFileInfo
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QListWidgetItem
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
        # See if OK was pressed
        if result:
            # GEO 03062017 Insert Otoklim Main Logic
            # Static File
            plugin_dir = os.path.dirname(os.path.realpath(__file__))
            station_file = os.path.join(plugin_dir, 'static', 'station_id.csv')
            provinsi_polygon_file = os.path.join(plugin_dir, 'static', 'jatim_provinsi.shp')
            kabupaten_kota_polygon_file = os.path.join(plugin_dir, 'static', 'jatim_kabupaten_kota.shp')
            kecamatan_polygon_file = os.path.join(plugin_dir, 'static', 'jatim_kecamatan.shp')
            desa_polygon_file = os.path.join(plugin_dir, 'static', 'jatim_desa.shp')
            jawa_bali_file = os.path.join(plugin_dir, 'static', 'jawa_bali.shp')
            map_template = os.path.join(plugin_dir, 'static', 'map_template.qpt')
            map_template2 = os.path.join(plugin_dir, 'static', 'map_template2.qpt')
            bathymetry_file = os.path.join(plugin_dir, 'static', 'byth_gebco.tif')
            rule_file_ch = os.path.join(plugin_dir, 'static', 'rule_ch.txt')
            rule_file_sh = os.path.join(plugin_dir, 'static', 'rule_sh.txt')
            driver = ogr.GetDriverByName("ESRI Shapefile")
            logger = logging.getLogger(__name__)

            # Input
            after_prov = False
            start_time = time.time()
            now = datetime.datetime.now()
            warning = None
            file_input = self.dlg.Input_CH_CSV.text()  # Input CSV File
            if not file_input:
                warning = 'fileinput'
            file_directory = str(os.path.dirname(os.path.realpath(file_input)))
            csv_delimiter = self.dlg.Delimiter.text() # Input CSV Delimiter
            try:
                yrs = self.dlg.Year.text()
                if yrs:
                    yrs = int(float(yrs))
                else:
                    yrs = datetime.datetime.now().year
            except:
                warning = 'thisyear'

            def select_date_now(yrs):
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
                logger.info('month: ' + str(month_header))
                logger.info('years: ' + str(years_header))
                return month_header, years_header

            def select_adm_region():
                if self.dlg.mode_1.isChecked():
                    mode = 1
                elif self.dlg.mode_2.isChecked():
                    mode = 2
                elif self.dlg.mode_3.isChecked():
                    mode = 3
                else:
                    mode = 4
                regional_list = []
                regional_list.append(['provinsi', 'JAWA TIMUR', 35, 'none'])
                if mode == 1:
                    logger.info('Running mode : ' + str(mode) + ' [Jawa Timut Province Only]')
                    logger.info(str(regional_list))
                    return regional_list
                elif mode == 2:
                    logger.info('Running mode : ' + str(mode) + ' [All Kabupaten \ Kota]')
                    dataSource = driver.Open(kabupaten_kota_polygon_file, 0)
                    layer_kab = dataSource.GetLayer()
                    for feature in layer_kab:
                        regional_list.append(['kabupaten_kota', feature.GetField("KABUPATEN"), feature.GetField("ID_KAB_CLE"),  feature.GetField("ID_PROV")])
                    logger.info(str(regional_list))
                    return regional_list
                elif mode == 3:
                    logger.info('Running mode : ' + str(mode) + ' [All Kecamatan]')
                    dataSource = driver.Open(kecamatan_polygon_file, 0)
                    layer_kec = dataSource.GetLayer()
                    for feature in layer_kec:
                        regional_list.append(['kecamatan', feature.GetField("KECAMATAN"), feature.GetField("ID_KEC_CLE"),  feature.GetField("ID_KAB_CLE")])
                    logger.info(str(regional_list))
                    return regional_list
                elif mode == 4:
                    logger.info('Running mode : ' + str(mode) + ' [Selected Region]')
                    items = []
                    for index in xrange(self.dlg.listWidget_selected.count()):
                        items.append(self.dlg.listWidget_selected.item(index))
                    slc = [int(float(i.whatsThis())) for i in items]
                    dataSource = driver.Open(kabupaten_kota_polygon_file, 0)
                    layer_kab = dataSource.GetLayer()
                    for feature in layer_kab:
                        if int(feature.GetField("ID_KAB_CLE")) in slc:
                            regional_list.append(['kabupaten_kota', feature.GetField("KABUPATEN"), feature.GetField("ID_KAB_CLE"),  feature.GetField("ID_PROV")])
                    dataSource = driver.Open(kecamatan_polygon_file, 0)
                    layer_kec = dataSource.GetLayer()
                    for feature in layer_kec:
                        if int(feature.GetField("ID_KEC_CLE")) in slc:
                            regional_list.append(['kecamatan', feature.GetField("KECAMATAN"), feature.GetField("ID_KEC_CLE"),  feature.GetField("ID_KAB_CLE")])
                    logger.info(str(regional_list))
                    return regional_list

            def combinecsv(delimiter):
                logger.info('Combine Input CSV With Station Data..')
                self.iface.mainWindow().statusBar().showMessage('Combine Input CSV With Station Data..')
                dict_input = {}
                dict_station = {}

                combine_file = os.path.join(file_directory, 'combine.csv')
                try:
                    if os.path.exists(combine_file):
                        driver.DeleteDataSource(combine_file)
                except:
                    pass

                if not delimiter:
                        delimiter = ','
                logger.info('CSV Input File delimited by ' + delimiter)

                with open(file_input, 'rb') as csvfile:
                    spamreader = csv.reader(csvfile, delimiter=str(delimiter), quotechar='|')
                    n = 0
                    for row in spamreader:
                        if n != 0:
                            dict_input.update({int(row[0]): row[1:]})
                        else:
                            header_input = row[1:]
                        n += 1

                with open(station_file, 'rb') as csvfile:
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
                    logger.debug('Write row in progress..')
                    for row in combine.values():
                        csv_writer.writerow(row)

                logger.info('Combining success.. Combine csv file has been stored on ' + str(combine_file))
                return combine_file

            def csvtoshp(delimiter, csv_file):
                logger.info('Convert Stasiun Data From CSV to Shapefile (Point)')
                self.iface.mainWindow().statusBar().showMessage('Convert Stasiun Data From CSV to Shapefile (Point)')
                filename_shp = os.path.join(file_directory, 'stasiun.shp')
                filename_prj = os.path.join(file_directory, 'stasiun.prj')

                try:
                    if os.path.exists(filename_shp):
                        driver.DeleteDataSource(filename_shp)
                    if os.path.exists(filename_prj):
                        driver.DeleteDataSource(filename_prj)
                except Exception as e:
                    pass
                data_source = driver.CreateDataSource(filename_shp)

                srs = osr.SpatialReference()
                srs.ImportFromEPSG(4326)
                srs.MorphToESRI()
                prj_file = open(filename_prj, 'w')
                prj_file.write(srs.ExportToWkt())
                prj_file.close()

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
                    if not delimiter:
                        delimiter = ','
                    logger.info('CSV Combine File delimited by ' + delimiter)
                    spamreader = csv.DictReader(csvfile, delimiter=str(delimiter), quotechar='|')
                    logger.debug('Create feature in progress...')
                    for row in spamreader:
                        point = ogr.Geometry(ogr.wkbPoint)
                        feature = ogr.Feature(layer.GetLayerDefn())
                        point.AddPoint(float(row['bujur']), float(row['lintang']))
                        for h in headers:
                            feature.SetField(h, row[h])
                        feature.SetGeometry(point)
                        layer.CreateFeature(feature)

                logger.info('Converting success.. Shapefile data has been stored on ' + str(filename_shp))
                return filename_shp

            def idw_interpolate(point, months):
                logger.info('Interpolate Stasiun Point By Using IDW Method..')
                self.iface.mainWindow().statusBar().showMessage('Interpolate Stasiun Point By Using IDW Method..')
                raster_interpolated_list = []
                layer = QgsVectorLayer(point, 'layer', 'ogr')
                fields = layer.pendingFields()
                field_names = [field.name() for field in fields]
                idw_params = field_names[5:]
                logger.info('Input file : ' + point)

                for param in idw_params:
                    raster_interpolated = os.path.join(temp_directory, param + 'raster_idw.tif')
                    try:
                        os.remove(raster_interpolated)
                    except OSError:
                        pass
                    logger.info('- Field (Parameter) : ' + param)
                    logger.debug('- Interpolating in progress...')
                    processing.runalg('grass7:v.surf.idw', layer, 8.0, 5.0, param, False, "%f,%f,%f,%f" % (110.5, 117, -9, -4.5), 0.001, -1.0, 0.0001, raster_interpolated)
                    raster_interpolated_list.append(raster_interpolated)
                    logger.info('- Interpolating success.. Raster data has been stored on ' + str(raster_interpolated))

                n = 0
                for month in months:
                    idw_params[n] = idw_params[n].split('_')[0] + '_' + str(month[0])
                    idw_params[n+1] = idw_params[n+1].split('_')[0] + '_' + str(month[0])
                    n += 2
                return raster_interpolated_list, idw_params

            def clip_raster(raster_input, region):
                logger.info('Clipping Raster..')
                self.iface.mainWindow().statusBar().showMessage('Clipping Raster..')
                raster_list = raster_input[0]
                param_list = raster_input[1]
                clip_raster_list = []
                for raster, param in zip(raster_list, param_list):
                    logger.info('- Raster: ' + str(raster))
                    logger.info('- Parameter: ' + str(param))
                    logger.info('- Region: ' + str(region))
                    raster_layer = QgsRasterLayer(raster, 'Raster CH')
                    QgsMapLayerRegistry.instance().addMapLayer(raster_layer)
                    if region[0] == 'provinsi':
                        raster_cropped = os.path.join(temp_directory, 'interpolated_' + str(param).lower() + '.tif')
                        try:
                            os.remove(raster_cropped)
                        except OSError:
                            pass
                        logger.info('-- Clipping region: ' + str(region[2]))
                        logger.debug('-- Clipping in progress')
                        processing.runalg("gdalogr:cliprasterbymasklayer", raster_layer, provinsi_polygon_file, -1, False, False, False, 6, 0, 75, 1, 1, False, 0, False, "", raster_cropped)
                        logger.info('-- Clipping success, Raster Clipped data has been stored on ' + raster_cropped)
                        clip_raster_list.append(raster_cropped)
                    else:
                        raster_cropped = os.path.join(temp_directory, 'idw_' + str(param).lower() + '_' +  str(int(region[2])) + '_' + str(region[1]).lower()  + '.tif')
                        try:
                            os.remove(raster_cropped)
                        except OSError:
                            pass
                        selected_file = os.path.join(temp_directory, str(param) + str(region[1]) + str(int(region[2])) + '_slctd_plygon.shp')

                        try:
                            os.remove(selected_file)
                        except OSError:
                            pass
                        if region[0] == 'kabupaten_kota':
                            layer = QgsVectorLayer(kabupaten_kota_polygon_file, 'Batas Kabupaten', 'ogr')
                            exp = "\"ID_KAB_CLE\" = " + str(region[2])
                        elif region[0] == 'kecamatan':
                            layer = QgsVectorLayer(kecamatan_polygon_file, 'Batas Kecamatan', 'ogr')
                            exp = "\"ID_KEC_CLE\" = " + str(region[2])
                        elif region[0] == 'desa':
                            layer = QgsVectorLayer(desa_polygon_file, 'Batas Desa', 'ogr')
                            exp = "\"ID_DESA_CL\" = " + str(region[2])

                        QgsMapLayerRegistry.instance().addMapLayer(layer)
                        it = layer.getFeatures(QgsFeatureRequest(QgsExpression(exp)))
                        ids = [i.id() for i in it]
                        layer.setSelectedFeatures(ids)
                        QgsVectorFileWriter.writeAsVectorFormat(layer, selected_file, "utf-8", layer.crs(), "ESRI Shapefile", 1)
                        layer_poly = QgsVectorLayer(selected_file, "lyr1", "ogr")
                        QgsMapLayerRegistry.instance().addMapLayer(layer_poly)
                        logger.info('-- Clipping region: ' + str(region[2]))
                        logger.debug('-- Clipping in progress')
                        processing.runalg("gdalogr:cliprasterbymasklayer", raster, layer_poly, -1, False, False, False, 6, 0, 75, 1, 1, False, 0, False, "", raster_cropped)
                        logger.info('-- Clipping success, Raster Clipped data has been stored on ' + str(raster_cropped))
                        QgsMapLayerRegistry.instance().removeMapLayer(layer_poly.id())
                        QgsMapLayerRegistry.instance().removeMapLayer(layer)
                        clip_raster_list.append(raster_cropped)
                        QgsVectorFileWriter.deleteShapeFile(selected_file)
                    QgsMapLayerRegistry.instance().removeMapLayer(raster_layer.id())
                return clip_raster_list, param_list

            def raster_classify(raster_input):
                logger.info('Classify Raster..')
                self.iface.mainWindow().statusBar().showMessage('Classify Raster..')
                raster_list = raster_input[0]
                param_list = raster_input[1]
                raster_classified_list = []
                for raster, param in zip(raster_list, param_list):
                    logger.info('- Raster: ' + str(raster))
                    logger.info('- Parameter: ' + str(param))
                    raster_classified = os.path.join(temp_directory, 'classfied_' + str(param).lower() + '.tif')
                    try:
                        os.remove(raster_classified)
                    except OSError:
                        pass
                    logger.debug('-- Raster Recode In Progress..')
                    if param[0:3] == 'ACH' or param[0:3] == 'PCH':
                        processing.runalg('grass7:r.recode', raster, rule_file_ch, False, "%f,%f,%f,%f" % (110.5, 117, -9, -4.5), 0.001, raster_classified)
                    else:
                        processing.runalg('grass7:r.recode', raster, rule_file_sh, False, "%f,%f,%f,%f" % (110.5, 117, -9, -4.5), 0.001, raster_classified)
                    logger.info('-- Classification success, Raster Classified data has been stored on ' + raster_classified)
                    raster_classified_list.append(raster_classified)
                return raster_classified_list, param_list

            def create_qgs(raster_input, point, region):
                logger.info('Create .qgs File..')
                self.iface.mainWindow().statusBar().showMessage('Create .qgs File..')
                raster_list = raster_input[0]
                param_list = raster_input[1]
                projectqgs_list = []
                for raster, param in zip(raster_list, param_list):
                    logger.info('- Raster: ' + str(raster))
                    logger.info('- Parameter: ' + str(param))
                    logger.info('- Region: ' + str(region))
                    projectqgs = os.path.join(temp_directory, str(param) + str(region[1]) + str(int(region[2])) + '_project.qgs')
                    try:
                        os.remove(projectqgs)
                    except OSError:
                        pass

                    # Raster CH Styling
                    logger.debug('-- CH Styling in progress..')
                    layer_raster_ch = QgsRasterLayer(raster, 'Raster CH')
                    s = QgsRasterShader()
                    c = QgsColorRampShader()
                    c.setColorRampType(QgsColorRampShader.DISCRETE)
                    i = []
                    if param[0:3] == 'ACH' or param[0:3] == 'PCH':
                        color = ['#340900', '#8e2800', '#dc6200', '#efa800', '#eae100', '#e0fd67', '#8bd48b', '#369134', '#00450c']
                        label = ['0 - 20', '21 - 50', '51 - 100', '101 - 150', '151 - 200', '201 - 300', '301 - 400', '401 - 500', '> 500']
                        lng = 10
                        list_value = [20, 50, 100, 150, 200, 300, 400, 500, 9999]
                    else:
                        color = ['#531616', '#ac5b17', '#f3c424', '#ffff17', '#90b716', '#2d813b', '#0d4624']
                        label = ['0 - 30', '31 - 50', '51 - 84', '85 - 115', '116 - 150', '151 - 200', '> 201']
                        lng = 8
                        list_value = [30, 50, 84, 115, 150, 200, 9999]
                    i.append(QgsColorRampShader.ColorRampItem(-1, QtGui.QColor.fromRgb(0,0,0,0), ''))
                    for n in range(1, lng):
                        i.append(QgsColorRampShader.ColorRampItem(list_value[n-1], QtGui.QColor(color[n-1]), label[n-1]))
                    c.setColorRampItemList(i)
                    s.setRasterShaderFunction(c)
                    ps = QgsSingleBandPseudoColorRenderer(layer_raster_ch.dataProvider(), 1, s)
                    layer_raster_ch.setRenderer(ps)

                    if region[0] == 'provinsi':
                        layer_parent = QgsVectorLayer(jawa_bali_file, 'Batas Provinsi', 'ogr')
                        layer_child = QgsVectorLayer(kabupaten_kota_polygon_file, 'Batas Kabupaten', 'ogr')
                        childtype = 'KABUPATEN'
                        parenttype = 'PROVINSI'
                    elif region[0] == 'kabupaten_kota':
                        layer_parent = QgsVectorLayer(kabupaten_kota_polygon_file, 'Batas Kabupaten', 'ogr')
                        layer_child = QgsVectorLayer(kecamatan_polygon_file, 'Batas Kecamatan', 'ogr')
                        exp = "\"ID_KAB_CLE\" = " + str(region[2])
                        fieldname1 = "ID_KAB_CLE"
                        fieldname2 = "ID_PROV"
                        childtype = 'KECAMATAN'
                        parenttype = 'KABUPATEN'
                    elif region[0] == 'kecamatan':
                        layer_parent = QgsVectorLayer(kecamatan_polygon_file, 'Batas Kecamatan', 'ogr')
                        layer_child = QgsVectorLayer(desa_polygon_file, 'Batas Desa', 'ogr')
                        exp = "\"ID_KEC_CLE\" = " + str(region[2])
                        fieldname1 = "ID_KEC_CLE"
                        fieldname2 = "ID_KAB_CLE"
                        childtype = 'DESA_CLEAN'
                        parenttype = 'KECAMATAN'

                    # Child Region Styling
                    logger.debug('-- Child Region Styling in progress..')
                    symbol = QgsFillSymbolV2.createSimple({'color': '0,0,0,0', 'outline_color': '0,0,0,255', 'outline_style': 'dot', 'outline_width': '0.25'})
                    if region[0] == 'provinsi':
                        layer_child.rendererV2().setSymbol(symbol)
                    else:
                        renderer = QgsCategorizedSymbolRendererV2(fieldname1)
                        cat = QgsRendererCategoryV2(region[2], symbol, str(region[2]))
                        renderer.addCategory(cat)
                        layer_child.setRendererV2(renderer)
                    layer_child.triggerRepaint()
                    palyr = QgsPalLayerSettings()
                    palyr.readFromLayer(layer_child)
                    palyr.enabled = True
                    palyr.fieldName = childtype
                    palyr.placement = QgsPalLayerSettings.OverPoint
                    palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '8', '')
                    palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferDraw, True, True, '1', '')
                    palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferSize, True, True, '1', '')
                    palyr.writeToLayer(layer_child)

                    logger.debug('-- Parent Region Styling in progress..')
                    symbol = QgsFillSymbolV2.createSimple({'color': '169,169,169,255', 'outline_color': '0,0,0,255', 'outline_style': 'solid', 'outline_width': '0.5'})
                    if region[0] == 'provinsi':
                        layer_parent.rendererV2().setSymbol(symbol)
                    else:
                        renderer = QgsCategorizedSymbolRendererV2(fieldname2)
                        cat = QgsRendererCategoryV2(region[3], symbol, str(region[3]))
                        renderer.addCategory(cat)
                        layer_parent.setRendererV2(renderer)
                    layer_parent.triggerRepaint()
                    palyr = QgsPalLayerSettings()
                    palyr.readFromLayer(layer_parent)
                    palyr.enabled = True
                    palyr.fieldName = parenttype
                    palyr.placement = QgsPalLayerSettings.OverPoint
                    palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '14', '')
                    palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferDraw, True, True, '1', '')
                    palyr.setDataDefinedProperty(QgsPalLayerSettings.BufferSize, True, True, '1', '')
                    palyr.writeToLayer(layer_parent)

                    # Add Bathymetry
                    layer_bathymetry = QgsRasterLayer(bathymetry_file, 'Raster Byth')

                    # Add Layer To QGIS Canvas
                    canvas = qgis.utils.iface.mapCanvas()
                    QgsMapLayerRegistry.instance().addMapLayer(layer_bathymetry)
                    QgsMapLayerRegistry.instance().addMapLayer(layer_parent)
                    QgsMapLayerRegistry.instance().addMapLayer(layer_raster_ch)
                    QgsMapLayerRegistry.instance().addMapLayer(layer_child)

                    # Set Extent
                    if region[0] != 'provinsi':
                        it = layer_parent.getFeatures(QgsFeatureRequest(QgsExpression(exp)))
                        ids = [i.id() for i in it]
                        layer_parent.setSelectedFeatures(ids)
                        box = layer_parent.boundingBoxOfSelected()
                        canvas.setExtent(box)
                        canvas.refresh()
                        layer_parent.removeSelection()
                    else:
                        canvas.setExtent(layer_child.extent())
                        canvas.refresh()

                    f = QFileInfo(projectqgs)
                    p = QgsProject.instance()
                    p.write(f)
                    QgsProject.instance().clear()
                    print "----"
                    logger.info('Create .qgs file success, .qgs file has been stored on ' + projectqgs)
                    projectqgs_list.append(projectqgs)
                return projectqgs_list, param_list

            def create_pdf_map(qgsfiles_input, region, dates_input):
                logger.info('Generate Map in PDF..')
                self.iface.mainWindow().statusBar().showMessage('Generate Map in PDF..')
                qgsfiles_list = qgsfiles_input[0]
                param_list = qgsfiles_input[1]
                months_list = dates_input[0]
                years_list = dates_input[1]
                n = 0
                m = 0
                for qgsfiles, param in zip(qgsfiles_list, param_list):
                    logger.info('- qgs file: ' + str(qgsfiles))
                    logger.info('- parameter file: ' + str(param))
                    map_filename = str(region[1]).lower() + '_map_' + str(param).lower() + '_' + str(int(region[2])) + '.pdf'
                    output_pdf = os.path.join(map_directory, map_filename)
                    try:
                        os.remove(output_pdf)
                    except OSError:
                        pass
                    if region[0] == 'provinsi':
                        template_file = open(map_template)
                    else:
                        template_file = open(map_template2)
                    template_content = template_file.read()
                    template_file.close()
                    document = QDomDocument()
                    document.setContent(template_content)
                    if param[0:3] == 'ACH' or param[0:3] == 'PCH':
                        title_type = "CURAH"
                    else:
                        title_type = "SIFAT"
                    map_title = 'PETA PERKIRAAN ' + title_type + ' HUJAN BULAN ' + str(months_list[m][1]) + ' TAHUN '+ str(years_list[m]) + ' JAWA TIMUR'
                    if n % 2 != 0:
                        m += 1
                    n += 1
                    substitution_map = {'map_title': map_title}
                    canvas = QgsMapCanvas()
                    QgsProject.instance().read(QFileInfo(qgsfiles))
                    bridge = QgsLayerTreeMapCanvasBridge(QgsProject.instance().layerTreeRoot(), canvas)
                    bridge.setCanvasLayers()
                    composition = QgsComposition(canvas.mapSettings())
                    composition.loadFromTemplate(document, substitution_map)
                    map_item = composition.getComposerItemById('map')
                    inset_item = composition.getComposerItemById('inset')
                    map_item.setMapCanvas(canvas)
                    if region[0] == 'provinsi':
                        zoom_layer = QgsMapLayerRegistry.instance().mapLayersByName('Batas Kabupaten')[0]
                        parent_layer = QgsMapLayerRegistry.instance().mapLayersByName('Batas Provinsi')[0]
                    else:
                        map_item.zoomToExtent(canvas.extent())
                        if region[0] == 'kabupaten_kota':
                            zoom_layer = QgsMapLayerRegistry.instance().mapLayersByName('Batas Kabupaten')[0]
                            exp = "\"ID_PROV\" = " + str(region[3])
                            parent_layer = QgsMapLayerRegistry.instance().mapLayersByName('Batas Kecamatan')[0]
                        elif region[0] == 'kecamatan':
                            zoom_layer = QgsMapLayerRegistry.instance().mapLayersByName('Batas Kecamatan')[0]
                            exp = "\"ID_KAB_CLE\" = " + str(region[3])
                            parent_layer = QgsMapLayerRegistry.instance().mapLayersByName('Batas Desa')[0]
                        elif region[0] == 'desa':
                            zoom_layer = QgsMapLayerRegistry.instance().mapLayersByName('Batas Desa')[0]
                            exp = "\"ID_KEC_CLE\" = " + str(region[3])
                            parent_layer = QgsMapLayerRegistry.instance().mapLayersByName('Desa')[0]
                        it = zoom_layer.getFeatures(QgsFeatureRequest(QgsExpression(exp)))
                        ids = [i.id() for i in it]
                        zoom_layer.setSelectedFeatures(ids)
                        box = zoom_layer.boundingBoxOfSelected()
                        inset_item.zoomToExtent(box)
                        zoom_layer.removeSelection()

                    logger.debug('Generate PDF in Progress..')
                    composition.refreshItems()
                    composition.exportAsPDF(output_pdf)
                    try:
                        raster_ch = QgsMapLayerRegistry.instance().mapLayersByName('Raster CH')[0]
                        raster_byth = QgsMapLayerRegistry.instance().mapLayersByName('Raster Byth')[0]
                        all_layer = [zoom_layer.id(), parent_layer.id(), raster_ch.id(), raster_byth.id()]
                    except Exception as e:
                        all_layer = [zoom_layer.id(), parent_layer.id()]
                        logger.error(e)
                    QgsMapLayerRegistry.instance().removeMapLayers(all_layer)
                    if region[0] != 'provinsi':
                        os.remove(qgsfiles)
                    logger.info('Create .pdf file success, .pdf file has been stored on ' + str(output_pdf))
                    print '----'

            def copy_shp(region_polygon, region_level):
                logger.info('Copy shapefile from ' + kabupaten_kota_polygon_file)
                self.iface.mainWindow().statusBar().showMessage('Copy shapefile from ' + kabupaten_kota_polygon_file)
                return_value = None
                rmv_ext = os.path.splitext(region_polygon)[0]
                #shp_name = rmv_ext.split("/")[-1]
                shp_name = os.path.split(rmv_ext)[-1]
                dir_name = os.path.dirname(rmv_ext)
                for file in os.listdir(dir_name):
                    if os.path.splitext(file)[0] == shp_name:
                        ext = os.path.splitext(file)[1]
                        source_file = os.path.join(dir_name, file)
                        target_file = os.path.join(temp_directory, 'zonal_statistic_' + region_level + ext)
                        logger.info('- Source Path: ' + source_file)
                        logger.info('- Target File: ' + target_file)
                        logger.info('- Copy shapefile in progress..')
                        shutil.copy(source_file, target_file)
                        if ext == '.shp':
                            return_value = target_file
                logger.info('Copy Shapefile success, .shp file has been stored on ' + str(return_value))
                return return_value

            def get_category(title, value):
                if title.startswith('c'):
                    if value == 1:
                        val = "0 - 20"
                    elif value == 2:
                        val = "21 - 50"
                    elif value == 3:
                        val = "51 - 100"
                    elif value == 4:
                        val = "101 - 150"
                    elif value == 5:
                        val = "151 - 200"
                    elif value == 6:
                        val = "201 - 300"
                    elif value == 7:
                        val = "301 - 400"
                    elif value == 8:
                        val = "401 - 500"
                    elif value == 9:
                        val = "> 500"
                    else:
                        val = str(value) + '_error'
                else:
                    if value == 1:
                        val = "0 - 30"
                    elif value == 2:
                        val = "31 - 50"
                    elif value == 3:
                        val = "51 - 84"
                    elif value == 4:
                        val = "85 - 115"
                    elif value == 5:
                        val = "116 - 150"
                    elif value == 6:
                        val = "151 - 200"
                    elif value == 7:
                        val = "> 200"
                    else:
                        val = str(value) + '_error'
                return val

            def create_csv(idw_param, raster_clip):
                logger.info('Create CSV Summary File..')
                self.iface.mainWindow().statusBar().showMessage('Create CSV Summary File..')
                kabupaten_csv = os.path.join(csv_directory, 'kabupaten.csv')
                kecamatan_csv = os.path.join(csv_directory, 'kecamatan.csv')
                desa_csv = os.path.join(csv_directory, 'desa.csv')
                output_csv_list = [kabupaten_csv, kecamatan_csv, desa_csv]
                copied_shp_list = [copy_shp(kabupaten_kota_polygon_file, 'kabupaten_kota'), copy_shp(kecamatan_polygon_file, 'kecamatan'), copy_shp(desa_polygon_file, 'desa')]
                region_id_list = [1, 2, 3]
                logger.info('- Generate CSV statistic file..')
                for copied_shp, output_csv, region_id in zip(copied_shp_list, output_csv_list, region_id_list):
                    logger.info('-- Shapefile: ' + str(copied_shp))
                    logger.info('-- Output csv: ' + str(output_csv))
                    logger.info('-- Region [ID]: ' + str(region_id))
                    with open(output_csv, "wb+") as csvfile:
                        csv_writer = csv.writer(csvfile, delimiter=',')
                        if region_id == 1:
                            main_header = ['No', 'Provinsi', 'ID_Kabupaten_Kota', 'Kabupaten_Kota']
                        elif region_id == 2:
                            main_header = ['No', 'Provinsi', 'ID_Kabupaten_Kota', 'Kabupaten_Kota', 'ID_Kecamatan', 'Kecamatan']
                        else:
                            main_header = ['No', 'Provinsi', 'ID_Kabupaten_Kota', 'Kabupaten_Kota', 'ID_Kecamatan', 'Kecamatan', 'ID_Desa', 'Desa']
                        param_header_1 = [idw_param[0] + '_min', idw_param[0] + '_maj', idw_param[0] + '_ket']
                        param_header_2 = [idw_param[1] + '_min', idw_param[1] + '_maj', idw_param[1] + '_ket']
                        param_header_3 = [idw_param[2] + '_min', idw_param[2] + '_maj', idw_param[2] + '_ket']
                        param_header_4 = [idw_param[3] + '_min', idw_param[3] + '_maj', idw_param[3] + '_ket']
                        param_header_5 = [idw_param[4] + '_min', idw_param[4] + '_maj', idw_param[4] + '_ket']
                        param_header_6 = [idw_param[5] + '_min', idw_param[5] + '_maj', idw_param[5] + '_ket']
                        param_header_7 = [idw_param[6] + '_min', idw_param[6] + '_maj', idw_param[6] + '_ket']
                        param_header_8 = [idw_param[7] + '_min', idw_param[7] + '_maj', idw_param[7] + '_ket']
                        header = main_header + param_header_1 + param_header_2 + param_header_3 + param_header_4 + param_header_5 + param_header_6 + param_header_7 + param_header_8
                        csv_writer.writerow(header)
                        for raster, param in zip(raster_clip[0], raster_clip[1]):
                            logger.info('--- Raster: ' + str(raster))
                            logger.info('--- Parameter: ' + str(param))
                            if param[0:3] == 'ACH' or param[0:3] == 'PCH':
                                typ = 'ch'
                            else:
                                typ = 'sh'
                            polygonLayer = QgsVectorLayer(copied_shp, 'zonepolygons', "ogr")
                            logger.debug('--- Zonal statistic in progress..')
                            zoneStat = QgsZonalStatistics(polygonLayer, raster, typ, 1, QgsZonalStatistics.Min|QgsZonalStatistics.Max|QgsZonalStatistics.Minority|QgsZonalStatistics.Majority)
                            zoneStat.calculateStatistics(None)

                        layer = QgsVectorLayer(copied_shp, 'layer', 'ogr')
                        fields = layer.pendingFields()
                        field_names = [field.name() for field in fields]
                        dataSource = driver.Open(copied_shp, 0)
                        layersource = dataSource.GetLayer()
                        n = 1
                        logger.debug('-- Write CSV from ' + str(copied_shp))
                        for feature in layersource:
                            if region_id == 1:
                                main_values = [n, feature.GetField("PROVINSI"), feature.GetField("ID_KAB_CLE"), feature.GetField("KABUPATEN")]
                            elif region_id == 2:
                                main_values = [n, feature.GetField("PROVINSI"), feature.GetField("ID_KAB_CLE"), feature.GetField("KABUPATEN"), feature.GetField("ID_KEC_CLE"), feature.GetField("KECAMATAN")]
                            else:
                                main_values = [n, feature.GetField("PROVINSI"), feature.GetField("ID_KAB_CLE"), feature.GetField("KABUPATEN"), feature.GetField("ID_KEC_CLE"), feature.GetField("KECAMATAN"), feature.GetField("ID_DESA_CL"), feature.GetField("DESA_CLEAN")]
                            param_values = []
                            h = 0
                            for fieldname in field_names:
                                if fieldname.startswith('ch'):
                                    break
                                h += 1
                            m = 0
                            for field1, field2, field3, field4 in zip(field_names[h:], field_names[h+1:], field_names[h+2:], field_names[h+3:]):
                                if m == 0:
                                    v_r = False
                                    v_m = False
                                    v_t = False
                                    v_bn = False
                                    v_n = False
                                    minor_val = get_category(field3, feature.GetField(str(field3)))
                                    major_val = get_category(field4, feature.GetField(str(field4)))
                                    param_values.append(minor_val)
                                    param_values.append(major_val)
                                    min_val = feature.GetField(str(field1))
                                    max_val = feature.GetField(str(field2))
                                    ket_list = []
                                    if min_val and max_val:
                                        for value in range(int(min_val), int(max_val) + 1):
                                            if field1.startswith('c'):
                                                if value == 1 or value == 2 or value == 3 and not v_r:
                                                    ket_list.append('R')
                                                    v_r = True
                                                elif value == 4 or value == 5 or value == 6 and not v_m:
                                                    ket_list.append('M')
                                                    v_m = True
                                                elif value == 7 and not v_t:
                                                    ket_list.append('T')
                                                    v_t = True
                                                else:
                                                    ket_list.append('ST')
                                                    break
                                            else:
                                                if value == 1 or value == 2 or value == 3 and not v_bn:
                                                    ket_list.append('BN')
                                                    v_bn = True
                                                elif value == 4 and not v_n:
                                                    ket_list.append('N')
                                                    v_n = True
                                                else:
                                                    ket_list.append('AN')
                                                    break
                                        param_values.append('/'.join(ket_list))
                                    else:
                                        logger.warn('ERROR VALUE IN ' + str(feature.GetField("KABUPATEN")))
                                        if region_id == 1:
                                            logger.warn('ERROR VALUE IN ' + str(feature.GetField("ID_KAB_CLE")))
                                        elif region_id == 2:
                                            logger.warn('ERROR VALUE IN ' + str(feature.GetField("ID_KEC_CLE")))
                                        else:
                                            logger.warn('ERROR VALUE IN ' + str(feature.GetField("ID_DESA_CL")))
                                        logger.info(str([field1, field2, field3, field4]))
                                        param_values.append('error')
                                m += 1
                                if m == 4:
                                    m = 0
                            csv_writer.writerow(main_values + param_values)
                            n += 1
                        dataSource.Destroy()
                    logger.info('-- Generate csv static file success, file has been stored on' + str(output_csv))

                # Create Province CSV Summary
                logger.info('- Generate Province CSV Summary..')
                for raster, param in zip(raster_clip[0], raster_clip[1]):
                    logger.info('-- Raster: ' + str(raster))
                    logger.info('-- Parameter: ' + str(param))
                    summary_csv = os.path.join(csv_directory, 'jawa_timur_sum_'+ param.lower() +'.csv')
                    with open(summary_csv, "wb+") as csvfile:
                        logger.debug('-- Counting in progress..')
                        read_raster = gdal.Open(raster, GA_ReadOnly)
                        raster_value = np.array(read_raster.GetRasterBand(1).ReadAsArray(), dtype ="int")
                        unique, counts = np.unique(raster_value, return_counts=True)
                        unique_counts = dict(zip(unique, counts))
                        unique_counts.pop(255, None)
                        all_cell = sum(unique_counts.values())
                        csv_writer = csv.writer(csvfile, delimiter=',')
                        if param[0:3] == 'ACH' or param[0:3] == 'PCH':
                            kat = 'ch'
                            for n in range(1,10):
                                if n not in unique_counts:
                                    unique_counts[n] = 0
                        else:
                            kat = 'sh'
                            for n in range(1,8):
                                if n not in unique_counts:
                                    unique_counts[n] = 0
                        csv_writer.writerow(['kategori_'+ kat, 'persentase (%)', 'jumlah_kabupaten'])
                        for key, value in zip(unique_counts.keys(), unique_counts.values()):
                            percentage = math.ceil((value/float(all_cell)) * 100)
                            kategori = get_category(kat, key)
                            with open(kabupaten_csv, 'rb') as csvfile:
                                spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
                                cumulative_kat = 0
                                for i in spamreader:
                                    if i[param + '_maj'] == kategori:
                                        cumulative_kat += 1
                            csv_writer.writerow([kategori, percentage, cumulative_kat])
                        logger.info('-- count each raster value in area: ' + str(unique_counts))
                        logger.info('-- sum all raster value in area: ' + str(all_cell))
                    logger.info(' -- Generate csv province summary success, file has been stored on' + str(summary_csv))

                # Create Kabupaten_Kota CSV Summary
                logger.info('- Generate Kabupaten\Kota CSV Summary..')
                layer = QgsVectorLayer(kabupaten_kota_polygon_file, 'kabupaten', 'ogr')
                QgsMapLayerRegistry.instance().addMapLayer(layer)
                kab_list = []
                for feature in layer.getFeatures():
                    kab_list.append([feature['ID_KAB_CLE'], feature['KABUPATEN']])
                for kab in kab_list:
                    logger.info('-- Kabupaten: ' + str(kab))
                    exp = "\"ID_KAB_CLE\" = " + str(kab[0])
                    it = layer.getFeatures(QgsFeatureRequest(QgsExpression(exp)))
                    ids = [i.id() for i in it]
                    layer.setSelectedFeatures(ids)
                    kab_poly = os.path.join(temp_directory, str(int(kab[0])) + '_ply.shp')
                    try:
                        os.remove(kab_poly)
                    except OSError:
                        pass
                    QgsVectorFileWriter.writeAsVectorFormat(layer, kab_poly, "utf-8", layer.crs(), "ESRI Shapefile", 1)
                    layer_kab = QgsVectorLayer(kab_poly, "lyr1", "ogr")
                    QgsMapLayerRegistry.instance().addMapLayer(layer_kab)
                    for raster, param in zip(raster_clip[0], raster_clip[1]):
                        logger.info('-- Raster: ' + str(raster))
                        logger.info('-- Parameter: ' + str(param))
                        cliped = os.path.join(temp_directory, str(int(kab[0])) + '_' + str(param) + '_clp.tif')
                        try:
                            os.remove(cliped)
                        except OSError:
                            pass
                        logger.debug('-- Clipping raster in progress..')
                        processing.runalg("gdalogr:cliprasterbymasklayer", raster, layer_kab, -1, False, False, False, 6, 0, 75, 1, 1, False, 0, False, "", cliped)
                        summary_csv = os.path.join(csv_directory, str(kab[1]).lower() + '_sum_'+ param.lower() + '_' + str(int(kab[0])) + '.csv')
                        with open(summary_csv, "wb+") as csvfile:
                            read_raster = gdal.Open(cliped, GA_ReadOnly)
                            raster_value = np.array(read_raster.GetRasterBand(1).ReadAsArray(), dtype ="int")
                            unique, counts = np.unique(raster_value, return_counts=True)
                            unique_counts = dict(zip(unique, counts))
                            unique_counts.pop(-1, None)
                            all_cell = sum(unique_counts.values())
                            csv_writer = csv.writer(csvfile, delimiter=',')
                            if param[0:3] == 'ACH' or param[0:3] == 'PCH':
                                kat = 'ch'
                                for n in range(1,10):
                                    if n not in unique_counts:
                                        unique_counts[n] = 0
                            else:
                                kat = 'sh'
                                for n in range(1,8):
                                    if n not in unique_counts:
                                        unique_counts[n] = 0
                            csv_writer.writerow(['kategori_'+ kat, 'persentase (%)', 'jumlah_kecamatan'])
                            for key, value in zip(unique_counts.keys(), unique_counts.values()):
                                percentage = math.ceil((value/float(all_cell)) * 100)
                                kategori = get_category(kat, key)
                                with open(kecamatan_csv, 'rb') as csvfile:
                                    spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
                                    cumulative_kat = 0
                                    for i in spamreader:
                                        if i[param + '_maj'] == kategori and i['Kabupaten_Kota'] == str(kab[1]).upper() and i['ID_Kabupaten_Kota'] == str(kab[0]):
                                            cumulative_kat += 1
                                csv_writer.writerow([kategori, percentage, cumulative_kat])
                            logger.info('-- count each raster value in area: ' + str(unique_counts))
                            logger.info('-- sum all raster value in area: ' + str(all_cell))
                            del read_raster
                        os.remove(cliped)
                    QgsMapLayerRegistry.instance().removeMapLayer(layer_kab.id())
                    QgsVectorFileWriter.deleteShapeFile(kab_poly)
                    logger.info(' -- Generate csv kabupaten\kota summary success, file has been stored on' + str(summary_csv))

            # Main Flow
            if not warning:
                self.iface.messageBar().pushMessage("Please wait.. ", level=QgsMessageBar.INFO)
                try:
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

                    log_filename = os.path.join(file_directory, 'otoklim_' + '{:%Y%m%d_%H%M%S}'.format(datetime.datetime.now()) + '.log')
                    try:
                        os.remove(log_filename)
                    except OSError:
                        pass
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
                    slcs_date = select_date_now(yrs)
                    slcs_adm = select_adm_region()
                    csv_input = combinecsv(csv_delimiter)
                    point_stn = csvtoshp(csv_delimiter, csv_input)
                    raster_idw = idw_interpolate(point_stn, slcs_date[0])
                    idw_param = raster_idw[1]
                    for slc_adm in slcs_adm:
                        logger.info('Region In Progress : ' + str(slc_adm))
                        raster_clip = clip_raster(raster_idw, slc_adm)
                        qgs_files = create_qgs(raster_clip, point_stn, slc_adm)
                        create_pdf_map(qgs_files, slc_adm, slcs_date)
                        if not after_prov:
                            raster_cls = raster_classify(raster_clip)
                            create_csv(idw_param, raster_cls)
                        if after_prov:
                            for raster in raster_clip[0]:
                                os.remove(raster)
                        after_prov = True

                    # Clear unuse file
                    for raster in raster_idw[0]:
                        os.remove(raster)
                    for file in os.listdir(temp_directory):
                        if file.split('.')[-1] != 'qgs':
                            try:
                                os.remove(os.path.join(temp_directory, file))
                            except:
                                pass

                    now = datetime.datetime.now()
                    logger.info('Running stop at ' + '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()))
                    logger.info("--- %s seconds ---" % (time.time() - start_time))
                except Exception as e:
                    logger.error(e)
                    self.iface.messageBar().pushMessage("ERROR : " + str(e), level=QgsMessageBar.CRITICAL, duration=10)
            else:
                if warning == 'thisyear':
                    self.iface.messageBar().pushMessage("WARNING : Input Year row must be numeric value", level=QgsMessageBar.WARNING, duration=10)
                elif warning == 'fileinput':
                    self.iface.messageBar().pushMessage("WARNING : File Input row is not allowed to be empty", level=QgsMessageBar.WARNING, duration=10)
