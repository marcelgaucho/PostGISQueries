# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterString,
                       QgsProcessingParameterVectorDestination)
import processing


class ReturnGeometryWithoutHoles(QgsProcessingAlgorithm):
    # Constants used to refer to parameters

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    TABLE = 'TABLE'
    PRIMARY_KEY = 'PRIMARY_KEY'


    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("PostGIS Queries: ReturnGeometryWithoutHoles", string)

    def createInstance(self):
        return ReturnGeometryWithoutHoles()

    def name(self):
        return 'returngeometrywithoutholes'

    def displayName(self):
        return self.tr('Return Geometry Without Holes')

    def group(self):
        return self.tr('Topology Scripts')

    def groupId(self):
        return 'topologyscripts'

    def shortHelpString(self):
        return self.tr("Return geometry without holes for a polygon layer.")

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input layer (connection)'),
                [QgsProcessing.TypeVectorPolygon]
            )
        )

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )

        self.addParameter(QgsProcessingParameterString(self.TABLE,
                                                       self.tr('Table'),
                                                       defaultValue=''))

        # Input Primary Key
        self.addParameter(QgsProcessingParameterString(self.PRIMARY_KEY,
                                                       self.tr('Primary Key'),
                                                       defaultValue='id'))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        output = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        # DO SOMETHING       
        sql = ('SELECT id, ST_BuildArea(ST_Collect(geom)) AS geom FROM ( '  
                 f'SELECT {parameters[self.PRIMARY_KEY]} AS id, ST_ExteriorRing((ST_Dump(geom)).geom) AS geom FROM ' 
                 f'{parameters[self.TABLE]}) AS T GROUP BY id') 
                
        feedback.pushInfo(sql)

        found = processing.run("gdal:executesql",
                                   {'INPUT': parameters['INPUT'],
                                   'SQL':sql,
                                   'OUTPUT': output},
                                   context=context, feedback=feedback, is_child_algorithm=True)


        return {self.OUTPUT: found['OUTPUT']}
