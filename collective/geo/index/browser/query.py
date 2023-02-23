from zope.interface import Interface, implementer
from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName
from zope.component import queryMultiAdapter
from .search import get_results
from shapely import wkt, geometry, box
import json


class ISearchView(Interface):
    """
    view interface
    """


@implementer(ISearchView)
class SearchView(BrowserView):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def portal_catalog(self):
        return getToolByName(self.context, 'portal_catalog')

    def parse_bbox(self, bbox=None):
        if bbox is None:
            b = self.request.form.get('bbox')
        else:
            b = bbox
        return tuple(float(x) for x in b.split(','))

    def results(self):
        results = []
        brains = get_results(self.context, self.request)
        for brain in brains:
            obj = brain.getObject()
            results.append(obj)
        return results

    def searchbox_geo_json(self):
        geo_json = {
            "type": "FeatureCollection",
            "features": [],
        }
        # bounding box
        if 'zgeo_geometry' not in self.request:
            return None
        bbox = self.request['zgeo_geometry']
        bbox = self.parse_bbox(bbox)
        geom = box(*bbox)

        feature = {
            "type": "Feature",
            "properties": {
                "color": "orange",
                "popup": str(bbox)
            },
            "geometry": geometry.mapping(geom)
        }
        geo_json['features'].append(feature)
        return geo_json

    def results_geojson(self):
        geo_json = {
            "type": "FeatureCollection",
            "features": [],
        }
        # bounding box
        if 'zgeo_geometry' not in self.request:
            return None
        bbox = self.request['zgeo_geometry']
        bbox = self.parse_bbox(bbox)
        geom = box(*bbox)
        feature = {
            "type": "Feature",
            "properties": {
                "color": "orange",
                "popup": str(bbox)
            },
            "geometry": geometry.mapping(geom)
        }
        geo_json['features'].append(feature)

        for geoobj in self.results():
            geom = wkt.loads(geoobj.geodata)
            popup_view = queryMultiAdapter(
                (geoobj, self.request), name="geolocation-geojson-popup"
            )
            feature = {
                "type": "Feature",
                "properties": {
                    "popup": popup_view(),
                    "color": "orange",
                },
                "geometry": geometry.mapping(geom)
            }
            geo_json['features'].append(feature)

        jsonstring = json.dumps(geo_json)
        return jsonstring
