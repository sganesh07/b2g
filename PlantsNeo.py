#!/usr/bin/env python
import json 
from json import dumps
import logging
import os
import neo4j 
from neo4j import GraphDatabase 
import re 

from flask import (
    Flask,
    g,
    request,
    Response,
)
from neo4j import (
    GraphDatabase,
    basic_auth,
)


app = Flask(__name__, static_url_path="/static/")

#url = os.getenv("NEO4J_URI", "neo4j+s://demo.neo4jlabs.com")
#url = os.getenv("NEO4J_URI", "bolt://localhost:7687")
#username = os.getenv("NEO4J_USER", "neo4j")
#password = os.getenv("NEO4J_PASSWORD", "b2g.com")
#neo4j_version = os.getenv("NEO4J_VERSION", "4")
#database = os.getenv("NEO4J_DATABASE", "neo4j")

url = os.getenv("NEO4J_URI", "neo4j+s://yourInstance.databases.neo4j.io:7687")
username = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "typeYourInstancePassword")
neo4j_version = os.getenv("NEO4J_VERSION", "4")
database = os.getenv("NEO4J_DATABASE", "neo4j")

port = os.getenv("PORT", 8080)

driver = GraphDatabase.driver(url, auth=basic_auth(username, password))


#def get_db():
 #   if not hasattr(g, "neo4j_db"):
  #      if neo4j_version.startswith("4"):
   #         g.neo4j_db = driver.session(database=database)
    #    else:
     #       g.neo4j_db = driver.session()
    #return g.neo4j_db

def get_db():
    if not hasattr(g, "neo4j_db"):
        if neo4j_version.startswith("4"):
            g.neo4j_db = driver.session()
        else:
            g.neo4j_db = driver.session()
    return g.neo4j_db
    
@app.teardown_appcontext
def close_db(error):
    if hasattr(g, "neo4j_db"):
        g.neo4j_db.close()

    
@app.route("/")
def get_index():
    return app.send_static_file("helloD3.v2.html")

@app.route("/getPlant", methods = ['GET','POST'])
def getPlant():
    db = get_db(); 
    query = request.args.get("pquery")
    jlinks = {"links":[]}
    print('Get Plant data for:',query) 
    query = query.lower()
    dct = [] 
    if (db): 
        sql = "match (a:Ailment)-[r:SOLVED_BY]->(p:Plant) where toLower(p.title)=\'"+query+"\' return a.title,r.Prep limit 20"
        plantData = db.run(sql)
        for node in plantData:
            ailment = node.value('a.title')
            cure = node.value('r.Prep')
            y = {"source":query, "target":ailment, "prep":cure}
            jlinks["links"].append(y)
        psql = "MATCH (p:Plant) where toLower(p.title)=\'"+query+"\' return properties(p) as prop"
        plantProps = db.run(psql) 
        if(plantProps):
            dct = plantProps.value('prop')
    if dct:
        print('len of plant properties output:',len(dct))
        for i in range(len(dct)):
            dct[i]=str(dct[i])
            temp=dct[i].replace("\'", "\"")
            dct[i]=json.loads(temp)
            
    db.close()
    print('sending so many objects for this plant:',len(jlinks))
    return Response(dumps({"links": jlinks, "plants":dct}),mimetype="application/json")




