# -*- coding: utf-8 -*-
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
def classFactory(iface):
    from .postgis_queries import PostGISQueries
    return PostGISQueries(iface)
