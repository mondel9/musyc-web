from django.db import models
from django.conf import settings
from django_celery_results.models import TaskResult
import json
import io


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                related_name='profile',
                                on_delete=models.CASCADE)
    first_name = models.TextField(default=None, blank=True)
    last_name = models.TextField(default=None, blank=True)
    organization = models.TextField(default=None, null=True)
    accept_eula = models.BooleanField(default=False)


class Dataset(models.Model):
    ORIENTATION_CHOICES = (
        (0, 'Emax>E0'),
        (1, 'Emax<E0')
    )
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE)
    name = models.TextField()
    creation_date = models.DateTimeField(auto_now_add=True)
    deleted_date = models.DateTimeField(null=True, default=None, editable=False)
    file = models.FileField(upload_to='_state/datasets', editable=False)
    orientation = models.PositiveSmallIntegerField(
        choices=ORIENTATION_CHOICES,
        default=1,
        editable=False
    )
    metric_name = models.TextField(default='Percent effect', editable=False)
    emax_lower = models.FloatField(default=None, null=True, editable=False)
    emax_upper = models.FloatField(default=None, null=True, editable=False)
    e0_lower = models.FloatField(default=None, null=True, editable=False)
    e0_upper = models.FloatField(default=None, null=True, editable=False)

    def __str__(self):
        return f'[{self.id}] {self.name} <{self.owner.email}>'


class DatasetTask(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    drug1 = models.TextField()
    drug2 = models.TextField()
    sample = models.TextField()
    batch = models.TextField(null=True, default=None)
    task = models.OneToOneField(TaskResult,
                                on_delete=models.CASCADE,
                                db_constraint=False,
                                to_field='task_id')
    FIELDS_CSV = (
        'sample', 'drug1_name', 'drug2_name', 'expt', 'batch', 'task_status',
        'converge_mc_nlls', 'beta', 'beta_ci', 'beta_obs', 'beta_obs_ci',
        'log_alpha1', 'log_alpha1_ci', 'log_alpha2', 'log_alpha2_ci', 'R2',
        'log_like_mc_nlls', 'E0', 'E0_ci', 'E1', 'E1_ci', 'E2', 'E2_ci', 'E3',
        'E3_ci', 'E1_obs', 'E1_obs_ci', 'E2_obs', 'E2_obs_ci', 'E3_obs',
        'E3_obs_ci', 'log_C1', 'log_C1_ci', 'log_C2', 'log_C2_ci', 'log_h1',
        'log_h1_ci', 'log_h2', 'log_h2_ci', 'h1', 'h2', 'C1', 'C2', 'time_total',
        'drug1_units', 'drug2_units', 'metric_name', 'fit_beta',
        'boundary_sampling', 'max_conc_d1', 'max_conc_d2', 'min_conc_d1',
        'min_conc_d2', 'fit_method', 'dataset_name'
    )
    FIELD_RENAMES = {
        'log_alpha1': 'log_alpha12',
        'log_alpha2': 'log_alpha21',
        'log_alpha1_ci': 'log_alpha12_ci',
        'log_alpha2_ci': 'log_alpha21_ci'
    }

    def __str__(self):
        return f'{self.task_id} [DS:{self.dataset_id}] ' \
               f'<{self.dataset.owner.email}>'

    @property
    def status(self):
        try:
            return self.task.status
        except TaskResult.DoesNotExist:
            return 'QUEUED'

    @property
    def error_message(self):
        if self.status != 'FAILURE':
            return None

        d = json.loads(self.task.result)
        if d.get('exc_type', '') == 'DataError' and 'exc_message' in d:
            return d['exc_message'][0]
        elif d.get('exc_type', '') == 'SoftTimeLimitExceeded':
            return 'Time limit exceeded'
        else:
            return 'Unknown error'

    @property
    def result_dict(self):
        if self.status != 'SUCCESS':
            d = dict(
                drug1_name=self.drug1,
                drug2_name=self.drug2,
                sample=self.sample
            )
        else:
            d = json.loads(self.task.result)
        d['task_status'] = self.status
        d['dataset_name'] = self.dataset.name
        return d

    @property
    def result_csv_header(self):
        return ','.join(f'"{self.FIELD_RENAMES.get(f, f)}"'
                        for f in self.FIELDS_CSV)

    @property
    def result_csv_line(self):
        d = self.result_dict
        return ','.join('"'+str(d.get(k, '')).replace('"', '\"')+'"'
                        for k in self.FIELDS_CSV)

    @property
    def result_csv(self):
        return f'{self.result_csv_header}\n{self.result_csv_line}'
