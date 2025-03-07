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
                       QgsProcessingParameterNumber,
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

class FindOverlapInTwoLayers(QgsProcessingAlgorithm):
    # Constants used to refer to parameters 

    INPUT = 'INPUT'
    LAYER2 = 'LAYER2'
    MIN_SQUARED_DISTANCE = 'MIN_SQUARED_DISTANCE'
    FILTER = 'FILTER'
    FILTER_PRIMARY_KEY = 'FILTER_PRIMARY_KEY'
    OUTPUT = 'OUTPUT'

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
        return self.tr("""Find the overlap area between polygons in the first and second layers. The result area is returned as polygons.
        
                          Input layer (connection): input polygon layer for algorithm, which originates from PostGIS database.
                          Second layer: layer that is compared with the input layer to find the overlap area. 
                          Minimum Squared Distance: distance, which squared, represents the minimum area allowed for a polygon in the result.
                          Filter layer (selected features): polygon layer that filters the input and second layer features that intersect the features selected in the filter layer.
                          Filter Primary Key: primary key field for filter layer.                          
        """)

    def initAlgorithm(self, config=None):
        # Input and Connection
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr('Input layer (connection)'),
                [QgsProcessing.TypeVectorPolygon]
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
        # return dump of the intersection part, which is the part that overlaps
        # For the sake of performance, ST_Overlaps is not used, 
        # instead ST_Intersects and not ST_Touches are used, 
        # which gives the same behavior, with the only difference 
        # that ST_Overlaps does not return identical geometries
        # returns only area elements and above threshold
        minimum_area = parameters[self.MIN_SQUARED_DISTANCE] * parameters[self.MIN_SQUARED_DISTANCE]

        if not parameters['FILTER']:
            sql = ('SELECT geom FROM (SELECT (ST_Dump(ST_Intersection(T1.geom, T2.geom))).geom FROM '  
                        f'{input_table} AS T1 JOIN {layer2_table} AS T2 '
                         'ON (ST_Intersects(T1.geom, T2.geom) AND NOT ST_Touches(T1.geom, T2.geom))) AS sobreposicao '
                  f'WHERE ST_Dimension(geom) = 2 AND ST_Area(geom) > {minimum_area}')    
        else:
            sql = ('SELECT geom FROM (SELECT (ST_Dump(ST_Intersection(T1.geom, T2.geom))).geom FROM '
                        f'(SELECT layer.geom FROM {input_table} AS layer JOIN {filter_table} AS filter '
                        f'ON ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) AS T1 JOIN ' 
                        f'(SELECT layer2.geom FROM {layer2_table} AS layer2 JOIN {filter_table} AS filter '
                        f'ON ST_Intersects(layer2.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) AS T2 ' 
                         'ON (ST_Intersects(T1.geom, T2.geom) AND NOT ST_Touches(T1.geom, T2.geom))) AS sobreposicao '
                  f'WHERE ST_Dimension(geom) = 2 AND ST_Area(geom) > {minimum_area}') 

        feedback.pushInfo(sql)

        # Run query
        found = processing.run("gdal:executesql",
                                   {'INPUT': parameters['INPUT'],
                                   'SQL':sql,
                                   'OUTPUT': output},
                                   context=context, feedback=feedback, is_child_algorithm=True)


        return {self.OUTPUT: found['OUTPUT']}
