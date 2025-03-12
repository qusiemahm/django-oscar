# pylint: disable=attribute-defined-outside-init


from django.conf import settings
from django.contrib import messages
from django.views.generic import ListView, UpdateView, CreateView, DeleteView
from oscar.core.loading import get_class, get_model
from django.urls import reverse_lazy
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

Branch = get_model("school", "Branch")
BranchForm = get_class("dashboard.school.forms", "BranchForm")


class BranchListView(ListView):
    model = Branch
    template_name = 'oscar/dashboard/school/branch_list.html'
    context_object_name = 'branches'

    def get_queryset(self):
        if hasattr(self.request.user, 'school'):
            return Branch.objects.filter(
                school=self.request.user.school
            )
        return Branch.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.request.user.school
        school_details = getattr(self.request.user.school, 'school_details', None)
        context['max_branches'] = school_details.branches_count
        context['current_branches'] = self.request.user.school.branches.count()
        return context

class BranchCreateView(CreateView):
    model = Branch
    form_class = BranchForm
    template_name = 'oscar/dashboard/school/branch_form.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['GOOGLE_MAPS_API_KEY'] = settings.GOOGLE_MAPS_API_KEY
        return context
    def get_success_url(self):
        return reverse_lazy('dashboard:school-branches-list')

    def form_valid(self, form):
        form.instance.school = self.request.user.school
        try:
            response = super().form_valid(form)
            messages.success(self.request, _('Branch created successfully.'))
            return response
        except ValidationError as e:
            form.add_error(None, e.message)
            return self.form_invalid(form)

class BranchUpdateView(UpdateView):
    model = Branch
    form_class = BranchForm
    template_name = 'oscar/dashboard/school/branch_form.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['GOOGLE_MAPS_API_KEY'] = settings.GOOGLE_MAPS_API_KEY
        return context
    def get_success_url(self):
        return reverse_lazy('dashboard:school-branches-list')

    def get_queryset(self):
        return Branch.objects.filter(
            school=self.request.user.school
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Branch updated successfully.'))
        return response

class BranchDeleteView(DeleteView):
    model = Branch
    template_name = 'oscar/dashboard/school/branch_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('dashboard:school-branches-list')

    def get_queryset(self):
        return Branch.objects.filter(
            school=self.request.user.school
        )

    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Branch deleted successfully.'))
        return super().delete(request, *args, **kwargs)