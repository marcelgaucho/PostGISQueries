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

class EndpointsDontTouchPolygon(QgsProcessingAlgorithm):
    # Constants used to refer to parameters

    INPUT = 'INPUT'
    LAYER2 = 'LAYER2'
    TOLERANCE = 'TOLERANCE'
    FILTER = 'FILTER'
    FILTER_PRIMARY_KEY = 'FILTER_PRIMARY_KEY'
    OUTPUT = 'OUTPUT'


    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("PostGIS Queries: EndpointsDontTouchPolygon", string)

    def createInstance(self):
        return EndpointsDontTouchPolygon()

    def name(self):
        return 'endpointsdonttouchpolygon'

    def displayName(self):
        return self.tr('Find Endpoints that don\'t touch polygon')

    def group(self):
        return self.tr('Topology Scripts')

    def groupId(self):
        return 'topologyscripts'

    def shortHelpString(self):
        return self.tr(""" Find endpoints of a line that don't touch a polygon boundary. A possible application of the script is to find bridges that don’t """
                       """touch the boundary of a water body. 
                       
        
                          Input layer (connection): input line layer for algorithm, which originates from PostGIS database.
                          Polygon layer: polygon layer that relates to the input layer.
                          Node Join Tolerance: distance of a node or endpoint to a polygon boundary that considers the node intersects this boundary.
                          Filter layer (selected features): polygon layer that filters the input and polygon features that intersect the features selected in the filter layer.
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
        
        # Second Layer
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.LAYER2,
                self.tr('Polygon layer'),
                [QgsProcessing.TypeVectorPolygon]
            )
        )
        
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
            sql = ('WITH extremos AS '  
                        f'(SELECT ST_StartPoint(geom) AS geom FROM {input_table} UNION ALL SELECT ST_EndPoint(geom) AS geom '
                        f'FROM {input_table}), '
                   'fronteira_massa AS '
                        f'(SELECT ST_Boundary(geom) AS geom FROM {layer2_table}) '
                  f'SELECT extremos.geom FROM extremos LEFT JOIN fronteira_massa ON ST_DWithin(extremos.geom, fronteira_massa.geom, {parameters[self.TOLERANCE]}) ' 
                   'WHERE fronteira_massa.geom IS NULL ')
        else:
            sql = ('WITH extremos AS '  
                        f'(SELECT ST_StartPoint(layer.geom) AS geom FROM {input_table} AS layer, {filter_table} AS filter '
                        f'WHERE ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string}) '
                         'UNION ALL '
                        f'SELECT ST_EndPoint(layer.geom) AS geom FROM {input_table} AS layer, {filter_table} AS filter '
                        f'WHERE ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})), '
                   'fronteira_massa AS '
                        f'(SELECT ST_Boundary(layer2.geom) AS geom FROM {layer2_table} AS layer2, {filter_table} AS filter '
                        f'WHERE ST_Intersects(layer2.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) '
                   'SELECT extremos.geom FROM extremos LEFT JOIN fronteira_massa ON ST_DWithin(extremos.geom, fronteira_massa.geom, {parameters[self.TOLERANCE]}) ' 
                   'WHERE fronteira_massa.geom IS NULL ')            
                
        feedback.pushInfo(sql)

        # Run query
        found = processing.run("gdal:executesql",
                                   {'INPUT': parameters['INPUT'],
                                   'SQL':sql,
                                   'OUTPUT': output},
                                   context=context, feedback=feedback, is_child_algorithm=True)


        return {self.OUTPUT: found['OUTPUT']}
