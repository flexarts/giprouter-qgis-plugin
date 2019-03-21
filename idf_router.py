import os
import time
import processing

from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.core import *
from qgis.analysis import *
from datetime import datetime

class IDFRouter(QObject):

    onFileProgress = pyqtSignal(float)

    def __init__(self, idf_file, mode='distance', bbox=None):
        super(IDFRouter, self).__init__()
        self.mode = mode
        self.bbox = bbox
        self.idf_file = idf_file
        self.node_layer = None
        self.link_layer = None
        self.route_layer = None
        self.poi_layer = None
        self.reachable_hulls = None
        self.reachable_layers = None
        self.reset()

    def reset(self):
        """ for the basic network """
        self.nodes = {}
        self.links = {}
        self.node_features = []
        self.link_features = []

        self.__cleanUpReachability()
        try:
            if self.node_layer != None:
                QgsProject.instance().removeMapLayer(self.node_layer)
            if self.link_layer != None:
                QgsProject.instance().removeMapLayer(self.link_layer)
            if self.route_layer != None:
                QgsProject.instance().removeMapLayer(self.route_layer)
        except:
            print('null')
        
        self.node_layer = None
        self.link_layer = None
        self.route_layer = None
        self.node_layer_canvas = None
        self.link_layer_canvas = None
    
        """ for the routing graph """
        self.use_to_link = {}
        self.graph = QgsGraph()
        self.link_to_vertex = {}
        self.vertex_to_link = {}
    
    def unload(self):
        self.reset()
    
    def load(self):
        self.reset()
        layers = self.readIdf(self.idf_file)
        for layer in layers:
            layer.updateExtents()
        self.node_layer = layers[0]
        self.link_layer = layers[1]
        
        QgsProject.instance().addMapLayer(self.node_layer)
        QgsProject.instance().addMapLayer(self.link_layer)
        print(self.node_layer.id())
        print(self.link_layer.id())
        self.node_layer_canvas = QgsProject.instance().layerTreeRoot().findLayer(self.node_layer.id())
        self.link_layer_canvas = QgsProject.instance().layerTreeRoot().findLayer(self.link_layer.id())
        
    def showLayers(self):
        self.node_layer_canvas.setItemVisibilityChecked(True)
        self.link_layer_canvas.setItemVisibilityChecked(True)
    
    def hideLayers(self):
        self.node_layer_canvas.setItemVisibilityChecked(False)
        self.link_layer_canvas.setItemVisibilityChecked(False)
    
    def getStatusText(self):
        return "%d Nodes / %d Links" % (len(self.nodes), len(self.links))

    def readIdf(self, idf_file):
        status = ""
        fileSize = os.path.getsize(idf_file)
        progress = 0
        lines = 0

        with open(idf_file, errors='ignore') as f:
            for line in f:
                lines = lines + 1
                progress = progress + len(line)

                # notify progress event every 1000 read lines
                if lines % 1000 == 0:
                    progressPercent = (100.0*progress)/fileSize
                    self.onFileProgress.emit(progressPercent)
                # print(progressPercent)

                line = line.strip().split(';')
                if line[0] == "tbl":
                    status = line[1]
                    print(str(datetime.now()) + ' ' + status)

                """ NODE """
                if status == "Node" and line[0] == "atr":
                    attribute_names = line[1:]
                if status == "Node" and line[0] == "frm":
                    node_layer = QgsVectorLayer(
                        "Point?crs=epsg:4326&index=yes", 
                        "nodes",
                        "memory")
                    node_pr = node_layer.dataProvider()
                    for frm in line [1:]:
                        atr = attribute_names.pop(0)
                        frm = frm.split("(")[0]
                        if frm == "decimal":
                            field = QgsField(atr,QVariant.Double)
                        elif frm == "string":
                            field = QgsField(atr,QVariant.String)
                        node_pr.addAttributes([field])
                    node_layer.updateFields()
                if status == "Node" and line[0] == "rec":
                    id = int(line[1])
                    x = float(line[4])
                    y = float(line[5])
                    # add a feature
                    fet = QgsFeature()
                    pt = QgsPointXY(x,y)
                    if self.bbox and not self.bbox.contains(pt):
                        continue
                    self.nodes[id] = pt
                    fet.setGeometry(QgsGeometry.fromPointXY(pt))
                    fet.setAttributes(line[1:])
                    self.node_features.append(fet)
                    
                """ LINK """    
                if status == "Link" and line[0] == "atr":
                    node_pr.addFeatures(self.node_features)
                    self.node_features = []
                    attribute_names = line[1:]
                if status == "Link" and line[0] == "frm":
                    link_layer = QgsVectorLayer(
                        "LineString?crs=epsg:4326&index=yes", 
                        "links", 
                        "memory")
                    link_pr = link_layer.dataProvider()
                    for frm in line [1:]:
                        atr = attribute_names.pop(0)
                        frm = frm.split("(")[0]
                        if frm == "decimal":
                            field = QgsField(atr,QVariant.Double)
                        elif frm == "string":
                            field = QgsField(atr,QVariant.String)
                        link_pr.addAttributes([field])
                    link_layer.updateFields()
                if status == "Link" and line[0] == "rec":
                    id = int(line[1])
                    try:
                        from_node = self.nodes[int(line[4])]
                        to_node = self.nodes[int(line[5])]
                    except KeyError:
                        continue
                    self.links[id] = (line[1:], [from_node,to_node])
                    
                """ LINK COORDINATE """
                if status == "LinkCoordinate" and line[0] == "rec":
                    id = int(line[1])
                    #count = int(line[2])
                    x = float(line[3])
                    y = float(line[4])
                    try:
                        self.links[id][1].insert(-1,QgsPointXY(x,y))
                    except KeyError:
                        continue
                    
                    
                """ LINK USE"""
                if status == "LinkUse" and line[0] == "rec":
                    #use_id = line[1]
                    #link_id = line[2]
                    #self.use_to_link[use_id] = link_id
                    pass
                
                if status == "TurnEdge" and line[0] == "atr":
                    """ prepare the links """
                    for id,[attrs,line] in self.links.items():
                        fet = QgsFeature()
                        fet.setGeometry(QgsGeometry.fromPolylineXY(line))
                        fet.setAttributes(attrs)
                        self.link_features.append(fet)
                        
                        """ create routing graph entry """
                        vertex_id = self.graph.addVertex(QgsGeometry.fromPolylineXY(line).centroid().asPoint())
                        self.link_to_vertex[id] = vertex_id
                        self.vertex_to_link[vertex_id] = id
                        
                    link_pr.addFeatures(self.link_features)
                    self.link_features = []
                    
                if status == "TurnEdge" and line[0] == "rec":
                    """ create routing graph entry """
                    id = line[1]
                    from_link_id = int(line[2])
                    to_link_id = int(line[3])
                    vehicle_type = "{0:08b}".format(int(line[5]))
                    #distance = QgsGeometry.fromPolyline(self.links[from_link_id][1]).length()/2 + QgsGeometry.fromPolyline(self.links[to_link_id][1]).length()/2
                    try:
                        from_link = self.links[from_link_id]
                        to_link = self.links[to_link_id]
                    except KeyError:
                        continue
                    len_from_link = float(from_link[0][15])
                    len_to_link = float(to_link[0][15])
                    
                    weights = []
                    for i in range(1,4):
                        if int(vehicle_type[i*-1]) == 1:
                            if self.mode == 'traveltime':
                                if i == 1: # pedestrian
                                    speed_from_link = 5 # km/h 
                                    speed_to_link = 5
                                elif i == 2: # bike
                                    speed_from_link = 15
                                    speed_to_link = 15
                                elif i == 3: # car
                                    speed_from_link = max([0.1,float(from_link[0][5]),float(from_link[0][6])])
                                    speed_to_link = max([0.1,float(to_link[0][5]),float(to_link[0][6])])
                                minutes_from_link = len_from_link / (speed_from_link *1000/60)
                                minutes_to_link = len_to_link / (speed_to_link *1000/60)
                                traveltime = minutes_from_link/2 + minutes_to_link/2
                                weights.append(traveltime) 
                            elif self.mode == 'ambulance':
                                if i == 1: # pedestrian
                                    speed_from_link = 5 # km/h 
                                    speed_to_link = 5
                                elif i == 2: # bike
                                    speed_from_link = 15
                                    speed_to_link = 15
                                elif i == 3: # car
                                    speed_from_link = 1.33 * max([0.1,float(from_link[0][5]),float(from_link[0][6])])*1000/60
                                    speed_to_link = 1.33 * max([0.1,float(to_link[0][5]),float(to_link[0][6])])*1000/60
                                minutes_from_link = len_from_link / speed_from_link
                                minutes_to_link = len_to_link / speed_to_link
                                traveltime = minutes_from_link/2 + minutes_to_link/2
                                weights.append(traveltime)
                            else:
                                distance = len_from_link/2 + len_to_link/2
                                weights.append(distance)
                        else:
                            weights.append(9999999)
                    arc_id = edge_id = self.graph.addEdge(
                        self.link_to_vertex[from_link_id],
                        self.link_to_vertex[to_link_id],
                        weights
                        )
                    
                if status == "TurnUse":
                    """ not implemented yet """
                    print(str(datetime.now()) + " finishing up ")
                    return [node_layer, link_layer]
    
    def computeRoute(self,from_link,to_link,vehicle_type):
        """ computes the route for the given vehicle type and adds a route layer to the map """
        print('route from %s to %s' %(from_link,to_link))
        print(str(datetime.now()) + " started")
        from_id = self.link_to_vertex[from_link]
        to_id = self.link_to_vertex[to_link]
        
        (tree,cost) = QgsGraphAnalyzer.dijkstra(self.graph,from_id,vehicle_type)
        
        if tree[to_id] == -1:
            pass # since the id cannot be found in the tree 
        else:
            """ collect all the vertices from target to source """
            route_vertices = []
            curPos = to_id
            while (curPos != from_id):
                route_vertices.append(curPos)
                curPos = self.graph.edge(tree[curPos]).fromVertex()
        route_vertices.append(from_id)
        route_vertices.reverse()
        
        route_layer = QgsVectorLayer(
            "LineString?crs=epsg:4326&field=id:integer&index=yes", 
            "route", 
            "memory")
        route_pr = route_layer.dataProvider()
        for id in route_vertices:
            attrs,line = self.links[self.vertex_to_link[id]]
            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPolylineXY(line))
            fet.setAttributes(attrs)
            route_pr.addFeatures([fet])
        
        route_layer.updateExtents()
        QgsProject.instance().addMapLayer(route_layer)
        # style route layer
        symbol = route_layer.renderer().symbol()
        symbol.setColor(QColor.fromRgb(0, 225, 0))
        symbol.setWidth(1.75)
        route_layer.triggerRepaint()
        # store route layer
        self.route_layer = route_layer
        
        print(str(datetime.now()) + " finished")

    def computeCatchment(self,from_link,vehicle_type,r=0.020):
        """ computes the catchment zone for the given vehicle type and adds it to the map """
        print('catchment zone around %s with size %f' %(from_link,r))
        print(str(datetime.now()) + " started")
        from_id = self.link_to_vertex[from_link]
        
        upperBound = []
        withinBound = []
        i = 0
        (tree,cost) = QgsGraphAnalyzer.dijkstra(self.graph,from_id,vehicle_type)

        reachable_layer = QgsVectorLayer(
            "LineString?crs=epsg:4326&field=id:integer&field=cost:double&index=yes", 
            "reachable links", 
            "memory")
        reachable_pr = reachable_layer.dataProvider()
        
        while i < len(cost):
            if cost[i] > r and tree[i] != -1:
                outVertexId = self.graph.edge(tree[i]).toVertex()
                if cost[outVertexId] < r:
                    attrs,line = self.links[self.vertex_to_link[outVertexId]]
                    attrs.append(cost[outVertexId])
                    upperBound.append(i)
                    fet = QgsFeature()
                    fet.setGeometry(QgsGeometry.fromPolyline(line))
                    fet.setAttributes(attrs)
                    reachable_pr.addFeatures([fet])
            elif tree[i] != -1:
                withinBound.append(self.graph.edge(tree[i]).toVertex())
                withinBound.append(self.graph.edge(tree[i]).fromVertex())
            i = i + 1

        for id in withinBound:
            attrs,line = self.links[self.vertex_to_link[id]]
            attrs = [ attrs[0] ]
            attrs.append(float(cost[id]))
            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPolylineXY(line))
            fet.setAttributes(attrs)
            reachable_pr.addFeatures([fet])

        reachable_layer.updateExtents()
        QgsProject.instance().addMapLayer(reachable_layer)

        print(str(datetime.now()) + " finished")

    def computeNearestPOI(self,poi_links,vehicle_type,r=0.020):
        """ computes the catchment zone around POIs for the given vehicle type and adds it to the map """

        reachable_layers = {}
        reachable_costs = {}
        reachable_hulls = {}

        upperBounds = {}
        withinBounds = {}

        poi_layer = QgsVectorLayer(
            "Point?crs=epsg:4326&field=id:integer&index=yes", 
            "POIs", 
            "memory")
        poi_pr = poi_layer.dataProvider()

        num_costs = None
        poi_id = 0
        for from_link in poi_links:
            poi_id += 1
            from_id = self.link_to_vertex[from_link]

            """ Add to POI layer """
            attrs,line = self.links[from_link]
            attrs = [ poi_id ]
            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPolylineXY(line).centroid())
            fet.setAttributes(attrs)
            poi_pr.addFeatures([fet])

            print('catchment zone around POI %d with size %f' %(poi_id,r))
            print(str(datetime.now()) + " started")
            
            (tree,cost) = QgsGraphAnalyzer.dijkstra(self.graph,from_id,vehicle_type)
            reachable_costs[poi_id] = (tree,cost)
            num_costs = len(cost)
            print("%d # costs for poi %d " % (num_costs, poi_id))

            reachable_layer = QgsVectorLayer(
                "LineString?crs=epsg:4326&field=id:integer&field=cost:double&index=yes", 
                "reachable POI " + str(poi_id), 
                "memory")
            reachable_layers[poi_id] = reachable_layer
            upperBounds[poi_id] = []
            withinBounds[poi_id] = []

            print(str(datetime.now()) + " finished")
        
        i = 0
        while i < num_costs:
            poi_id = None
            min_cost = None
            # find POI for which cost of current index i is minimal
            for _poi_id in reachable_costs:
                if min_cost == None or min_cost > reachable_costs[_poi_id][1][i]:
                    min_cost = reachable_costs[_poi_id][1][i]
                    poi_id = _poi_id
            
            # find objects for min_cost POI
            reachable_layer = reachable_layers[poi_id]
            reachable_pr = reachable_layer.dataProvider()
            (tree,cost) = reachable_costs[poi_id]
            upperBound = upperBounds[poi_id]
            withinBound = withinBounds[poi_id]

            if cost[i] > r and tree[i] != -1:
                outVertexId = self.graph.edge(tree[i]).toVertex()
                if cost[outVertexId] < r:
                    upperBound.append(i)
                    self.__addFeatureToReachability(reachable_pr, outVertexId, cost[outVertexId])
            elif tree[i] != -1:
                toVertexId = self.graph.edge(tree[i]).toVertex()
                fromVertexId =  self.graph.edge(tree[i]).fromVertex()
                withinBound.append(toVertexId)
                withinBound.append(fromVertexId)
                self.__addFeatureToReachability(reachable_pr, toVertexId, cost[toVertexId])
                self.__addFeatureToReachability(reachable_pr, fromVertexId, cost[fromVertexId])
            i = i + 1

        print(str(datetime.now()) + " catchments finished")

        print("Generating concave hull for POI polygonal outlines")
        
        self.__cleanUpReachability()

        # add reacable layers to map
        for poi_id in reachable_layers:
            reachable_hulls[poi_id] = self.computeConcaveHull(reachable_layers[poi_id], 'Polygon POI %d' % (poi_id))
            reachable_layers[poi_id].updateExtents()
            QgsProject.instance().addMapLayer(reachable_layers[poi_id])
        
        # add poi layer to map
        poi_layer.updateExtents()
        QgsProject.instance().addMapLayer(poi_layer)

        # store for later removal
        self.reachable_layers = reachable_layers
        self.reachable_hulls = reachable_hulls
        self.poi_layer = poi_layer

        print(str(datetime.now()) + " all finished")

    def computeConcaveHull(self, layer, name):
        hull = processing.run("qgis:knearestconcavehull", {
            'INPUT': layer,
            'KNEIGHBORS': 3,
            'OUTPUT': 'memory:'+name
        })
        QgsProject.instance().addMapLayer(hull['OUTPUT'])
        return hull['OUTPUT']

    def __cleanUpReachability(self):
        # remove old reachability layers
        if self.reachable_layers:
            for poi_id in self.reachable_layers:
                try:
                    QgsProject.instance().removeMapLayer(self.reachable_layers[poi_id])
                except:
                    print('Error')
        self.reachable_layers = None
        
        # remove old hulls layers
        if self.reachable_hulls:
            for poi_id in self.reachable_hulls:
                try:
                    QgsProject.instance().removeMapLayer(self.reachable_hulls[poi_id])
                except:
                    print('Error')
        self.reachable_hulls = None
        
        # remove old hulls layers
        if self.reachable_hulls:
            for poi_id in self.reachable_hulls:
                try:
                    QgsProject.instance().removeMapLayer(self.reachable_hulls[poi_id])
                except:
                    print('Error')
        
        # remove old poi layer
        if self.poi_layer:
            try:
                QgsProject.instance().removeMapLayer(self.poi_layer)
            except:
                print('Error')
        self.poi_layer = None

    def __addFeatureToReachability(self, reachable_pr, id, cost):
        attrs,line = self.links[self.vertex_to_link[id]]
        attrs = [ attrs[0] ]
        attrs.append(float(cost))
        fet = QgsFeature()
        fet.setGeometry(QgsGeometry.fromPolylineXY(line))
        fet.setAttributes(attrs)
        reachable_pr.addFeatures([fet])
