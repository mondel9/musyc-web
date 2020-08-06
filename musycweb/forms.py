from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from allauth.account import forms as allauth_forms
from allauth.account.adapter import DefaultAccountAdapter
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Group
from .models import Dataset, Profile
import numpy as np
import swot


class CreateDatasetForm(forms.Form):
    REQUIRED_FIELDS = {
        'expt.date': str,
        'drug1.conc': float,
        'drug2.conc': float,
        'effect': float,
        'sample': str,
        'drug1': str,
        'drug2': str,
        'drug1.units': str,
        'drug2.units': str
    }
    OPTIONAL_FIELDS = {
        'batch': str,
        'effect.95ci': float
    }

    name = forms.CharField()
    file = forms.FileField()
    orientation = forms.ChoiceField(
        choices=Dataset.ORIENTATION_CHOICES,
        widget=forms.RadioSelect,
        initial=Dataset._meta.get_field('orientation').default)
    metric_name = forms.CharField(
        max_length=32,
        initial=Dataset._meta.get_field('metric_name').default)
    effect_constraint = forms.ChoiceField(
        choices=(('none', 'Unconstrained'),
                 ('fixed', 'Fixed (No synergistic efficacy, beta=0)'),
                 ('bounded', 'Upper/lower bounds')),
        widget=forms.RadioSelect,
        initial='none'
    )
    e0_fixed_value = forms.FloatField(required=False)
    emax_fixed_value = forms.FloatField(required=False)
    e0_lower_bound = forms.FloatField(required=False)
    e0_upper_bound = forms.FloatField(required=False)
    emax_lower_bound = forms.FloatField(required=False)
    emax_upper_bound = forms.FloatField(required=False)

    def __init__(self, *args, **kwargs):
        super(CreateDatasetForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_id = 'create-dataset-form'
        self.helper.add_input(Submit('submit', 'Create Dataset',
                                     css_class='btn-block'))

    def clean_file(self):
        f = self.cleaned_data['file']
        try:
            c = next(f.chunks())
        except StopIteration:
            raise forms.ValidationError('File is empty!')

        try:
            c = c.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise forms.ValidationError(
                'File needs to use Unicode UTF-8 '
                'encoding. Either the encoding is wrong, or this isn\'t a '
                'CSV file.')

        first_line = c.splitlines()[0]
        if ',' not in first_line:
            raise forms.ValidationError(
                'No comma detected in first line. Check separator is comma '
                'and not tab, for example.')
        if first_line.lower() != first_line:
            raise forms.ValidationError('Column names must be in lower case')

        headers = set(first_line.split(','))
        # Remove quotes, if applicable
        if all(h.startswith('"') and h.endswith('"') for h in headers):
            headers = [h[1:-1] for h in headers]
        missing_headers = self.REQUIRED_FIELDS.keys() - headers
        if missing_headers:
            raise forms.ValidationError(
                f'Missing required fields: {", ".join(missing_headers)}'
            )

        return f

    def _clean_orientation(self):
        try:
            orientation = int(self.cleaned_data['orientation'])
            if orientation not in (0, 1):
                raise ValueError()
        except ValueError:
            raise forms.ValidationError('Orientation must be 0 or 1')

        return orientation

    def _clean_e0_fixed_value(self):
        if self.cleaned_data['effect_constraint'] in ('none', 'bounded'):
            return None

        if self.cleaned_data['e0_fixed_value'] is not None:
            if self.cleaned_data['emax_fixed_value'] is None:
                raise forms.ValidationError('Must specify fixed values for '
                                            'both E0 and Emax')

        return self.cleaned_data['e0_fixed_value']

    def _clean_emax_fixed_value(self):
        if self.cleaned_data['effect_constraint'] in ('none', 'bounded'):
            return None

        if self.cleaned_data['emax_fixed_value'] is not None:
            if self.cleaned_data['e0_fixed_value'] is None:
                raise forms.ValidationError('Must specify fixed values for '
                                            'both E0 and Emax')

            if self.cleaned_data['orientation'] == 0 and \
                    self.cleaned_data['emax_fixed_value'] <= \
                    self.cleaned_data['e0_fixed_value']:
                raise forms.ValidationError(
                    'Emax must be > E0, or change orientation'
                )
            if self.cleaned_data['orientation'] == 1 and \
                    self.cleaned_data['emax_fixed_value'] >= \
                    self.cleaned_data['e0_fixed_value']:
                raise forms.ValidationError(
                    'Emax must be < E0, or change orientation'
                )

        return self.cleaned_data['emax_fixed_value']

    def _clean_e0_lower_bound(self):
        if self.cleaned_data['effect_constraint'] == 'none':
            return None

        if self.cleaned_data['effect_constraint'] == 'fixed':
            return self.cleaned_data['e0_fixed_value']

        return self.cleaned_data['e0_lower_bound']

    def _clean_emax_lower_bound(self):
        if self.cleaned_data['effect_constraint'] == 'none':
            return None

        if self.cleaned_data['effect_constraint'] == 'fixed':
            return self.cleaned_data['emax_fixed_value']

        return self.cleaned_data['emax_lower_bound']

    def _clean_e0_upper_bound(self):
        if self.cleaned_data['effect_constraint'] == 'none':
            return None

        if self.cleaned_data['effect_constraint'] == 'bounded':
            if self.cleaned_data['e0_lower_bound'] is None:
                self.cleaned_data['e0_lower_bound'] = -np.inf
            if self.cleaned_data['e0_upper_bound'] is None:
                self.cleaned_data['e0_upper_bound'] = np.inf

            if self.cleaned_data['e0_upper_bound'] < \
                    self.cleaned_data['e0_lower_bound']:
                raise forms.ValidationError(
                    'Upper bound must be >= lower bound'
                )

        if self.cleaned_data['effect_constraint'] == 'fixed':
            return self.cleaned_data['e0_fixed_value']

        return self.cleaned_data['e0_upper_bound']

    def _clean_emax_upper_bound(self):
        if self.cleaned_data['effect_constraint'] == 'none':
            return None

        if self.cleaned_data['effect_constraint'] == 'bounded':
            if self.cleaned_data['emax_lower_bound'] is None:
                self.cleaned_data['emax_lower_bound'] = -np.inf
            if self.cleaned_data['emax_upper_bound'] is None:
                self.cleaned_data['emax_upper_bound'] = np.inf

            if self.cleaned_data['emax_upper_bound'] < \
                    self.cleaned_data['emax_lower_bound']:
                raise forms.ValidationError(
                    'Upper bound must be >= lower bound'
                )

        if self.cleaned_data['effect_constraint'] == 'fixed':
            return self.cleaned_data['emax_fixed_value']

        return self.cleaned_data['emax_upper_bound']

    def clean(self):
        # Standard field cleaning can't rely on field ordering, so we use
        # the clean method with manual field ordering
        self.cleaned_data['orientation'] = self._clean_orientation()
        self.cleaned_data['e0_fixed_value'] = self._clean_e0_fixed_value()
        self.cleaned_data['emax_fixed_value'] = self._clean_emax_fixed_value()
        self.cleaned_data['e0_lower_bound'] = self._clean_e0_lower_bound()
        self.cleaned_data['emax_lower_bound'] = self._clean_emax_lower_bound()
        self.cleaned_data['e0_upper_bound'] = self._clean_e0_upper_bound()
        self.cleaned_data['emax_upper_bound'] = self._clean_emax_upper_bound()
        return self.cleaned_data


class CentredAuthForm(allauth_forms.LoginForm):
    def __init__(self, *args, **kwargs):
        super(CentredAuthForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-vertical'
        self.helper.add_input(Submit('submit', 'Log in',
                                     css_class='btn-block'))


def assert_email_academic(email):
    if not swot.is_academic(email):
        raise forms.ValidationError(
            'Please use an email address from an academic or non-profit '
            'institution. Contact musyc@gmail.com if you would like your '
            'non-profit institution to be added to our list.'
        )

    return email


class AddEmailForm(allauth_forms.AddEmailForm):
    def __init__(self, *args, **kwargs):
        super(AddEmailForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-vertical'
        self.helper.add_input(Submit('action_add', 'Add email',
                                     css_class='btn-block'))

    def clean_email(self):
        return assert_email_academic(self.cleaned_data['email'])


class ResetPasswordForm(allauth_forms.ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super(ResetPasswordForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-vertical'
        self.helper.add_input(Submit('submit', 'Submit',
                                     css_class='btn-block'))


class SetPasswordFrom(allauth_forms.SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super(SetPasswordFrom, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-vertical'
        self.helper.add_input(Submit('submit', 'Change password',
                                     css_class='btn-block'))


class ResetPasswordKeyForm(allauth_forms.ResetPasswordKeyForm):
    def __init__(self, *args, **kwargs):
        super(ResetPasswordKeyForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-vertical'
        self.helper.add_input(Submit('submit', 'Change password',
                                     css_class='btn-block'))


class ChangePasswordForm(allauth_forms.ChangePasswordForm):
    def __init__(self, *args, **kwargs):
        super(ChangePasswordForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-vertical'
        self.helper.add_input(Submit('submit', 'Change password',
                                     css_class='btn-block'))


class SignUpForm(allauth_forms.SignupForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    organization = forms.CharField(max_length=30)
    accept_eula = forms.BooleanField(
        required=True,
        label='I accept the <a id="terms-link" href="/terms?popup" '
              'target="_blank">terms and conditions</a>')

    field_order = ['email', 'first_name', 'last_name', 'organization',
                   'password1', 'password2', 'accept_eula']

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['email'].widget.attrs.update({'autofocus': 'autofocus'})
        self.helper.form_class = 'form-vertical'
        self.helper.add_input(Submit('submit', 'Sign Up',
                                     css_class='btn-block'))

    def signup(self, request, user):
        return user

    def clean_email(self):
        return assert_email_academic(self.cleaned_data['email'])


class AccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit)

        profile = Profile(
            user=user,
            first_name=form.cleaned_data['first_name'],
            last_name=form.cleaned_data['last_name'],
            organization=form.cleaned_data['organization'],
            accept_eula=form.cleaned_data['accept_eula']
        )
        if commit:
            profile.save()

        return user


class GroupAdminForm(forms.ModelForm):
    class Meta:
        model = Group
        exclude = []

    # Add list of users to group selection form
    users = forms.ModelMultipleChoiceField(
         queryset=get_user_model().objects.all(),
         required=False,
         widget=FilteredSelectMultiple('users', False,
                                       attrs={'readonly': True}),
         label='Users'
    )

    def __init__(self, *args, **kwargs):
        super(GroupAdminForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['users'].initial = self.instance.user_set.all()

    def save_m2m(self):
        self.instance.user_set.set(self.cleaned_data['users'])

    def save(self, *args, **kwargs):
        instance = super(GroupAdminForm, self).save()
        self.save_m2m()
        return instance
