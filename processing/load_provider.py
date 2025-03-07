#-*- coding: utf-8 -*-
"""
/***************************************************************************
                           PostGIS Queries
                             --------------------
        begin                : 2021-19-02
        copyright            : (C) 2021 by Marcel Rotunno (IBGE)
        email                : marcelgaucho@yahoo.com.br
 ***************************************************************************/
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License v3.0 as          *
 *   published by the Free Software Foundation.                            *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.core import QgsProcessingProvider
from processing.core.ProcessingConfig import Setting, ProcessingConfig
from PostGISQueries.processing.algs.find_dangles import FindDangles
from PostGISQueries.processing.algs.find_endpoints_that_dont_touch_polygon import EndpointsDontTouchPolygon 
from PostGISQueries.processing.algs.find_undershoot_overshoot import FindUndershootOvershoot
from PostGISQueries.processing.algs.return_geometry_without_holes import ReturnGeometryWithoutHoles
from PostGISQueries.processing.algs.find_overlap_in_two_layers import FindOverlapInTwoLayers
from PostGISQueries.processing.algs.find_overlap_in_one_layer import FindOverlapInOneLayer
from PostGISQueries.processing.algs.find_pseudonodes import FindPseudonodes
from PostGISQueries.processing.algs.find_polygons_that_arent_filled_by_polygons import PolygonsArentFilledByPolygons
from PostGISQueries.processing.algs.find_polygons_that_dont_contain_1_point import PolygonsDontContainOnePoint
from PostGISQueries.processing.algs.find_invalid_polygons import FindInvalidPolygons
from PostGISQueries.processing.algs.find_geometries_with_repeated_vertices import FindGeometriesWithRepeatedVertices
from PostGISQueries.processing.algs.find_not_simple_lines import FindNotSimpleLines
from PostGISQueries.processing.algs.find_k_nearest_neighbors_within_distance import FindKNearestNeighborsWithinDistance
from PostGISQueries.processing.algs.find_empty_or_null_geometries import FindEmptyOrNullGeometries
from PostGISQueries.processing.algs.find_polygons_with_holes import FindPolygonsWithHoles
from PostGISQueries.processing.algs.find_gaps import FindGaps
from PostGISQueries.processing.algs.find_repeated_geometries import FindRepeatedGeometries
from PostGISQueries.processing.algs.find_geometries_different_from_other_layer import FindGeometriesDifferentFromOtherLayer













class LoadAlgorithmProvider(QgsProcessingProvider):

    def __init__(self):
        super().__init__()

    def load(self):
        ProcessingConfig.settingIcons[self.name()] = self.icon()
        # Activate provider by default
        ProcessingConfig.addSetting(Setting(self.name(), 'ACTIVATE_POSTGIS_QUERIES', 'Activate', True))
        ProcessingConfig.readSettings()
        self.refreshAlgorithms()
        return True

    def unload(self):
        """Setting should be removed here, so they do not appear anymore
        when the plugin is unloaded.
        """
        ProcessingConfig.removeSetting('ACTIVATE_POSTGIS_QUERIES')

    def isActive(self):
        """Return True if the provider is activated and ready to run algorithms"""
        return ProcessingConfig.getSetting('ACTIVATE_POSTGIS_QUERIES')

    def setActive(self, active):
        ProcessingConfig.setSettingValue('ACTIVATE_POSTGIS_QUERIES', active)

    def id(self):
        """This is the name that will appear on the toolbox group.

        It is also used to create the command line name of all the
        algorithms from this provider.
        """
        return 'postgisqueries'

    def name(self):
        """This is the localised full name.
        """
        return 'PostGIS Queries'

    def icon(self):
        """We return the default icon.
        """
        return QgsProcessingProvider.icon(self)

    def loadAlgorithms(self):
        """Here we fill the list of algorithms in self.algs.

        This method is called whenever the list of algorithms should
        be updated. If the list of algorithms can change (for instance,
        if it contains algorithms from user-defined scripts and a new
        script might have been added), you should create the list again
        here.

        In this case, since the list is always the same, we assign from
        the pre-made list. This assignment has to be done in this method
        even if the list does not change, since the self.algs list is
        cleared before calling this method.
        """
        for alg in [FindDangles(), EndpointsDontTouchPolygon(), FindUndershootOvershoot(), ReturnGeometryWithoutHoles(),
                    FindOverlapInTwoLayers(), FindOverlapInOneLayer(), FindPseudonodes(), PolygonsArentFilledByPolygons(),
                    PolygonsDontContainOnePoint(), FindInvalidPolygons(), FindGeometriesWithRepeatedVertices(),
                    FindNotSimpleLines(), FindKNearestNeighborsWithinDistance(), FindEmptyOrNullGeometries(),
                    FindPolygonsWithHoles(), FindGaps(), FindRepeatedGeometries(), FindGeometriesDifferentFromOtherLayer()]:
            self.addAlgorithm(alg)
