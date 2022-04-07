from django.shortcuts import render, reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404,\
    JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from matplotlib.pyplot import scatter
from .forms import CreateDatasetForm #, CreateProjectForm
from .models import Dataset, DatasetTask #, Project
from .tasks import process_dataset, DataError
from django.contrib import messages
from django_celery_results.models import TaskResult
from django.template.context_processors import csrf
from musyc_code.SynergyCalculator.doseResponseSurfPlot import \
    plotDoseResponseSurf
from crispy_forms.utils import render_crispy_form
import numpy as np
import plotly.offline
from plotly.utils import PlotlyJSONEncoder
from plotly.offline.offline import get_plotlyjs
from django.utils.html import escape
from django.utils.html import strip_tags
import re
import json
# For shared projects
from django.contrib.auth import get_user_model
# New plots
from .drugComboBar import combo_bar
from .singleDrugBar import single_bar
from .drugComboScatter import combo_scatter
from .singleDrugScatter import single_scatter
from .doseResponseCurves import doseResponse_Curve
import math
import csv
import io


def about(request):
    return render(request, 'about.html', {})


def help(request):
    return render(request, 'help.html', {})


def terms(request):
    return render(
        request,
        'terms_popup.html' if 'popup' in request.GET else 'terms_with_nav.html',
        {}
    )

@login_required
def account(request):
    return render(request, 'account/account.html')

# @login_required
# def index(request, project_id):
#     p = Project.objects.get(id=project_id, deleted_date=None)
#     # Make sure user can see projects shared with them 
#     shared_ps = Project.objects.filter(shared_with__email=request.user.email, id=project_id)
#     datasets = None
#     shared_ds = None
#     # Show datasets for owned project 
#     if request.user == p.owner:
#         datasets = Dataset.objects.filter(
#             owner=request.user,
#             project_id=project_id,
#             deleted_date=None
#         ).order_by('-creation_date')
#     # Show datasets for shared projects
#     elif shared_ps is not None:
#         shared_ds = Dataset.objects.filter(
#             project_id=project_id,
#             deleted_date=None
#         ).order_by('-creation_date')

#     return render(request, 'index.html', {'datasets': datasets, 'p': p, 'shared_ds': shared_ds})

# New homw page; Show all datasets owned by user
@login_required
def all_datasets(request):
    datasets = Dataset.objects.filter(
        owner=request.user,
        deleted_date=None
    ).order_by('-creation_date')
    
    return render(request, 'dataset_index.html', {'datasets': datasets})


@login_required
def analysis(request, dataset_id): 
    try:
        d = Dataset.objects.get(id=dataset_id, deleted_date=None)
    except Dataset.DoesNotExist:
        raise Http404()
    
      if d.owner_id != request.user.id and not request.user.is_staff:
        raise Http404()
        
    datasets = Dataset.objects.filter(
        owner=request.user,
        deleted_date=None
    ).order_by('-creation_date')

    return render(request, 'analysis.html', {'d': d, 'datasets': datasets})

def _create_dataset_response(request, form):
    if 'ajax' in request.GET:
        return JsonResponse({
            'success': False,
            'form_html': render_crispy_form(form, context=csrf(request))
        })
    else:
        return render(request, 'create_dataset.html', {
            'form': form
        })


@login_required
def create_dataset(request):
    if request.method == 'POST':
        form = CreateDatasetForm(request.POST, request.FILES)
        if form.is_valid():
            d = Dataset(
                owner=request.user,
                name=form.cleaned_data['name'],
                file=form.cleaned_data['file'],
                orientation=form.cleaned_data['orientation'],
                metric_name=form.cleaned_data['metric_name'],
                e0_lower=form.cleaned_data['e0_lower_bound'],
                e0_upper=form.cleaned_data['e0_upper_bound'],
                emax_lower=form.cleaned_data['emax_lower_bound'],
                emax_upper=form.cleaned_data['emax_upper_bound']
            )
            d.save()

            # Fire off the fitting tasks
            try:
                process_dataset(d, request=request)
            except DataError as e:
                form.add_error('file', e)
                d.delete()
                return _create_dataset_response(request, form, p)

            # Success
            if 'ajax' in request.GET:
                return JsonResponse({'success': True, 'dataset_id': d.id})
            else:
                return HttpResponseRedirect(reverse(
                    'view_dataset', kwargs={'dataset_id': d.id}
                ))
    else:
        form = CreateDatasetForm()

    return _create_dataset_response(request, form)


