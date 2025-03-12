from django.urls import path
from django.utils.translation import gettext_lazy as _

from oscar.core.application import OscarDashboardConfig
from oscar.core.loading import get_class


class SchoolDashboardConfig(OscarDashboardConfig):
    label = "school_dashboard"
    name = "oscar.apps.dashboard.school"
    verbose_name = _("School dashboard")

    # pylint: disable=attribute-defined-outside-init
    def ready(self):
        self.branch_list_view = get_class("dashboard.school.views", "BranchListView")
        self.branch_create_view = get_class("dashboard.school.views", "BranchCreateView")
        self.branch_update_view = get_class("dashboard.school.views", "BranchUpdateView")
        self.branch_delete_view = get_class("dashboard.school.views", "BranchDeleteView")
        
    def get_urls(self):
        urls = [
            path("branches/", self.branch_list_view.as_view(), name="school-branches-list"),
            path('branches/create/', self.branch_create_view.as_view(), name='school-branch-create'),
            path('branches/<int:pk>/update/', self.branch_update_view.as_view(), name='school-branch-update'),
            path('branches/<int:pk>/delete/', self.branch_delete_view.as_view(), name='school-branch-delete'),
        ]

        return self.post_process_urls(urls)
