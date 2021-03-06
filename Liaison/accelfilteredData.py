import os
import sys
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../updews-pycodes/Analysis/'))
if not path in sys.path:
   sys.path.insert(1, path)
del path
from querySenslopeDb import *
import filterSensorData
import pandas as pd
import numpy as np
from datetime import timedelta as td
from datetime import datetime as dt
import sqlalchemy
from sqlalchemy import create_engine
import sys
import requests 

site_column = sys.argv[1]
start_date = sys.argv[2]
end_date = sys.argv[3]
node_id = sys.argv[4]
version = sys.argv[5]
#accel_id = sys.argv[6]

#site_column = "plab"
#start_date = "2017-07-12"
#end_date = "2017-07-13"
#node_id = 1
#version = 1

# engine = create_engine('mysql+pymysql://updews:october50sites@127.0.0.1/senslopedb')
# query = "SELECT timestamp,id,msgid,xvalue,yvalue,zvalue,batt,IF (msgid in (11,32),1,2) as 'accel' FROM senslopedb.%s where id = '%s'and msgid ='%s' and timestamp between '%s ' and '%s'" % (site,nid,ms,fdate,tdate)
# df = pd.io.sql.read_sql(query,engine)
# df.columns = ['ts','id','msgid','x','y','z','v','accel']
# df['name'] = site
# df_filt = filterSensorData.applyFilters(df, orthof=True, rangef=True, outlierf=True)
# dfajson = df_filt.reset_index().to_json(orient='records',date_format='iso')
# dfajson = dfajson.replace("T"," ").replace("Z","").replace(".000","")
# print dfajson

def queryFilteredAccel( query, engine, version ):
    df = pd.io.sql.read_sql(query, engine)  
    
    if version == 1:
        df.columns = ['ts', 'id', 'x', 'y', 'z', 'accel']
    else:
        df.columns = ['ts', 'id', 'x', 'y', 'z', 'batt', 'accel']
    
    df['name'] = site_column
    df_filt = filterSensorData.applyFilters(df, orthof=True, rangef=True, outlierf=True)
    dfajson = df_filt.reset_index()
    #dfajson = df_filt.reset_index().to_json(orient='records',date_format='iso')
    #dfajson = dfajson.replace("T"," ").replace("Z","").replace(".000","")
    return dfajson;

engine = create_engine('mysql+pymysql://updews:october50sites@127.0.0.1/senslopedb')
query_base = "SELECT timestamp, id, xvalue, yvalue, zvalue"
accel_id = []
filtered_data = pd.DataFrame()

if version == 1:
    query = query_base + ", 1 as accel FROM senslopedb.%s where id = '%s' and timestamp between '%s' and '%s'" % (site_column, node_id, start_date, end_date)
    c = queryFilteredAccel( query, engine, version );
    filtered_data['v1'] = [c]
else:
    if version == 2:
        accel_id = [32, 33]
    else:
        accel_id = [11, 12]
    
    for a_id in accel_id:
        query = query_base + ", batt, msgid AS accel FROM senslopedb.%s where id = '%s' and msgid = '%s' and timestamp between '%s ' and '%s'" % (site_column, node_id, a_id, start_date, end_date)
        c = queryFilteredAccel( query, engine, version );
        filtered_data[a_id] = [c]
    
print filtered_data.to_json(orient='records',date_format='iso').replace("T"," ").replace("Z","").replace(".000","")
    
#query = "SELECT timestamp,id,msgid,xvalue,yvalue,zvalue,batt,IF (msgid in (11,32),1,2) as 'accel' FROM senslopedb.%s where id = '%s'and msgid ='%s' and timestamp between '%s ' and '%s'" % (site,nid,ms,fdate,tdate)
#df = pd.io.sql.read_sql(query,engine)
#df.columns = ['ts','id','msgid','x','y','z','v','accel']
#df['name'] = site
#df_filt = filterSensorData.applyFilters(df, orthof=True, rangef=True, outlierf=True)
#dfajson = df_filt.reset_index().to_json(orient='records',date_format='iso')
#dfajson = dfajson.replace("T"," ").replace("Z","").replace(".000","")
#print dfajson