from django.shortcuts import render, reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404,\
    JsonResponse
from django.contrib.auth.decorators import login_required
from .forms import CreateDatasetForm
from .models import Dataset, DatasetTask
from .tasks import process_dataset
from django_celery_results.models import TaskResult
from django.template.context_processors import csrf
from musyc_code.SynergyCalculator.doseResponseSurfPlot import \
    plotDoseResponseSurf
from crispy_forms.utils import render_crispy_form
import numpy as np
import plotly.offline


def about(request):
    return render(request, 'about.html', {})


@login_required
def index(request):
    datasets = Dataset.objects.filter(owner=request.user).order_by('-creation_date')

    return render(request, 'index.html', {'datasets': datasets})


@login_required
def account(request):
    return render(request, 'account/account.html')


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
            process_dataset(d)

            if 'ajax' in request.GET:
                return JsonResponse({'success': True, 'dataset_id': d.id})
            else:
                return HttpResponseRedirect(reverse(
                    'view_dataset', kwargs={'dataset_id': d.id}
                ))
    else:
        form = CreateDatasetForm()
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
def view_dataset(request, dataset_id):
    try:
        d = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        raise Http404()

    if d.owner_id != request.user.id and not request.user.is_staff:
        raise Http404()

    return render(request, 'dataset.html', {'d': d})


@login_required
def ajax_tasks(request, dataset_id):
    try:
        d = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        raise Http404()

    if d.owner_id != request.user.id and not request.user.is_staff:
        raise Http404()

    tasks = DatasetTask.objects.filter(dataset=d).select_related(
        'task').order_by('drug1', 'drug2', 'sample')

    return JsonResponse({'data': [
        [t.drug1, t.drug2, t.sample, t.status, t.task_uuid] for t in tasks]})


@login_required
def ajax_dataset_csv(request, dataset_id):
    tasks = DatasetTask.objects.filter(dataset_id=dataset_id).select_related(
        'task').select_related('dataset')

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
        task = DatasetTask.objects.filter(task_uuid=task_id).select_related(
            'task').select_related('dataset').get()
    except DatasetTask.DoesNotExist:
        raise Http404()

    if task.dataset.owner_id != request.user.id and not request.user.is_staff:
        raise Http404()

    return render(request, 'task_result.html', {'task': task})


@login_required
def ajax_task_csv(request, task_id):
    try:
        task = DatasetTask.objects.filter(task_uuid=task_id).select_related(
            'task').select_related('dataset').get()
    except DatasetTask.DoesNotExist:
        return HttpResponse(f'Task {task_id} not found', status=404)

    if task.dataset.owner_id != request.user.id and not request.user.is_staff:
        return HttpResponse(f'Task {task_id} not found', status=404)

    if not task.task:
        return HttpResponse(f'Task {task_id} task object not found', status=404)

    if task.task.status == 'FAILED':
        return HttpResponse(f'Task {task.task_uuid} Failed')

    if task.task.status != 'SUCCESS':
        return HttpResponse(f'Task {task.task_uuid} not complete (status: '
                            f'{task.task.status})')

    # OK to return CSV
    response = HttpResponse(task.result_csv, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{task_id}.csv"'
    return response


@login_required
def ajax_surface_plot(request, task_id):
    try:
        task = DatasetTask.objects.filter(task_uuid=task_id).select_related(
            'task').select_related('dataset').get()
    except DatasetTask.DoesNotExist:
        raise Http404()

    if task.dataset.owner_id != request.user.id and not request.user.is_staff:
        raise Http404()

    # Get any plot
    rd = task.result_dict
    if rd:
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

    return HttpResponse(plot_html)


@login_required
def ajax_task_status(request, dataset_id):
    tasks = DatasetTask.objects.filter(
        dataset_id=dataset_id,
    ).select_related('task')
    if not request.user.is_staff:
        tasks = tasks.filter(dataset__owner_id=request.user.id)
    return JsonResponse({task.task_uuid: task.status for task in tasks})
