#!/usr/bin/env python
from json import dumps
from flask import Flask, g, Response, request, current_app
import sys, csv, utils
import networkx as nx

app = Flask(__name__, static_url_path='/static/')
print("Loading app", app.name)
# @app.teardown_appcontext
# def close_db(error):
#     # print('App teardown', app.name)

def _get_top_nodes(Gph, company, howmany=2):
    """Generate top-most commodities: returns sorted list of (u, v, d)"""
    all_edges = Gph.edges(nbunch=[company], data='monthcount')
    lim = howmany
    if (lim > len(all_edges)): lim = len(all_edges)
    sorted_edges = sorted(all_edges, key=lambda tup: -int(tup[lim]))
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
    if len(tops) > 1:
        top1, top2 = tops[:2]
    else:
        raise NotImplementedError
    common_HS = [top1[1], top2[1]]
    names = [n for n in nx.common_neighbors(NETX_DB, common_HS[0], common_HS[1])]
    i = 0
    for name in names:
        if i < 20:
            nodes.append({"title": name, "label": "Company"})
            target = i
            i += 1
            cmdties = dict([(c[1], c[2]) for c in 
                _get_top_nodes(NETX_DB, name, howmany=2)])
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
    """Returns other companies trading similar commodities"""
    try:
        q = request.args['q']
    except KeyError:
        return []
    else:
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

if __name__ == '__main__':
    print('Loading graph to memory...')
    NETX_DB = nx.Graph()
    NETX_DB = nx.read_gml('impex_full.graphml')
    print('loaded', NETX_DB.order(), 'nodes and', NETX_DB.size(), 'edges')
    host='127.0.0.1'
    port=8080
    print('Server running on http://{0}:{1}...'.format(host, port))
    app.run(host=host, port=port)  # , debug=True, use_reloader=False

