'''
Drug combination scatter plot
Author: Monica Del Valle
'''

import plotly.graph_objects as go
import plotly.offline
import csv
import pandas as pd
import string


def translate_ci(df_ci):
     return df_ci.str.translate(str.maketrans({'[':'',']':''}))

def parse_ci(df_ci, lower, upper):
     temp = df_ci.split(',')
     lower.append(float(temp[0]))
     upper.append(float(temp[1]))

# This would need to be changed to the musyc base url
def create_link(task_id):
     link = 'http://127.0.0.1/task/' + task_id
     return link

def combo_scatter(dataset_list, task_list):
     # read parameters .csv file to read the params to toggle
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
     df['beta_obs_ci'] = translate_ci(df['beta_obs_ci'])
     df['beta_ci'] = translate_ci(df['beta_ci'])
     df['log_alpha12_ci'] = translate_ci(df['log_alpha12_ci'])
     df['log_alpha21_ci'] = translate_ci(df['log_alpha21_ci'])
     df['E0_ci'] = translate_ci(df['E0_ci'])
     df['E3_ci'] = translate_ci(df['E3_ci'])

     # default plotly color scheme: change to generate unlimited list of unique colors. 
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

     button_layer_1_height = 1.0
     button_layer_2_height = 0.54

     fig = go.Figure() 
     
     # Generate all parameter traces 
     drugs = '(drug1 = ' + df['drug1_name'] + ' , drug2 = ' + df['drug2_name'] + ')<br>'
     sample = 'sample = ' + df['sample']
     batch = '<br>batch = ' + df['batch'].apply(str)
     dataset_names = '<br>dataset = ' + df['dataset_name']

     # default trace: beta vs alpha12
     fig.add_trace(go.Scatter(
          x=df['beta'],
          y=df['log_alpha12'],
          mode='markers',
          marker=dict(size=10, color=df['color']),
          hovertemplate = 'x = %{x:.3g}<extra></extra><br>' +
                         'y = %{y:.3g}<br>' +
                         '%{text}',
          text=drugs + sample + batch + dataset_names,
          customdata=df['links']
     ))
     
     updatemenus = list([
          # buttons to show x-axis
          dict(buttons=list([
                    dict(label='\u03B2',
                         method='restyle',
                         args=['x', [df['beta']]]),
                    dict(label='\u03B2_obs',
                         method='restyle',
                         args=['x', [df['beta_obs']]]),
                    dict(label='log_\u03B112',
                         method='restyle',
                         args=['x', [df['log_alpha12']]]),
                    dict(label='log_\u03B121',
                         method='restyle',
                         args=['x', [df['log_alpha21']]]),
                    dict(label='E0',
                         method='restyle',
                         args=['x', [df['E0']]]),
                    dict(label='E3',
                         method='restyle',
                         args=['x', [df['E3']]]), 
                    dict(label='R2',
                         method='restyle',
                         args=['x', [df['R2']]])
               ]),
               direction="down",
               pad={"r": 10, "t": 10},
               showactive=True,
               x=1.03,
               xanchor="left",
               y=button_layer_2_height,
               yanchor="top"
          ),
          #buttons to show y axis
          dict(active=2,
               buttons=list([
                    dict(label='\u03B2',
                         method='restyle',
                         args=['y',[df['beta']]]),
                    dict(label='\u03B2_obs',
                         method='restyle',
                         args=['y',[df['beta_obs']]]),
                    dict(label='log_\u03B112',
                         method='restyle',
                         args=['y', [df['log_alpha12']]]),
                    dict(label='log_\u03B121',
                         method='restyle',
                         args=['y', [df['log_alpha21']]]),
                    dict(label='E0',
                         method='restyle',
                         args=['y', [df['E0']]]),
                    dict(label='E3',
                         method='restyle',
                         args=['y', [df['E3']]]),
                    dict(label='R2',
                         method='restyle',
                         args=['y', [df['R2']]])
               ]),
               direction="down",
               pad={"r": 10, "t": 10},
               showactive=True,
               x=-0.3,
               y=button_layer_1_height,
               xanchor="left",
               yanchor="top"
          )
     ])

     layout = dict(
          title={
               'text':'Drug Combination Parameter Comparison',
               'x':0.53,
               'y':0.90,
               'xanchor': 'center'
          }, 
          template="plotly_white",
          hovermode='closest',
          updatemenus=updatemenus,
          annotations=[
               dict(text='y-axis', x=-0.3, xref='paper', y=button_layer_1_height+0.03, yref='paper', align='left', showarrow=False),
               dict(text='x-axis', x=1.13, xref='paper', y=0.55, yref='paper',showarrow=False)
          ]
     )

     fig.update_layout(layout)
     fig.update_xaxes(zeroline=True, zerolinewidth=1.5, zerolinecolor='black', range=[-2.0, 2.0])
     fig.update_yaxes(zeroline=True, zerolinewidth=1.5, zerolinecolor='black', range=[-2.0, 2.0])

     return fig


