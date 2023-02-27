#
# Copyright (c) 2008 Eric BREHAULT
# contact: eric.brehault@makina-corpus.org
# (c) 2011 Christian Ledermann

from App.special_dtml import DTMLFile
from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager
from zope.interface import implementer
from zope.interface import Interface
from zope.component import adapter
from Products.PluginIndexes.common.util import parseIndexRequest
from Products.PluginIndexes.interfaces import IPluggableIndex
from Products.PluginIndexes.interfaces import ISortIndex
from Products.PluginIndexes.interfaces import IUniqueValueIndex
from shapely.geometry import MultiPoint

from BTrees.IIBTree import IITreeSet
from shapely.geometry import shape
from shapely import wkt
from .index import BaseIndex
from collective.geo.geographer.interfaces import IGeoreferenceable, IGeoreferenced
from plone.restapi.interfaces import IIndexQueryParser
from plone.restapi.search.query import BaseIndexQueryParser
import logging

logger = logging.getLogger('collective.geo.index')

_marker = []

OPERATORS = ('equals', 'disjoint', 'intersects', 'touches',
            'crosses', 'within', 'contains', 'overlaps')


def bboxAsTuple(geometry):
    """ return the geometry bbox as tuple
    """
    envelope = geometry.envelope
    if envelope.geometryType() == "Point":
        x = envelope.coords[0][0]
        y = envelope.coords[0][1]
        return (x, y, x, y)
    else:
        return envelope.bounds


@implementer(IPluggableIndex, IUniqueValueIndex, ISortIndex)
class GeometryIndex(SimpleItem, BaseIndex, PropertyManager):
    """Index for geometry attribute provided by IGeoManager adapter
    """

    meta_type="GeometryIndex"

    query_options = ('query','geometry_operator')

    manage_browse = DTMLFile('dtml/browseGeometryIndex', globals())

    manage_main = DTMLFile('dtml/manageGeometryIndex', globals())

    manage_options= (
        {'label': 'Settings',
         'action': 'manage_main'},
        {'label': 'Browse',
         'action': 'manage_browse'},
    )




    def __init__(self, id):
        self.id = id
        BaseIndex.__init__(self)
        self.clear()
        self.operators = OPERATORS
        self.useOperator = 'within'

    def getId(self):
        """See IPluggableIndex.
        """
        return self.id

    def getEntryForObject(self, documentId, default=None):
        """ See IPluggableIndex
        """
        return self.backward.get(documentId, default)


    def index_object(self, documentId, obj, threshold=None):
        """index an object, normalizing the indexed value to its bounds

           o Objects which have 'None' as indexed value are *omitted*,
             by design.

        'documentId' is the integer ID of the document.
        'obj' is the object to be indexed.
        """
        returnStatus = 0
        try:
            geoitem_wkt = shape(IGeoreferenced(obj).geo).wkt
        except:
            return 0
        if geoitem_wkt:
            geometry = wkt.loads(geoitem_wkt)
        else:
            geometry = None
        if IGeoreferenceable.providedBy(obj) and IGeoreferenced(obj).coordinates:
            newValue = geoitem_wkt
            if newValue is callable:
                newValue = newValue()
            oldValue = self.backward.get(documentId, _marker )

            if newValue is _marker:
                if oldValue is not _marker:
                    self.rtree.delete(documentId, wkt.loads(oldValue).bounds)
                    try:
                        del self.backward[documentId]
                    # except ConflictError:
                    #     raise
                    except:
                        pass
            else:
                if oldValue is not _marker and newValue!=oldValue:
                    self.rtree.delete(documentId, wkt.loads(oldValue).bounds)
                if geometry:
                    self.rtree.add(documentId, geometry.bounds)
                self.backward[documentId] = newValue

            returnStatus = 1

        return returnStatus

    def unindex_object( self, documentId ):
        """
            Remove the object corresponding to 'documentId' from the index.
        """
        datum = self.backward.get( documentId, None )

        if datum is None:
            return

        self.rtree.delete(documentId, wkt.loads(datum).bounds)
        try:
            del self.backward[documentId]
        # except ConflictError:
        #     raise
        except:
            logger.debug('Attempt to unindex nonexistent document'
                      ' with id %s' % documentId, exc_info=True)

    def _apply_index(self, request, cid='', type=type):
        """
        """
        record = parseIndexRequest(request, self.id, self.query_options)
        if record.keys is None:
            return None
        r = None

        operator = record.get('geometry_operator', self.useOperator)
        if operator not in self.operators:
            # raise RuntimeError()"operator not valid: %s" % operator
            raise RuntimeError("operator not valid")
        if operator == 'disjoint':
            raise RuntimeError("DISJOINT not supported yet")
        logger.debug('Operator: ' + str(operator))

        # we only process one key
        key = record.keys[0]
        bbox = [float(c) for c in key.split(',')]  # bboxAsTuple(key)
        intersection = self.rtree.intersection(bbox)
        set = []
        for d in [l for l in intersection]:
            try:
                geom_wkt = self.backward.get(int(d), None)
            except:
                logger.info('backward.get failed for %s : %s' %(str(d), str(int(d))))
                continue

            if geom_wkt is not None:
                geom = wkt.loads(geom_wkt)
                if geom is not None:
                    opr = getattr(geom, operator)
                    mp = MultiPoint([bbox[:2], bbox[2:]])
                    if opr(mp.envelope):
                        set.append(int(d))

        r = IITreeSet(set)
        #import pdb; pdb.set_trace()
        return r, (self.id,)

    def destroy_spatialindex(self):
        """
        """
        self.clear()

    def uniqueValues(self):
        """ Just a dummy to make ZCatalog/plan.py happy
        """
        return []


manage_addGeometryIndexForm = DTMLFile('dtml/addGeometryIndex', globals())


def manage_addGeometryIndex(self, id, REQUEST=None, RESPONSE=None, URL3=None):
    """Add a DateDate index"""
    return self.manage_addIndex(id, 'GeometryIndex', extra=None, 
        REQUEST=REQUEST, RESPONSE=RESPONSE, URL1=URL3)


@implementer(IIndexQueryParser)
@adapter(GeometryIndex, Interface, Interface)
class GeometryIndexQueryParser(BaseIndexQueryParser):

    query_value_type = str
    query_options = {
        "geometry_operator": str,
    }