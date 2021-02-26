#-*- coding: utf-8 -*-
"""
/***************************************************************************
                           PostGIS Queries
                             --------------------
        begin                : 2021-19-02
        git sha              : :%H$
        copyright            : (C) 2021 by Marcel Rotunno (IBGE)
        email                : marcel.rotunno@gmail.com
 ***************************************************************************/
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License v3.0 as          *
 *   published by the Free Software Foundation.                            *
 *                                                                         *
 ***************************************************************************/
"""

from qgis.core import QgsApplication

from .processing.load_provider import LoadAlgorithmProvider

class PostGISQueries:

    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initGui(self):
        # Add provider and models to QGIS
        self.provider = LoadAlgorithmProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)
        
    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)


