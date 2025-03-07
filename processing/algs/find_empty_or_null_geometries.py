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
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterField)
import processing


def find_table(layer):
    layer_source = layer.source()
    layer_source_split = layer_source.split()
    for source_param in layer_source_split:
        if source_param.startswith('table'):
            table = source_param.split('=', maxsplit=1)[1]
            break
    else:
        raise QgsProcessingException('Not found the table parameter in filter layer')
        
    return table
    
class FindEmptyOrNullGeometries(QgsProcessingAlgorithm):
    # Constants used to refer to parameters
    INPUT = 'INPUT'
    LAYER_PRIMARY_KEY = 'LAYER_PRIMARY_KEY'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("PostGIS Queries: FindEmptyOrNullGeometries", string)

    def createInstance(self):
        return FindEmptyOrNullGeometries()

    def name(self):
        return 'findemptyornullgeometries'

    def displayName(self):
        return self.tr('Find Empty or NULL Geometries')

    def group(self):
        return self.tr('Topology Scripts')

    def groupId(self):
        return 'topologyscripts'

    def shortHelpString(self):
        return self.tr("""Find layer geometries that are either Empty or NULL.        
        
                          Input layer (connection): input layer for algorithm, which originates from PostGIS database.
                          Input Primary Key: primary key field for input layer.
        """)

    def initAlgorithm(self, config=None):
        # Input and Connection
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr('Input layer (connection)'),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )

        # Input Primary Key
        self.addParameter(QgsProcessingParameterField(name=self.LAYER_PRIMARY_KEY,
                                                      description=self.tr('Input Primary Key'),
                                                      defaultValue='id',
                                                      parentLayerParameterName=self.INPUT))
                                                      
        # Output Layer
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        # Get Parameters as Layers
        input = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        output = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        
        # Schema.Table for Input
        input_table = find_table(input)

        # Build SQL
        sql =(f'SELECT {parameters[self.LAYER_PRIMARY_KEY]}, geom FROM {input_table} '  
                    'WHERE ST_IsEmpty(geom) OR geom IS NULL ') 
                       
        feedback.pushInfo(sql)

        # Run query
        found = processing.run("gdal:executesql",
                                   {'INPUT': parameters['INPUT'],
                                   'SQL':sql,
                                   'OUTPUT': output},
                                   context=context, feedback=feedback, is_child_algorithm=True)


        return {self.OUTPUT: found['OUTPUT']}
