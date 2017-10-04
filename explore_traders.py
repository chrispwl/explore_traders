#!/usr/bin/env python
from json import dumps
from flask import Flask, g, Response, request, current_app
<<<<<<< Updated upstream
# from werkzeug.local import LocalProxy
=======
>>>>>>> Stashed changes
import sys, csv, utils
import networkx as nx
# from neo4j.v1 import GraphDatabase, basic_auth

app = Flask(__name__, static_url_path='/static/')
print("Loading app", app.name)
<<<<<<< Updated upstream
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
=======
# @app.teardown_appcontext
# def close_db(error):
#     # print('App teardown', app.name)
>>>>>>> Stashed changes

def _get_top_nodes(Gph, company, howmany=2):
    """Generate top-most commodities: returns sorted list of (u, v, d)"""
    all_edges = Gph.edges(nbunch=[company], data='monthcount')
<<<<<<< Updated upstream
    sorted_edges = sorted(all_edges, key=lambda tup: -int(tup[howmany]))
=======
    lim = howmany
    if (lim > len(all_edges)): lim = len(all_edges)
    sorted_edges = sorted(all_edges, key=lambda tup: -int(tup[lim]))
>>>>>>> Stashed changes
    return sorted_edges

@app.route("/")
def get_index():
    return app.send_static_file('index.html')

def serialize_company(company):
    x = NETX_DB[company]
    return {
    'name': company,
    'count': len(x)
    }

def serialize_cmdty(trade):
    x = NETX_DB.get_edge_data(trade[0], trade[1])
    return {
        'comcode': trade[1],
        'direction': x['direction'],
        'monthcount': x['monthcount']
    }

@app.route("/graph")
def get_graph():
<<<<<<< Updated upstream
    global NETX_DB
    Gph = NETX_DB
    nodes = []
    rels = []
    tops = [t for t in _get_top_nodes(Gph, 'GODIVA UK LIMITED')]
    # print(tops)
=======
    """
    Returns subgraph surrounding the target company (input to be implemented)
    Subgraph contains
    -- commodities exported or imported by the target company
    -- companies that share at least the TOP [two] commodities of the target
    in either direction (top for target, not necessarily the other company)
    -- commodities exported or imported by those companies
    """
    global NETX_DB
    nodes = []
    rels = []
    tops = [t for t in _get_top_nodes(NETX_DB, 'GODIVA UK LIMITED')]
>>>>>>> Stashed changes
    if len(tops) > 1:
        top1, top2 = tops[:2]
    else:
        raise NotImplementedError
    common_HS = [top1[1], top2[1]]
<<<<<<< Updated upstream
    names = [n for n in nx.common_neighbors(Gph, common_HS[0], common_HS[1])]
    # retdict = {}
=======
    names = [n for n in nx.common_neighbors(NETX_DB, common_HS[0], common_HS[1])]
>>>>>>> Stashed changes
    i = 0
    for name in names:
        if i < 20:
            nodes.append({"title": name, "label": "Company"})
            target = i
            i += 1
<<<<<<< Updated upstream
            cmdties = dict([(c[1], c[2]) for c in _get_top_nodes(Gph, name)])
=======
            cmdties = dict([(c[1], c[2]) for c in 
                _get_top_nodes(NETX_DB, name, howmany=2)])
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
    # print('in get_search g has', dir(g))
=======
    """Returns other companies trading similar commodities"""
>>>>>>> Stashed changes
    try:
        q = request.args['q']
    except KeyError:
        return []
    else:
<<<<<<< Updated upstream
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
=======
        global NETX_DB
        print('searching for other companies trading similar comcodes as', q)
        tops = [t for t in _get_top_nodes(NETX_DB, q, howmany=2)]
        if len(tops) > 1:
            top1, top2 = tops[:2]
        else:
            print('Not enough comcodes found, searching by SIC code instead')
            raise NotImplementedError
        common_HS = [top1[1], top2[1]]
        names = [n for n in nx.common_neighbors(NETX_DB, common_HS[0], common_HS[1])]
        return Response(dumps([serialize_company(name) for name in names]),
                        mimetype="application/json")


@app.route("/company/<name>")
def get_company(name):
    """Returns the commodities exportd by a company"""
    print('get commodities for company {}'.format(name), end='\n')
    global NETX_DB
    result = {}
    if NETX_DB.has_node(name):
        trades_list = [t for t in NETX_DB.edges(name)]
    return Response(dumps({
        "name": name,
        "cast": [serialize_cmdty(trade) for trade in trades_list]
        }), mimetype="application/json")
>>>>>>> Stashed changes

# print('before name=main, g has', dir(g))

if __name__ == '__main__':
    print('Loading graph to memory...')
    NETX_DB = nx.Graph()
    NETX_DB = nx.read_gml('impex_full.graphml')
    print('loaded', NETX_DB.order(), 'nodes and', NETX_DB.size(), 'edges')
    host='127.0.0.1'
    port=8080
    print('Server running on http://{0}:{1}...'.format(host, port))
    app.run(host=host, port=port)  # , debug=True, use_reloader=False

