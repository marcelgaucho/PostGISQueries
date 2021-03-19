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


class FindGaps(QgsProcessingAlgorithm):
    # Constants used to refer to parameters
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    TABLE = 'TABLE'

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
        return self.tr("Find gaps for a polygon layer.")

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

        self.addParameter(QgsProcessingParameterString(self.TABLE,
                                                       self.tr('Table'),
                                                       defaultValue=''))



    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        output = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        # DO SOMETHING       
        sql = ('SELECT aneis_uniao.geom FROM '  
                   '(SELECT (ST_DumpRings(geom)).* FROM '
                        f'(SELECT (ST_Dump(ST_Union(geom))).geom AS geom FROM {parameters[self.TABLE]}) AS uniao '
                   ') AS aneis_uniao LEFT JOIN '
                   '(SELECT geom FROM '
                        f'(SELECT (ST_DumpRings((ST_Dump(geom)).geom)).* FROM {parameters[self.TABLE]}) AS dump '
                   'WHERE path[1] != 0) AS interior_rings ON ST_Equals(aneis_uniao.geom, interior_rings.geom) '
               'WHERE path[1] != 0 AND ST_Area(aneis_uniao.geom) > 0.0000001 AND interior_rings.geom IS NULL')
                
        feedback.pushInfo(sql)

        found = processing.run("gdal:executesql",
                                   {'INPUT': parameters['INPUT'],
                                   'SQL':sql,
                                   'OUTPUT': output},
                                   context=context, feedback=feedback, is_child_algorithm=True)


        return {self.OUTPUT: found['OUTPUT']}
