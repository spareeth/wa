# -*- coding: utf-8 -*-
"""
Authors: Bert Coerver, Tim Hessels
         UNESCO-IHE 2017
Contact: t.hessels@unesco-ihe.org
Repository: https://github.com/wateraccounting/wa
Module: Function/Two
"""

# import general python modules
import pandas as pd
import numpy as np
import datetime
import os
import matplotlib.pyplot as plt
   
def ITE(Dir_Basin, Name_NC_ET, Name_NC_LAI, Name_NC_P, Name_NC_RD, Name_NC_NDM, Name_NC_LU, Startdate, Enddate, Simulation):
    """
    This functions split the evapotranspiration into interception, transpiration, and evaporation.

    Parameters
    ----------
    Dir_Basin : str
        Path to all the output data of the Basin
    Name_NC_ET : str
        Path to the .nc file containing ET data
    Name_NC_LAI : str
        Path to the .nc file containing LAI data
    Name_NC_P : str
        Path to the .nc file containing P data
    Name_NC_RD : str
        Path to the .nc file containing Rainy Days data
    Name_NC_NDM : str
        Path to the .nc file containing Normalized Dry Matter data
    Name_NC_LU : str
        Path to the .nc file containing Landuse data
    Startdate : str
        Contains the start date of the model 'yyyy-mm-dd'    
    Enddate : str
        Contains the end date of the model 'yyyy-mm-dd' 
    Simulation : int
        Defines the simulation    
        
    Returns
    -------
    I : array
        Array[time, lat, lon] contains the interception data
    T : array
        Array[time, lat, lon] contains the transpiration data
    E : array
        Array[time, lat, lon] contains the evaporation data

    """
    
    # import WA modules
    import wa.General.raster_conversions as RC
    import wa.Functions.Start.Get_Dictionaries as GD

    # Define monthly dates
    Dates = pd.date_range(Startdate, Enddate, freq = "MS")
    
    # Extract LU data from NetCDF file
    LU = RC.Open_nc_array(Name_NC_LU, Var = 'LU')
    
    # Create a mask to ignore non relevant pixels.
    lulc_dict = GD.get_lulcs().keys()
    mask=np.logical_or.reduce([LU == value for value in lulc_dict[:-1]])    
    mask3d = mask * np.ones(len(Dates))[:,None,None]
    mask3d_neg = (mask3d-1) * 9999          
    
    # Extract Evapotranspiration data from NetCDF file
    ET = RC.Open_nc_array(Name_NC_ET, Var = 'ET')[-len(Dates):,:,:]
    # Extract Leaf Area Index data from NetCDF file
    LAI = RC.Open_nc_array(Name_NC_LAI, Var = 'LAI')[-len(Dates):,:,:]
    # Extract Precipitation data from NetCDF file
    P = RC.Open_nc_array(Name_NC_P, Var = 'Prec')[-len(Dates):,:,:]
    # Extract Rainy Days data from NetCDF file
    RD = RC.Open_nc_array(Name_NC_RD, Var = 'RD')[-len(Dates):,:,:]
    # Extract Normalized Dry Matter data and time from NetCDF file
    NDM = RC.Open_nc_array(Name_NC_NDM, Var = 'NDM')[-len(Dates):,:,:]
    timeNDM = RC.Open_nc_array(Name_NC_NDM, Var = 'time')
    
    # Create dictory to get every month and year for each timestep
    datesNDMmonth = dict()
    datesNDMyear = dict()
    # Loop over all timestep
    for i in range(0,len(timeNDM)):
        # change toordinal to month and year
        datesNDMmonth[i] = datetime.date.fromordinal(timeNDM[i]).month
        datesNDMyear[i] = datetime.date.fromordinal(timeNDM[i]).year   
    
    # Calculate the max monthly NDM over the whole period
    NDMmax = dict()
   
    # loop over the months
    for month in range(1,13):
        dimensions = []
        # Define which dimension must be opened to get the same month
        for dimension, monthdict in datesNDMmonth.items():
            if monthdict == month:
                dimensions = np.append(dimensions,dimension)
        # Open those time dimension
        NDMmonth = np.zeros([np.size(dimensions), int(np.shape(NDM)[1]), int(np.shape(NDM)[2])])
        dimensions = np.int_(dimensions)        
        NDMmonth[:,:,:] = NDM[dimensions, :,:]
        # Calculate the maximum over the month
        NDMmax[month] = np.nanmax(NDMmonth,0)

    NDMmax_months = np.zeros([len(timeNDM), int(np.shape(NDM)[1]), int(np.shape(NDM)[2])])

    # Create 3D array with NDMmax
    for i in range(0,len(timeNDM)):
        NDMmax_months[i,:,:] = np.nanmax(NDMmax[datesNDMmonth[i]])

    # Create some variables needed to plot graphs.
    et = np.array([])
    i = np.array([])
    t = np.array([])

    # Change zero values in RD so we do not get errors
    RD[RD==0] = 0.001
    LAI[LAI==0] = 0.001
    LAI[np.isnan(LAI)] = 0.1
       
    # Calculate I
    I = LAI * (1 - np.power(1 + (P/RD) * (1 - np.exp(-0.5 * LAI)) * (1/LAI),-1)) * RD      
          
    # Set boundary
    I[np.isnan(LAI)] = np.nan
     
    # Calculate T
    T = np.minimum((NDM/NDMmax_months),np.ones(np.shape(NDM))) * 0.95 * (ET - I)
     
    # Mask Data
    ET = ET * mask3d
    T = T * mask3d
    I = I * mask3d
    ET[mask3d_neg<-1] = np.nan
    T[mask3d_neg<-1] = np.nan    
    I[mask3d_neg<-1] = np.nan
      
    # Calculate E
    E = ET - T - I
    
    # Calculate monthly averages
    et = np.nanmean(ET.reshape(ET.shape[0], -1),1)
    i = np.nanmean(I.reshape(I.shape[0], -1),1)
    t = np.nanmean(T.reshape(T.shape[0], -1),1)    
 
    # Plot graph of ET and E, T and I fractions.
    fig = plt.figure(figsize = (10,10))
    plt.grid(b=True, which='Major', color='0.65',linestyle='--', zorder = 0)
    ax = fig.add_subplot(111)
    ax.plot(Dates, et, color = 'k')
    ax.patch.set_visible(False)
    ax.set_title('Average ET and E, T and I fractions')
    ax.set_ylabel('ET [mm/month]')
    ax.patch.set_visible(True)
    ax.fill_between(Dates, et, color = '#a3db76', label = 'Evapotranspiration')
    ax.fill_between(Dates, i + t , color = '#6bb8cc', label = 'Transpiration')
    ax.fill_between(Dates, i , color = '#497e7c', label = 'Interception')
    ax.scatter(Dates, et, color = 'k')
    ax.legend(loc = 'upper left',fancybox=True, shadow=True)
    fig.autofmt_xdate()
    ax.set_xlim([Dates[0], Dates[-1]])
    ax.set_ylim([0, max(et) * 1.2])
    ax.set_xlabel('Time')
    [r.set_zorder(10) for r in ax.spines.itervalues()]
    
    # Define output folder and name for image
    NamePic = "Sim%s_Mean_ET_E_T_I.jpg" %Simulation
    Dir_Basin_Image = os.path.join(Dir_Basin, "Simulations", "Images")
    if not os.path.exists(Dir_Basin_Image):
        os.mkdir(Dir_Basin_Image)

    # Save Images
    plt.savefig(os.path.join(Dir_Basin_Image,NamePic))

    return(I, T, E)



      