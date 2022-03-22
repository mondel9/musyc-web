
import plotly.graph_objs as go 
from plotly.offline import  plot
import numpy as np
from musyc_code.SynergyCalculator.NDHillFun import Edrug1D, Edrug2D_NDB_hill


def doseResponse_Curve(T,d1,d2,dip,dip_sd,zero_conc=1):
    # Avoid making edits to original drug array by copying
    t_d1 = d1.copy()
    # In order to plot in log space, we replace the zero concentration with a number 
    # equal to 10fold lower than the lowest non-zero tested concentration
    t_d1[t_d1==0] = min(t_d1[t_d1!=0])/10.**zero_conc
    #Repeat for d2
    t_d2 = d2.copy()
    t_d2[t_d2==0] = min(t_d2[t_d2!=0])/10.**zero_conc

    # Generate arrays for calculating the dose response curve along
    # these are both float64
    dr1 = np.logspace(np.log10(np.min(t_d1)),np.log10(np.max(t_d1)))
    dr2 = np.logspace(np.log10(np.min(t_d2)),np.log10(np.max(t_d2)))

    # Fitted single drug effects (drug1 and drug2 by them selves)
    y1 = Edrug1D(dr1,T['E0'],T['E1'],T['C1'],T['h1'])
    y2 = Edrug1D(dr2,T['E0'],T['E2'],T['C2'],T['h2'])
    
    # Dose response (effects) of each drug plus the maximum tested concentration of the second drug.
    Ed1_mx  = Edrug2D_NDB_hill([np.array(dr1),np.array(np.ones(len(dr1))*max(dr2).astype(int))],T['E0'],T['E1'],T['E2'],T['E3'],T['r1'],T['r2'],10**T['log_C1'],10**T['log_C2'],T['h1'],T['h2'],10**T['log_alpha1'],10**T['log_alpha2'],10**T['log_gamma1'],10**T['log_gamma2'])
    Ed2_mx  = Edrug2D_NDB_hill([np.array(np.ones(len(dr2))*max(dr1).astype(int)),np.array(dr2)],T['E0'],T['E1'],T['E2'],T['E3'],T['r1'],T['r2'],10**T['log_C1'],10**T['log_C2'],T['h1'],T['h2'],10**T['log_alpha1'],10**T['log_alpha2'],10**T['log_gamma1'],10**T['log_gamma2'])

    # Drug1 dose response (no drug 2). Data
    trace0 = go.Scatter(x=np.log10(t_d1[d2==0]), 
                        y=dip[(d2==0)],
                        mode='markers',
                        marker=dict(size=8,color='blue'),
                        visible='legendonly',
                        name="Drug1 (no drug2) data"
                       )
    
    # Drug1 dose response (no drug 2). Fit    
    trace1 = go.Scatter(x=np.log10(dr1),
                        y=y1,
                        mode='lines',
                        marker=dict(size=8,color='blue'),
                        hovertext=T['drug1_name'], 
                        name="Drug1 (no drug2) fit"
                    )
    # Plot for the dose response curve of d1+d2_max (outside edge of surface plot)
    # Drug1 dose response (+ maximum drug 2). data    
    trace0_mx = go.Scatter(x=np.log10(t_d1[d2==max(d2)]), 
                        y=dip[d2==max(d2)],
                        mode='markers',
                        marker=dict(size=8,color='lightblue'),
                        visible='legendonly',
                        name="Drug1 (+ max drug2) data"
                       )
    #Drug1 dose response (+ maximum drug 2). Fit    
    trace1_mx = go.Scatter(x=np.log10(dr1),
                        y=Ed1_mx,
                        mode='lines',
                        marker=dict(size=8,color='lightblue'),
                        hovertext=T['drug1_name'] + ' + max(' +T['drug2_name']+')',
                        name="Drug1 (+ max drug2) fit"
                    )

    #Drug2 dose response (no drug 1). DAta    
    trace2 = go.Scatter(x=np.log10(t_d2[d1!=0]),
                        y=dip[d1!=0],
                        mode='markers',
                        marker=dict(size=8,color='red'),
                        visible='legendonly',
                        name="Drug2 (no drug1) data"
                    )
    #Drug2 dose response (no drug 1). fit    
    trace3 = go.Scatter(x=np.log10(dr2),
                        y=y2,
                        mode='lines',
                        marker=dict(size=8,color='red'),
                        hovertext=T['drug2_name'], 
                        name="Drug2 (no drug1) fit"
                        )  
    #Drug2 dose response (+ max drug 1). data    
    trace2_mx = go.Scatter(x=np.log10(t_d2[d1==max(d1)]), 
                        y=dip[d1==max(d1)],
                        mode='markers',
                        marker=dict(size=8,color='salmon'),
                        visible='legendonly',
                        name="Drug2 (+ max drug1) data"
                       )
    
    #Drug2 dose response (+ max drug 1). fit        
    trace3_mx = go.Scatter(x=np.log10(dr2),
                        y=Ed2_mx,
                        mode='lines',
                        marker=dict(size=8,color='salmon'),
                        hovertext=T['drug2_name'] + ' + max(' +T['drug1_name']+')',
                        name="Drug2 (+ max drug1) fit"
                    )     
    
    #Append all the traces into 2 lists
    data1=[]
    data1.append(trace0)
    data1.append(trace1)
    data1.append(trace0_mx)
    data1.append(trace1_mx)
    
    data2=[]
    data2.append(trace2)
    data2.append(trace3)
    data2.append(trace2_mx)
    data2.append(trace3_mx)

    if T['asym_ci']==1:
        title = T['sample'] + ":\n" + r"alpha={:.2} [{:.2},{:.2}]" "\n" r"beta(obs)={:.2} [{:.2},{:.2}]".format(float(T['log_alpha2']),
                  float(T['log_alpha2_ci'][0]),float(T['log_alpha2_ci'][1]),float(T['beta_obs']),float(T['beta_obs_ci'][0]),float(T['beta_obs_ci'][1]))
    else:
        title = T['sample'] + ":\n" + r"$\alpha$={:.2}$\pm${:.2}" "\n" r"$\beta(obs)$={:.2}$\pm${:.2}".format(float(T['log_alpha2']),
                  float(T['log_alpha2_std']),float(T['beta_obs']),float(T['beta_obs_std']))

    layout = dict(
          title={
               'text':title,
               'x':0.5,
               'y':0.92,
               'xanchor': 'center'
          },
          xaxis_title='log(drug)',
          yaxis_title=T['metric_name']
    )

    #Return 2 figures! 
    fig1 = go.Figure(data=data1, layout=layout)
    fig2 = go.Figure(data=data2, layout=layout)

    return fig1, fig2