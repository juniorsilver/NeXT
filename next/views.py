import os
import csv

from pyramid.response import Response
from pyramid.httpexceptions import HTTPNotFound
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPForbidden
from pyramid.url import route_url
from geoalchemy import WKTSpatialElement

from next.models import Scenario
from next.models import Node
from next.models import NodeType
from next.models import DBSession


def get_object_or_404(cls, id):
    session = DBSession()
    obj = session.query(cls).get(id)
    if obj is not None:
        return obj
    else:
        raise HTTPNotFound('Unable to locate class:%s id:%s' % (cls, id))


@view_config(route_name='index', renderer='index.mako')
def index(request):
    session = DBSession()
    return {'scenarios': session.query(Scenario).all()}


def csv_to_nodes(request, csv_file, scenario, node_type):
    """Function to read a csv file and add the contents of a csv file to
    the nodes table.

    Arguments:
        csv_reader:
        scenario:
        node_type:
    Returns a list of nodes to be added.

    """
    c = []  # collector list for all of the nodes.
    # get the raw file data and write it to tmp file
    raw_file = csv_file.file
    filename = csv_file.filename
    tmp_file_path = os.path.join('/tmp', filename)
    tmp_file = open(tmp_file_path, 'wb')
    tmp_file.write(raw_file.read())
    tmp_file.close()
    # open the csv reader
    # using rU because of encoding issues with windows
    csv_reader = csv.reader(open(tmp_file_path, 'rU'))
    for row in csv_reader:
        geom = WKTSpatialElement('POINT(%s %s)' % (row[0], row[1]))

        if len(row) == 3:
            # do we have a csv file with a weight ?
            # if so, add it to the node
            node = Node(geom, row[2], node_type, scenario)
            c.append(node)
        elif len(row) == 2:
            # else don't add a weight to the node
            node = Node(geom, 1, node_type, scenario)
            c.append(node)

    return c


@view_config(route_name='create-scenario', renderer='create-scenario.mako')
def create_scenario(request):
    """
    1. look up data from html form
    2. create new scenario (allow use to give name)
    3. upload two csv files
      -> import the csv files as nodes
      -> assgin types
    4. run scenario
    """
    session = DBSession()
    if request.method == 'POST':

        # query for the two node types we are currently using.
        pop_type = session.query(NodeType)\
            .filter_by(name=u'population').first()

        fac_type = session.query(NodeType)\
            .filter_by(name=u'facility').first()

        # TODO remove these asserts
        assert pop_type
        assert fac_type

        name = request.POST['name']
        # make sure that we have a name
        # fix me
        assert len(name) != 0

        sc = Scenario(name)
        session.add(sc)
        pop_nodes = csv_to_nodes(request, request.POST['pop-csv'],
                                        sc, pop_type)
        fac_nodes = csv_to_nodes(request, request.POST['fac-csv'],
                                      sc, fac_type)

        # TODO, double check to make sure these are being added in
        # batch mode.
        session.add_all(pop_nodes)
        session.add_all(fac_nodes)

        # Chris you are going to hate me... except that I need the
        # sc.id to send the user to. If I don't call flush, I get a None.
        # TODO... FIX this.
        session.flush()
        # send the user to the show page right now
        return HTTPFound(location=request.route_url('show-scenario', id=sc.id))

    elif request.method == 'GET':
        return {}
    else:
        return HTTPForbidden()


def run_scenario(request):
    """
    """
    # scenario = get_object_or_404(Scenario, request.matchdict['id'])
    return Response('You can\'t run these things yet !')


@view_config(route_name='show-scenario', renderer='show-scenario.mako')
def show_scenario(request):

    session = DBSession()

    scenario = get_object_or_404(Scenario, request.matchdict['id'])
    nodes = session.query(Node).filter_by(scenario=scenario)

    if scenario.has_run():
        return {'scenario': scenario, 'nodes': nodes }
    else:
        return HTTPFound(route_url('run-scenario', id=scenario.id))