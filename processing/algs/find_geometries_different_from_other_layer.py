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
        raise QgsProcessingException('Not found the table parameter in layer')
        
    return table
    

def find_field(layer, field: str):
    layer_fields = layer.fields()
    for layer_field in layer_fields:
        if layer_field.name() == field:
            break
    else:
        raise QgsProcessingException('Not found the field parameter in layer')
        
    return layer_field

class FindGeometriesDifferentFromOtherLayer(QgsProcessingAlgorithm):
    # Constants used to refer to parameters 
    INPUT = 'INPUT'
    LAYER2 = 'LAYER2'
    FILTER = 'FILTER'
    FILTER_PRIMARY_KEY = 'FILTER_PRIMARY_KEY'
    OUTPUT = 'OUTPUT'
    
    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("PostGIS Queries: FindGeometriesDifferentFromOtherLayer", string)

    def createInstance(self):
        return FindGeometriesDifferentFromOtherLayer()

    def name(self):
        return 'findgeometriesdifferentfromotherlayer'

    def displayName(self):
        return self.tr('Find Geometries Different From Other Layer')

    def group(self):
        return self.tr('Topology Scripts')

    def groupId(self):
        return 'topologyscripts'

    def shortHelpString(self):
        return self.tr("""Find geometries of input layer that are different from geometries in the second layer.   
        
                          Input layer (connection): input layer for algorithm, which originates from PostGIS database.
                          Second layer: layer that is compared with the input layer. 
                          Input Primary Key: primary key field for input layer.
                          Filter layer (selected features): polygon layer that filters the input and second layer features that intersect the features selected in the filter layer.
                          Filter Primary Key: primary key field for filter layer.                          
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
                
        # Second Layer
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.LAYER2,
                self.tr('Second layer'),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )

        # Filter
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                name=self.FILTER,
                description=self.tr('Filter layer (selected features)'),
                types=[QgsProcessing.TypeVectorPolygon],
                optional=True
            )
        ) 

        # Filter Primary Key
        self.addParameter(QgsProcessingParameterField(name=self.FILTER_PRIMARY_KEY,
                                                      description=self.tr('Filter Primary Key'),
                                                      defaultValue='id',
                                                      parentLayerParameterName=self.FILTER,
                                                      optional=True))
                                                      
        # Output
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        # Get Parameters as Layers
        input = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        layer2 = self.parameterAsVectorLayer(parameters, self.LAYER2, context)
        filter = self.parameterAsVectorLayer(parameters, self.FILTER, context)
        output = self.parameterAsOutputLayer(parameters, self.OUTPUT, context) 
 
        # Selected features
        if parameters['FILTER']:
            selection = filter.selectedFeatures()
            if not selection:
                raise QgsProcessingException('No features selected in Filter Layer')
            
            # Depending on the type of the Filter Primary Key, build the string with selected values
            if not parameters['FILTER_PRIMARY_KEY']:
                raise QgsProcessingException('No field selected for primary key in Filter Layer')
                                
            filter_pk_field = find_field(filter, parameters['FILTER_PRIMARY_KEY'])
            if filter_pk_field.isNumeric():
                selection_field_list = [str(f[parameters['FILTER_PRIMARY_KEY']]) for f in selection]
            else:
                selection_field_list = [f"'{f[ parameters['FILTER_PRIMARY_KEY'] ]}'" for f in selection]
                
            selection_field_string = ', '.join(selection_field_list) 
            
        # Schema.Table for Input and Filter
        feedback.pushInfo('Finding table of input layer ...')
        input_table = find_table(input) 
        feedback.pushInfo('Finding table of second layer ...')
        layer2_table = find_table(layer2) 
        if parameters['FILTER']:        
            feedback.pushInfo('Finding table of filter layer ...')
            filter_table = find_table(filter)  

        # Build SQL  
        if not parameters['FILTER']:
            sql = (f'SELECT T1.geom FROM {input_table} AS T1 LEFT JOIN {layer2_table} AS T2 '  
                   f'ON T1.geom && T2.geom AND ST_Equals(T1.geom, T2.geom) WHERE T2.geom IS NULL')   
        else:
            sql = (f'SELECT T1.geom FROM (SELECT layer.geom FROM {input_table} AS layer, {filter_table} AS filter '
                   f'WHERE ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) AS T1 '
                   f'LEFT JOIN (SELECT layer2.geom FROM {layer2_table} AS layer2, {filter_table} AS filter '
                   f'WHERE ST_Intersects(layer2.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) AS T2 '
                   f'ON T1.geom && T2.geom AND ST_Equals(T1.geom, T2.geom) WHERE T2.geom IS NULL') 

        feedback.pushInfo(sql)

        found = processing.run("gdal:executesql",
                                   {'INPUT': parameters['INPUT'],
                                   'SQL':sql,
                                   'OUTPUT': output},
                                   context=context, feedback=feedback, is_child_algorithm=True)


        return {self.OUTPUT: found['OUTPUT']}
