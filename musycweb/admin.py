from django.contrib import admin
from .models import Dataset, DatasetTask
from django.urls import reverse
from django.utils.html import format_html
from django_celery_results.models import TaskResult


class DatasetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'creation_date', 'owner')


class DatasetTaskAdmin(admin.ModelAdmin):
    list_display = ('task_link',
                    'task_status',
                    'dataset_link',
                    'owner',
                    'drug1', 'drug2', 'sample')
    list_display_links = None
    list_select_related = ('task', 'dataset', 'dataset__owner')

    def task_link(self, obj):
        if not obj.task and not obj._task_set():
            return {obj.task_uuid}
        return format_html(f'<a href="/admin/django_celery_results/taskresult/{obj.task.id}/change/">{obj.task_uuid}</a>')
    task_link.short_description = 'Task'

    def task_status(self, obj):
        if not obj.task and not obj._task_set():
            return 'Not found'

        return obj.task.status
    task_status.short_description = 'Status'

    def dataset_link(self, obj):
        return format_html(f'<a href="/admin/musycweb/dataset/{obj.dataset.id}/change">[{obj.dataset.id}] {obj.dataset.name}</a>')
    dataset_link.short_description = 'Dataset'

    def owner(self, obj):
        return obj.dataset.owner.email


admin.site.register(Dataset, DatasetAdmin)
admin.site.register(DatasetTask, DatasetTaskAdmin)
