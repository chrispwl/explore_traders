#!/usr/bin/env python
from json import dumps

from flask import Flask, g, Response, request
import sys, csv, utils
# import networkx as nx
from neo4j.v1 import GraphDatabase, basic_auth #, ResultError

app = Flask(__name__, static_url_path='/static/')
# basic auth:
uri = "bolt://127.0.0.1:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "TIComphoeLON"))

def get_db():
    if not hasattr(g, 'neo4j_db'):
        g.neo4j_db = driver.session()
    return g.neo4j_db
    # """Reads in from tab separated file"""
    # if not hasattr(g, 'netx_db'):
    #     Gph = nx.Graph()
    #     for action in ['Ex', 'Im']:
    #         sourcedata = action+'port_combined_summary_test.csv'
    #         with open(sourcedata, 'r') as tsvfile:
    #             tsvin = csv.reader(tsvfile, delimiter='\t')
    #             # Adjust row[] indices depending on if sourcedata has
    #             # EITHER 5, 3, 5, 3, 7
    #             # [' CompanyNumber', 'RegAddress.PostCode', 'Postcode', 'HScode',
    #             # 'co_name', 'Name', 'SICCode.SicText_1', 'MonthCount']
    #             # OR 2, 1, 2, 1, 3 for
    #             # ['Postcode', 'HScode', 'Name', 'MonthCount']
    #             for i, row in enumerate(tsvin):
    #                 Gph.add_node(row[2], type='Name')
    #                 Gph.add_node(row[1], type='Commodity')
    #                 Gph.add_edge(row[2], row[1], 
    #                     direction=action+'ported', monthcount=row[3])
    #     g.netx_db = Gph
    # return g.netx_db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'neo4j_db'):
        g.neo4j_db.close()
    # if hasattr(g, 'netx_db'):
    #     g.netx_db = None

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
    db = get_db()
    results = db.run("MATCH (c:Comcode)<-[:EXPORTED]-(n:Company) "
             "RETURN n.name as movie, collect(c.comcode) as cast "
             "LIMIT {limit}", {"limit": request.args.get("limit", 100)})
    # print('searching for comcodes traded by', rg['name'])
    # tops = [t for t in get_top_nodes(Gph, rg['name'])]
    # if len(tops) > 1:
    #     top1, top2 = tops[:2]
    # else:
    #     raise NotImplementedError
    # common_HS = [top1[1], top2[1]]
    # names = [n for n in nx.common_neighbors(Gph, common_HS[0], common_HS[1])]
    # retdict = {}
    # for name in names:
    #     cmdties = dict([(c[1], c[2]) for c in get_top_nodes(Gph, name)])
    #     retdict[name] = cmdties
    nodes = []
    rels = []
    i = 0
    for j, record in enumerate(results):
        if j < 100:
            nodes.append({"title": record["movie"], "label": "movie"})
            target = i
            i += 1
            for name in record['cast']:
                actor = {"title": name, "label": "actor"}
                try:
                    source = nodes.index(actor)
                except ValueError:
                    nodes.append(actor)
                    source = i
                    i += 1
                rels.append({"source": source, "target": target})
    return Response(dumps({"nodes": nodes, "links": rels}),
                    mimetype="application/json")


@app.route("/search")
def get_search():
    try:
        q = request.args['q']
    except KeyError:
        return []
    else:
        db = get_db()
        results = db.run("MATCH (n:Company) "
                 "WHERE n.name =~ {title} "
                 "RETURN n", {"title": "(?i).*" + q + ".*"}
        )
        # print('searching for comcodes traded by', rg['name'])
        # tops = [t for t in get_top_nodes(Gph, rg['name'])]
        # if len(tops) > 1:
        #     top1, top2 = tops[:2]
        # else:
        #     print('Not enough comcodes found, searching by SIC code instead')
        #     print('SIC-based search not implemented')
        #     raise NotImplementedError
        # common_HS = [top1[1], top2[1]]
        # print('Identified', common_HS[0], common_HS[1], 'as two top comcodes')
        # names = [n for n in nx.common_neighbors(Gph, common_HS[0], common_HS[1])]
        # retdict = {}
        # for name in names:
        #     cmdties = dict([(c[1], c[2]) for c in get_top_nodes(Gph, name)])
        #     retdict[name] = cmdties
        # return Response(dumps({'competitors': dict(retdict)}),
        #     mimetype="application/json")
        return Response(dumps([serialize_company(record['n']) for record in results]),
                        mimetype="application/json")


@app.route("/movie/<name>")
def get_movie(name):
    db = get_db()
    results = db.run("MATCH (n:Company {name:{name}}) "
             "OPTIONAL MATCH (n)-[r]->(c:Comcode) "
             "RETURN n.name as name,"
             "collect([c.comcode, "
             "         lower(type(r)), r.monthcount]) as cast "
             "LIMIT 1", {"name": name})

    result = results.single();
    return Response(dumps({"name": result['name'],
                           "cast": [serialize_cmdty(member)
                                    for member in result['cast']]}),
                    mimetype="application/json")


if __name__ == '__main__':
    print('Server running on localhost:8080 ...')
    app.run(port=8080, debug=True)