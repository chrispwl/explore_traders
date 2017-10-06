#!/usr/bin/env python
from json import dumps
from flask import Flask, Response, request
import networkx as nx
import utils

app = Flask(__name__, static_url_path='/static/')
print("Loading app", app.name)

# @app.teardown_appcontext
# def close_db(error):
#     global NETX_DB
#     del NETX_DB
#     print('App teardown', app.name)

@app.route("/")
def get_index():
    return app.send_static_file('index.html')

@app.route("/descriptions")
def get_descriptions():
    code = request.args['cn1']
    print("checking for", code)
    return utils.get_desc_by_CN(code)['Self-Explanatory text (English)'].values[0]

def dir_edge_count(node, direction):
    global NETX_DB
    dir_edge_list = [n for n in NETX_DB[node] if (
        NETX_DB.edge[node][n]['direction'] == direction
        ) ]
    return len(dir_edge_list)

def serialize_company(company, direction='focal'):
    global NETX_DB
    if (direction == 'focal'):
        x = len(NETX_DB[company])
    else:
        x = len(NETX_DB[company]) #dir_edge_count(company, direction) too slow
    return {
    'type': "company",
    'direction': direction,
    'size': x,
    'size_metric': 'HS code diversity',
    'name': company,
    'postcode': 'AB12 CDE'
    }

def serialize_cmdty(good, direction):
    return {
    'type': "hscode",
    'direction': direction,
    'size': len(NETX_DB[good]), #dir_edge_count(good, direction), too slow
    'size_metric': '# of companies that traded this', #({} this)'.format(direction),
    'name': good
    }

def common_goods_traded(Gph, goods_list, direction, exclude=None):
    """
    Variant of nx.common_neighbors(G, u, v)
    Return the companies with TWO common goods
    traded in the SAME DIRECTION (import or export)
    """
    for x in goods_list:
        if x not in Gph: raise nx.NetworkXError('{} is not in the graph.'.format(x))
    
    # Returns a generator
    if (len(goods_list) == 1):
        u = goods_list[0]
        return (
            x for x in Gph[u] if (
                (x is not u) and
                (Gph.edge[u][x]['direction'] == direction) and
                (x != exclude)
                )
            )
    elif (len(goods_list) == 2):
        u, v = goods_list
        return (
            x for x in Gph[u] if (
                (x in Gph[v]) and 
                (x not in (u, v)) and
                (Gph.edge[u][x]['direction'] == direction) and
                (Gph.edge[v][x]['direction'] == direction) and
                (x != exclude)
                )
            )
    elif (len(goods_list) == 3):
        u, v, w = goods_list
        return (
            x for x in Gph[u] if (
                (x in Gph[v]) and
                (x in Gph[w]) and
                (x not in (u, v, w)) and
                (
                    (Gph.edge[u][x]['direction'] == direction) or
                    (Gph.edge[v][x]['direction'] == direction) or
                    (Gph.edge[w][x]['direction'] == direction) 
                ) and
                (x != exclude)
                )
            )
    else:
        raise NotImplementedError
    

def _get_top_edges(Gph, company, howmany=None):
    """
    Commodities with the most months: returns sorted list of (u, v, data)
    """
    if company in Gph:
        all_edges = Gph.edges(nbunch=[company], data=True)
        sorted_edges = sorted(
            all_edges, 
            key=lambda tup: int(tup[2]['monthcount']),
            reverse=True
            )
        if howmany is None:
            return sorted_edges
        elif len(sorted_edges) < howmany:
            print(company, 'only trades', Gph[company])
            return sorted_edges
        else:
            results_list = sorted_edges[:howmany]
            return results_list
    else:
        print(company, 'not in database')
        raise NotImplementedError

