from dateutil import parser
import pandas as pd
from pandas.stats.api import ols
import numpy as np
from numpy import nan
import scipy.stats.stats as st
import matplotlib.pyplot as plt
import os
import csv
from datetime import datetime, date, time, timedelta
import gc
from scipy.interpolate import UnivariateSpline
from numpy.fft import fft, ifft, fftfreq

def Input_Loc_Col(loc_col_list,num_nodes_loc_col,col_seg_len_list,IWS):
    colname=loc_col_list[IWS]
    num_nodes=num_nodes_loc_col[IWS]
    seg_len=col_seg_len_list[IWS]
    return colname,num_nodes,seg_len


def xzxy_to_cart(node_len, xz, xy):
    #xz and xy here are in angular units (degrees)
    cond=(xz==0)*(xy==0)
    H=np.round(np.where(cond,
                        node_len*np.ones(len(xz)),
                        node_len/np.sqrt(1+(np.tan(np.radians(xz)))**2+(np.tan(np.radians(xy)))**2)),3)
    a=np.where(cond,
               np.zeros(len(xz)),
               (np.round(H*np.tan(np.radians(xz)),3)))
    b=np.where(cond,
               np.zeros(len(xz)),
               (np.round(H*np.tan(np.radians(xy)),3)))
    return H,a,b


def df_from_csv(csvfilepath,colname,col,usecol):
    df=pd.read_csv(csvfilepath+colname+"_proc.csv",names=col,usecols=usecol,parse_dates=[col[0]],index_col=col[0])

    #computing equivalent linear displacements
    x,xz,xy=xzxy_to_cart(seg_len,df['xz'].values,df['xy'].values)

    #appending linear displacements series to data frame
    df['xlin']=pd.Series(data=x,index=df.index)
    df['xzlin']=pd.Series(data=xz,index=df.index)
    df['xylin']=pd.Series(data=xy,index=df.index)
    df.drop(['xz','xy'],inplace=True,axis=1)
    gc.collect()
    
    #creating dataframes
    xzdf, xydf, xdf = create_dataframes(df, num_nodes, seg_len)

    return xzdf, xydf, xdf    

def create_dataframes(df, num_nodes, seg_len):
    #creating series list
    xzlist=[]
    xylist=[]
    xlist=[]
    for curnodeID in range(num_nodes):
        #extracting data from current node, with good tilt filter
        df_curnode=df[(df.Node_ID==curnodeID+1) & (df.good_tilt==1)]
        dates=df_curnode.index

        #handling "no data"
        if len(dates)<1:
            print curnodeID 
            xzlist.append(pd.Series(data=[0],index=[df.index[0]]))
            xylist.append(pd.Series(data=[0],index=[df.index[0]]))
            xlist.append(pd.Series(data=[seg_len],index=[df.index[0]]))
            continue

        #extracting component displacements as series
        xz=pd.Series(data=df_curnode['xzlin'], index=df_curnode.index, name=curnodeID+1)
        xy=pd.Series(data=df_curnode['xylin'], index=df_curnode.index, name=curnodeID+1)
        x=pd.Series(data=df_curnode['xlin'], index=df_curnode.index, name=curnodeID+1)
        
        #resampling series to 30-minute intervals
        xz=xz.resample('30Min',how='mean',base=0)
        xy=xy.resample('30Min',how='mean',base=0)
        x=x.resample('30Min',how='mean',base=0)
        
        #appending resampled series to list
        xzlist.append(xz)
        xylist.append(xy)
        xlist.append(x)

    #creating unfilled XZ, XY and X dataframes
    xzdf=pd.concat([xzlist[num_nodes-a-1] for a in range(num_nodes)] ,axis=1,join='outer', names=[num_nodes-b for b in range(num_nodes)])
    xydf=pd.concat([xylist[num_nodes-a-1] for a in range(num_nodes)] ,axis=1,join='outer', names=[num_nodes-b for b in range(num_nodes)])
    xdf=pd.concat([xlist[num_nodes-a-1] for a in range(num_nodes)] ,axis=1,join='outer', names=[num_nodes-b for b in range(num_nodes)])

    #conversion from m to cm
    xzdf=xzdf*100
    xydf=xydf*100
    
    return xzdf, xydf, xdf