@login_required
def view_dataset(request, dataset_id):
    try:
        d = Dataset.objects.get(id=dataset_id, deleted_date=None)
    except Dataset.DoesNotExist:
        raise Http404()

    if d.owner_id != request.user.id and not request.user.is_staff:
        raise Http404()
    
    return render(request, 'dataset.html', {'d': d})


@login_required
def delete_dataset(request, dataset_id):
    if request.method != 'DELETE':
        return HttpResponseBadRequest()
    d = Dataset.objects.filter(id=dataset_id, deleted_date=None)
    if not request.user.is_staff:
        d = d.filter(owner_id=request.user.id)
    try:
        d = d.get()
    except Dataset.DoesNotExist:
        raise Http404()

    d.deleted_date = timezone.now()
    d.save()

    messages.success(request, f'Dataset "{d.name}" was deleted')
    return JsonResponse({'status': 'success', 'dataset_id': dataset_id})


@login_required
def rename_dataset(request, dataset_id):
    if request.method != 'POST':
        return HttpResponseBadRequest()
    d = Dataset.objects.filter(id=dataset_id, deleted_date=None)
    if not request.user.is_staff:
        d = d.filter(owner_id=request.user.id)
    try:
        d = d.get()
    except Dataset.DoesNotExist:
        raise Http404()

    if 'dataset-name' not in request.POST:
        return HttpResponseBadRequest('Missing dataset-name field')

    d.name = request.POST['dataset-name']
    d.save()

    return JsonResponse({'status': 'success', 'dataset_id': dataset_id,
                         'dataset_name': d.name})


@login_required
def ajax_tasks(request, dataset_id):
    try:
        d = Dataset.objects.get(id=dataset_id, deleted_date=None)
    except Dataset.DoesNotExist:
        raise Http404()

    if d.owner_id != request.user.id and not request.user.is_staff:
        raise Http404()

    tasks = DatasetTask.objects.filter(dataset=d).prefetch_related(
        'task').order_by('drug1', 'drug2', 'sample')

    return JsonResponse({'data': [
        [t.drug1, t.drug2, t.sample, t.status, t.task_id, t.batch]
        for t in tasks
    ], 'use_batches': any(t.batch for t in tasks)})


