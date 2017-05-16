import csv
import os
import json
import time
import processing
import numpy as np

from osgeo import gdal, ogr, osr
from gdalconst import GA_ReadOnly
from qgis.gui import QgsMapCanvas, QgsMapCanvasLayer, QgsLayerTreeMapCanvasBridge
from qgis.core import (
            QgsVectorLayer,
            QgsRasterLayer,
            QgsMapLayerRegistry,
            QgsRasterShader,
            QgsColorRampShader,
            QgsSingleBandPseudoColorRenderer,
            QgsProject,
            QgsComposition
        )
from PyQt4 import QtGui
from PyQt4.QtGui import QFileDialog, QColor
from PyQt4.QtCore import QFileInfo
from PyQt4.QtXml import QDomDocument


file_input = QFileDialog.getOpenFileName(QFileDialog(), 'Select Stasiun data in csv')
file_directory = str(os.path.dirname(os.path.realpath(file_input)))

# Static File
provinsi_polygon_file = "E:/Music/adm_bndy/jatim_provinsi.shp"
kabupaten_kota_polygon_file = "E:/Music/adm_bndy/jatim_kabupaten_kota.shp"
kecamatan_polygon_file = "E:/Music/adm_bndy/jatim_kecamatan.shp"
desa_polygon_file = "E:/Music/adm_bndy/jatim_desa.shp"
map_template = "E:/Music/adm_bndy/map_template.qpt"