def resamp_fill_df(resampind, xzdf,xydf,xdf):
    #resampling XZ, XY and X dataframes to desired interval
    r_xzdf=xzdf.resample(resampind,how='mean',base=0)
    r_xydf=xydf.resample(resampind,how='mean',base=0)
    r_xdf=xdf.resample(resampind,how='mean',base=0)
    #filling XZ,XY and X dataframes
    fr_xzdf=r_xzdf.fillna(method='pad')
    fr_xydf=r_xydf.fillna(method='pad')
    fr_xdf=r_xdf.fillna(method='pad')
    fr_xzdf=fr_xzdf.fillna(method='bfill')
    fr_xydf=fr_xydf.fillna(method='bfill')
    fr_xdf=fr_xdf.fillna(method='bfill')
    return fr_xzdf, fr_xydf, fr_xdf


def plot_node_disp(colname,num_nodes, xz, xy, x, voff, title):
    fig,ax=plt.subplots(nrows=3,ncols=1, sharex=True,sharey=True, figsize=fig_size )
    plt.suptitle(colname+"\n"+title)
    cm = plt.get_cmap('gist_rainbow')
    ax[0].set_color_cycle([cm(1.*(num_nodes-i-1)/(num_nodes)) for i in range((num_nodes))])
    ax[1].set_color_cycle([cm(1.*(num_nodes-i-1)/(num_nodes)) for i in range((num_nodes))])
    ax[2].set_color_cycle([cm(1.*(num_nodes-i-1)/(num_nodes)) for i in range((num_nodes))])
    for curnodeID in range(num_nodes):
        plt.sca(ax[0])
        xplot=voff*(curnodeID)+(x[num_nodes-curnodeID]-x[num_nodes-curnodeID][0])
        xplot.plot()
        plt.sca(ax[1])
        xzplot=voff*(curnodeID)+(xz[num_nodes-curnodeID]-xz[num_nodes-curnodeID][0])
        xzplot.plot()
        plt.sca(ax[2])
        xyplot=voff*(curnodeID)+(xy[num_nodes-curnodeID]-xy[num_nodes-curnodeID][0])
        xyplot.plot()
    ax[0].set_xlabel([], visible=False)
    ax[1].set_xlabel([], visible=False)
    ax[0].set_ylabel("X, m", fontsize='small')
    ax[1].set_ylabel("XZ, m", fontsize='small')
    ax[2].set_ylabel("XY, m", fontsize='small')
    plt.tight_layout()
    plt.subplots_adjust(left=None, bottom=None, right=None, top=0.9,wspace=None, hspace=None)
    return fig, ax


def plot_col_pos(cs_xzdf, cs_xydf, cs_xdf, colposperiod, colpostype):
    dat=pd.date_range(start=cs_xzdf.index[0],end=cs_xzdf.index[-1], freq=colposperiod)
    
    fig,ax=plt.subplots(nrows=1,ncols=2, sharex=True, sharey=True,figsize=fig_size)
    plt.suptitle(colname+"\n"+colpostype+" col pos")
    cm = plt.get_cmap('gist_rainbow')
    ax[0].set_color_cycle([cm(1.*(len(dat)-i-1)/len(dat)) for i in range(len(dat))])
    ax[1].set_color_cycle([cm(1.*(len(dat)-i-1)/len(dat)) for i in range(len(dat))])

    for d in range(len(dat)):
        curxz=cs_xzdf[(cs_xzdf.index==dat[d])]
        curxy=cs_xydf[(cs_xydf.index==dat[d])]
        curx=cs_xdf[(cs_xdf.index==dat[d])]

        if colpostype=='rel':
            curxz=curxz.sub(cs_xzdf.iloc[0,:],axis=1)    
            curxy=curxy.sub(cs_xydf.iloc[0,:],axis=1)    

        plt.sca(ax[0])
        plt.axis('equal')
        plt.plot([[0]]+curxz.values.T.tolist(),[[0.0]]+curx.values.T.tolist(), '.-')

        plt.sca(ax[1])
        plt.axis('equal')
        plt.plot([[0.0]]+curxy.values.T.tolist(),[[0.0]]+curx.values.T.tolist(), '.-',label=datetime.strftime(dat[d],'%Y-%m-%d'))
        

    ax[0].set_xlabel("XZ disp, m \n (+) downslope", fontsize='small',horizontalalignment='center')
    ax[0].set_ylabel("X disp, m \n (+) towards surface", fontsize='small', rotation='vertical',horizontalalignment='center')
    ax[1].set_xlabel("XY disp, m \n (+) to the right, facing downslope", fontsize='small', horizontalalignment='center')
    plt.legend(loc='lower right', fontsize='small')
    
    plt.tight_layout()
    plt.subplots_adjust(left=None, bottom=None, right=None, top=0.9,wspace=None, hspace=None)
    return fig,ax


