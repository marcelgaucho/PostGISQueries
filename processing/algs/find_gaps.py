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

class FindGaps(QgsProcessingAlgorithm):
    # Constants used to refer to parameters
    INPUT = 'INPUT'
    LAYER_PRIMARY_KEY = 'LAYER_PRIMARY_KEY'
    MIN_SQUARED_DISTANCE = 'MIN_SQUARED_DISTANCE'
    FILTER = 'FILTER'
    FILTER_PRIMARY_KEY = 'FILTER_PRIMARY_KEY'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("PostGIS Queries: FindGaps", string)

    def createInstance(self):
        return FindGaps()

    def name(self):
        return 'findgaps'

    def displayName(self):
        return self.tr('Find Gaps')

    def group(self):
        return self.tr('Topology Scripts')

    def groupId(self):
        return 'topologyscripts'

    def shortHelpString(self):
        return self.tr("""For a polygon layer that should have adjacent features, the gaps between polygons are returned as polygons.
        
                          Input layer (connection) (use selection if exists): input polygon layer for algorithm, which originates from PostGIS database. If features are selected in this layer, """
                       """the algorithm is applied only to these features.
                          Input Primary Key: primary key field for input layer. If there are features selected in the input layer, the input primary key must be selected.
                          Minimum Squared Distance: distance, which squared, represents the minimum area allowed for a polygon in the result.  
                          Filter layer (selected features): polygon layer that filters the input features that intersect the features selected in the filter layer.
                          Filter Primary Key: primary key field for filter layer.                          
        """)

    def initAlgorithm(self, config=None):
        # Input and Connection
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr('Input layer (connection) (use selection if exists)'),
                [QgsProcessing.TypeVectorPolygon]
            )
        )
        
        # Input Primary Key
        self.addParameter(QgsProcessingParameterField(name=self.LAYER_PRIMARY_KEY,
                                                      description=self.tr('Input Primary Key'),
                                                      defaultValue=None,
                                                      parentLayerParameterName=self.INPUT,
                                                      optional=True))
                                                      
        # Minimum distance that squared forms the minimum area of polygons returned - Default is 0.000001 (111 mm in Equator)
        # In area, this is equivalent to approximately 10 squared centimeters
        minsquareddistance_param = QgsProcessingParameterNumber(
            name=self.MIN_SQUARED_DISTANCE,
            description=self.tr('Minimum Squared Distance'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0000001
        )
        minsquareddistance_param.setMetadata( {'widget_wrapper': { 'decimals': 7 }} )
        
        self.addParameter(minsquareddistance_param)

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
        
        # Selected features of input layer
        selection_input = input.selectedFeatures()
        if selection_input:
            # Warn because there are features selected in input layer, so these will be used
            feedback.pushWarning('There are features selected in input layer, so only these will be used in the algorithm')
            # Raise erros if features are selected in input layer, but no primary key for the input layer is selected
            if not parameters['LAYER_PRIMARY_KEY']:
                raise QgsProcessingException('Features selected in the Input Layer, but no primary key selected')
                
            input_pk_field = find_field(input, parameters['LAYER_PRIMARY_KEY'])
            if input_pk_field.isNumeric():
                selection_field_list = [str(f[parameters['LAYER_PRIMARY_KEY']]) for f in selection_input]
            else:
                selection_field_list = [f"'{f[ parameters['LAYER_PRIMARY_KEY'] ]}'" for f in selection_input]
                
            selection_field_string_input = ', '.join(selection_field_list)       
        
        # Selected features of filter layer
        if parameters['FILTER']:
            selection_filter = filter.selectedFeatures()
            if not selection_filter:
                raise QgsProcessingException('No features selected in Filter Layer')
            
            # Depending on the type of the Filter Primary Key, build the string with selected values
            if not parameters['FILTER_PRIMARY_KEY']:
                raise QgsProcessingException('No field selected for primary key in Filter Layer')
                                
            filter_pk_field = find_field(filter, parameters['FILTER_PRIMARY_KEY'])
            if filter_pk_field.isNumeric():
                selection_field_list = [str(f[parameters['FILTER_PRIMARY_KEY']]) for f in selection_filter]
            else:
                selection_field_list = [f"'{f[ parameters['FILTER_PRIMARY_KEY'] ]}'" for f in selection_filter]
                
            selection_field_string_filter = ', '.join(selection_field_list)
            
        # Schema.Table for Input and Filter
        feedback.pushInfo('Finding table of input layer ...')
        input_table = find_table(input) 
        if parameters['FILTER']:        
            feedback.pushInfo('Finding table of filter layer ...')
            filter_table = find_table(filter)        

        # Build SQL
        # aneis_uniao is the rings of the dissolved polygons,
        # where the inner rings (holes) are the potencial gaps,
        # in case there aren't equal with the original inner rings.
        # Without filter
        minimum_area = parameters[self.MIN_SQUARED_DISTANCE] * parameters[self.MIN_SQUARED_DISTANCE]
        if not parameters['FILTER']:
            # No selection in input 
            if not selection_input:
                # Warn because no features are selected, but the primary key is used
                if parameters['LAYER_PRIMARY_KEY']:
                    feedback.pushWarning('Primary key is selected, but no selection was found. The result will be computed for the entire layer.')
                
                sql = ('SELECT aneis_uniao.geom FROM '  
                           '(SELECT (ST_DumpRings(geom)).* FROM '
                                f'(SELECT (ST_Dump(ST_Union(geom))).geom AS geom FROM {input_table}) AS uniao '
                           ') AS aneis_uniao LEFT JOIN '
                           '(SELECT geom FROM '
                                f'(SELECT (ST_DumpRings((ST_Dump(geom)).geom)).* FROM {input_table}) AS dump '
                           'WHERE path[1] != 0) AS interior_rings ON ST_Equals(aneis_uniao.geom, interior_rings.geom) '
                      f'WHERE path[1] != 0 AND ST_Area(aneis_uniao.geom) >= {minimum_area} AND interior_rings.geom IS NULL')
            # With selection in input
            else:
                sql = ('SELECT aneis_uniao.geom FROM '  
                           '(SELECT (ST_DumpRings(geom)).* FROM '
                                f'(SELECT (ST_Dump(ST_Union(geom))).geom AS geom FROM {input_table} WHERE {parameters[self.LAYER_PRIMARY_KEY]} IN ({selection_field_string_input})) AS uniao '
                           ') AS aneis_uniao LEFT JOIN '
                           '(SELECT geom FROM '
                                f'(SELECT (ST_DumpRings((ST_Dump(geom)).geom)).* FROM {input_table} WHERE {parameters[self.LAYER_PRIMARY_KEY]} IN ({selection_field_string_input})) AS dump '
                           'WHERE path[1] != 0) AS interior_rings ON ST_Equals(aneis_uniao.geom, interior_rings.geom) '
                      f'WHERE path[1] != 0 AND ST_Area(aneis_uniao.geom) >= {minimum_area} AND interior_rings.geom IS NULL')
                       
        # With filter
        else:
            # No selection in input
            if not selection_input:
                sql = ('SELECT aneis_uniao.geom FROM '  
                           '(SELECT (ST_DumpRings(geom)).* FROM '
                                f'(SELECT (ST_Dump(ST_Union(layer.geom))).geom AS geom FROM {input_table} AS layer JOIN {filter_table} AS filter '
                                f'ON ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string_filter})) AS uniao '
                           ') AS aneis_uniao LEFT JOIN '
                           '(SELECT geom FROM '
                                f'(SELECT (ST_DumpRings((ST_Dump(layer.geom)).geom)).* FROM {input_table} AS layer JOIN {filter_table} AS filter '
                                f'ON ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string_filter})) AS dump '                                
                           'WHERE path[1] != 0) AS interior_rings ON ST_Equals(aneis_uniao.geom, interior_rings.geom) '
                      f'WHERE path[1] != 0 AND ST_Area(aneis_uniao.geom) >= {minimum_area} AND interior_rings.geom IS NULL')    
            # With selection in input
            else:
                sql = ('SELECT aneis_uniao.geom FROM '  
                           '(SELECT (ST_DumpRings(geom)).* FROM '
                                f'(SELECT (ST_Dump(ST_Union(layer.geom))).geom AS geom FROM {input_table} AS layer JOIN {filter_table} AS filter '
                                f'ON ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string_filter}) '
                                f'WHERE layer.{parameters[self.LAYER_PRIMARY_KEY]} IN ({selection_field_string_input})) AS uniao '
                           ') AS aneis_uniao LEFT JOIN '
                           '(SELECT geom FROM '
                                f'(SELECT (ST_DumpRings((ST_Dump(layer.geom)).geom)).* FROM {input_table} AS layer JOIN {filter_table} AS filter '
                                f'ON ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string_filter}) '                                
                                f'WHERE layer.{parameters[self.LAYER_PRIMARY_KEY]} IN ({selection_field_string_input})) AS dump '
                           'WHERE path[1] != 0) AS interior_rings ON ST_Equals(aneis_uniao.geom, interior_rings.geom) '
                      f'WHERE path[1] != 0 AND ST_Area(aneis_uniao.geom) >= {minimum_area} AND interior_rings.geom IS NULL')    
                    
        feedback.pushInfo(sql)

        found = processing.run("gdal:executesql",
                                   {'INPUT': parameters['INPUT'],
                                   'SQL':sql,
                                   'OUTPUT': output},
                                   context=context, feedback=feedback, is_child_algorithm=True)

        return {self.OUTPUT: found['OUTPUT']}
