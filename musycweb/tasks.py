from celery import shared_task
from musycdjango.celery import app
import time
from .models import Dataset, DatasetTask
import pandas as pd
import numpy as np
from musyc_code.SynergyCalculator.SynergyCalculator import MuSyC_2D
import itertools
from django_celery_results.models import TaskResult, states
from .forms import CreateDatasetForm
from django.contrib.messages import warning
import warnings
from django.conf import settings


class DataError(Exception):
    pass


@shared_task(bind=True)
def test_add(self, x, y, sleep=0):
    if not self.request.called_directly:
        self.update_state(state='STARTED')
    time.sleep(sleep)
    return x + y


@shared_task(bind=True)
def fit_drug_combination(
        self, dataset_id, drug1_name, drug2_name, sample,
        d1, d2, dip, dip_sd,
        E_fix, E_bnd,
        drug1_units, drug2_units, expt_date, output_dir,
        expt,
        metric_name,
        hill_orient,
        init_seed=None,
        fit_alg='nlls_mcnlls',
        find_opt=False,
        fit_gamma=False,
        batch=None
):
    # Mark task as started
    if not self.request.called_directly:
        self.update_state(state='STARTED')
        # self.update_state(state='PROGRESS',
        #                   meta={'current': i, 'total': len(filenames)})

    if len(drug1_units) > 1:
        raise DataError(f'drug1.units contains multiple values: {", ".join(drug1_units)}')

    if len(drug2_units) > 1:
        raise DataError(f'drug1.units contains multiple values: {", ".join(drug2_units)}')

    drug1_units = drug1_units[0]
    drug2_units = drug2_units[0]

    # Convert d1, d2, dip, dip_sd, expt_date back to ndarrays
    d1 = np.array(d1)
    d2 = np.array(d2)
    dip = np.array(dip)
    dip_sd = np.array(dip_sd)
    expt_date = np.array(expt_date)

    # Check for -ve drug concentrations
    if (d1 < 0).any():
        raise DataError('Negative concentrations for drug1 - not supported')
    if (d2 < 0).any():
        raise DataError('Negative concentrations for drug2 - not supported')

    # Check both drugs have some +ve concentrations
    if not (d1 > 0).any():
        raise DataError('No non-zero concentrations for drug1; single drug '
                        'expts not yet supported')
    if not (d2 > 0).any():
        raise DataError('No non-zero concentrations for drug2; single drug '
                        'expts not yet supported')

    if drug1_name == drug2_name:
        raise DataError('Drug 1 and drug 2 are the same; single drug expts '
                        'not yet supported')

    if (dip_sd <= 0).any():
        string = 'WARNING: Combination Screen: Drugs(' + drug1_name + ' ' + drug2_name + ') Sample: ' + sample + ' the effect.95ci column has a value <0!  Confidence intervals (CI) on effect MUST be positive.  If CI is unknown, assign a small finite number to all conditions.'
        print(string)
        dip_sd[dip_sd <= 0] = min(dip_sd[dip_sd > 0])

    if len(dip) < 4:
        raise DataError('At least four data points are needed to fit '
                        f'dose-response surface (found: {len(dip)})')

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

    expt_and_batch = f'{expt} [{batch}]' if batch else expt

    try:
        T = MuSyC_2D(d1,d2,dip,dip_sd,drug1_name,drug2_name,E_fix=E_fix,E_bnd=E_bnd,find_opt=find_opt,fit_gamma=fit_gamma,
                      fit_alg=fit_alg,to_plot=False,sample=sample,expt=expt_and_batch,metric_name=metric_name,
                      hill_orient=hill_orient,to_save=False,direc=None,
                      SAMPLES=50000,BURN=5000,PSO_PARTICLES=100,PSO_ITER=50,PSO_SPEED=10,
                      init_seed=init_seed,
                     # other_metrics=other_metrics
                     )
    except ValueError as e:
        err = str(e)
        if 'lower bound must be strictly less than each upper bound' in err:
            raise DataError(
                'Lower bound must be strictly less than upper bound')

        # Re-raise any unknown error
        raise

    T['E_fix'] = E_fix
    T['E_bnd'] = E_bnd
    T['drug1_units'] = drug1_units
    T['drug2_units'] = drug2_units
    T['d1'] = d1.tolist()
    T['d2'] = d2.tolist()
    T['dip'] = dip.tolist()
    T['dip_sd'] = dip_sd.tolist()
    T['expt_date'] = expt_date.tolist()
    T['batch'] = batch

    for k in ('save_direc', 'to_save_traces', 'to_save_plots', 'memory_Mb'):
        del T[k]

    return T


def _swap_drug1_drug2(data):
    return data.rename(columns={
        'drug1': 'drug2',
        'drug2': 'drug1',
        'drug1.conc': 'drug2.conc',
        'drug2.conc': 'drug1.conc',
        'drug1.units': 'drug2.units',
        'drug2.units': 'drug1.units'
    })


