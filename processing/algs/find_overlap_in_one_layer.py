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


class FindOverlapInOneLayer(QgsProcessingAlgorithm):
    # Constants used to refer to parameters
    
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    TABLE = 'TABLE'
    PRIMARY_KEY = 'PRIMARY_KEY'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return FindOverlapInOneLayer()

    def name(self):
        return 'findoverlapinonelayer'

    def displayName(self):
        return self.tr('Find Overlap In One Layer')

    def group(self):
        return self.tr('Topology Scripts')

    def groupId(self):
        return 'topologyscripts'

    def shortHelpString(self):
        return self.tr("Find overlap of distinct polygons in one layer.")

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

        # Input table
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
        sql = ('SELECT geom FROM (SELECT (ST_Dump(ST_Intersection(T1.geom, T2.geom))).geom FROM '  
              f'{parameters[self.TABLE]} AS T1 JOIN {parameters[self.TABLE]} AS T2 '
               'ON (ST_Intersects(T1.geom, T2.geom) AND NOT ST_Touches(T1.geom, T2.geom)) '
              f'AND T1.{parameters[self.PRIMARY_KEY]} > T2.{parameters[self.PRIMARY_KEY]}) AS sobreposicao '
               'WHERE ST_Dimension(geom) = 2 AND ST_Area(geom) > 0.0000001') 
               
                
        feedback.pushInfo(sql)

        find_pseudo = processing.run("gdal:executesql",
                                   {'INPUT': parameters['INPUT'],
                                   'SQL':sql,
                                   'OUTPUT': output},
                                   context=context, feedback=feedback, is_child_algorithm=True)


        return {self.OUTPUT: find_pseudo['OUTPUT']}
