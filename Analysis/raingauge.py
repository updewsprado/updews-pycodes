from datetime import datetime
import pandas as pd
import numpy as np
import querySenslopeDb as q
from sqlalchemy import create_engine
import requests


def to_MySQL(df, table_name):
    engine = create_engine('mysql://'+q.Userdb+':'+q.Passdb+'@'+q.Hostdb+':3306/'+q.Namedb)
    if table_name == 'rain_gauge':
        site = df['dev_id'].values[0]
    elif table_name == 'rain_props':
        site = df['name'].values[0]
    try:
        df.to_sql(name = table_name, con = engine, if_exists = 'append', schema = q.Namedb, index = False)
        print site, ': success'
    except:
        try:
            db, cur = q.SenslopeDBConnect(q.Namedb)
            if table_name == 'rain_gauge':
                query = "DELETE FROM %s WHERE dev_id = '%s'" %(table_name, site)
            elif table_name == 'rain_props':
                query = "DELETE FROM %s WHERE name = '%s'" %(table_name, site)
            cur.execute(query)
            db.commit()
            db.close()
            df.to_sql(name = table_name, con = engine, if_exists = 'append', schema = q.Namedb, index = False)
            print site, ': updated'
        except:
            print site, ': error'

def updateDB():
    r = requests.get('http://weather.asti.dost.gov.ph/web-api/index.php/api/devices', auth=('phivolcs.ggrdd', 'PhiVolcs0117'))    
    NOAHRG = pd.DataFrame(r.json())
    NOAHRG = NOAHRG[NOAHRG['sensor_name'].str.contains('rain', case = False)]
    NOAHRG = NOAHRG.loc[(NOAHRG.longitude != 0) & (NOAHRG.latitude != 0)]
    NOAHRG = NOAHRG[['dev_id', 'longitude', 'latitude', 'location', 'province']]
    id_NOAHRG = NOAHRG.groupby('dev_id')
    id_NOAHRG.apply(to_MySQL, table_name = 'rain_gauge')

################################################################################

def SiteCoord():
    RGdf = q.GetRainProps('rain_props')
    RGdf = RGdf.loc[RGdf.name != 'msl']
    
    RG = list(RGdf.rain_arq.dropna().apply(lambda x: x[:len(x)-1]))
    RG = '|'.join(RG)
    query = "SELECT * FROM senslopedb.site_column where name REGEXP '%s'" %RG
    RGCoord = q.GetDBDataFrame(query)
    RGCoord['name'] = RGCoord.name.apply(lambda x: x + 'w')

    RG = list(RGdf.rain_senslope.dropna().apply(lambda x: x[:len(x)-1]))
    RG = '|'.join(RG)
    query = "SELECT * FROM senslopedb.site_column where name REGEXP '%s'" %RG
    df = q.GetDBDataFrame(query)
    df['name'] = df.name.apply(lambda x: x[0:3] + 'w')
    RGCoord = RGCoord.append(df)
    
    RGCoord = RGCoord.drop_duplicates(['sitio', 'barangay', 'municipality', 'province'])
    RGCoord = RGCoord[['name', 'lat', 'lon', 'barangay', 'province']]    
    RGCoord = RGCoord.rename(columns = {'name': 'dev_id', 'barangay': 'location'})
    RGCoord['type'] = 'SenslopeRG'
    RGCoord = RGCoord.sort('dev_id')
    return RGCoord

def NOAHRGCoord():
    db, cur = q.SenslopeDBConnect(q.Namedb)
    query = "SELECT * FROM senslopedb.rain_gauge"
    RGCoord = q.GetDBDataFrame(query)
    RGCoord['dev_id'] = RGCoord.dev_id.apply(lambda x: 'rain_noah_' + str(x))
    RGCoord = RGCoord.rename(columns = {'latitude': 'lat', 'longitude': 'lon'})
    RGCoord['type'] = 'NOAHRG'
    return RGCoord
    
def AllRGCoord():
    SenslopeCoord = SiteCoord()
    NOAHCoord = NOAHRGCoord()
    RGCoord = SenslopeCoord.append(NOAHCoord)
    return RGCoord
    
def Distance(name):
    Coord = SiteCoord()
    lat = Coord.loc[Coord.dev_id == name]['lat'].values[0]
    lon = Coord.loc[Coord.dev_id == name]['lon'].values[0]
    
    NearGauge = AllRGCoord()
    NearGauge = NearGauge.drop_duplicates('dev_id')
    
    NearGauge['dlat'] = NearGauge['lat'].apply(lambda x: float(x) - lat)
    NearGauge['dlon'] = NearGauge['lon'].apply(lambda x: float(x) - lon)
    NearGauge['dlat'] = np.radians(NearGauge.dlat)
    NearGauge['dlon'] = np.radians(NearGauge.dlon)
    
    NearGauge['a1'] = NearGauge['dlat'].apply(lambda x: np.sin(x/2)**2)
    NearGauge['a3'] = NearGauge['lat'].apply(lambda x: np.cos(np.radians(float(x))))
    NearGauge['a4'] = NearGauge['dlon'].apply(lambda x: np.sin(x/2)**2)
    
    NearGauge['a'] = NearGauge['a1'] + (np.cos(np.radians(lat)) * NearGauge['a3'] * NearGauge['a4'])
    NearGauge['c']= 2 * np.arctan2(np.sqrt(NearGauge.a),np.sqrt(1-NearGauge.a))
    NearGauge['d']= 6371 * NearGauge.c
    NearGauge = NearGauge.drop(['a','c','dlon','dlat'], axis=1)
#    NearGauge = NearGauge.loc[NearGauge.d <= 20]
    NearGauge = NearGauge.sort('d', ascending = True)
    NearGauge = NearGauge.loc[NearGauge.dev_id != name]
    
    return NearGauge[0:3]

def NearRGdf(df):
    try:
        d = Distance(df['rain_arq'].values[0])
    except:
        d = Distance(df['rain_senslope'].values[0])

    d['d'] = np.round(d['d'], 2)
    
    df['RG1'] = d['dev_id'].values[0]
    df['d_RG1'] = d['d'].values[0] 
    df['RG2'] = d['dev_id'].values[1]
    df['d_RG2'] = d['d'].values[1]
    df['RG3'] = d['dev_id'].values[2]
    df['d_RG3'] = d['d'].values[2]
    
    to_MySQL(df, 'rain_props')

    return df

def main():
    RGdf = q.GetRainProps('rain_props')[['r_id','name', 'max_rain_2year', 'rain_senslope', 'rain_arq']]
    siteRGdf = RGdf.groupby('name')
    RG = siteRGdf.apply(NearRGdf)
    return RG
    
if __name__ == "__main__":
    start = datetime.now()
    
    updateDB()
    main()

    print 'runtime =', datetime.now() - start