@app.route("/getA", methods = ['GET', 'POST'])
def getA():
    db = get_db()
     
    print('get A gets called to search for: ', request.args.get("aquery"))
    query = (request.args.get("aquery"))
    plants = ''
    q_=query 
    nodes = []
    ailment = []
    cure = []
    jlinks = {"links":[]}
    uniqueNodes = {"nodes":[]}
    uniquePlants = [] 
    prep=[]
    def work(tx, q_):
        print('q_ on the primary query:', q_)
        n = (tx.run("match (a:Ailment)-[r:SOLVED_BY]->(theCURE) where toLower(a.title) CONTAINS toLower($query) return a as ailment, theCURE, r.Prep LIMIT 10",{"query": q_}))
        return list(n) 
    try:
        q = request.args.get("aquery")
    except KeyError:
        print('key error')
        return ''
    else:
        db = get_db()
        nodes = db.read_transaction(work, q)
   
    #sql = "MATCH (movie:Movie) WHERE toLower(movie.title) CONTAINS toLower($query) RETURN movie"
    sql = "match (a:Ailment)-[:SOLVED_BY]->(theCURE) where toLower(a.title) CONTAINS toLower($query) return a, theCURE LIMIT 10",{"query": q_}
    #print(sql) 
    #with db as graphDB_Session:
    #    nodes = graphDB_Session.run(sql, q_=query)
    print("output:")
    for node in nodes:
        #print(node)
        ailment, cure, prep = prepare_links(node, ailment, cure, prep)

    counter = 0
    print('length of ailment:',len(ailment))
    print('length of cure:',len(cure))
    print('length of prep:', len(prep))
    
    for idx, value in enumerate(ailment):
        source = ailment[idx]['title']
        target = cure[idx]['title']
        concoction = prep[idx]
        y = {"source":str(source), "target":str(target), "prep":str(concoction)}
        jlinks["links"].append(y)
        
        if source not in uniqueNodes["nodes"]:
            uniqueNodes["nodes"].append(source)
        if target not in uniqueNodes["nodes"]: 
            uniqueNodes["nodes"].append(target)
            uniquePlants.append(target)
            
    #print(jlinks)    
    #print(uniqueNodes)
    dct = []
    for i in range(len(uniquePlants)):
        plants = plants+('p.title=\''+str(uniquePlants[i])+'\'')
        if i<(len(uniquePlants)-1):
            plants = plants+(' OR ')
    db.close()
    print('query to fetch plant info now has : ',plants)
    if (len(plants) > 0):
        db = get_db()
    else:
        print('nothing to fetch ... ')
    if (db and len(plants)>0):
        psql = 'MATCH (p:Plant) where '+plants+' return properties(p) as prop'
        plantNodes = db.run(psql)
        if (plantNodes):
            dct = plantNodes.value('prop')

    if dct:
        print(dct)
        print('len of plant properties output:',len(dct))
        for i in range(len(dct)):
            dct[i]=str(dct[i])
            temp=dct[i].replace("\'", "\"")
            dct[i]=json.loads(temp)
        
        print('plant properties going out:',dct) 
    
    # now get the larger list of plants 
    allPlants = []
    allNodes = [] 
    if (db):
        asql = 'MATCH (p:Plant) return p.title as aplants' 
        allPlants = db.run(asql) 
        if (allPlants):
            allNodes = allPlants.value('aplants') 
            print('all plant list going out:', allNodes)
            
    db.close()
    
    return Response(dumps({"allPlants": allNodes, "links": jlinks, "plants":dct}),mimetype="application/json")



def serialize_ailment(ailment):
    return {
        "title":ailment["title"]
    }
def serialize_cure(cure):
    return {
        "title":cure["title"]
    }


def prepare_links(node, ailment, cure, prep):
    #ailment.append(serialize_ailment(node.value("ailment")))
    ailment.append(node.value("ailment"))
    #cure.append(serialize_cure(node.value("theCURE")))
    cure.append(node.value("theCURE"))
    prep.append(node.value("r.Prep"))
    return ailment, cure, prep 

def build_links(result):
    return {
        
    }
def serialize_plant(plant):
    return {
        "English":plant["English"],
        "Title":plant["title"],
        "Family":palnt["family"]
    }

def serialize_ailment(ailment):
    return {
        "title":ailment["title"]
    }
   


if __name__ == "__main__":
    logging.root.setLevel(logging.INFO)
    
    #app = Flask(__name__, static_url_path='/')
    logging.info("Starting on port %d, database is at %s, static url path", port, static_url_path)
    app.run(port=port)
