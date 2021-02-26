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


class PolygonsArentFilledByPolygons(QgsProcessingAlgorithm):
    # Constants used to refer to parameters

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    TABLE = 'TABLE'
    TABLE2 = 'TABLE2'
    PRIMARY_KEY = 'PRIMARY_KEY'


    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return PolygonsArentFilledByPolygons()

    def name(self):
        return 'PolygonsArentFilledByPolygons'

    def displayName(self):
        return self.tr('Find polygons that aren\'t filled by polygons from other layer')

    def group(self):
        return self.tr('Topology Scripts')

    def groupId(self):
        return 'topologyscripts'

    def shortHelpString(self):
        return self.tr("Find parts of polygons that aren't filled by polygons from other layer.")

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
                                                       self.tr('Outer Polygon table'),
                                                       defaultValue=''))

        self.addParameter(QgsProcessingParameterString(self.TABLE2,
                                                       self.tr('Inner Polygon table'),
                                                       defaultValue=''))                                                       

        # Input Primary Key
        self.addParameter(QgsProcessingParameterString(self.PRIMARY_KEY,
                                                       self.tr('Outer Polygon Table Primary Key'),
                                                       defaultValue='id'))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        output = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        # Parameters
        table = parameters[self.TABLE]
        table2 = parameters[self.TABLE2]
        
        pk = parameters[self.PRIMARY_KEY]
        
        # DO SOMETHING       
        sql = ('SELECT id, geom FROM ( '
                    'SELECT id, (ST_Dump(geom)).geom FROM ( '
                        'SELECT id, CASE WHEN geom2 IS NULL THEN geom '
                        'ELSE ST_CollectionExtract(ST_Difference(geom, geom2), 3) END AS geom FROM ( ' 
                            f'SELECT T1.{pk} AS id, T1.geom AS geom, ST_Union(T2.geom) AS geom2 FROM '
                                f'{table} AS T1 LEFT JOIN {table2} AS T2 '
                                 'ON ST_Intersects(T1.geom, T2.geom) AND NOT ST_Touches(T1.geom, T2.geom) '
                                f'GROUP BY T1.{pk} '
                            ') AS sub1 '
                        ') AS sub2 '
                    ') AS sub3 '
               ' WHERE ST_Area(geom) > 0.0000001')
 
               
                
        feedback.pushInfo(sql)

        found = processing.run("gdal:executesql",
                                   {'INPUT': parameters['INPUT'],
                                   'SQL':sql,
                                   'OUTPUT': output},
                                   context=context, feedback=feedback, is_child_algorithm=True)


        return {self.OUTPUT: found['OUTPUT']}