@login_required
def ajax_dataset_csv(request, dataset_id):
    tasks = DatasetTask.objects.filter(
        dataset_id=dataset_id,
        dataset__deleted_date=None
    ).prefetch_related('task').select_related('dataset')

    if not tasks:
        return HttpResponse(f'Dataset {dataset_id} has no tasks or not found')

    if tasks[0].dataset.owner_id != request.user.id and \
            not request.user.is_staff:
        return HttpResponse(f'Dataset {dataset_id} not found', status=404)

    csv_lines = tasks[0].result_csv_header + '\n'
    for task in tasks:
        csv_lines += task.result_csv_line + '\n'

    dataset_name = tasks[0].dataset.name.replace('"', '')

    response = HttpResponse(csv_lines, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; ' \
                                      f'filename="{dataset_name}.csv"'
    return response


@login_required
def view_task(request, task_id):
    try:
        task = DatasetTask.objects.filter(
            task_id=task_id,
            dataset__deleted_date=None
        ).select_related(
            'task').select_related('dataset').get()
    except DatasetTask.DoesNotExist:
        raise Http404()

    if task.dataset.owner_id != request.user.id and not request.user.is_staff:
        raise Http404()

    return render(request, 'task_result.html', {'task': task})


@login_required
def ajax_task_csv(request, task_id):
    try:
        task = DatasetTask.objects.filter(
            task_id=task_id,
            dataset__deleted_date=None
        ).select_related(
            'task').select_related('dataset').get()
    except DatasetTask.DoesNotExist:
        return HttpResponse(f'Task {task_id} not found', status=404)

    if task.dataset.owner_id != request.user.id and not request.user.is_staff:
        return HttpResponse(f'Task {task_id} not found', status=404)

    if not task.task:
        return HttpResponse(f'Task {task_id} task object not found', status=404)

    if task.task.status == 'FAILED':
        return HttpResponse(f'Task {task.task_id} Failed')

    if task.task.status != 'SUCCESS':
        return HttpResponse(f'Task {task.task_id} not complete (status: '
                            f'{task.task.status})')

    # OK to return CSV
    response = HttpResponse(task.result_csv, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{task_id}.csv"'
    return response


@login_required
def ajax_surface_plot(request, task_id):
    try:
        task = DatasetTask.objects.filter(
            task_id=task_id,
            dataset__deleted_date=None
        ).select_related(
            'task').select_related('dataset').get()
    except DatasetTask.DoesNotExist:
        raise Http404()

    if task.dataset.owner_id != request.user.id and not request.user.is_staff:
        raise Http404()

    # Get any plot
    rd = task.result_dict
    if rd:
        # Apply HTML escapes
        for field in ('sample', 'drug1_name', 'drug2_name', 'batch',
                      'metric_name'):
            if field in rd:
                rd[field] = escape(rd[field])
        # Force a surface plot - can't handle matplotlib yet
        rd['boundary_sampling'] = 0
        rd['to_save_plots'] = 1
        rd['save_direc'] = None
        plot = plotDoseResponseSurf(
            rd,
            np.array(rd['d1']),
            np.array(rd['d2']),
            np.array(rd['dip']),
            np.array(rd['dip_sd'])
        )['plot']
        plot_html = plotly.offline.plot(plot, output_type='div',
                                        include_plotlyjs=False)
    else:
        plot_html = '<strong>Plot not ready</strong>'

    # for creating plot html for download
    if 'plotType' in request.GET:
        return plot
    else:
        return HttpResponse(plot_html)


@login_required
def ajax_task_status(request, dataset_id):
    tasks = DatasetTask.objects.filter(
        dataset_id=dataset_id,
        dataset__deleted_date=None
    ).prefetch_related('task')
    
    if not request.user.is_staff:
        tasks = tasks.filter(dataset__owner_id=request.user.id)
        
    return JsonResponse({task.task_id: task.status for task in tasks})

# New plotting code
@login_required
def ajax_get_plot(request, dataset_id):
    file_type = 'html'

    # Get plot figures
    if request.GET['plotType'] == 'comboBar':
        plot_fig = ajax_comboBar_plot(request, dataset_id)
    elif request.GET['plotType'] == 'singleBar':
        plot_fig = ajax_singleBar_plot(request, dataset_id)
    elif request.GET['plotType'] == 'comboScatter':
        plot_fig = ajax_comboScatter_plot(request, dataset_id)
    elif request.GET['plotType'] == 'singleScatter':
        plot_fig = ajax_singleScatter_plot(request, dataset_id)
    
    # Return file to download (as_attachment is only option right now)
    # as_attachment = request.GET.get('download', '0') == '1'
    as_attachment = True

    if file_type == 'html':
        template = 'plotly_plot{}.html'.format('_standalone')
        context = {
            'data': json.dumps(plot_fig, cls=PlotlyJSONEncoder),
            'page_title': strip_tags(plot_fig['layout']['title']['text'])
        }
        
        if as_attachment:
            context['plotlyjs'] = get_plotlyjs()
        response = render(request, template, context)
    else:
        return HttpResponse('Unknown file type: %s' % file_type, status=400)
    
    if as_attachment:
        try:
            # title = plot_fig['layout']['title']['text']
            title = 'plot_' + request.GET['plotType']
        except KeyError:
            title = 'Plot'
        response['Content-Disposition'] = \
            'attachment; filename="{}.{}"'.format(strip_tags(title), file_type)
    return response

@login_required
def ajax_get_plot2(request, task_id):
    file_type = 'html'

    if request.GET['plotType'] == 'surface':
        plot_fig = ajax_surface_plot(request, task_id)
    elif request.GET['plotType'] == 'drCurve1':
        plot_fig = ajax_curve_plot(request, task_id)
    elif request.GET['plotType'] == 'drCurve2':
        plot_fig = ajax_curve2_plot(request, task_id)
    
    # Return file to download
    as_attachment = request.GET.get('download', '0') == '1'

    if file_type == 'html':
        template = 'plotly_plot{}.html'.format('_standalone') # if as_attachment else '')
        context = {
            'data': json.dumps(plot_fig, cls=PlotlyJSONEncoder),
            'page_title': strip_tags(plot_fig['layout']['title']['text'])
        }
        if as_attachment:
            context['plotlyjs'] = get_plotlyjs()
        response = render(request, template, context)
    else:
        return HttpResponse('Unknown file type: %s' % file_type, status=400)
    
    if as_attachment:
        try:
            # TODO: Change title to drug1 name and drug2 name _ dataset for the curve plots
            # title = plot_fig['layout']['title']['text']
            title = 'plot_' + request.GET['plotType']
        except KeyError:
            title = 'Plot'
        response['Content-Disposition'] = \
            'attachment; filename="{}.{}"'.format(strip_tags(title), file_type)
    return response

@login_required
def ajax_curve_plot(request, task_id):
    try:
        task = DatasetTask.objects.filter(
            task_id=task_id,
            dataset__deleted_date=None
        ).select_related(
            'task').select_related('dataset').get()
    except DatasetTask.DoesNotExist:
        raise Http404()

    if task.dataset.owner_id != request.user.id and not request.user.is_staff:
        raise Http404()

    # Get any plot
    rd = task.result_dict
    if rd:
        # Apply HTML escapes
        for field in ('sample', 'drug1_name', 'drug2_name', 'batch',
                    'metric_name'):
            if field in rd:
                rd[field] = escape(rd[field])

        rd['boundary_sampling']= 1
        rd['to_save_plots'] = 1
        rd['save_direc'] = None
        
        curve1, curve2 = doseResponse_Curve(
            rd,
            np.array(rd['d1']),
            np.array(rd['d2']),
            np.array(rd['dip']),
            np.array(rd['dip_sd'])
        )

        plot1_html = plotly.offline.plot(curve1, output_type='div',
                                        include_plotlyjs=False)
    
    if 'plotType' in request.GET:
        return curve1
    else: 
        return HttpResponse(plot1_html)
    
@login_required
def ajax_curve2_plot(request, task_id):
    try:
        task = DatasetTask.objects.filter(
            task_id=task_id,
            dataset__deleted_date=None
        ).select_related(
            'task').select_related('dataset').get()
    except DatasetTask.DoesNotExist:
        raise Http404()

    if task.dataset.owner_id != request.user.id and not request.user.is_staff:
        raise Http404()

    # Get any plot
    rd = task.result_dict
    if rd:
        # Apply HTML escapes
        for field in ('sample', 'drug1_name', 'drug2_name', 'batch',
                    'metric_name'):
            if field in rd:
                rd[field] = escape(rd[field])

        rd['boundary_sampling']= 1
        rd['to_save_plots'] = 1
        rd['save_direc'] = None
        
        curve1, curve2 = doseResponse_Curve(
            rd,
            np.array(rd['d1']),
            np.array(rd['d2']),
            np.array(rd['dip']),
            np.array(rd['dip_sd'])
        )
        # return HttpResponse(curve2) 
        plot2_html = plotly.offline.plot(curve2, output_type='div',
                                        include_plotlyjs=False)

        if 'plotType' in request.GET:
            return curve2
        else:
            return HttpResponse(plot2_html)
        
@login_required
def ajax_comboBar_plot(request, dataset_id):
    # To show the added datasets
    if request.method == 'POST':
        datasets = []
        for key in request.POST:
            if key != 'csrfmiddlewaretoken':
                datasets.append(request.POST[key])
 
        dataset_list =[]
        task_list = []
        for x in datasets:
            tasks = DatasetTask.objects.filter(
                dataset_id=x,
                dataset__deleted_date=None
            ).prefetch_related('task').select_related('dataset')

            if not tasks:
                return HttpResponse(f'Dataset {x} has no tasks or not found')

            if tasks[0].dataset.owner_id != request.user.id and \
                    not request.user.is_staff:
                return HttpResponse(f'Dataset {x} not found', status=404)
            
            for task in tasks:
                csv_lines = '"'
                csv_lines += task.result_csv_line.replace(' ', '').lstrip("\"")
                test = csv_lines.split('\",\"')
                test = [x.lstrip('\"') for x in test]
                test = [x.replace('\"', '') for x in test]
                dataset_list.append(test)
                task_list.append(task.task_id)

        barPlots = combo_bar(dataset_list, task_list)
        bar_final_plot = get_plot_html(barPlots)
        return HttpResponse(bar_final_plot)
    elif 'plotType' in request.GET:
        datasets = []
        for key in request.GET:
            if key != 'csrfmiddlewaretoken' and key != 'plotType' and key != 'download':
                datasets.append(request.GET[key])
        
        dataset_list =[]
        task_list = []
        for x in datasets:
            tasks = DatasetTask.objects.filter(
                dataset_id=x,
                dataset__deleted_date=None
            ).prefetch_related('task').select_related('dataset')

            if not tasks:
                return HttpResponse(f'Dataset {x} has no tasks or not found')

            if tasks[0].dataset.owner_id != request.user.id and \
                    not request.user.is_staff:
                return HttpResponse(f'Dataset {x} not found', status=404)
            
            for task in tasks:
                csv_lines = '"'
                csv_lines += task.result_csv_line.replace(' ', '').lstrip("\"")
                test = csv_lines.split('\",\"')
                test = [x.lstrip('\"') for x in test]
                test = [x.replace('\"', '') for x in test]
                dataset_list.append(test)
                task_list.append(task.task_id)

        barPlots = combo_bar(dataset_list, task_list)
        return barPlots
    else:
        tasks = DatasetTask.objects.filter(
            dataset_id=dataset_id,
            dataset__deleted_date=None
        ).prefetch_related('task').select_related('dataset')

        if not tasks:
            return HttpResponse(f'Dataset {dataset_id} has no tasks or not found')

        if tasks[0].dataset.owner_id != request.user.id and \
                not request.user.is_staff:
            return HttpResponse(f'Dataset {dataset_id} not found', status=404)
        
        task_list = []
        results = []
        for t in tasks:
            task = DatasetTask.objects.filter(
                task_id=t.task_id,
                dataset__deleted_date=None
            ).select_related('task').select_related('dataset').get()

            csv_lines = '"'
            csv_lines += task.result_csv_line.replace(' ', '').lstrip("\"")
            test = csv_lines.split('\",\"')
            test = [x.lstrip('\"') for x in test]
            test = [x.replace('\"', '') for x in test]
            results.append(test)
            task_list.append(t.task_id)
        
        barPlot = combo_bar(results, task_list)
        bar_final_plot = get_plot_html(barPlot)
        return HttpResponse(bar_final_plot)
    
@login_required
def ajax_singleBar_plot(request, dataset_id):
    if request.method == 'POST':
        datasets = []
        # Keys are the checked dataset id's
        for key in request.POST:
            if key != 'csrfmiddlewaretoken':
                datasets.append(request.POST[key])
        
        dataset_list =[]
        task_list = []
        # x is a dataset_id in the list of dataset id's
        for x in datasets:
            tasks = DatasetTask.objects.filter(
                dataset_id=x,
                dataset__deleted_date=None
            ).prefetch_related('task').select_related('dataset')

            if not tasks:
                return HttpResponse(f'Dataset {x} has no tasks or not found')

            if tasks[0].dataset.owner_id != request.user.id and \
                    not request.user.is_staff:
                return HttpResponse(f'Dataset {x} not found', status=404)
            
            for task in tasks:
                csv_lines = '"'
                csv_lines += task.result_csv_line.replace(' ', '').lstrip("\"")
                test = csv_lines.split('\",\"')
                test = [x.lstrip('\"') for x in test]
                test = [x.replace('\"', '') for x in test]
                dataset_list.append(test)
                # Added for creating URL for surface plot
                task_list.append(task.task_id)

        barPlots = single_bar(dataset_list, task_list)
        bar_final_plot = get_plot_html(barPlots)
        return HttpResponse(bar_final_plot)
    elif 'plotType' in request.GET:
        datasets = []
        for key in request.GET:
            if key != 'csrfmiddlewaretoken' and key != 'plotType' and key != 'download':
                datasets.append(request.GET[key])
        
        dataset_list =[]
        task_list = []
        # x is a dataset_id in the list of dataset id's
        for x in datasets:
            tasks = DatasetTask.objects.filter(
                dataset_id=x,
                dataset__deleted_date=None
            ).prefetch_related('task').select_related('dataset')

            if not tasks:
                return HttpResponse(f'Dataset {x} has no tasks or not found')

            if tasks[0].dataset.owner_id != request.user.id and \
                    not request.user.is_staff:
                return HttpResponse(f'Dataset {x} not found', status=404)
            
            for task in tasks:
                csv_lines = '"'
                csv_lines += task.result_csv_line.replace(' ', '').lstrip("\"")
                test = csv_lines.split('\",\"')
                test = [x.lstrip('\"') for x in test]
                test = [x.replace('\"', '') for x in test]
                dataset_list.append(test)
                # Added for creating URL for surface plot
                task_list.append(task.task_id)

        barPlots = single_bar(dataset_list, task_list)
        return barPlots
    else:
        tasks = DatasetTask.objects.filter(
                dataset_id=dataset_id,
                dataset__deleted_date=None
            ).prefetch_related('task').select_related('dataset')

        if not tasks:
            return HttpResponse(f'Dataset {dataset_id} has no tasks or not found')

        if tasks[0].dataset.owner_id != request.user.id and \
                not request.user.is_staff:
            return HttpResponse(f'Dataset {dataset_id} not found', status=404)

        task_list = []
        results = []
        for t in tasks:
            task = DatasetTask.objects.filter(
                task_id=t.task_id,
                dataset__deleted_date=None
            ).select_related(
                'task').select_related('dataset').get()

            csv_lines = '"'
            csv_lines += task.result_csv_line.replace(' ', '').lstrip("\"")
            test = csv_lines.split('\",\"')
            test = [x.lstrip('\"') for x in test]
            test = [x.replace('\"', '') for x in test]
            results.append(test)
            # Added for creating URL to surface plot
            task_list.append(t.task_id)
    
    barPlot = single_bar(results, task_list)
    bar_final_plot = get_plot_html(barPlot)
    return HttpResponse(bar_final_plot)

@login_required
def ajax_comboScatter_plot(request, dataset_id):
    if request.method == 'POST':
        datasets = []
        for key in request.POST:
            if key != 'csrfmiddlewaretoken':
                datasets.append(request.POST[key])
        
        dataset_list =[]
        task_list = []
        for x in datasets:
            tasks = DatasetTask.objects.filter(
                dataset_id=x,
                dataset__deleted_date=None
            ).prefetch_related('task').select_related('dataset')

            if not tasks:
                return HttpResponse(f'Dataset {x} has no tasks or not found')
            
            if tasks[0].dataset.owner_id != request.user.id and \
                    not request.user.is_staff:
                return HttpResponse(f'Dataset {x} not found', status=404)
            
            for task in tasks:
                csv_lines = '"'
                csv_lines += task.result_csv_line.replace(' ', '').lstrip("\"")
                test = csv_lines.split('\",\"')
                test = [x.lstrip('\"') for x in test]
                test = [x.replace('\"', '') for x in test]
                dataset_list.append(test)
                # Add the task_id for each task within that dataset
                task_list.append(task.task_id)

        comboScatterPlots = combo_scatter(dataset_list, task_list)
        comboScatter_final_plot = get_plot_html(comboScatterPlots)
        return HttpResponse(comboScatter_final_plot)
    elif 'plotType' in request.GET:
        datasets = []
        for key in request.GET:
            if key != 'csrfmiddlewaretoken' and key != 'plotType' and key != 'download':
                datasets.append(request.GET[key])
        
        dataset_list =[]
        task_list = []
        for x in datasets:
            tasks = DatasetTask.objects.filter(
                dataset_id=x,
                dataset__deleted_date=None
            ).prefetch_related('task').select_related('dataset')

            if not tasks:
                return HttpResponse(f'Dataset {x} has no tasks or not found')

            if tasks[0].dataset.owner_id != request.user.id and \
                    not request.user.is_staff:
                return HttpResponse(f'Dataset {x} not found', status=404)
            
            for task in tasks:
                csv_lines = '"'
                csv_lines += task.result_csv_line.replace(' ', '').lstrip("\"")
                test = csv_lines.split('\",\"')
                test = [x.lstrip('\"') for x in test]
                test = [x.replace('\"', '') for x in test]
                dataset_list.append(test)
                # Add the task_id for each task within that dataset
                task_list.append(task.task_id)

        comboScatterPlots = combo_scatter(dataset_list, task_list)
        return comboScatterPlots
    else:
        tasks = DatasetTask.objects.filter(
                dataset_id=dataset_id,
                dataset__deleted_date=None
            ).prefetch_related('task').select_related('dataset')

        if not tasks:
            return HttpResponse(f'Dataset {dataset_id} has no tasks or not found')

        if tasks[0].dataset.owner_id != request.user.id and \
                not request.user.is_staff:
            return HttpResponse(f'Dataset {dataset_id} not found', status=404)
        
        task_list = []
        results = []
        for t in tasks:
            task = DatasetTask.objects.filter(
                task_id=t.task_id,
                dataset__deleted_date=None
            ).select_related('task').select_related('dataset').get()

            csv_lines = '"'
            csv_lines += task.result_csv_line.replace(' ', '').lstrip("\"")
            test = csv_lines.split('\",\"')
            test = [x.lstrip('\"') for x in test]
            test = [x.replace('\"', '') for x in test]
            results.append(test)
            task_list.append(t.task_id)
        
        scatterPlot = combo_scatter(results, task_list)
        comboScatter_final_plot = get_plot_html(scatterPlot)
        return HttpResponse(comboScatter_final_plot)

@login_required
def ajax_singleScatter_plot(request, dataset_id):
    # Update the plot based on checked form
    if request.method == 'POST':
        datasets = []
        for key in request.POST:
            if key != 'csrfmiddlewaretoken':
                datasets.append(request.POST[key])

        task_list = []
        dataset_list =[]
        for x in datasets:
            tasks = DatasetTask.objects.filter(
                dataset_id=x,
                dataset__deleted_date=None
            ).prefetch_related('task').select_related('dataset')

            if not tasks:
                return HttpResponse(f'Dataset {x} has no tasks or not found')

            if tasks[0].dataset.owner_id != request.user.id and \
                    not request.user.is_staff:
                return HttpResponse(f'Dataset {x} not found', status=404)
            
            for task in tasks:
                csv_lines = '"'
                csv_lines += task.result_csv_line.replace(' ', '').lstrip("\"")
                test = csv_lines.split('\",\"')
                test = [x.lstrip('\"') for x in test]
                test = [x.replace('\"', '') for x in test]
                dataset_list.append(test)
                # Add the task_id for each task within that dataset
                task_list.append(task.task_id)

        scatterPlot = single_scatter(dataset_list, task_list)
        singleScatter_final_plot = get_plot_html(scatterPlot)
        return HttpResponse(singleScatter_final_plot) 
    elif 'plotType' in request.GET:
        datasets = []
        for key in request.GET:
            if key != 'csrfmiddlewaretoken' and key != 'plotType' and key != 'download':
                datasets.append(request.GET[key])
        
        task_list = []
        dataset_list =[]
        for x in datasets:
            tasks = DatasetTask.objects.filter(
                dataset_id=x,
                dataset__deleted_date=None
            ).prefetch_related('task').select_related('dataset')

            if not tasks:
                return HttpResponse(f'Dataset {x} has no tasks or not found')

            if tasks[0].dataset.owner_id != request.user.id and \
                    not request.user.is_staff:
                return HttpResponse(f'Dataset {x} not found', status=404)
            
            for task in tasks:
                csv_lines = '"'
                csv_lines += task.result_csv_line.replace(' ', '').lstrip("\"")
                test = csv_lines.split('\",\"')
                test = [x.lstrip('\"') for x in test]
                test = [x.replace('\"', '') for x in test]
                dataset_list.append(test)
                # Add the task_id for each task within that dataset
                task_list.append(task.task_id)

        scatterPlot = single_scatter(dataset_list, task_list)
        return scatterPlot
    else:
        tasks = DatasetTask.objects.filter(
                dataset_id=dataset_id,
                dataset__deleted_date=None
            ).prefetch_related('task').select_related('dataset')

        if not tasks:
            return HttpResponse(f'Dataset {dataset_id} has no tasks or not found')

        if tasks[0].dataset.owner_id != request.user.id and \
                not request.user.is_staff:
            return HttpResponse(f'Dataset {dataset_id} not found', status=404)

        task_list = []
        results = []
        for t in tasks: 
            task = DatasetTask.objects.filter(
                task_id=t.task_id,
                dataset__deleted_date=None
            ).select_related(
                'task').select_related('dataset').get()

            csv_lines = '"'
            csv_lines += task.result_csv_line.replace(' ', '').lstrip("\"")
            test = csv_lines.split('\",\"')
            test = [x.lstrip('\"') for x in test]
            test = [x.replace('\"', '') for x in test]
            results.append(test)
            task_list.append(t.task_id)

        scatterPlot = single_scatter(results, task_list)
        singleScatter_final_plot = get_plot_html(scatterPlot)
        return HttpResponse(singleScatter_final_plot)

def get_plot_html(plot_figure):
    plot_html = plotly.offline.plot(plot_figure, output_type='div', include_plotlyjs=False)
    final_plot = add_plotly_links(plot_html)
    return final_plot

def add_plotly_links(plot_div):
    # Get id of html div element that looks like
    # <div id="301d22ab-bfba-4621-8f5d-dc4fd855bb33" ... >
    res = re.search('<div id="([^"]*)"', plot_div)
    div_id = res.groups()[0]

    # Build JavaScript callback for handling clicks
    # and opening the URL in the trace's customdata 
    js_callback = """
    <script>
    var plot_element = document.getElementById("{div_id}");
    plot_element.on('plotly_click', function(data){{
        console.log(data);
        var point = data.points[0];
        if (point) {{
            console.log(point.customdata);
            window.open(point.customdata, "Surface and Curve Plots", "height=500,width=500");
        }}
    }})
    </script>
    """.format(div_id=div_id)

    # Build HTML string
    html_str = """
    <html>
    <body>
    {plot_div}
    {js_callback}
    </body>
    </html>
    """.format(plot_div=plot_div, js_callback=js_callback)
    return html_str
