#-*- coding: utf-8 -*-
"""
/***************************************************************************
                           PostGIS Queries
                             --------------------
        begin                : 2021-19-02
        copyright            : (C) 2021 by Marcel Rotunno (IBGE)
        email                : marcelgaucho@yahoo.com.br
 ***************************************************************************/
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License v3.0 as          *
 *   published by the Free Software Foundation.                            *
 *                                                                         *
 ***************************************************************************/
"""
import os

from qgis.core import QgsApplication

from .processing.load_provider import LoadAlgorithmProvider

from PyQt5.QtCore import QSettings, qVersion, QFileInfo, QTranslator, QCoreApplication

class PostGISQueries:

    def __init__(self, iface):
        self.iface = iface
        self.provider = None

        # Plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        
    def initGui(self):
        # Add provider and models to QGIS
        self.provider = LoadAlgorithmProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)
        
    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)


