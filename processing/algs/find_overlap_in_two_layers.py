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


class FindOverlapInTwoLayers(QgsProcessingAlgorithm):
    # Constants used to refer to parameters 

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    TABLE = 'TABLE'
    TABLE2 = 'TABLE2'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("PostGIS Queries: FindOverlapInTwoLayers", string)

    def createInstance(self):
        return FindOverlapInTwoLayers()

    def name(self):
        return 'findoverlapintwolayers'

    def displayName(self):
        return self.tr('Find Overlap In Two Layers')

    def group(self):
        return self.tr('Topology Scripts')

    def groupId(self):
        return 'topologyscripts'

    def shortHelpString(self):
        return self.tr("Find overlap of polygons between two layers.")

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have polygon geometry
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

        # Input tables
        self.addParameter(QgsProcessingParameterString(self.TABLE,
                                                       self.tr('Table'),
                                                       defaultValue=''))

        self.addParameter(QgsProcessingParameterString(self.TABLE2,
                                                       self.tr('Table2'),
                                                       defaultValue=''))                                                       



    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        output = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        # DO SOMETHING       
        sql = ('SELECT geom FROM (SELECT (ST_Dump(ST_Intersection(T1.geom, T2.geom))).geom FROM '  
                    f'{parameters[self.TABLE]} AS T1 JOIN {parameters[self.TABLE2]} AS T2 '
                     'ON (ST_Intersects(T1.geom, T2.geom) AND NOT ST_Touches(T1.geom, T2.geom))) AS sobreposicao '
               'WHERE ST_Dimension(geom) = 2 AND ST_Area(geom) > 0.0000001') 
               
                
        feedback.pushInfo(sql)

        found = processing.run("gdal:executesql",
                                   {'INPUT': parameters['INPUT'],
                                   'SQL':sql,
                                   'OUTPUT': output},
                                   context=context, feedback=feedback, is_child_algorithm=True)


        return {self.OUTPUT: found['OUTPUT']}