def csvtoshp():
    print '-- Start Convert Stasiun Data From CSV to Shapefile (Point) --'
    csv_file = file_input
    driver = ogr.GetDriverByName("ESRI Shapefile")
    filename_shp = os.path.join(file_directory, 'stasiun.shp')
    filename_prj = os.path.join(file_directory, 'stasiun.prj')

    try:
        if os.path.exists(filename_shp):
            driver.DeleteDataSource(filename_shp)
        if os.path.exists(filename_prj):
            driver.DeleteDataSource(filename_prj)
    except Exception as e:
        print e
    data_source = driver.CreateDataSource(filename_shp)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.MorphToESRI()
    prj_file = open(filename_prj, 'w')
    prj_file.write(srs.ExportToWkt())
    prj_file.close()

    layer = data_source.CreateLayer(filename_shp, srs, ogr.wkbPoint)
    layer.CreateField(ogr.FieldDefn("nama_pos", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("no_pos", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("z_nz", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("provinsi", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("kabupaten", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("kecamatan", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("kontak", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("elevasi", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("ch_value", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("ch_total", ogr.OFTReal))

    with open(csv_file, 'rb') as csvfile:
        spamreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
        for row in spamreader:
            point = ogr.Geometry(ogr.wkbPoint)
            feature = ogr.Feature(layer.GetLayerDefn())
            point.AddPoint(float(row['latitude']), float(row['longitude']))
            feature.SetField("nama_pos", row['nama_pos'])
            feature.SetField("no_pos", row['no_pos'])
            feature.SetField("z_nz", row['z_nz'])
            feature.SetField("provinsi", row['provinsi'])
            feature.SetField("kabupaten", row['kabupaten'])
            feature.SetField("kecamatan", row['kecamatan'])
            feature.SetField("kontak", row['kontak'])
            try:
                feature.SetField("elevasi", float(row['elevasi']))
            except:
                feature.SetField("elevasi", 0)
            ch_value = list()
            for i in range(1, 32):
                try:
                    ch_value.append(float(row[str(i)]))
                except:
                    pass
            feature.SetField("ch_value", json.dumps(ch_value))
            feature.SetField("ch_total", sum(ch_value))
            feature.SetGeometry(point)
            layer.CreateFeature(feature)

    print 'Converting Finished'
    print 'Shapefile data has been stored on ' + filename_shp
    return filename_shp


def idw_interpolate(point):
    print '-- Start Interpolate Stasiun Point By Using IDW Method --'
    raster_interpolated = os.path.join(file_directory, 'raster_idw.tif')
    try:
        os.remove(raster_interpolated)
    except OSError:
        pass

    layer = QgsVectorLayer(point, 'layer', 'ogr')
    processing.runalg('grass7:v.surf.idw', layer, 50.0, 2.0, 'ch_total', False, "%f,%f,%f,%f" % (110.5, 117, -9, -4.5), 0.001, -1.0, 0.0001, raster_interpolated)
    print 'Interpolate Finished'
    print 'Raster Interpolated data has been stored on ' + raster_interpolated
    return raster_interpolated


def raster_classify(raster):
    print '-- Start Classify Raster --'
    raster_classified = os.path.join(file_directory, 'raster_class_nocrop.tif')
    try:
        os.remove(raster_classified)
    except OSError:
        pass

    read_raster = gdal.Open(raster, GA_ReadOnly)
    geotransform = read_raster.GetGeoTransform()
    cell_size = geotransform[1]
    origin_x = geotransform[0]
    origin_y = geotransform[3]
    row = read_raster.RasterYSize
    col = read_raster.RasterXSize

    outras_array = np.zeros(shape=(row, col), dtype=int)
    Raster_Value = np.array(read_raster.GetRasterBand(1).ReadAsArray(), dtype="int")
    for r in range(row):
        for c in range(col):
            if Raster_Value[r][c] >= 0 and Raster_Value[r][c] <= 20:
                outras_array[r][c] = 1
            elif Raster_Value[r][c] >= 21 and Raster_Value[r][c] <= 50:
                outras_array[r][c] = 2
            elif Raster_Value[r][c] >= 51 and Raster_Value[r][c] <= 100:
                outras_array[r][c] = 3
            elif Raster_Value[r][c] >= 101 and Raster_Value[r][c] <= 150:
                outras_array[r][c] = 4
            elif Raster_Value[r][c] >= 151 and Raster_Value[r][c] <= 200:
                outras_array[r][c] = 5
            elif Raster_Value[r][c] >= 201 and Raster_Value[r][c] <= 300:
                outras_array[r][c] = 6
            elif Raster_Value[r][c] >= 301 and Raster_Value[r][c] <= 400:
                outras_array[r][c] = 7
            elif Raster_Value[r][c] >= 401 and Raster_Value[r][c] <= 500:
                outras_array[r][c] = 8
            elif Raster_Value[r][c] > 500:
                outras_array[r][c] = 9

    driver = gdal.GetDriverByName('GTiff')
    outRaster = driver.Create(raster_classified, col, row, 1, gdal.GDT_Byte)
    outRaster.SetGeoTransform((origin_x, cell_size, 0, origin_y - (cell_size * row), 0, cell_size))
    outband = outRaster.GetRasterBand(1)
    outband.WriteArray(outras_array[::-1])
    outRasterSRS = osr.SpatialReference()
    outRasterSRS.ImportFromEPSG(4326)
    outRaster.SetProjection(outRasterSRS.ExportToWkt())
    outband.FlushCache()
    print 'Classify Finished'
    print 'Raster Classified data has been stored on ' + raster_classified
    return raster_classified


def clip_raster(raster):
    print '-- Start Clipping Raster --'
    raster_provinsi = os.path.join(file_directory, 'raster_provinsi.tif')
    try:
        os.remove(raster_provinsi)
    except OSError:
        pass

    processing.runalg("gdalogr:cliprasterbymasklayer", raster, provinsi_polygon_file, "none", False, False, False, 0, 0, 1, 1, 1, False, 0, False, "", raster_provinsi)
    print 'Clipping Raster Finished'
    print 'Raster Clipped data has been stored on ' + raster_provinsi
    return raster_provinsi


def create_qgs(raster, point):
    print '-- Start Create .qgs File --'
    qgs_filename = os.path.join(file_directory, 'project.qgs')
    try:
        os.remove(qgs_filename)
    except OSError:
        pass

    layer_raster_ch = QgsRasterLayer(raster, 'Raster CH')
    layer_point_stasiun = QgsVectorLayer(point, 'Station Point', 'ogr')

    # Administration Boundary
    layer_kabupaten = QgsVectorLayer(kabupaten_kota_polygon_file, 'Batas Kabupaten', 'ogr')

    # Raster CH Styling
    s = QgsRasterShader()
    c = QgsColorRampShader()
    c.setColorRampType(QgsColorRampShader.INTERPOLATED)
    i = []
    color = ['#400d0a', '#8b1428', '#b04a13', '#cd801c', '#cdc636', '#ffd948', '#2ebd12', '#53de73', '#2c773c']
    label = ['0 - 20', '21 - 50', '51 - 100', '101 - 150', '151 - 200', '201 - 300', '301 - 400', '401 - 500', '> 500']
    i.append(QgsColorRampShader.ColorRampItem(0, QtGui.QColor.fromRgb(0,0,0,0), 'none'))
    for n in range(1, 10):
        i.append(QgsColorRampShader.ColorRampItem(n, QtGui.QColor(color[n-1]), label[n-1]))
    c.setColorRampItemList(i)
    s.setRasterShaderFunction(c)
    ps = QgsSingleBandPseudoColorRenderer(layer_raster_ch.dataProvider(), 1, s)
    layer_raster_ch.setRenderer(ps)

    # Batas Kabupaten Styling
    symbols = layer_kabupaten.rendererV2().symbols()
    sym = symbols[0]
    sym.setColor(QColor.fromRgb(0, 0, 0, 0))
    layer_kabupaten.triggerRepaint()

    # Add Layer To QGIS Canvas
    canvas = QgsMapCanvas()
    layer1 = QgsMapLayerRegistry.instance().addMapLayer(layer_raster_ch)
    layer2 = QgsMapLayerRegistry.instance().addMapLayer(layer_point_stasiun)
    layer3 = QgsMapLayerRegistry.instance().addMapLayer(layer_kabupaten)
    canvas.setExtent(layer3.extent())
    canvas.setLayerSet([QgsMapCanvasLayer(layer3)])
    canvas.zoomToFullExtent()

    # Save .qgs file
    f = QFileInfo(qgs_filename)
    p = QgsProject.instance()
    p.write(f)
    print 'Create .qgs file finished'
    print '.qgs file has been stored on ' + qgs_filename
    return qgs_filename


def create_pdf_map(qgsfile):
    print '-- Start Create Map in PDF --'
    output_pdf = os.path.join(file_directory, 'map.pdf')
    try:
        os.remove(output_pdf)
    except OSError:
        pass

    canvas = QgsMapCanvas()
    QgsProject.instance().read(QFileInfo(qgsfile))
    bridge = QgsLayerTreeMapCanvasBridge(QgsProject.instance().layerTreeRoot(), canvas)
    bridge.setCanvasLayers()

    template_file = file(map_template)
    template_content = template_file.read()
    template_file.close()
    document = QDomDocument()
    document.setContent(template_content)
    composition = QgsComposition(canvas.mapSettings())
    substitution_map = {'test': 'judul peta'}
    composition.loadFromTemplate(document, substitution_map)
    map_item = composition.getComposerItemById('map')
    map_item.setMapCanvas(canvas)
    map_item.zoomToExtent(canvas.extent())

    composition.refreshItems()
    composition.exportAsPDF(output_pdf)
    #QgsProject.instance().clear()
    print 'Create .pdf file finished'
    print '.pdf file has been stored on ' + output_pdf


# if __name__ == '__main__':
start_time = time.time()
point_stn = csvtoshp()
raster_idw = idw_interpolate(point_stn)
raster_cls = raster_classify(raster_idw)
raster_clip = clip_raster(raster_cls)
qgs_file = create_qgs(raster_clip, point_stn)
create_pdf_map(qgs_file)
print("--- %s seconds ---" % (time.time() - start_time))