#CONSTANTS and SETTINGS
loc_col_list=("eeet","sinb","sint","sinu","lipb","lipt","bolb","pugb","pugt","mamb","mamt","oslb","labt", "labb", "gamt","gamb", "humt","humb", "plat","plab","blct","blcb")
num_nodes_loc_col=(14,29,19,29,28,31,30,14,10,29,24,23,39,25,18,22,21,26,39,40,24,19)
col_seg_len_list=(0.5,1,1,1,0.5,0.5,0.5,1.2,1.2,1.0,1.0,1.,1.,1.,1.,1.,1.,1,0.5,0.5,1,1)
col = ['Time','Node_ID', 'x', 'y', 'z', 'good_tilt', 'xz', 'xy', 'phi', 'rho', 'moi', 'good_moi']
usecol = ['Time','Node_ID','good_tilt', 'xz', 'xy']
fig_size=(9.5,6.5)


#set file path for input *.proc files
csvfilepath="D:/Dropbox/Senslope Data/Proc/csv/"

#set file path for saving figures
figsavefilepath="C:/Users/Jasper/Desktop/"

#set this to 1 to plot figures
plotfigs=1

#set this to 1 to save figures, 0 to just display the output
savefigs=0

#set this to desired node date sampling interval: D=daily, 3H=3-hourly, M=monthly, Q=quarterly, etc...
resampind='30Min'

#set this to desired interval between column positions: D=daily, 3H=3-hourly, M=monthly, Q=quarterly, etc...
colposperiod='Q'
    
 
#MAIN

Y=2012
m=9
d=28
H=0
M=0
S=0
start=datetime.combine(date(Y,m,d),time(H,M,S))
end=start-timedelta(days=3)
day=start-timedelta(days=1)

which_sensor=3
which_node=7
length=7

for INPUT_which_sensor in range(1,len(loc_col_list)):
    if INPUT_which_sensor!=which_sensor:continue
    colname,num_nodes,seg_len=Input_Loc_Col(loc_col_list,num_nodes_loc_col,col_seg_len_list, INPUT_which_sensor)

    print "\n",colname, num_nodes, seg_len
    
    #reading from csv file and writing to dataframe
    xzdf, xydf, xdf = df_from_csv(csvfilepath,colname,col,usecol)

    #slicing dataframe
    xzdf = xzdf[end:start]
    
    #resampling and filling XZ, XY and X dataframes
    fr_xzdf, fr_xydf, fr_xdf = resamp_fill_df(resampind, xzdf,xydf,xdf)
    fr_xzdf[which_node].plot()

    #computing cumulative node displacements
    cs_xzdf=fr_xzdf.cumsum(axis=1)
    cs_xydf=fr_xydf.cumsum(axis=1)
    cs_xdf=fr_xdf.cumsum(axis=1)

    for cur_node_ID in range(num_nodes):
        if cur_node_ID!=which_node:continue
        
        #rolling mean in 3 hour-window and 3 minimum data points
        rm_xzdf=pd.rolling_mean(fr_xzdf,window=length)
    #    rm_xydf=pd.rolling_mean(fr_xydf,window=7)
    #    rm_xdf=pd.rolling_mean(fr_xdf,window=7)

        #linear regression in 3 hour-window and 3 minimum data points
        td_rm_xzdf=rm_xzdf.index.values-rm_xzdf.index.values[0]
    #    td_rm_xydf=rm_xydf.index.values-rm_xydf.index.values[0]
    #    td_rm_xdf=rm_xdf.index.values-rm_xdf.index.values[0]

        tdelta=pd.Series(td_rm_xzdf/np.timedelta64(1,'D'),index=rm_xzdf.index)
    #    tdelta=pd.Series(td_rm_xydf/np.timedelta64(1,'D'),index=rm_xydf.index)
    #    tdelta=pd.Series(td_rm_xdf/np.timedelta64(1,'D'),index=rm_xdf.index)

        plt.figure()
        lr_xzdf=ols(y=rm_xzdf[which_node],x=tdelta,window=length,intercept=True)
    #    lr_xydf=ols(y=rm_xydf[node],x=tdelta,window=7,intercept=True)
    #    lr_xdf=ols(y=rm_xdf[node],x=tdelta,window=7,intercept=True)
        lr_xzdf.beta.x.plot(marker='o',legend=False)

        #generating inverse velocity plot
        plt.figure()
        temp_lr_xzdf = lr_xzdf.beta.x
        filtered_xzdf = temp_lr_xzdf[temp_lr_xzdf>0.5]
        inv_xzdf = 1/filtered_xzdf
        inv_xzdf.plot(marker='o',legend=False)

        #linear regression
        plt.figure()
        temp_inv_xzdf = inv_xzdf[day:]
        time=pd.Series(temp_inv_xzdf.values,index=temp_inv_xzdf.index)
        response_xzdf=ols(y=temp_inv_xzdf,x=time,window=3,intercept=True)
        response_xzdf.beta.x.plot(marker='o',legend=False)

