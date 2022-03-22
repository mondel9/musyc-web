from django.contrib import admin
from .models import Dataset, DatasetTask, Project
from django.urls import reverse
from django.utils.html import format_html
from django_celery_results.models import TaskResult

admin.site.site_header = 'MuSyC Administration'
admin.site.site_title = 'MuSyC Admin'


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'owner', 'num_datasets')

class DatasetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'creation_date', 'owner', 'project_id)


class DatasetTaskAdmin(admin.ModelAdmin):
    list_display = ('task_link',
                    'task_status',
                    'dataset_link',
                    'owner',
                    'drug1', 'drug2', 'sample')
    list_display_links = None
    list_select_related = ('dataset', 'dataset__owner')
    list_prefetch_related = ('task', )

    def task_link(self, obj):
        try:
            return format_html(f'<a href="/admin/django_celery_results/taskresult/{obj.task.id}/change/">{obj.task_id}</a>')
        except TaskResult.DoesNotExist:
            return obj.task_id
    task_link.short_description = 'Task'

    def task_status(self, obj):
        try:
            return obj.task.status
        except TaskResult.DoesNotExist:
            return 'QUEUED'
    task_status.short_description = 'Status'

    def dataset_link(self, obj):
        return format_html(f'<a href="/admin/musycweb/dataset/{obj.dataset.id}/change">[{obj.dataset.id}] {obj.dataset.name}</a>')
    dataset_link.short_description = 'Dataset'

    def owner(self, obj):
        return obj.dataset.owner.email


admin.site.register(Dataset, DatasetAdmin)
admin.site.register(DatasetTask, DatasetTaskAdmin)
admin.site.register(Project, ProjectAdmin)


