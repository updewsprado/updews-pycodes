import pandas as pd
import numpy as np
from datetime import timedelta

def RoundTime(date_time):
    # rounds time to 4/8/12 AM/PM
    time_hour = int(date_time.strftime('%H'))

    quotient = time_hour / 4
    if quotient == 5:
        date_time = pd.to_datetime(date_time.date() + timedelta(1))
    else:
        time = (quotient+1)*4
        date_time = pd.to_datetime(date_time.date()) + timedelta(hours=time)
            
    return date_time

def node_alert(disp_vel, colname, num_nodes, T_disp, T_velL2, T_velL3, k_ac_ax,lastgooddata,window,config):
    valid_data = pd.to_datetime(window.end - timedelta(hours=3))
    #initializing DataFrame object, alert
    alert=pd.DataFrame()

    #adding node IDs
    node_id = disp_vel.node_id.values[0]
    alert['node_id']= [node_id]

    #checking for nodes with no data
    lastgooddata=lastgooddata.loc[lastgooddata.node_id == node_id]

    try:
        cond = pd.to_datetime(lastgooddata.ts.values[0]) < valid_data
    except IndexError:
        cond = False
        
    alert['ND']=np.where(cond,
                         
                         #No data within valid date 
                         np.nan,
                         
                         #Data present within valid date
                         1)
    
    #evaluating net displacements within real-time window
    alert['xz_disp']=np.round(disp_vel.xz.values[-1]-disp_vel.xz.values[0], 3)
    alert['xy_disp']=np.round(disp_vel.xy.values[-1]-disp_vel.xy.values[0], 3)

    #determining minimum and maximum displacement
    cond = np.asarray(np.abs(alert['xz_disp'].values)<np.abs(alert['xy_disp'].values))
    min_disp=np.round(np.where(cond,
                               np.abs(alert['xz_disp'].values),
                               np.abs(alert['xy_disp'].values)), 4)
    cond = np.asarray(np.abs(alert['xz_disp'].values)>=np.abs(alert['xy_disp'].values))
    max_disp=np.round(np.where(cond,
                               np.abs(alert['xz_disp'].values),
                               np.abs(alert['xy_disp'].values)), 4)

    #checking if displacement threshold is exceeded in either axis    
    cond = np.asarray((np.abs(alert['xz_disp'].values)>T_disp, np.abs(alert['xy_disp'].values)>T_disp))
    alert['disp_alert']=np.where(np.any(cond, axis=0),

                                 #checking if proportional velocity is present across node
                                 #disp alert 2
                                 np.where(min_disp/max_disp>k_ac_ax,
                                          2,
                                          0),

                                 #disp alert 0
                                 0)
    
    #getting minimum axis velocity value
    alert['min_vel']=np.round(np.where(np.abs(disp_vel.vel_xz.values[-1])<np.abs(disp_vel.vel_xy.values[-1]),
                                       np.abs(disp_vel.vel_xz.values[-1]),
                                       np.abs(disp_vel.vel_xy.values[-1])), 4)

    #getting maximum axis velocity value
    alert['max_vel']=np.round(np.where(np.abs(disp_vel.vel_xz.values[-1])>=np.abs(disp_vel.vel_xy.values[-1]),
                                       np.abs(disp_vel.vel_xz.values[-1]),
                                       np.abs(disp_vel.vel_xy.values[-1])), 4)
                                       
    #checking if proportional velocity is present across node
    alert['vel_alert']=np.where(alert['min_vel'].values/alert['max_vel'].values>k_ac_ax,   

                                #checking if max node velocity exceeds threshold velocity for alert 2
                                np.where(alert['max_vel'].values>=T_velL2,                  

                                         #checking if max node velocity exceeds threshold velocity for alert 3
                                         np.where(alert['max_vel'].values>=T_velL3,         

                                                  #vel alert 3
                                                  3,

                                                  #vel alert 2
                                                  2),

                                         #vel alert 0
                                         0),

                                #vel alert 0
                                0)
    
    alert['disp_alert']=(alert['ND']*alert['disp_alert']).fillna(value=-1).apply(lambda x: int(x))
    alert['vel_alert']=(alert['ND']*alert['vel_alert']).fillna(value=-1).apply(lambda x: int(x))

    alert['node_alert']=np.where(alert['vel_alert'].values >= alert['disp_alert'].values,

                                 #node alert takes the higher perceive risk between vel alert and disp alert
                                 alert['vel_alert'].values,                                

                                 alert['disp_alert'].values)

    alert['ND'] = alert['ND'].fillna(value=0)

    return alert