def _warning(request, message):
    if request:
        # Use Django warnings, if available
        warning(request, message)
    else:
        warnings.warn(message)


def process_dataset(dataset_or_id, clear_existing=None, request=None,
                    priority=None):
    """ Split a dataset into drug combinations and submit as tasks """
    if isinstance(dataset_or_id, int):
        dataset = Dataset.objects.get(pk=dataset_or_id, deleted_date=None)
    else:
        dataset = dataset_or_id

    assert clear_existing is None or clear_existing in ('unsuccessful', True)

    if clear_existing:
        # Revoke any unprocessed tasks
        app.control.revoke(
            list(TaskResult.objects.filter(
                datasettask__dataset_id=dataset.id,
                status__in=states.UNREADY_STATES
            ).values_list(
                'task_id', flat=True
            ))
        )
        # Delete TaskResults and their linked DatasetTasks
        tq = TaskResult.objects.filter(datasettask__dataset_id=dataset.id)
        if clear_existing == 'unsuccessful':
            tq = tq.exclude(status=states.SUCCESS)
        tq.delete()

        # Delete DatasetTasks without any linked TaskResult
        DatasetTask.objects.filter(
            dataset_id=dataset.id
        ).exclude(
            task__in=TaskResult.objects.filter(
                datasettask__dataset_id=dataset.id
            )
        ).delete()

    if clear_existing == 'unsuccessful':
        # Get list of completed tasks to skip
        tasks_to_skip = set(
            (t.drug1,
             t.drug2,
             t.sample,
             t.batch)
            for t in
            DatasetTask.objects.filter(
                dataset_id=dataset.id,
                task__status=states.SUCCESS
            )
        )
    else:
        tasks_to_skip = set()

    # Read in file
    fields = {**CreateDatasetForm.REQUIRED_FIELDS,
              **CreateDatasetForm.OPTIONAL_FIELDS}
    try:
        data = pd.read_table(
            dataset.file,
            delimiter=',',
            dtype=fields
        )
    except ValueError as e:
        err = str(e)
        if 'could not convert string to float' in err:
            float_fields = [f for f, v in fields.items() if v is float]
            raise DataError(
                'Error in one or more of the '
                f'{", ".join(float_fields)} columns: {err}')

        # Re-raise any unknown error
        raise

    use_batches = 'batch' in data.columns

    # Start of validation and normalisation

    # Warn about surplus columns
    surplus_columns = set(data.columns) - set(fields.keys())
    if surplus_columns:
        _warning(request,
                 f'Extra columns were ignored: {", ".join(surplus_columns)}')

    # Drop empty rows
    nrows = data.shape[0]
    data.dropna(axis=0, how='all', thresh=None, subset=None, inplace=True)
    if data.shape[0] != nrows:
        _warning(request, 'Empty rows have been dropped')

    # Drug concentrations should be non-negative
    if (data['drug1.conc'] < 0).any() or (data['drug2.conc'] < 0).any():
        raise DataError('Drug concentrations cannot be negative')

    # Batches cannot contain empty values, if present
    if use_batches and (data['batch'].isna().any() or
                        (data['batch'].str.strip() == '').any()):
        raise DataError('Batch column should not contain empty values')
    # Remove rows with missing effect value
    if data['effect'].isna().any():
        _warning(request,
                 'Effect columns which are missing/NaN will be removed')
    data = data[data['effect'].notna()]
    # Add in optional effect.95ci column if not present and validate
    if 'effect.95ci' not in data.columns:
        ci_val = abs(min(data['effect']/100.))
        if ci_val == 0:
            ci_val = 1e-16
        data['effect.95ci'] = ci_val
    else:
        if data['effect.95ci'].isna().any():
            raise DataError('effect.95ci column cannot contain blank/NA values')
        if (data['effect.95ci'] <= 0).any():
            raise DataError('effect.95ci column cannot contain zero or '
                            'negative values')

    # Add SD
    data['effect.sd'] = data['effect.95ci'] / (2 * 1.96)

    if priority is None:
        if data.shape[0] >= settings.CELERY_DEPRIORITISE_SIZE_L2:
            priority = 2
        elif data.shape[0] >= settings.CELERY_DEPRIORITISE_SIZE_L3:
            priority = 3
        if priority:
            _warning(request, 'Tasks will run at lower priority due to large '
                              'dataset size')

    # Global fitting bounds
    e_fix = None
    e_bnd = None
    if dataset.emax_lower is not None or \
            dataset.emax_upper is not None or \
            dataset.e0_lower is not None or \
            dataset.e0_upper is not None:
        if dataset.emax_lower == dataset.emax_upper and \
                dataset.emax_lower is not None and \
                dataset.e0_lower == dataset.e0_upper and \
                dataset.e0_lower is not None:
            # Fixed value
            e_fix = [dataset.e0_lower] + [dataset.emax_lower] * 3
        else:
            # Constraint
            e0_lwr = dataset.e0_lower if dataset.e0_lower is not None else -np.Inf
            e0_upr = dataset.e0_upper if dataset.e0_upper is not None else np.Inf
            emax_lwr = dataset.emax_lower if dataset.emax_lower is not None else -np.Inf
            emax_upr = dataset.emax_upper if dataset.emax_upper is not None else np.Inf
            e_bnd = [[e0_lwr] + [emax_lwr] * 3, [e0_upr] + [emax_upr] * 3]

    # Canonicalise drug order, alphabetically
    # i.e. drug1 should come alphabetically first
    out_of_order = data['drug1'] > data['drug2']
    data.loc[out_of_order, ['drug1', 'drug1.conc', 'drug1.units',
                            'drug2', 'drug2.conc', 'drug2.units']] = \
                data.loc[out_of_order, ['drug2', 'drug2.conc', 'drug2.units',
                                        'drug1', 'drug1.conc', 'drug1.units']]

    # Control filter (no drug)
    data_ctrl = data.loc[(data['drug1.conc'] == 0) & (data['drug2.conc'] == 0)]

    # SA = Single agent filter (exactly one drug added)
    data_sa_1 = data.loc[(data['drug1.conc'] == 0) & (data['drug2.conc'] != 0)]
    data_sa_2 = data.loc[(data['drug1.conc'] != 0) & (data['drug2.conc'] == 0)]

    # Dual agent (two drugs added in non-zero concentration
    data_expt = data.loc[(data['drug1.conc'] != 0) & (data['drug2.conc'] != 0)]

    # Loop through each (drug1, drug2, sample) combination and launch tasks
    dataset_tasks = []

    def lfrom(lists, attr):
        return list(itertools.chain(*(l[attr].array for l in lists)))

    def sfrom(lists, attr):
        return list(set(itertools.chain(*(l[attr].array for l in lists))))

    outer_grouping = ['batch', 'sample'] if use_batches else ['sample']

    try:
        for bat_smp, samp_grp in data_expt.groupby(outer_grouping, sort=False):
            if use_batches:
                batch, sample = bat_smp
                data_ctrl_s = data_ctrl.loc[
                      (data_ctrl['batch'] == batch) &
                      (data_ctrl['sample'] == sample)]
                data_sa_1_s = data_sa_1.loc[
                      (data_sa_1['batch'] == batch) &
                      (data_sa_1['sample'] == sample)]
                data_sa_2_s = data_sa_2.loc[
                      (data_sa_2['batch'] == batch) &
                      (data_sa_2['sample'] == sample)]
            else:
                sample = bat_smp
                batch = None
                data_ctrl_s = data_ctrl.loc[data_ctrl['sample'] == sample]
                data_sa_1_s = data_sa_1.loc[data_sa_1['sample'] == sample]
                data_sa_2_s = data_sa_2.loc[data_sa_2['sample'] == sample]

            for drug_names, grp_dat in samp_grp.groupby(
                    ['drug1', 'drug2'], sort=False):
                drug1_name, drug2_name = drug_names
                if (drug1_name, drug2_name, sample, batch) in tasks_to_skip:
                    continue

                df_list = [
                    grp_dat,
                    data_ctrl_s,
                    data_sa_1_s.loc[data_sa_1_s['drug2'] == drug2_name],
                    data_sa_2_s.loc[data_sa_2_s['drug1'] == drug1_name],
                    # Need to swap drugs in single agent case where drug is in wrong col
                    _swap_drug1_drug2(data_sa_1_s.loc[data_sa_1_s['drug2'] == drug1_name]),
                    _swap_drug1_drug2(data_sa_2_s.loc[data_sa_2['drug1'] == drug2_name])
                ]

                task = fit_drug_combination.apply_async(
                    kwargs=dict(
                        dataset_id=dataset.id,
                        drug1_name=drug1_name,
                        drug2_name=drug2_name,
                        sample=sample,
                        batch=batch,
                        d1=lfrom(df_list, 'drug1.conc'),
                        d2=lfrom(df_list, 'drug2.conc'),
                        dip=lfrom(df_list, 'effect'),
                        dip_sd=lfrom(df_list, 'effect.sd'),
                        E_fix=e_fix,
                        E_bnd=e_bnd,
                        drug1_units=sfrom(df_list, 'drug1.units'),
                        drug2_units=sfrom(df_list, 'drug2.units'),
                        expt_date=sfrom(df_list, 'expt.date'),
                        output_dir=None,
                        expt=dataset.name,
                        metric_name=dataset.metric_name,
                        hill_orient=dataset.orientation
                    ),
                    priority=priority
                )

                # # Create DB entry for tracking this task
                dataset_tasks.append(DatasetTask(
                    dataset=dataset,
                    drug1=drug1_name,
                    drug2=drug2_name,
                    sample=sample,
                    batch=batch,
                    task_id=task.id
                ))
    finally:
        DatasetTask.objects.bulk_create(dataset_tasks)
