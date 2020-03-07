from celery import shared_task
import time
from .models import Dataset, DatasetTask
import pandas as pd
import numpy as np
from musyc_code.SynergyCalculator.gatherData import subset_data,\
    subset_expt_info
from musyc_code.SynergyCalculator.SynergyCalculator import MuSyC_2D
import os
from django.conf import settings
import uuid
from django_celery_results.models import TaskResult
from django.db.models.signals import post_save
from django.dispatch import receiver
import json


@shared_task(bind=True)
def test_add(self, x, y, sleep=0):
    if not self.request.called_directly:
        self.update_state(state='STARTED')
    time.sleep(sleep)
    return x + y


@receiver(post_save, sender=TaskResult)
def link_datasetresult(sender, instance=None, created=None, **kwargs):
    if not instance.task_name.endswith('fit_drug_combination'):
        return
    if not created:
        return
    DatasetTask.objects.filter(task_uuid=instance.task_id).update(task=instance)


@shared_task(bind=True)
def fit_drug_combination(
        self, dataset_id, drug1_name, drug2_name, sample, d1, d2, dip, dip_sd,
        E_fix, E_bnd,
        drug1_units, drug2_units, expt_date, output_dir,
        expt,
        metric_name,
        hill_orient,
        init_seed=None,
        fit_alg='mcnlls',
        find_opt=False,
        fit_gamma=False
):
    # Mark task as started
    if not self.request.called_directly:
        self.update_state(state='STARTED')
        # self.update_state(state='PROGRESS',
        #                   meta={'current': i, 'total': len(filenames)})

    # Convert d1, d2, dip, dip_sd, expt_date back to ndarrays
    d1 = np.array(d1)
    d2 = np.array(d2)
    dip = np.array(dip)
    dip_sd = np.array(dip_sd)
    expt_date = np.array(expt_date)

    # Consider the special case when one of the drugs has no effect.
    # Flip drug names around so that the no effect drug is drug 1
    if E_fix is not None:
        if E_fix[0] == E_fix[2]:
            E_fix[2], E_fix[1] = E_fix[1], E_fix[2]
            drug1_name, drug2_name = drug2_name, drug1_name
            d1, d2 = d2, d1

    # Consider the special case when using boundary sampling conditions
    # Make sure this is drug 2
    if len(np.unique(d1)) == 2:
        if E_fix is not None:
            E_fix[2], E_fix[1] = E_fix[1], E_fix[2]
        if E_bnd is not None:
            E_bnd[0][1], E_bnd[0][2], E_bnd[1][1], E_bnd[1][2] = E_bnd[0][2], \
                                                                 E_bnd[0][1], \
                                                                 E_bnd[1][2], \
                                                                 E_bnd[1][1]
        drug1_name, drug2_name = drug2_name, drug1_name
        d1, d2 = d2, d1

    T = MuSyC_2D(d1,d2,dip,dip_sd,drug1_name,drug2_name,E_fix=E_fix,E_bnd=E_bnd,find_opt=find_opt,fit_gamma=fit_gamma,
                  fit_alg=fit_alg,to_plot=False,sample=sample,expt=expt,metric_name=metric_name,
                  hill_orient=hill_orient,to_save=False,direc=None,
                  SAMPLES=50000,BURN=5000,PSO_PARTICLES=100,PSO_ITER=50,PSO_SPEED=10,
                  init_seed=init_seed,
                 # other_metrics=other_metrics
                 )

    T['drug1_units'] = drug1_units
    T['drug2_units'] = drug2_units
    T['d1'] = d1.tolist()
    T['d2'] = d2.tolist()
    T['dip'] = dip.tolist()
    T['dip_sd'] = dip_sd.tolist()
    T['expt_date'] = expt_date.tolist()

    for k in ('save_direc', 'to_save_traces', 'to_save_plots', 'memory_Mb'):
        del T[k]

    return T


def process_dataset(dataset_or_id):
    """ Split a dataset into drug combinations and submit as tasks """
    if isinstance(dataset_or_id, int):
        dataset = Dataset.objects.get(pk=dataset_or_id)
    else:
        dataset = dataset_or_id

    # Read in file
    data = pd.read_table(dataset.file, delimiter=',')
    if 'effect.95ci' not in data.columns:
        data['effect.95ci'] = min(data['effect']/100.)

    # Loop through each (drug1, drug2, sample) combination and launch tasks
    for group_name, _ in data.groupby(['drug1', 'drug2', 'sample']):
        drug1_name, drug2_name, sample = group_name
        # Subset data for doses for fitting
        d1, d2, dip, dip_sd = subset_data(data, drug1_name, drug2_name, sample)
        drug1_units, drug2_units, expt_date = subset_expt_info(data, drug1_name,
                                                               drug2_name,
                                                               sample)

        task = fit_drug_combination.delay(
            dataset_id=dataset.id,
            drug1_name=drug1_name,
            drug2_name=drug2_name,
            sample=sample,
            d1=d1.tolist(),
            d2=d2.tolist(),
            dip=dip.tolist(),
            dip_sd=dip_sd.tolist(),
            E_fix=None,
            E_bnd=None,
            drug1_units=drug1_units,
            drug2_units=drug2_units,
            expt_date=expt_date.tolist(),
            output_dir=None,
            expt=dataset.name,
            metric_name=dataset.metric_name,
            hill_orient=dataset.orientation
        )

        # # Create DB entry for tracking this task
        dt = DatasetTask.objects.create(
            dataset=dataset,
            drug1=drug1_name,
            drug2=drug2_name,
            sample=sample,
            task_uuid=task.id
        )
        dt.save()