def column_alert(alert, num_nodes_to_check):

    #DESCRIPTION
    #Evaluates column-level alerts from node alert and velocity data

    #INPUT
    #alert:                             Pandas DataFrame object, with length equal to number of nodes, and columns for displacements along axes,
    #                                   displacement alerts, minimum and maximum velocities, velocity alerts and final node alerts
    #num_nodes_to_check:                integer; number of adjacent nodes to check for validating current node alert
    
    #OUTPUT:
    #alert:                             Pandas DataFrame object; same as input dataframe "alert" with additional column for column-level alert

#    print alert
    col_alert=[]
    col_node=[]
    #looping through each node
    for i in range(1,len(alert)+1):

        if alert['ND'].values[i-1]==0:
            col_node.append(i-1)
            col_alert.append(-1)
    
        #checking if current node alert is 2 or 3
        elif alert['node_alert'].values[i-1]!=0:
            
            #defining indices of adjacent nodes
            adj_node_ind=[]
            for s in range(1,num_nodes_to_check+1):
                if i-s>0: adj_node_ind.append(i-s)
                if i+s<=len(alert): adj_node_ind.append(i+s)

            #looping through adjacent nodes to validate current node alert
            validity_check(adj_node_ind, alert, i, col_node, col_alert)
               
        else:
            col_node.append(i-1)
            col_alert.append(alert['node_alert'].values[i-1])
            
    alert['col_alert']=np.asarray(col_alert)

    return alert

def validity_check(adj_node_ind, alert, i, col_node, col_alert):

    #DESCRIPTION
    #used in validating current node alert

    #INPUT
    #adj_node_ind                       Indices of adjacent node
    #alert:                             Pandas DataFrame object, with length equal to number of nodes, and columns for displacements along axes,
    #                                   displacement alerts, minimum and maximum velocities, velocity alerts, final node alerts and olumn-level alert
    #i                                  Integer, used for counting
    #col_node                           Integer, current node
    #col_alert                          Integer, current node alert
    
    #OUTPUT:
    #col_alert, col_node                             

    adj_node_alert=[]
    for j in adj_node_ind:
        if alert['ND'].values[j-1]==0:
            adj_node_alert.append(-1)
        else:
            if alert['vel_alert'].values[i-1]!=0:
                #comparing current adjacent node velocity with current node velocity
                if abs(alert['max_vel'].values[j-1])>=abs(alert['max_vel'].values[i-1])*1/(2.**abs(i-j)):
                    #current adjacent node alert assumes value of current node alert
                    col_node.append(i-1)
                    col_alert.append(alert['node_alert'].values[i-1])
                    break
                    
                else:
                    adj_node_alert.append(0)
                    col_alert.append(max(getmode(adj_node_alert)))
                    break
                
            else:
                col_node.append(i-1)
                col_alert.append(alert['node_alert'].values[i-1])
                break

        if j==adj_node_ind[-1]:
            col_alert.append(max(getmode(adj_node_alert)))
        
    return col_alert, col_node

def getmode(li):
    li.sort()
    numbers = {}
    for x in li:
        num = li.count(x)
        numbers[x] = num
    highest = max(numbers.values())
    n = []
    for m in numbers.keys():
        if numbers[m] == highest:
            n.append(m)
    return n