@app.route("/graph")
def get_graph():
    """
    Returns subgraph surrounding the target company (input to be implemented)
    Subgraph contains
    -- commodities exported or imported by the target company
    -- companies that share at least the TOP [two] commodities of the target
    in each direction (top for target, not necessarily the other company)
    """
    focus_co = request.args['q']
    num_nodes = int(request.args['n'])
    print('Preparing graph for {0} with {1} common goods'.format(focus_co, num_nodes))
    global NETX_DB
    nodes = []
    rels = []
    i =0
    # Add the focal company
    nodes.append(serialize_company(focus_co, direction='focal'))
    i += 1
    # Goods traded by focal company
    focal_co_goods = NETX_DB.edges(nbunch=[focus_co], data=True)
    for cmdty in focal_co_goods:
        hsnode = serialize_cmdty(good=cmdty[1], direction=cmdty[2]['direction'])
        try:
            target = nodes.index(hsnode)
        except ValueError:
            nodes.append(hsnode)
            target = i
            i += 1
        rels.append({"target": target, "source": 0})
        # print(cmdty[1], end=' ')
    # print(' ')
    focal_co_goods_sorted = [
        (c[1], c[2]['monthcount']) for r, c in 
        enumerate(_get_top_edges(NETX_DB, focus_co)) if r < 10
        ]
    # print(focal_co_goods_sorted)
    print('top goods:')
    [print(c[0], c[1], utils.get_desc_by_CN(c[0])['Self-Explanatory text (English)'
        ].values[0]) for c in focal_co_goods_sorted]
    # Just the top goods from focal_co_gods
    common_HS = [tup[1] for tup in _get_top_edges(NETX_DB, focus_co, howmany=num_nodes)]
    print('checking:')
    [print(code, utils.get_desc_by_CN(code)['Self-Explanatory text (English)'].values[0]
        ) for code in common_HS]
    # Companies trading at least two goods in the SAME DIRECTION as the focal company
    importers = [name for name in common_goods_traded(NETX_DB, common_HS, 
        direction='Imported', exclude=focus_co)]
    exporters = [name for name in common_goods_traded(NETX_DB, common_HS, 
        direction='Exported', exclude=focus_co)]

    # Dummy list for finding companies that import OR export these goods
    # MAY INCLUDE GOODS THAT ARE NOT TRADED BY ANY RELATED COMPANIES
    goods_to_show = [serialize_cmdty(n[1], 'Imported') for n in focal_co_goods]
    [goods_to_show.append(serialize_cmdty(n[1], 'Exported')) for n in focal_co_goods]
    for direction in ['Imported', 'Exported']:
        # Related companies and the goods they trade
        if (direction=='Imported'):
            names_list = importers
        else:
            names_list = exporters
        for name in names_list:
            # if i < 5000:
            conode = serialize_company(company=name, direction=direction)
            try:
                source = nodes.index(conode)
                # print('\n_', end='')
                # print(i, conode['name'], end=' ')
            except ValueError:
                nodes.append(conode)
                source = i
                i += 1
                # print('\n+', end=' ')
                # print(i, conode, end=' ')
            for cmdty in NETX_DB[name]:
                hsnode = serialize_cmdty(good=cmdty, direction=direction)
                if hsnode in goods_to_show:
                    # print(hsnode, end=' ')
                    # check if the commodity is already there
                    # on the particular import / export side
                    try:
                        target = nodes.index(hsnode)
                    except ValueError:
                        nodes.append(hsnode)
                        target = i
                        i += 1
                        # print('+', end=' ')
                        # print(i, hsnode['name'], end=' ')
                    # else:  # executes if try statement raised no exception
                    rels.append({"target": target, "source": source})
                    # print('.', end=' ')
                    # print(hsnode['name'], end=' ')
                # else:
                #     print('-', end='')
    print('\nSending json for background graph...')
    return Response(dumps({"nodes": nodes, "links": rels}),
        mimetype="application/json")

if __name__ == '__main__':
    print('Loading graph to memory...')
    NETX_DB = nx.Graph()
    NETX_DB = nx.read_gml('impex_full.graphml')
    print('loaded', NETX_DB.order(), 'nodes and', NETX_DB.size(), 'edges')
    host='127.0.0.1'
    port=8081
    print('Server running on http://{0}:{1}...'.format(host, port))
    app.run(host=host, port=port)  # , debug=True, use_reloader=False