#!/usr/bin/env python
from json import dumps
from flask import Flask, g, Response, request, current_app
# from werkzeug.local import LocalProxy
import sys, csv, utils
import networkx as nx
from neo4j.v1 import GraphDatabase, basic_auth

app = Flask(__name__, static_url_path='/static/')
print("Loading app", app.name)
print('Loading graph to memory...')
NETX_DB = nx.Graph()
NETX_DB = nx.read_gml('impex_full.graphml')
print('loaded', NETX_DB.order(), 'nodes and', NETX_DB.size(), 'edges')

# basic auth for neo4j db:
uri = "bolt://127.0.0.1:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "TIComphoeLON"))
def get_n4jdb():
    if not hasattr(g, 'neo4j_db'):
        g.neo4j_db = driver.session()
    return g.neo4j_db

@app.teardown_appcontext
def close_db(error):
    print('App teardown', app.name)
    if hasattr(g, 'neo4j_db'):
        g.neo4j_db.close()

def _get_top_nodes(Gph, company, howmany=2):
    """Generate top-most commodities: returns sorted list of (u, v, d)"""
    all_edges = Gph.edges(nbunch=[company], data='monthcount')
    sorted_edges = sorted(all_edges, key=lambda tup: -int(tup[howmany]))
    return sorted_edges

@app.route("/")
def get_index():
    return app.send_static_file('index.html')

def serialize_company(company):
    return {
        'id': company['id'],
        'name': company['name'],
        'postcode': company['postcode']
    }

def serialize_cmdty(cast):
    return {
        'comcode': cast[0],
        'direction': cast[1],
        'monthcount': cast[2]
    }

@app.route("/graph")
def get_graph():
    global NETX_DB
    Gph = NETX_DB
    nodes = []
    rels = []
    tops = [t for t in _get_top_nodes(Gph, 'GODIVA UK LIMITED')]
    # print(tops)
    if len(tops) > 1:
        top1, top2 = tops[:2]
    else:
        raise NotImplementedError
    common_HS = [top1[1], top2[1]]
    names = [n for n in nx.common_neighbors(Gph, common_HS[0], common_HS[1])]
    # retdict = {}
    i = 0
    for name in names:
        if i < 20:
            nodes.append({"title": name, "label": "Company"})
            target = i
            i += 1
            cmdties = dict([(c[1], c[2]) for c in _get_top_nodes(Gph, name)])
            for cmdty in cmdties:
                hsnode = {"title": cmdty, "label": "commodity"}
                try:
                    source = nodes.index(hsnode)
                except ValueError:
                    nodes.append(hsnode)
                    source = i
                    i += 1
                rels.append({"source": source, "target": target})
    print('sending json for background graph...')
    return Response(dumps({"nodes": nodes, "links": rels}),
        mimetype="application/json")


@app.route("/search")
def get_search():
    # print('in get_search g has', dir(g))
    try:
        q = request.args['q']
    except KeyError:
        return []
    else:
        n4db = get_n4jdb()
        results = n4db.run("MATCH (n:Company) "
                 "WHERE n.name =~ {coname} "
                 "RETURN n", {"coname": "(?i).*" + q + ".*"}
        )
        # print('searching for comcodes traded by', q)
        # tops = [t for t in _get_top_nodes(db, 'GODIVA%20LIMITED')]
        # if len(tops) > 1:
        #     top1, top2 = tops[:2]
        # else:
        #     print('Not enough comcodes found, searching by SIC code instead')
        #     print('SIC-based search not implemented')
        #     raise NotImplementedError
        # common_HS = [top1[1], top2[1]]
        # print('Identified', common_HS[0], common_HS[1], 'as two top comcodes')
        # names = [n for n in nx.common_neighbors(db, common_HS[0], common_HS[1])]
        # retdict = {}
        # for name in names:
        #     cmdties = dict([(c[1], c[2]) for c in _get_top_nodes(db, name)])
        #     retdict[name] = cmdties
        # return Response(dumps({'competitors': dict(retdict)}),
        #     mimetype="application/json")
        return Response(dumps([serialize_company(record['n']) for record in results]),
                        mimetype="application/json")


@app.route("/movie/<name>")
def get_movie(name):
    n4db = get_n4jdb()
    results = n4db.run("MATCH (n:Company {name:{name}}) "
             "OPTIONAL MATCH (n)-[r]->(c:Comcode) "
             "RETURN n.name as name,"
             "collect([c.comcode, "
             "         lower(type(r)), r.monthcount]) as cmdties "
             "LIMIT 1", {"name": name})
    result = results.single();
    global NETX_DB
    Gph = NETX_DB
    co_name = Gph.nodes(name)

    return Response(dumps({"name": result['name'],
                           "cast": [serialize_cmdty(member)
                                    for member in result['cmdties']]}),
                    mimetype="application/json")

# print('before name=main, g has', dir(g))

if __name__ == '__main__':
    host='127.0.0.1'
    port=8080
    print('Server running on http://{0}:{1}...'.format(host, port))
    app.run(host=host, port=port)  # , debug=True, use_reloader=False

