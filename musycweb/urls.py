from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about', views.about, name='about'),
    path('account', views.account, name='account'),
    path('upload', views.create_dataset, name='create_dataset'),
    path('dataset/<int:dataset_id>', views.view_dataset, name='view_dataset'),
    path('dataset/<int:dataset_id>/delete', views.delete_dataset, name='ajax_delete_dataset'),
    path('dataset/<int:dataset_id>/csv', views.ajax_dataset_csv, name='ajax_dataset_csv'),
    path('task/<uuid:task_id>', views.view_task, name='view_task'),
    path('task/<uuid:task_id>/csv', views.ajax_task_csv, name='ajax_task_csv'),
    path('task/<uuid:task_id>/surfaceplot', views.ajax_surface_plot, name='ajax_surface_plot'),
    path('dataset/<int:dataset_id>/tasks', views.ajax_tasks, name='ajax_tasks'),
    path('dataset/<int:dataset_id>/status', views.ajax_task_status, name='ajax_task_status')
]

