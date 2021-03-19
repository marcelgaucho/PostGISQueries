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
                       QgsProcessingParameterVectorDestination)
import processing


class FindUndershootOvershoot(QgsProcessingAlgorithm):
    # Constants used to refer to parameters

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    TABLE = 'TABLE'
    TOLERANCE = 'TOLERANCE'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("PostGIS Queries: FindUndershootOvershoot", string)

    def createInstance(self):
        return FindUndershootOvershoot()

    def name(self):
        return 'findmicrodanglesquery'

    def displayName(self):
        return self.tr('Find Undershoot and Overshoot')

    def group(self):
        return self.tr('Topology Scripts')

    def groupId(self):
        return 'topologyscripts'

    def shortHelpString(self):
        return self.tr("Find undershoot and overshoot for a line layer.")

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input layer (connection)'),
                [QgsProcessing.TypeVectorLine]
            )
        )

        # Tolerance
        self.addParameter(QgsProcessingParameterNumber(
            self.TOLERANCE,
            self.tr('Tolerance'),
            QgsProcessingParameterNumber.Double,
            0.0001
        ))
     
        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )

        self.addParameter(QgsProcessingParameterString(self.TABLE,
                                                       self.tr('Table'),
                                                       defaultValue=''))



    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        output = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
       
        # Tolerance
        tolerance = parameters[self.TOLERANCE]
        table = parameters[self.TABLE]
        
        # DO SOMETHING       
        sql = ('SELECT DISTINCT dangles.geom FROM '  
                    '(SELECT geom FROM '
                            '(SELECT geom, count(*) AS cnt FROM '
                                  f'(SELECT  ST_StartPoint(ST_GeometryN(geom, 1)) AS geom FROM {table} '
                                  f'UNION ALL SELECT  ST_EndPoint(ST_GeometryN(geom, 1)) AS geom FROM {table}) AS endpoints '
                             'GROUP BY geom) AS nodes '
                    'WHERE cnt = 1) AS dangles JOIN '
                   f'{table} AS B '
                   f'ON ST_DWithin(dangles.geom, B.geom, {tolerance}) AND ST_Distance(dangles.geom, B.geom) BETWEEN 0.0000001 AND {tolerance}')
                            

                
        feedback.pushInfo(sql)

        found = processing.run("gdal:executesql",
                                   {'INPUT': parameters['INPUT'],
                                   'SQL':sql,
                                   'OUTPUT': output},
                                   context=context, feedback=feedback, is_child_algorithm=True)


        return {self.OUTPUT: found['OUTPUT']}
