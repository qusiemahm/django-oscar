from django.contrib.auth.decorators import login_required
from django.urls import path, re_path
from django.utils.translation import gettext_lazy as _
from django.views import generic

from oscar.core.application import OscarConfig
from oscar.core.loading import get_class


class CustomerConfig(OscarConfig):
    label = "customer"
    name = "oscar.apps.customer"
    verbose_name = _("Customer")

    namespace = "customer"

    # pylint: disable=attribute-defined-outside-init, reimported, unused-import
    def ready(self):
        from . import receivers
        from .alerts import receivers

        self.summary_view = get_class("customer.views", "AccountSummaryView")
        self.order_history_view = get_class("customer.views", "OrderHistoryView")
        self.order_detail_view = get_class("customer.views", "OrderDetailView")
        self.anon_order_detail_view = get_class(
            "customer.views", "AnonymousOrderDetailView"
        )
        self.order_line_view = get_class("customer.views", "OrderLineView")

        self.address_list_view = get_class("customer.views", "AddressListView")
        self.address_create_view = get_class("customer.views", "AddressCreateView")
        self.address_update_view = get_class("customer.views", "AddressUpdateView")
        self.address_delete_view = get_class("customer.views", "AddressDeleteView")
        self.address_change_status_view = get_class(
            "customer.views", "AddressChangeStatusView"
        )

        self.email_list_view = get_class("customer.views", "EmailHistoryView")
        self.email_detail_view = get_class("customer.views", "EmailDetailView")
        self.login_view = get_class("customer.views", "AccountAuthView")
        self.logout_view = get_class("customer.views", "LogoutView")
        self.register_view = get_class("customer.views", "AccountRegistrationView")
        self.profile_view = get_class("customer.views", "ProfileView")
        self.profile_update_view = get_class("customer.views", "ProfileUpdateView")
        self.profile_delete_view = get_class("customer.views", "ProfileDeleteView")
        self.change_password_view = get_class("customer.views", "ChangePasswordView")

        self.notification_inbox_view = get_class(
            "communication.notifications.views", "InboxView"
        )
        self.notification_archive_view = get_class(
            "communication.notifications.views", "ArchiveView"
        )
        self.notification_update_view = get_class(
            "communication.notifications.views", "UpdateView"
        )
        self.notification_detail_view = get_class(
            "communication.notifications.views", "DetailView"
        )

        self.alert_list_view = get_class(
            "customer.alerts.views", "ProductAlertListView"
        )
        self.alert_create_view = get_class(
            "customer.alerts.views", "ProductAlertCreateView"
        )
        self.alert_confirm_view = get_class(
            "customer.alerts.views", "ProductAlertConfirmView"
        )
        self.alert_cancel_view = get_class(
            "customer.alerts.views", "ProductAlertCancelView"
        )

        self.wishlists_add_product_view = get_class(
            "customer.wishlists.views", "WishListAddProduct"
        )
        self.wishlists_list_view = get_class(
            "customer.wishlists.views", "WishListListView"
        )
        self.wishlists_detail_view = get_class(
            "customer.wishlists.views", "WishListDetailView"
        )
        self.wishlists_create_view = get_class(
            "customer.wishlists.views", "WishListCreateView"
        )
        self.wishlists_create_with_product_view = get_class(
            "customer.wishlists.views", "WishListCreateView"
        )
        self.wishlists_update_view = get_class(
            "customer.wishlists.views", "WishListUpdateView"
        )
        self.wishlists_delete_view = get_class(
            "customer.wishlists.views", "WishListDeleteView"
        )
        self.wishlists_remove_product_view = get_class(
            "customer.wishlists.views", "WishListRemoveProduct"
        )
        self.wishlists_move_product_to_another_view = get_class(
            "customer.wishlists.views", "WishListMoveProductToAnotherWishList"
        )

    def get_urls(self):
        from django.shortcuts import redirect
        from django.urls import path, re_path
        from oscar.views.decorators import login_forbidden
        from django.views.generic import RedirectView

        def redirect_to_dashboard(request, *args, **kwargs):
            return redirect('/dashboard/')

        urls = [
            # Login, logout, and register
            path("login/", redirect_to_dashboard),
            path("login/", self.login_view.as_view(), name="login"),
            path("logout/", redirect_to_dashboard),
            path("logout/", self.logout_view.as_view(), name="logout"),
            path("register/", redirect_to_dashboard),
            path("register/", self.register_view.as_view(), name="register"),
            
            # Summary
            path("", redirect_to_dashboard),
            path("", login_required(self.summary_view.as_view()), name="summary"),
            
            # Change password
            path("change-password/", redirect_to_dashboard),
            path("change-password/", login_required(self.change_password_view.as_view()), name="change-password"),
            
            # Profile
            path("profile/", redirect_to_dashboard),
            path("profile/", login_required(self.profile_view.as_view()), name="profile-view"),
            path("profile/edit/", redirect_to_dashboard),
            path("profile/edit/", login_required(self.profile_update_view.as_view()), name="profile-update"),
            path("profile/delete/", redirect_to_dashboard),
            path("profile/delete/", login_required(self.profile_delete_view.as_view()), name="profile-delete"),
            
            # Subscription
            # path("subscription/", redirect_to_dashboard),
            # path("subscription/", login_required(self.subscription_view.as_view()), name="subscription-view"),
            # path("subscription/cancel/", redirect_to_dashboard),
            # path("subscription/cancel/", login_required(self.cancel_subscription_view.as_view()), name="cancel-subscription-view"),
            # path("subscription/cancel/confirm/", redirect_to_dashboard),
            # path("subscription/cancel/confirm/", login_required(self.cancel_subscription.as_view()), name="cancel-subscription"),
            # path("subscription/reactivate/", redirect_to_dashboard),
            # path("subscription/reactivate/", login_required(self.reactivate_subscription_view.as_view()), name="reactivate-subscription-view"),
            # path("subscription/subscribe/", redirect_to_dashboard),
            # path("subscription/subscribe/", login_required(self.subscripe_view.as_view()), name="subscribe-view"),
            # path("subscription/change/", redirect_to_dashboard),
            # path("subscription/change/", login_required(self.change_subscription_view.as_view()), name="change-subscription-view"),
            # path("subscription/renew/", redirect_to_dashboard),
            # path("subscription/renew/", login_required(self.renew_subscription_view.as_view()), name="renew-subscription-view"),
            
            # Order history
            path("orders/", redirect_to_dashboard),
            path("orders/", login_required(self.order_history_view.as_view()), name="order-list"),
            re_path(r"^order-status/(?P<order_number>[\w-]*)/(?P<hash>[A-z0-9-_=:]+)/$", redirect_to_dashboard),
            re_path(r"^order-status/(?P<order_number>[\w-]*)/(?P<hash>[A-z0-9-_=:]+)/$", self.anon_order_detail_view.as_view(), name="anon-order"),
            path("orders/<str:order_number>/", redirect_to_dashboard),
            path("orders/<str:order_number>/", login_required(self.order_detail_view.as_view()), name="order"),
            path("orders/<str:order_number>/<int:line_id>/", redirect_to_dashboard),
            path("orders/<str:order_number>/<int:line_id>/", login_required(self.order_line_view.as_view()), name="order-line"),
            
            # Address book
            path("addresses/", redirect_to_dashboard),
            path("addresses/", login_required(self.address_list_view.as_view()), name="address-list"),
            path("addresses/add/", redirect_to_dashboard),
            path("addresses/add/", login_required(self.address_create_view.as_view()), name="address-create"),
            path("addresses/<int:pk>/", redirect_to_dashboard),
            path("addresses/<int:pk>/", login_required(self.address_update_view.as_view()), name="address-detail"),
            path("addresses/<int:pk>/delete/", redirect_to_dashboard),
            path("addresses/<int:pk>/delete/", login_required(self.address_delete_view.as_view()), name="address-delete"),
            re_path(r"^addresses/(?P<pk>\d+)/(?P<action>default_for_(billing|shipping))/$", redirect_to_dashboard),
            re_path(r"^addresses/(?P<pk>\d+)/(?P<action>default_for_(billing|shipping))/$", login_required(self.address_change_status_view.as_view()), name="address-change-status"),
            
            # Email history
            path("emails/", redirect_to_dashboard),
            path("emails/", login_required(self.email_list_view.as_view()), name="email-list"),
            path("emails/<int:email_id>/", redirect_to_dashboard),
            path("emails/<int:email_id>/", login_required(self.email_detail_view.as_view()), name="email-detail"),
            
            # Notifications
            path("notifications/", redirect_to_dashboard),
            path("notifications/inbox/", redirect_to_dashboard),
            path("notifications/inbox/", login_required(self.notification_inbox_view.as_view()), name="notifications-inbox"),
            path("notifications/archive/", redirect_to_dashboard),
            path("notifications/archive/", login_required(self.notification_archive_view.as_view()), name="notifications-archive"),
            path("notifications/update/", redirect_to_dashboard),
            path("notifications/update/", login_required(self.notification_update_view.as_view()), name="notifications-update"),
            path("notifications/<int:pk>/", redirect_to_dashboard),
            path("notifications/<int:pk>/", login_required(self.notification_detail_view.as_view()), name="notifications-detail"),
            
            # Alerts
            path("alerts/", redirect_to_dashboard),
            path("alerts/", login_required(self.alert_list_view.as_view()), name="alerts-list"),
            path("alerts/create/<int:pk>/", redirect_to_dashboard),
            path("alerts/create/<int:pk>/", self.alert_create_view.as_view(), name="alert-create"),
            path("alerts/confirm/<str:key>/", redirect_to_dashboard),
            path("alerts/confirm/<str:key>/", self.alert_confirm_view.as_view(), name="alerts-confirm"),
            path("alerts/cancel/key/<str:key>/", redirect_to_dashboard),
            path("alerts/cancel/key/<str:key>/", self.alert_cancel_view.as_view(), name="alerts-cancel-by-key"),
            path("alerts/cancel/<int:pk>/", redirect_to_dashboard),
            path("alerts/cancel/<int:pk>/", login_required(self.alert_cancel_view.as_view()), name="alerts-cancel-by-pk"),
            
            # Wishlists
            path("wishlists/", redirect_to_dashboard),
            path("wishlists/", login_required(self.wishlists_list_view.as_view()), name="wishlists-list"),
            path("wishlists/add/<int:product_pk>/", redirect_to_dashboard),
            path("wishlists/add/<int:product_pk>/", login_required(self.wishlists_add_product_view.as_view()), name="wishlists-add-product"),
            path("wishlists/<str:key>/add/<int:product_pk>/", redirect_to_dashboard),
            path("wishlists/<str:key>/add/<int:product_pk>/", login_required(self.wishlists_add_product_view.as_view()), name="wishlists-add-product"),
            path("wishlists/create/", redirect_to_dashboard),
            path("wishlists/create/", login_required(self.wishlists_create_view.as_view()), name="wishlists-create"),
            path("wishlists/create/with-product/<int:product_pk>/", redirect_to_dashboard),
            path("wishlists/create/with-product/<int:product_pk>/", login_required(self.wishlists_create_view.as_view()), name="wishlists-create-with-product"),
            path("wishlists/<str:key>/", redirect_to_dashboard),
            path("wishlists/<str:key>/", self.wishlists_detail_view.as_view(), name="wishlists-detail"),
            path("wishlists/<str:key>/update/", redirect_to_dashboard),
            path("wishlists/<str:key>/update/", login_required(self.wishlists_update_view.as_view()), name="wishlists-update"),
            path("wishlists/<str:key>/delete/", redirect_to_dashboard),
            path("wishlists/<str:key>/delete/", login_required(self.wishlists_delete_view.as_view()), name="wishlists-delete"),
            path("wishlists/<str:key>/lines/<int:line_pk>/delete/", redirect_to_dashboard),
            path("wishlists/<str:key>/lines/<int:line_pk>/delete/", login_required(self.wishlists_remove_product_view.as_view()), name="wishlists-remove-product"),
            path("wishlists/<str:key>/products/<int:product_pk>/delete/", redirect_to_dashboard),
            path("wishlists/<str:key>/products/<int:product_pk>/delete/", login_required(self.wishlists_remove_product_view.as_view()), name="wishlists-remove-product"),
            path("wishlists/<str:key>/lines/<int:line_pk>/move-to/<str:to_key>/", redirect_to_dashboard),
            path("wishlists/<str:key>/lines/<int:line_pk>/move-to/<str:to_key>/", login_required(self.wishlists_move_product_to_another_view.as_view()), name="wishlists-move-product-to-another"),
        ]

        return self.post_process_urls(urls)
