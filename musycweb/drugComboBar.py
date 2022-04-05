'''
Drug combo parameter bar plot
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

def check_batch(row):
     if row['batch'] != 'None':
        return row['drug2_name'] + '_b' + str(row['batch'])
     else: 
          return row['drug2_name']

def combo_bar(dataset_list, task_list):
     col_list = ["sample","drug1_name","drug2_name","expt","batch","task_status","converge_mc_nlls",
               "beta","beta_ci","beta_obs","beta_obs_ci","log_alpha12","log_alpha12_ci","log_alpha21",
               "log_alpha21_ci","R2","log_like_mc_nlls","E0","E0_ci","E1","E1_ci","E2","E2_ci","E3",
               "E3_ci","E1_obs","E1_obs_ci","E2_obs","E2_obs_ci","E3_obs","E3_obs_ci","log_C1","log_C1_ci",
               "log_C2","log_C2_ci","log_h1","log_h1_ci","log_h2","log_h2_ci","h1","h2","C1","C2","time_total",
               "drug1_units","drug2_units","metric_name","fit_beta","boundary_sampling","max_conc_d1","max_conc_d2",
               "min_conc_d1","min_conc_d2","fit_method","dataset_name"]
     
     # create links to task surface plot
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
     df['beta_obs_ci'] = translate_ci(df['beta_obs_ci'])
     df['beta_ci'] = translate_ci(df['beta_ci'])
     df['log_alpha12_ci'] = translate_ci(df['log_alpha12_ci'])
     df['log_alpha21_ci'] = translate_ci(df['log_alpha21_ci'])
     df['E0_ci'] = translate_ci(df['E0_ci'])
     df['E3_ci'] = translate_ci(df['E3_ci'])

     # Adding batches to name to prevent bar stacking 
     df['drug2_name'] = df.apply(lambda x: check_batch(x), axis=1)

     # Default plotly color scheme: change to generate unlimited list of unique colors 
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

     # Generate all parameter traces 
     """ drugs = '(' + df['drug1_name'] + ' , ' + df['drug2_name'] + ')'
     sample = '<br>sample=' + df['sample']
     dataset_names = '<br>dataset= ' + df['dataset_name'] """
     betaU=[]
     betaL=[]
     df['beta_ci'].apply(lambda x: parse_ci(x, betaL, betaU))

     df = df.sort_values(by=['beta'],ascending=False)
     
     betaTrace = go.Bar(x=[x for _, x in zip(df['beta'],'(' + df['drug1_name'] + ' , ' + df['drug2_name'] + ')')],
                         y=df['beta'],
                         name='\u03B2',
                         visible=True,
                         marker_color= df['color'],
                         hovertemplate = '\u03B2 = %{y:.3g}<extra></extra><br>' + 
                                             'x = %{x}' +
                                             '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         error_y= dict(
                                   type='data',
                                   symmetric=False,
                                   array=betaU,
                                   arrayminus=betaL,
                                   visible=False),
                         customdata=df['links']
                    )
     boU = []
     boL = []
     df['beta_obs_ci'].apply(lambda x: parse_ci(x, boL, boU))
     df = df.sort_values(by=['beta_obs'],ascending=False)
     betaObsTrace = go.Bar(x=[x for _, x in zip(df['beta_obs'],'(' + df['drug1_name'] + ' , ' + df['drug2_name'] + ')')],
                              y=df['beta_obs'],
                              name='\u03B2_obs',
                              visible=False,
                              marker_color= df['color'],
                              hovertemplate='\u03B2_obs = %{y:.3g}<extra></extra><br>'
                                             'x = %{x}' + 
                                             '%{text}',
                              text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                              error_y=dict(
                                   type='data',
                                   symmetric=False,
                                   array=boU,
                                   arrayminus=boL,
                                   visible=False),
                              customdata=df['links']
                         )
     a12U=[]
     a12L=[]
     df['log_alpha12_ci'].apply(lambda x: parse_ci(x, a12L, a12U))
     df = df.sort_values(by=['log_alpha12'],ascending=False)
     alpha12Trace = go.Bar(x=[x for _, x in zip(df['log_alpha12'],'(' + df['drug1_name'] + ' , ' + df['drug2_name'] + ')')],
                              y=df['log_alpha12'],
                              name='log_\u03B112',
                              visible=False,
                              marker_color= df['color'],
                              hovertemplate='log_\u03B112 = %{y:.3g}<extra></extra><br>' + 
                                             'x= %{x}'+ 
                                             '%{text}',
                              text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                              error_y=dict(
                                   type='data',
                                   symmetric=False,
                                   array=a12U,
                                   arrayminus=a12L,
                                   visible=False),
                              customdata=df['links']
                              )
     
     a21U=[]
     a21L=[]
     df['log_alpha21_ci'].apply(lambda x: parse_ci(x, a21L, a21U))
     df = df.sort_values(by=['log_alpha21'],ascending=False)
     alpha21Trace = go.Bar(x=[x for _, x in zip(df['log_alpha21'],'(' + df['drug1_name'] + ' , ' + df['drug2_name'] + ')')],
                              y=df['log_alpha21'],
                              name='log_\u03B121',
                              visible=False,
                              marker_color= df['color'],
                              hovertemplate='log_\u03B121 = %{y:.3g}<extra></extra><br>' + 
                                             'x= %{x}' + 
                                             '%{text}',
                              text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'], 
                              error_y=dict(
                                   type='data',
                                   symmetric=False,
                                   array=a21U,
                                   arrayminus=a21L,
                                   visible=False),
                              customdata=df['links']
                              )
     e0U=[]
     e0L=[]
     df['E0_ci'].apply(lambda x: parse_ci(x, e0L, e0U))
     df = df.sort_values(by=['E0'],ascending=False)
     e0Trace = go.Bar(x=[x for _, x in zip(df['E0'],'(' + df['drug1_name'] + ' , ' + df['drug2_name'] + ')')],
                         y=df['E0'],
                         name='E0',
                         visible=False,
                         marker_color= df['color'],
                         hovertemplate='E0 = %{y:.3g}<extra></extra><br>' + 
                                        'x= %{x}' + 
                                        '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         error_y=dict(
                              type='data',
                              symmetric=False,
                              array=e0U,
                              arrayminus=e0L,
                              visible=False),
                         customdata=df['links']
                         )
     e3U=[]
     e3L=[]
     df['E3_ci'].apply(lambda x: parse_ci(x, e3L, e3U))
     df = df.sort_values(by=['E3'],ascending=False)
     e3Trace = go.Bar(x=[x for _, x in zip(df['E3'],'(' + df['drug1_name'] + ' , ' + df['drug2_name'] + ')')],
                         y=df['E3'],
                         name='E3',
                         visible=False,
                         marker_color= df['color'],
                         hovertemplate='E3 = %{y:.3g}<extra></extra><br>' + 
                                        'x= %{x}' + 
                                        '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         error_y=dict(
                              type='data',
                              symmetric=False,
                              array=e3U,
                              arrayminus=e3L,
                              visible=False),
                         customdata=df['links']
                         )
     
     df = df.sort_values(by=['R2'],ascending=False)
     r2Trace = go.Bar(x=[x for _, x in zip(df['R2'],'(' + df['drug1_name'] + ' , ' + df['drug2_name'] + ')')],
                         y=df['R2'],
                         name='R2',
                         visible=False,
                         marker_color= df['color'],
                         hovertemplate='R2 = %{y:.3g}<extra></extra><br>' + 
                                        'x= %{x}' + 
                                        '%{text}',
                         text='<br>sample = ' + df['sample'] + '<br>dataset = ' + df['dataset_name'],
                         customdata=df['links']
                         )
          
     data.append(betaTrace)
     data.append(betaObsTrace)
     data.append(alpha12Trace)
     data.append(alpha21Trace)
     data.append(e0Trace)
     data.append(e3Trace)
     data.append(r2Trace)

     # confidence interval: hide or show
     button_layer_1_height = 1.55
     # parameter buttons
     button_layer_2_height = 1.4

     updatemenus = list([
          # buttons to show different params vs drug combos
          dict(active=0,
               buttons=list([
                    dict(label='\u03B2',
                         method='update',
                         args=[{'visible': [True, False, False, False, False, False, False]},
                              {'title': 'Synergistic Efficacy (\u03B2)'}]),
                    dict(label='\u03B2_obs',
                         method='update',
                         args=[{'visible': [False, True, False, False, False, False, False]},
                              {'title': 'Synergistsic Efficacy Observed (\u03B2_obs)'}]),
                    dict(label='log_\u03B112',
                         method='update',
                         args=[{'visible': [False, False, True, False, False, False, False ]},
                              {'title': 'log_\u03B112'}]),
                    dict(label='log_\u03B121',
                         method='update',
                         args=[{'visible': [False, False, False, True, False, False, False ]},
                              {'title': 'log_\u03B121'}]),
                    dict(label='E0',
                         method='update',
                         args=[{'visible': [False, False, False, False, True, False, False]},
                              {'title': 'Fitted basal effect when [drug1]=[drug2]=0 (E0)'}]),
                    dict(label='E3',
                         method='update',
                         args=[{'visible': [False, False, False, False, False, True, False]},
                              {'title': 'Fitted effect for [drug2]->inf and [drug1]=0 (E3)'}]),
                    dict(label='R2',
                         method='update',
                         args=[{'visible': [False, False, False, False, False, False, True]},
                              {'title': 'R Squared of Fit (R2)'}]),
                    dict(label='ALL',
                         method='update',
                         args=[{'visible': [True, True, True, True, True, True, True]},
                              {'title': 'All Drug Combo Parameters'}])
               ]),
               type = "buttons",
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
               'text':'Synergistic Efficacy (\u03B2)',
               'x':0.50,
               'y':0.76,
               'xanchor': 'center'
          },
          margin=dict(
               l=20,
               r=20,
               b=20,
               t=90,
               pad=4
          ),
          template="plotly_white",
          xaxis_title='Drug Combinations',
          yaxis_title='Parameter',
          updatemenus=updatemenus,
          hovermode='closest',
          showlegend=False,
          xaxis_tickangle=45,
          bargap=0.15,
          annotations=[
               dict(text='Parameters', x=-0.1, xref='paper', y=button_layer_1_height-0.03, yref='paper', align='left', showarrow=False),
               dict(text='95% Confidence<br>Interval', x=-0.1, xref='paper', y=button_layer_2_height-0.02, yref='paper',showarrow=False)
          ]
     )
     fig1 = go.Figure(data=data, layout=layout)
     
     return fig1

