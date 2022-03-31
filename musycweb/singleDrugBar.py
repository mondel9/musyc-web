'''
Single drug parameter bar plot
Author: Monica Del Valle
'''

import plotly.graph_objects as go
import plotly.offline
import csv
import pandas as pd
import string

# Function to remove non-numeric chars from the confidence intervals
def translate_ci(df_ci):
     return df_ci.str.translate(str.maketrans({'[':'',']':''}))

# Separate the upper and lower bounds into two separate lists 
def parse_ci(df_ci, lower, upper):
     temp = df_ci.split(',')
     lower.append(float(temp[0]))
     upper.append(float(temp[1]))

# This would need to be changed to the musyc base url 
def create_link(task_id):
     link = 'https://musyc.lolab.xyz/task/' + task_id
     return link

def check_batch(row, drug):
     if row['batch'] != 'None':
          if drug == 1:
               return row['drug1_name'] + '_b' + str(row['batch']) 
          elif drug == 2:
               return row['drug2_name'] + '_b' + str(row['batch'])
     else:
          if drug == 1:
               return row['drug1_name']
          elif drug == 2:
               return row['drug2_name']
          

def single_bar(dataset_list, task_list):
     col_list = ["sample","drug1_name","drug2_name","expt","batch","task_status","converge_mc_nlls",
               "beta","beta_ci","beta_obs","beta_obs_ci","log_alpha12","log_alpha12_ci","log_alpha21",
               "log_alpha21_ci","R2","log_like_mc_nlls","E0","E0_ci","E1","E1_ci","E2","E2_ci","E3",
               "E3_ci","E1_obs","E1_obs_ci","E2_obs","E2_obs_ci","E3_obs","E3_obs_ci","log_C1","log_C1_ci",
               "log_C2","log_C2_ci","log_h1","log_h1_ci","log_h2","log_h2_ci","h1","h2","C1","C2","time_total",
               "drug1_units","drug2_units","metric_name","fit_beta","boundary_sampling","max_conc_d1","max_conc_d2",
               "min_conc_d1","min_conc_d2","fit_method","dataset_name"]
     
     # create links to the proper surface plot
     links = list(map(lambda x: create_link(x), task_list))
     new_col = pd.Series(links)

     if len([dataset_list]) == 1:
          df1 = pd.DataFrame(dataset_list,columns=col_list)
          cols = len(df1.columns)
          df1.insert(cols, "links", new_col)
          new_clist = df1.columns
     else:
          for i in range(len(dataset_list)):
               if i == 0:
                    df1 = pd.DataFrame(dataset_list[i],columns=col_list)
               else:
                    temp = pd.DataFrame(dataset_list[i], columns=col_list)
                    df1.append(temp)
          cols = len(df1.columns)
          df1.insert(cols, "links", new_col)
          new_clist = df1.columns

     df1.to_csv('dataset_csv.csv', index=False)
     # append each csv to a list as well
     df = pd.read_csv('dataset_csv.csv', usecols=new_clist)
     
     # Remove special chars. from confidence intervals for parsing
     df['E1_ci'] = translate_ci(df['E1_ci'])
     df['E1_obs_ci'] = translate_ci(df['E1_obs_ci'])
     df['E2_ci'] = translate_ci(df['E2_ci'])
     df['E2_obs_ci'] = translate_ci(df['E2_obs_ci'])
     df['log_h1_ci'] = translate_ci(df['log_h1_ci'])
     df['log_h2_ci'] = translate_ci(df['log_h2_ci'])
     df['log_C1_ci'] = translate_ci(df['log_C1_ci'])
     df['log_C2_ci'] = translate_ci(df['log_C2_ci'])

     # Adding batches to name to try to prevent bar stacking - could be cleaner way to do this
     df['drug1_name'] = df.apply(lambda x: check_batch(x, 1), axis=1)
     df['drug2_name'] = df.apply(lambda x: check_batch(x, 2), axis=1)
 
     color_pallete = [
          '#636efa',  # blue
          '#00cc96',  # green-teal
          '#d62728',  # brick red
          '#ab63fa',  # muted purple
          '#ff7f0e',  # safety orange
          '#e377c2',  # raspberry yogurt pink
          '#1616a7',  # dark blue
          '#7f7f7f',  # middle gray
          '#17becf',  # blue-teal
          '#8c564b',  # chestnut brown
          '#bcbd22'   # curry yellow-green
     ] 

     # Assign each dataset name a color for visualization
     colors = {}
     y=0
     for x in df.dataset_name.unique():
          new_color = {x: color_pallete[y]}
          colors.update(new_color)
          y+=1
          
     df['color'] = df['dataset_name'].apply(lambda x: colors[x])
     
     data=[]

     e1U = []
     e1L = []
     df['E1_ci'].apply(lambda x: parse_ci(x, e1L, e1U))
     df = df.sort_values(by=['E1'],ascending=False)
     E1Trace = go.Bar(x=[x for _, x in zip(df['E1'],df['drug1_name']+' ('+df['drug2_name']+')')],
                         y=df['E1'],
                         name='E1',
                         visible=True,
                         marker_color= df['color'],
                         hovertemplate = 'E1 = %{y:.3g}<extra></extra><br>' + 
                                         'x = %{x}' + 
                                         '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         error_y= dict(
                                   type='data',
                                   symmetric=False,
                                   array=e1U,
                                   arrayminus=e1L,
                                   visible=False),
                         customdata=df['links']
                    )
     e1oU = []
     e1oL = []
     df['E1_obs_ci'].apply(lambda x: parse_ci(x, e1oL, e1oU))
     df = df.sort_values(by=['E1_obs'],ascending=False)
     E1ObsTrace = go.Bar(x=[x for _, x in zip(df['E1_obs'],df['drug1_name']+' ('+df['drug2_name']+')')],
                         y=df['E1_obs'],
                         name='E1_obs',
                         visible=False,
                         marker_color= df['color'],
                         hovertemplate = 'E1_obs = %{y:.3g}<extra></extra><br>' + 
                                         'x = %{x}' + 
                                         '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         error_y= dict(
                                   type='data',
                                   symmetric=False,
                                   array=e1oU,
                                   arrayminus=e1oL,
                                   visible=False),
                         customdata=df['links']
                    )
     e2U = []
     e2L = []
     df['E2_ci'].apply(lambda x: parse_ci(x, e2L, e2U))
     df = df.sort_values(by=['E2'],ascending=False)
     E2Trace = go.Bar(x=[x for _, x in zip(df['E2'],df['drug2_name']+' ('+df['drug1_name']+')')],
                         y=df['E2'],
                         name='E2',
                         visible=False,
                         marker_color= df['color'],
                         hovertemplate = 'E2 = %{y:.3g}<extra></extra><br>' + 
                                         'x = %{x}'+ 
                                         '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         error_y= dict(
                                   type='data',
                                   symmetric=False,
                                   array=e2U,
                                   arrayminus=e2L,
                                   visible=False),
                         customdata=df['links']
                    )
     e2oU = []
     e2oL = []
     df['E2_obs_ci'].apply(lambda x: parse_ci(x, e1L, e1U))
     df = df.sort_values(by=['E2_obs'],ascending=False)
     E2ObsTrace = go.Bar(x=[x for _, x in zip(df['E2_obs'],df['drug2_name']+' ('+df['drug1_name']+')')],
                         y=df['E2_obs'],
                         name='E2_obs',
                         visible=False,
                         marker_color= df['color'],
                         hovertemplate = 'E2_obs = %{y:.3g}<extra></extra><br>' + 
                                        'x = %{x}' + 
                                         '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         error_y= dict(
                                   type='data',
                                   symmetric=False,
                                   array=e2oU,
                                   arrayminus=e2oL,
                                   visible=False),
                         customdata=df['links']
                    )
     df = df.sort_values(by=['C1'],ascending=False)
     C1Trace = go.Bar(x=[x for _, x in zip(df['C1'],df['drug1_name']+' ('+df['drug2_name']+')')],
                         y=df['C1'],
                         name='C1',
                         visible=False,
                         marker_color= df['color'],
                         hovertemplate = 'C1 = %{y:.3g}<extra></extra><br>' + 
                                         'x = %{x}' + 
                                         '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         customdata=df['links']
                    )
     df = df.sort_values(by=['C2'],ascending=False)
     C2Trace = go.Bar(x=[x for _, x in zip(df['C2'],df['drug2_name']+' ('+df['drug1_name']+')')],
                         y=df['C2'],
                         name='C2',
                         visible=False,
                         marker_color= df['color'],
                         hovertemplate = 'C2 = %{y:.3g}<extra></extra><br>' + 
                                         'x = %{x}' + 
                                         '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         customdata=df['links']
                    )
     df = df.sort_values(by=['h1'],ascending=False)
     h1Trace = go.Bar(x=[x for _, x in zip(df['h1'],df['drug1_name']+' ('+df['drug2_name']+')')],
                         y=df['h1'],
                         name='h1',
                         visible=False,
                         marker_color= df['color'],
                         hovertemplate = 'h1 = %{y:.3g}<extra></extra><br>' + 
                                         'x = %{x}' + 
                                         '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         customdata=df['links']
                    )
     df = df.sort_values(by=['h2'],ascending=False)
     h2Trace = go.Bar(x=[x for _, x in zip(df['h2'],df['drug2_name']+' ('+df['drug1_name']+')')],
                         y=df['h2'],
                         name='h2',
                         visible=False,
                         marker_color= df['color'],
                         hovertemplate = 'h2 = %{y:.3g}<extra></extra><br>' + 
                                        'x = %{x}' + 
                                         '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         customdata=df['links']
                    )
     lh1U = []
     lh1L = []
     df['log_h1_ci'].apply(lambda x: parse_ci(x, lh1L, lh1U))
     df = df.sort_values(by=['log_h1'],ascending=False)
     logh1Trace = go.Bar(x=[x for _, x in zip(df['log_h1'],df['drug1_name']+' ('+df['drug2_name']+')')],
                         y=df['log_h1'],
                         name='log_h1',
                         visible=False,
                         marker_color= df['color'],
                         hovertemplate = 'log_h1 = %{y:.3g}<extra></extra><br>' + 
                                         'x = %{x}' + 
                                         '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         error_y= dict(
                                   type='data',
                                   symmetric=False,
                                   array=lh1U,
                                   arrayminus=lh1L,
                                   visible=False),
                         customdata=df['links']
                    )
     lh2U = []
     lh2L = []
     df['log_h2_ci'].apply(lambda x: parse_ci(x, lh2L, lh2U))
     df = df.sort_values(by=['log_h2'],ascending=False)
     logh2Trace = go.Bar(x=[x for _, x in zip(df['log_h2'],df['drug2_name']+' ('+df['drug1_name']+')')],
                         y=df['log_h2'],
                         name='log_h2',
                         visible=False,
                         marker_color= df['color'],
                         hovertemplate = 'log_h2 = %{y:.3g}<extra></extra><br>' + 
                                         'x = %{x}' + 
                                         '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         error_y= dict(
                                   type='data',
                                   symmetric=False,
                                   array=lh2U,
                                   arrayminus=lh2L,
                                   visible=False),
                         customdata=df['links']
                    )

     lc1U=[]
     lc1L=[]
     df['log_C1_ci'].apply(lambda x: parse_ci(x, lc1L, lc1U))
     df = df.sort_values(by=['log_C1'],ascending=False)
     logC1Trace = go.Bar(x=[x for _, x in zip(df['log_C1'],df['drug1_name']+' ('+df['drug2_name']+')')],
                         y=df['log_C1'],
                         name='log_C1',
                         visible=False,
                         marker_color= df['color'],
                         hovertemplate = 'log_C1 = %{y:.3g}<extra></extra><br>' + 
                                         'x = %{x}' + 
                                         '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         error_y= dict(
                                   type='data',
                                   symmetric=False,
                                   array=lc1U,
                                   arrayminus=lc1L,
                                   visible=False),
                         customdata=df['links']
                    )
     lc2U=[]
     lc2L=[]
     df['log_C2_ci'].apply(lambda x: parse_ci(x, lc2L, lc2U))
     df = df.sort_values(by=['log_C2'],ascending=False)
     logC2Trace = go.Bar(x=[x for _, x in zip(df['log_C2'],df['drug2_name']+' ('+df['drug1_name']+')')],
                         y=df['log_C2'],
                         name='log_C2',
                         visible=False,
                         marker_color= df['color'],
                         hovertemplate = 'log_C2 = %{y:.3g}<extra></extra><br>' + 
                                         'x = %{x}' + 
                                         '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         error_y= dict(
                                   type='data',
                                   symmetric=False,
                                   array=lc2U,
                                   arrayminus=lc2L,
                                   visible=False),
                         customdata=df['links']
                    )
     
     data.append(E1Trace)
     data.append(E2Trace)
     data.append(C1Trace)
     data.append(C2Trace)
     data.append(h1Trace)
     data.append(h2Trace)
     data.append(E1ObsTrace)
     data.append(E2ObsTrace)
     data.append(logC1Trace)
     data.append(logC2Trace)
     data.append(logh1Trace)
     data.append(logh2Trace)

     # confidence interval: hide or show
     button_layer_1_height = 1.55
     # parameter buttons
     button_layer_2_height = 1.4

     updatemenus = list([
          # buttons to show different params vs drug combos
          dict(active=0,
               buttons=list([
                    dict(label='E1',
                         method='update',
                         args=[{'visible': [True, False, False, False, False, False, False, False, False, False, False, False]},
                              {'title': 'Drug 1 Effifacy (E1)'}]),
                    dict(label='E2',
                         method='update',
                         args=[{'visible': [False, True, False, False, False, False, False, False, False, False, False, False]},
                              {'title': 'Drug 2 Effifacy (E2)'}]),
                    dict(label='C1',
                         method='update',
                         args=[{'visible': [False, False, True, False, False, False, False, False, False, False, False, False]},
                              {'title': 'Drug 1 Potency (C1)'}]),
                    dict(label='C2',
                         method='update',
                         args=[{'visible': [False, False, False, True, False, False, False, False, False, False, False, False]},
                              {'title': 'Drug 2 Potency (C2)'}]),
                    dict(label='h1',
                         method='update',
                         args=[{'visible': [False, False, False, False, True, False, False, False, False, False, False, False]},
                              {'title': 'Drug 1 Hill Slope (h1)'}]),
                    dict(label='h2',
                         method='update',
                         args=[{'visible': [False, False, False, False, False, True, False, False, False, False, False, False]},
                              {'title': 'Drug 2 Hill Slope (h2)'}]),
                    dict(label='E1_obs',
                         method='update',
                         args=[{'visible': [False, False, False, False, False, False, True, False, False, False, False, False]},
                              {'title': 'Drug 1 Effifacy_observed (E1_obs)'}]),
                    dict(label='E2_obs',
                         method='update',
                         args=[{'visible': [False, False, False, False, False, False, False, True, False, False, False, False]},
                              {'title': 'Drug 2 Effifacy_observed (E2_obs)'}]),
                    dict(label='log_C1',
                         method='update',
                         args=[{'visible': [False, False, False, False, False, False, False, False, True, False, False, False]},
                              {'title': 'log of Drug 1 Potency (log_C1)'}]),
                    dict(label='log_C2',
                         method='update',
                         args=[{'visible': [False, False, False, False, False, False, False, False, False, True, False, False]},
                              {'title': 'log Drug 2 Potency (log_C2)'}]),
                    dict(label='log_h1',
                         method='update',
                         args=[{'visible': [False, False, False, False, False, False, False, False, False, False, True, False]},
                              {'title': 'log Drug 1 Hill Slope (log_h1)'}]),
                    dict(label='log_h2',
                         method='update',
                         args=[{'visible': [False, False, False, False, False, False, False, False, False, False, False, True]},
                              {'title': 'log Drug 2 Hill Slope (log_h2)'}])
               ]),
               # type="buttons",
               direction="right",
               pad={"r": 10, "t": 10},
               showactive=True,
               x=0.1,
               xanchor="left",
               y=button_layer_1_height,
               yanchor="top"
          ),
          # button for toggling 95% confidence intervals
          dict(
               buttons=list([
                    dict(args=[{"error_y.visible": False}],
                         label='Hide',
                         method='restyle'
                         ),
                    dict(args=[{"error_y.visible": True}],
                         label='Show',
                         method='restyle'
                    )
               ]),
               type = "buttons",
               direction="right",
               pad={"r": 10, "t": 10},
               showactive=True,
               x=0.1,
               xanchor="left",
               y=button_layer_2_height,
               yanchor="top"
          )
     ])

     layout = dict(
          title={
               'text':'Drug 1 Effifacy (E1)',
               'x':0.50,
               'y':0.76,
               'xanchor': 'center'
          },
          template="plotly_white",
          margin=dict(
               l=20,
               r=20,
               b=20,
               t=90,
               pad=4
          ),
          xaxis_title='Drugs',
          yaxis_title='Parameter',
          updatemenus=updatemenus,
          showlegend=False,
          xaxis_tickangle=45,
          bargap=0.15,
          barmode='group',
          annotations=[
               dict(text='Parameters', x=-0.1, xref='paper', y=button_layer_1_height-0.03, yref='paper', align='left', showarrow=False),
               dict(text='95% Confidence<br>Interval', x=-0.1, xref='paper', y=button_layer_2_height-0.02, yref='paper',showarrow=False)
          ]
     )
     fig = go.Figure(data=data, layout=layout)
     
     return fig
