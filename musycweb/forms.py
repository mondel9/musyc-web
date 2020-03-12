from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from allauth.account import forms as allauth_forms
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Group
from .models import Dataset


class CreateDatasetForm(forms.Form):
    REQUIRED_FIELDS = {
        'expt.date',
        'drug1.conc',
        'drug2.conc',
        'effect',
        'sample',
        'drug1',
        'drug2',
        'drug1.units',
        'drug2.units'
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
    # emin_fixed = forms.FloatField(required=False)
    # emax_fixed = forms.FloatField(required=False)
    # emin_min = forms.FloatField(required=False)
    # emax_min = forms.FloatField(required=False)
    # emin_max = forms.FloatField(required=False)
    # emax_max = forms.FloatField(required=False)

    def __init__(self, *args, **kwargs):
        super(CreateDatasetForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-vertical'
        self.helper.add_input(Submit('submit', 'Create Dataset',
                                     css_class='btn-block'))

    def clean_file(self, ):
        f = self.cleaned_data['file']
        try:
            c = next(f.chunks())
        except StopIteration:
            raise forms.ValidationError('File is empty!')

        try:
            c = c.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise forms.ValidationError('File needs to use Unicode UTF-8 '
                                        'encoding. Is this a CSV file?')

        first_line = c.splitlines()[0]
        if ',' not in first_line:
            raise forms.ValidationError(
                'No comma detected in first line. Check separator is comma '
                'and not tab, for example.')

        headers = set(first_line.split(','))
        missing_headers = self.REQUIRED_FIELDS.difference(headers)
        if missing_headers:
            raise forms.ValidationError(
                f'Missing required fields: {", ".join(missing_headers)}'
            )


class CentredAuthForm(allauth_forms.LoginForm):
    def __init__(self, *args, **kwargs):
        super(CentredAuthForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-vertical'
        self.helper.add_input(Submit('submit', 'Log in',
                                     css_class='btn-block'))


class AddEmailForm(allauth_forms.AddEmailForm):
    def __init__(self, *args, **kwargs):
        super(AddEmailForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-vertical'
        self.helper.add_input(Submit('action_add', 'Add email',
                                     css_class='btn-block'))


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
    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['email'].widget.attrs.update({'autofocus': 'autofocus'})
        self.helper.form_class = 'form-vertical'
        self.helper.add_input(Submit('submit', 'Sign Up',
                                     css_class='btn-block'))


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
