# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Otoklim
                                 A QGIS plugin
 Lorem ipsum dolor sit amet
                             -------------------
        begin                : 2017-07-03
        copyright            : (C) 2017 by Geo Enviro Omega
        email                : faizalprbw@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load Otoklim class from file Otoklim.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .otoklim import Otoklim
    return Otoklim(iface)
