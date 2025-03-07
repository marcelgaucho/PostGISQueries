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


class FindPseudonodes(QgsProcessingAlgorithm):
    # Constants used to refer to parameters 

    INPUT = 'INPUT'
    LAYER_PRIMARY_KEY = 'LAYER_PRIMARY_KEY'
    EXCLUDED_FIELD = 'EXCLUDED_FIELD'
    FILTER = 'FILTER'
    FILTER_PRIMARY_KEY = 'FILTER_PRIMARY_KEY'
    TOLERANCE = 'TOLERANCE'    
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("PostGIS Queries: FindPseudonodes", string)

    def createInstance(self):
        return FindPseudonodes()

    def name(self):
        return 'findpseudonodesquery'

    def displayName(self):
        return self.tr('Find Pseudonodes')

    def group(self):
        return self.tr('Topology Scripts')

    def groupId(self):
        return 'topologyscripts'

    def shortHelpString(self):
        return self.tr("""Find pseudonodes for a line layer. Pseudonodes are nodes that form a break in the geometry, but without intersecting lines.
                                  
                          Input layer (connection): input line layer for algorithm, which originates from PostGIS database.
                          Input Primary Key: primary key field for input layer.
                          Excluded Field(s): if fields are selected, adjacent features with a change in these fields don't generate pseudonodes. 
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
                                                      
        # Excluded Field(s)
        self.addParameter(QgsProcessingParameterField(name=self.EXCLUDED_FIELD,
                                                      description=self.tr('Excluded Field(s)'),
                                                      defaultValue=None,
                                                      parentLayerParameterName=self.INPUT,
                                                      allowMultiple=True,
                                                      optional=True))
                                                      
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
        filter = self.parameterAsVectorLayer(parameters, self.FILTER, context)
        output = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        
        # Excluded Field(s)
        if parameters['EXCLUDED_FIELD']:
            excluded_field_list_text_T1 = [f"COALESCE(MAX(T1.{field}::text), 'NULL')" for field in parameters['EXCLUDED_FIELD']]
            excluded_field_list_text_T2 = [f"COALESCE(MAX(T2.{field}::text), 'NULL')" for field in parameters['EXCLUDED_FIELD']]
            excluded_field_string_T1 = ', '.join(excluded_field_list_text_T1)
            excluded_field_string_T2 = ', '.join(excluded_field_list_text_T2)
        
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
        # Join of each start point of each line with the lines that are nearby
        # add to
        # Join of each end point of each line with the lines that are nearby   
        # Set excluded fields in WHERE clause
        # Excluded fields are the fields that, if adjacent lines have changes in it,
        # does not create pseudonodes  
        # We can add ,array_agg(T2.id) AS ids_nearby, count(*) AS contagem_ids_nearby
        # to the fields selected in pseudonodes subquery to see the adjacent lines and their count
        
        if not parameters['FILTER']:
            if not parameters['EXCLUDED_FIELD']:
                sql = ('SELECT DISTINCT geom FROM ' 
                       '( '
                      f'SELECT T1.{parameters[self.LAYER_PRIMARY_KEY]} AS id1, ST_StartPoint(ST_GeometryN(T1.geom, 1)) AS geom '
                      f'FROM {input_table} AS T1 JOIN '
                      f'{input_table} AS T2 ON '
                      f'T1.{parameters[self.LAYER_PRIMARY_KEY]} != T2.{parameters[self.LAYER_PRIMARY_KEY]} AND ST_DWithin(ST_StartPoint(ST_GeometryN(T1.geom, 1)), T2.geom, {parameters[self.TOLERANCE]}) '
                      f'GROUP BY T1.{parameters[self.LAYER_PRIMARY_KEY]} '
                       'HAVING count(*)=1 '
                       'UNION ALL '
                      f'SELECT T1.{parameters[self.LAYER_PRIMARY_KEY]} AS id1, ST_EndPoint(ST_GeometryN(T1.geom, 1)) AS geom '
                      f'FROM {input_table} AS T1 JOIN '
                      f'{input_table} AS T2 ON '
                      f'T1.{parameters[self.LAYER_PRIMARY_KEY]} != T2.{parameters[self.LAYER_PRIMARY_KEY]} AND ST_DWithin(ST_EndPoint(ST_GeometryN(T1.geom, 1)), T2.geom, {parameters[self.TOLERANCE]}) '
                      f'GROUP BY T1.{parameters[self.LAYER_PRIMARY_KEY]} '
                       'HAVING count(*)=1 '
                       ') AS pseudonodes ')
            else:
                sql = ('SELECT DISTINCT geom FROM ' 
                       '( '
                      f'SELECT T1.{parameters[self.LAYER_PRIMARY_KEY]} AS id1, ST_StartPoint(ST_GeometryN(T1.geom, 1)) AS geom '
                      f'FROM {input_table} AS T1 JOIN '
                      f'{input_table} AS T2 ON '
                      f'T1.{parameters[self.LAYER_PRIMARY_KEY]} != T2.{parameters[self.LAYER_PRIMARY_KEY]} AND ST_DWithin(ST_StartPoint(ST_GeometryN(T1.geom, 1)), T2.geom, {parameters[self.TOLERANCE]}) '
                      f'GROUP BY T1.{parameters[self.LAYER_PRIMARY_KEY]} '
                       'HAVING count(*)=1 AND '
                      f'({excluded_field_string_T1}) = ({excluded_field_string_T2}) '
                       'UNION ALL '
                      f'SELECT T1.{parameters[self.LAYER_PRIMARY_KEY]} AS id1, ST_EndPoint(ST_GeometryN(T1.geom, 1)) AS geom '
                      f'FROM {input_table} AS T1 JOIN '
                      f'{input_table} AS T2 ON '
                      f'T1.{parameters[self.LAYER_PRIMARY_KEY]} != T2.{parameters[self.LAYER_PRIMARY_KEY]} AND ST_DWithin(ST_EndPoint(ST_GeometryN(T1.geom, 1)), T2.geom, {parameters[self.TOLERANCE]}) '
                      f'GROUP BY T1.{parameters[self.LAYER_PRIMARY_KEY]} '
                       'HAVING count(*)=1 AND '
                      f'({excluded_field_string_T1}) = ({excluded_field_string_T2}) '
                       ') AS pseudonodes ')
        else:
            if not parameters['EXCLUDED_FIELD']:
                sql = ('SELECT DISTINCT geom FROM ' 
                       '( '
                      f'SELECT T1.{parameters[self.LAYER_PRIMARY_KEY]} AS id1, ST_StartPoint(ST_GeometryN(MAX(T1.geom), 1)) AS geom '
                      f'FROM (SELECT layer.{parameters[self.LAYER_PRIMARY_KEY]}, layer.geom FROM {input_table} AS layer JOIN '
                      f'{filter_table} AS filter ON '
                      f'ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) AS T1 JOIN '
                      f'(SELECT layer.{parameters[self.LAYER_PRIMARY_KEY]}, layer.geom FROM {input_table} AS layer JOIN '
                      f'{filter_table} AS filter ON '
                      f'ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) AS T2 ON '
                      f'T1.{parameters[self.LAYER_PRIMARY_KEY]} != T2.{parameters[self.LAYER_PRIMARY_KEY]} AND ST_DWithin(ST_StartPoint(ST_GeometryN(T1.geom, 1)), T2.geom, {parameters[self.TOLERANCE]}) '
                      f'GROUP BY T1.{parameters[self.LAYER_PRIMARY_KEY]} '
                       'HAVING count(*)=1 '
                       'UNION ALL '
                      f'SELECT T1.{parameters[self.LAYER_PRIMARY_KEY]} AS id1, ST_EndPoint(ST_GeometryN(MAX(T1.geom), 1)) AS geom '
                      f'FROM (SELECT layer.{parameters[self.LAYER_PRIMARY_KEY]}, layer.geom FROM {input_table} AS layer JOIN '
                      f'{filter_table} AS filter ON '
                      f'ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) AS T1 JOIN '
                      f'(SELECT layer.{parameters[self.LAYER_PRIMARY_KEY]}, layer.geom FROM {input_table} AS layer JOIN '
                      f'{filter_table} AS filter ON '
                      f'ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) AS T2 ON '
                      f'T1.{parameters[self.LAYER_PRIMARY_KEY]} != T2.{parameters[self.LAYER_PRIMARY_KEY]} AND ST_DWithin(ST_EndPoint(ST_GeometryN(T1.geom, 1)), T2.geom, {parameters[self.TOLERANCE]}) '
                      f'GROUP BY T1.{parameters[self.LAYER_PRIMARY_KEY]} '
                       'HAVING count(*)=1 '
                       ') AS pseudonodes ')
            else:
                sql = ('SELECT DISTINCT geom FROM ' 
                       '( '
                      f'SELECT T1.{parameters[self.LAYER_PRIMARY_KEY]} AS id1, ST_StartPoint(ST_GeometryN(MAX(T1.geom), 1)) AS geom '
                      f'FROM (SELECT layer.* FROM {input_table} AS layer JOIN '
                      f'{filter_table} AS filter ON '
                      f'ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) AS T1 JOIN '
                      f'(SELECT layer.* FROM {input_table} AS layer JOIN '
                      f'{filter_table} AS filter ON '
                      f'ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) AS T2 ON '
                      f'T1.{parameters[self.LAYER_PRIMARY_KEY]} != T2.{parameters[self.LAYER_PRIMARY_KEY]} AND ST_DWithin(ST_StartPoint(ST_GeometryN(T1.geom, 1)), T2.geom, {parameters[self.TOLERANCE]}) '
                      f'GROUP BY T1.{parameters[self.LAYER_PRIMARY_KEY]} '
                       'HAVING count(*)=1 AND '
                      f'({excluded_field_string_T1}) = ({excluded_field_string_T2}) '
                       'UNION ALL '
                      f'SELECT T1.{parameters[self.LAYER_PRIMARY_KEY]} AS id1, ST_EndPoint(ST_GeometryN(MAX(T1.geom), 1)) AS geom '
                      f'FROM (SELECT layer.* FROM {input_table} AS layer JOIN '
                      f'{filter_table} AS filter ON '
                      f'ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) AS T1 JOIN '
                      f'(SELECT layer.* FROM {input_table} AS layer JOIN '
                      f'{filter_table} AS filter ON '
                      f'ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) AS T2 ON '
                      f'T1.{parameters[self.LAYER_PRIMARY_KEY]} != T2.{parameters[self.LAYER_PRIMARY_KEY]} AND ST_DWithin(ST_EndPoint(ST_GeometryN(T1.geom, 1)), T2.geom, {parameters[self.TOLERANCE]}) '
                      f'GROUP BY T1.{parameters[self.LAYER_PRIMARY_KEY]} '
                       'HAVING count(*)=1 AND '
                      f'({excluded_field_string_T1}) = ({excluded_field_string_T2}) '
                       ') AS pseudonodes ')
        
        feedback.pushInfo(sql)

        # Run query
        found = processing.run("gdal:executesql",
                                   {'INPUT': parameters['INPUT'],
                                   'SQL':sql,
                                   'OUTPUT': output},
                                   context=context, feedback=feedback, is_child_algorithm=True)


        return {self.OUTPUT: found['OUTPUT']}
        