from django import forms
from django.forms.models import construct_instance, InlineForeignKeyField
from .models import Report

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason', 'description']
        widgets = {
            'reason': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'يرجى توضيح سبب الإبلاغ...',
                'rows': 4
            })
        }

    def _post_clean(self):
        opts = self._meta
        exclude = self._get_validation_exclusions()
        for name, field in self.fields.items():
            if isinstance(field, InlineForeignKeyField):
                exclude.add(name)
        try:
            self.instance = construct_instance(self, self.instance, opts.fields, opts.exclude)
        except forms.ValidationError as e:
            self._update_errors(e)
        try:
            self.instance.clean_fields(exclude=exclude)
        except forms.ValidationError as e:
            self._update_errors(e)
        if self._validate_unique:
            self.validate_unique()