#        plt.figure()
#        accel_xzdf=ols(y=lr_xzdf.beta.x,x=tdelta,window=length,intercept=True)
#        count=len(lr_xzdf.beta.x)-len(accel_xzdf.beta.x)
#        plt.plot(lr_xzdf.beta.x[count:],accel_xzdf.beta.x,marker='>')

#        plt.axvline(x=0.5,color='y', ls=':',lw=3)
#        plt.axvline(x=50,color='r', ls=':',lw=3)
#        plt.axvline(x=-0.5,color='y', ls=':',lw=3,)
#        plt.axvline(x=-50,color='r', ls=':',lw=3,)

#        plt.yscale('symlog')
#        plt.xscale('symlog')

        plt.show()

    if plotfigs==1:

        #plotting individual node displacements

        #unfilled
        voff=0.1 #in meters
#        fig_id, ax_id=plot_node_disp(colname,num_nodes, xzdf, xydf, xdf, voff, "unfilled individual node disp")
        if savefigs==1:plt.savefig(figsavefilepath+colname+"nd_u.png", dpi=300,orientation='portrait', format="png")

        #filled and resampled
        voff=0.1 #in meters
#        fig_id, ax_id=plot_node_disp(colname, num_nodes, fr_xzdf, fr_xydf, fr_xdf, voff, "individual node disp")
        if savefigs==1:plt.savefig(figsavefilepath+colname+"nd_f.png", dpi=300,orientation='portrait', format="png")

        #with rolling mean
        voff=0.1 #in meters
#        fig_id, ax_id=plot_node_disp(colname, num_nodes, rm_xzdf, rm_xydf, rm_xdf, voff, "individual node disp with rolling mean")
        if savefigs==1:plt.savefig(figsavefilepath+colname+"nd_f_rm.png", dpi=300,orientation='portrait', format="png")

        #plotting cumulative node displacements
        voff=0.1 #in meters
#        fig_cd, ax_cd=plot_node_disp(colname, num_nodes, cs_xzdf, cs_xydf, cs_xdf, voff, "cumulative node disp")
        if savefigs==1:plt.savefig(figsavefilepath+colname+"nd_fc.png", dpi=300,orientation='portrait', format="png")

        #plotting column positions time series
        
        #absolute position
#        fig_cp, ax_cp=plot_col_pos(cs_xzdf, cs_xydf, cs_xdf, colposperiod, "abs")
        if savefigs==1:plt.savefig(figsavefilepath+colname+"col_a.png", dpi=300,orientation='portrait', format="png")

        #relative position
#        fig_cp, ax_cp=plot_col_pos(cs_xzdf, cs_xydf, cs_xdf, colposperiod, "rel")
        if savefigs==1:plt.savefig(figsavefilepath+colname+"col_r.png", dpi=300,orientation='portrait', format="png")

#        print "finished plots: ",(datetime.now()-start)

        if savefigs==0:plt.show()

    plt.close('all')
