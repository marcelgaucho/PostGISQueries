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

class FindKNearestNeighborsWithinDistance(QgsProcessingAlgorithm):
    # Constants used to refer to parameters 
    INPUT = 'INPUT'
    LAYER_PRIMARY_KEY = 'LAYER_PRIMARY_KEY'
    LAYER2 = 'LAYER2'
    LAYER2_PRIMARY_KEY = 'LAYER2_PRIMARY_KEY'
    THRESHOLD_DISTANCE = 'THRESHOLD_DISTANCE'
    KNEIGHBORS = 'KNEIGHBORS'
    FILTER = 'FILTER'
    FILTER_PRIMARY_KEY = 'FILTER_PRIMARY_KEY'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("PostGIS Queries: FindKNearestNeighborsWithinDistance", string)

    def createInstance(self):
        return FindKNearestNeighborsWithinDistance()

    def name(self):
        return 'findknearestneighborswithindistance'

    def displayName(self):
        return self.tr('Find K Nearest Neighbors Within Distance')

    def group(self):
        return self.tr('Topology Scripts')

    def groupId(self):
        return 'topologyscripts'

    def shortHelpString(self):
        return self.tr("""Find the K Nearest Neighbors within certain distance of the features. It takes 2 layers. """
                       """The first is the input layer and the second is the neighbors layer. The features returned are from the neighbors layer. """
                       """For each feature of the input layer, the K nearest features from the neighbors layer that are within the threshold distance are returned.
                       
                          Input layer (connection): input layer for algorithm, which originates from PostGIS database.
                          Input Primary Key: primary key field for input layer.
                          Second layer: neighbors layer, from which features are returned.
                          Second Layer Primary Key:  primary key field for second layer.
                          Threshold Distance: limit distance from the input layer at which features from the second layer are returned. Neighbors that do not intersect """
                       """the search radius designated by the threshold distance will not be returned.
                          Number of neighbors: maximum number of neighbors, for each feature and located within the threshold distance, that can be returned.
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
        
        # Input Primary Key
        self.addParameter(QgsProcessingParameterField(name=self.LAYER_PRIMARY_KEY,
                                                      description=self.tr('Input Primary Key'),
                                                      defaultValue='id',
                                                      parentLayerParameterName=self.INPUT))

        # Second Layer
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.LAYER2,
                self.tr('Second layer'),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )
        
        # Second Layer Primary Key
        self.addParameter(QgsProcessingParameterField(name=self.LAYER2_PRIMARY_KEY,
                                                      description=self.tr('Second Layer Primary Key'),
                                                      defaultValue='id',
                                                      parentLayerParameterName=self.LAYER2))
                                                      
        # Threshold Distance - Default is in degrees and is approximately 111 meters in Equator
        self.addParameter(QgsProcessingParameterNumber(
            self.THRESHOLD_DISTANCE,
            self.tr('Threshold Distance'),
            QgsProcessingParameterNumber.Double,
            0.001
        ))                                                       

        # K Neighbors. Number of neighbors to find within distance. Default is 1
        self.addParameter(QgsProcessingParameterNumber(
            self.KNEIGHBORS,
            self.tr('Number of neighbors'),
            QgsProcessingParameterNumber.Integer,
            1
        ))
        
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
        output = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        layer2 = self.parameterAsVectorLayer(parameters, self.LAYER2, context)
        filter = self.parameterAsVectorLayer(parameters, self.FILTER, context)
        
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
            sql = (f'SELECT id, idN, distance, rank, geom FROM ( '
                        f'SELECT T1.{parameters[self.LAYER_PRIMARY_KEY]} AS id, T2.{parameters[self.LAYER2_PRIMARY_KEY]} AS idN, '  
                               f'ST_Distance(T1.geom, T2.geom) AS distance, RANK() OVER win AS rank, T2.geom '
                        f'FROM {input_table} AS T1 JOIN {layer2_table} AS T2 '
                        f'ON ST_DWithin(T1.geom, T2.geom, {parameters[self.THRESHOLD_DISTANCE]}) '
                        f'WINDOW win AS (PARTITION BY T1.{parameters[self.LAYER_PRIMARY_KEY]} ORDER BY ST_Distance(T1.geom, T2.geom) ASC) '
                        f') AS foo '
                   f'WHERE rank <= {parameters[self.KNEIGHBORS]} ')         
        else:
            sql = (f'SELECT id, idN, distance, rank, geom FROM ( '
                        f'SELECT T1.{parameters[self.LAYER_PRIMARY_KEY]} AS id, T2.{parameters[self.LAYER2_PRIMARY_KEY]} AS idN, '  
                               f'ST_Distance(T1.geom, T2.geom) AS distance, RANK() OVER win AS rank, T2.geom '
                        f'FROM (SELECT layer.{parameters[self.LAYER_PRIMARY_KEY]}, layer.geom FROM {input_table} AS layer, {filter_table} as filter '
                               f'WHERE ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) AS T1 '
                        f'JOIN (SELECT layer.{parameters[self.LAYER2_PRIMARY_KEY]}, layer.geom FROM {layer2_table} AS layer, {filter_table} as filter '
                               f'WHERE ST_Intersects(layer.geom, filter.geom) AND filter.{parameters[self.FILTER_PRIMARY_KEY]} IN ({selection_field_string})) AS T2 '
                        f'ON ST_DWithin(T1.geom, T2.geom, {parameters[self.THRESHOLD_DISTANCE]}) '
                        f'WINDOW win AS (PARTITION BY T1.{parameters[self.LAYER_PRIMARY_KEY]} ORDER BY ST_Distance(T1.geom, T2.geom) ASC) '
                         ') AS foo '
                   f'WHERE rank <= {parameters[self.KNEIGHBORS]} ')         
        
        feedback.pushInfo(sql)
        
        # Run query
        found = processing.run("gdal:executesql",
                                   {'INPUT': parameters['INPUT'],
                                   'SQL':sql,
                                   'OUTPUT': output},
                                   context=context, feedback=feedback, is_child_algorithm=True)


        return {self.OUTPUT: found['OUTPUT']}
