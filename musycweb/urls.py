from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about', views.about, name='about'),
    path('help', views.help, name='help'),
    path('terms', views.terms, name='terms'),
    path('account', views.account, name='account'),
    path('upload', views.create_dataset, name='create_dataset'),
    path('dataset/<int:dataset_id>', views.view_dataset, name='view_dataset'),
    path('dataset/<int:dataset_id>/delete', views.delete_dataset, name='ajax_delete_dataset'),
    path('dataset/<int:dataset_id>/rename', views.rename_dataset, name='ajax_rename_dataset'),
    path('dataset/<int:dataset_id>/csv', views.ajax_dataset_csv, name='ajax_dataset_csv'),
    path('task/<uuid:task_id>', views.view_task, name='view_task'),
    path('task/<uuid:task_id>/csv', views.ajax_task_csv, name='ajax_task_csv'),
    path('task/<uuid:task_id>/surfaceplot', views.ajax_surface_plot, name='ajax_surface_plot'),
    path('task/<uuid:task_id>/curve1', views.ajax_curve_plot, name='ajax_curve_plot'),
    path('task/<uuid:task_id>/curve2', views.ajax_curve2_plot, name='ajax_curve2_plot'),
    path('task/<uuid:task_id>/plot_download', views.ajax_get_plot2, name='ajax_get_plot2'),
    path('dataset/<int:dataset_id>/tasks', views.ajax_tasks, name='ajax_tasks'),
    path('dataset/<int:dataset_id>/status', views.ajax_task_status, name='ajax_task_status'),
    path('analysis/<int:dataset_id>', views.analysis, name='analysis'),
    path('analysis/<int:dataset_id>/barplot', views.ajax_comboBar_plot, name='ajax_comboBar_plot'),
    path('analysis/<int:dataset_id>/barplot2', views.ajax_singleBar_plot, name='ajax_singleBar_plot'),
    path('analysis/<int:dataset_id>/scatterplot',views.ajax_comboScatter_plot, name='ajax_comboScatter_plot'),
    path('analysis/<int:dataset_id>/scatterplot2',views.ajax_singleScatter_plot, name='ajax_singleScatter_plot'),
    path('analysis/<int:dataset_id>/plot_download', views.ajax_get_plot, name='ajax_get_plot')
]
