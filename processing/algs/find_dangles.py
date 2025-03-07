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
                       QgsProcessingParameterNumber,
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
    

class FindDangles(QgsProcessingAlgorithm):
    # Constants used to refer to parameters

    INPUT = 'INPUT'
    LAYER_PRIMARY_KEY = 'LAYER_PRIMARY_KEY'
    TOLERANCE = 'TOLERANCE'
    FILTER = 'FILTER'
    FILTER_PRIMARY_KEY = 'FILTER_PRIMARY_KEY'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("PostGIS Queries: FindDangles", string)

    def createInstance(self):
        return FindDangles()

    def name(self):
        return 'finddanglesquery'

    def displayName(self):
        return self.tr('Find Dangles')

    def group(self):
        return self.tr('Topology Scripts')

    def groupId(self):
        return 'topologyscripts'

    def shortHelpString(self):
        return self.tr("""Find dangles for a line layer. Dangles are line nodes not connected to another line.        
        
                          Input layer (connection): input line layer for algorithm, which originates from PostGIS database.
                          Input Primary Key: primary key field for input layer.
                          Node Join Tolerance: distance of a node to another line that considers the node connected to it.
                          Filter layer (selected features): polygon layer that filters the input features that intersect the features selected in the filter layer.
                          Filter Primary Key: primary key field for filter layer.                          
        """)

    def initAlgorithm(self, config=None):
        # Input and Connection
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr('Input layer (connection)'),
                [QgsProcessing.TypeVectorLine]
            )
        )
        
        # Input Primary Key
        self.addParameter(QgsProcessingParameterField(name=self.LAYER_PRIMARY_KEY,
                                                      description=self.tr('Input Primary Key'),
                                                      defaultValue='id',
                                                      parentLayerParameterName=self.INPUT))
                                                      
        # Tolerance - Default is 0.0000001 (11 mm in Equator)
        tolerance_param = QgsProcessingParameterNumber(
            name=self.TOLERANCE,
            description=self.tr('Node Join Tolerance'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0000001
        )
        tolerance_param.setMetadata( {'widget_wrapper': { 'decimals': 7 }} )
        
        self.addParameter(tolerance_param)

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
        if parameters['FILTER']:        
            feedback.pushInfo('Finding table of filter layer ...')
            filter_table = find_table(filter)                                                                       

        # Build SQL
        if not parameters['FILTER']:
            sql = ('SELECT endpoints.geom FROM '  
                        f'(SELECT {parameters[self.LAYER_PRIMARY_KEY]}, ST_StartPoint(ST_GeometryN(geom, 1)) AS geom FROM {input_table} ' 
                         'UNION ALL '
                        f'SELECT {parameters[self.LAYER_PRIMARY_KEY]}, ST_EndPoint(ST_GeometryN(geom, 1)) AS geom FROM {input_table} '
                         ') AS endpoints ' 
                   f'LEFT JOIN {input_table} AS T '
                   f'ON endpoints.{parameters[self.LAYER_PRIMARY_KEY]} != T.{parameters[self.LAYER_PRIMARY_KEY]} '
                   f'AND ST_DWithin(endpoints.geom, T.geom, {parameters[self.TOLERANCE]}) '
                    'WHERE T.geom IS NULL')
        else:
            sql = ('SELECT endpoints.geom FROM '  
                        f'(SELECT layer.{parameters[self.LAYER_PRIMARY_KEY]}, ST_StartPoint(ST_GeometryN(layer.geom, 1)) AS geom FROM {input_table} AS layer, '
                        f'{filter_table} AS filter WHERE ST_Intersects(layer.geom, filter.geom) AND '
                        f"filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string}) "
                         'UNION ALL '
                        f'SELECT layer.{parameters[self.LAYER_PRIMARY_KEY]}, ST_EndPoint(ST_GeometryN(layer.geom, 1)) AS geom FROM {input_table} AS layer, '
                        f'{filter_table} AS filter WHERE ST_Intersects(layer.geom, filter.geom) AND '
                        f"filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string}) "
                         ') AS endpoints ' 
                    'LEFT JOIN '
                  f'(SELECT layer.{parameters[self.LAYER_PRIMARY_KEY]}, layer.geom FROM {input_table} AS layer, {filter_table} AS filter '
                   f'WHERE ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string}) ) AS T ' 
                   f'ON endpoints.{parameters[self.LAYER_PRIMARY_KEY]} != T.{parameters[self.LAYER_PRIMARY_KEY]} '
                   f'AND ST_DWithin(endpoints.geom, T.geom, {parameters[self.TOLERANCE]}) '
                    'WHERE T.geom IS NULL')
              
        feedback.pushInfo(sql)

        found = processing.run("gdal:executesql",
                                   {'INPUT': parameters['INPUT'],
                                   'SQL':sql,
                                   'OUTPUT': output},
                                   context=context, feedback=feedback, is_child_algorithm=True)


        return {self.OUTPUT: found['OUTPUT']}
