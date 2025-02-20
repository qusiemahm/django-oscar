# Python Standard Library
import datetime
from decimal import Decimal

# Django Core
from django import forms, http
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    login as auth_login,
    logout as auth_logout,
    update_session_auth_hash,
)
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import generic

# Third-party Apps
from plans.models import Plan, UserPlan
from plans.signals import activate_user_plan
from plans.plan_change import StandardPlanChangePolicy
from server.apps.payments.gateways.tap import TapPaymentGateway
from plans.models import Order as PlansOrder
from plans.base.models import UserPlanCancellationReason


class SubscriptionsListView(generic.TemplateView):
    template_name = "oscar/dashboard/subscription/subscription.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        ctx = super().get_context_data(**kwargs)
        ctx["dashboard"] = True
        ctx["currency"] = settings.PLANS_CURRENCY
        if hasattr(user, "vendor"):
            ctx["available_plans"] = Plan.objects.filter(
                available=True, plan_for="vendors"
            ).order_by("-order")
        else:
            ctx["school"] = True
            ctx["available_plans"] = Plan.objects.filter(
                available=True, plan_for="schools"
            )
        try:
            ctx["current_plan"] = user.userplan.plan
            ctx["students_count"] = user.userplan.students
            ctx["branches_count"] = user.userplan.branches
            ctx["current_plan_paid"] = user.userplan.paid
            ctx["current_plan_active"] = user.userplan.is_active()
            ctx["current_plan_trial"] = user.userplan.is_trial()
            ctx["current_plan_trial_end_date"] = user.userplan.trial_end_date
            ctx["current_plan_expired"] = user.userplan.is_expired()
            ctx["current_plan_canceled"] = user.userplan.is_canceled()
            ctx["current_plan_canceled_date"] = user.userplan.canceled_date
            ctx["expiration_date"] = user.userplan.expire
        except:
            ctx["current_plan"] = None
        return ctx


class CancelSubscriptionForm(forms.Form):
    # Adding a fixed choice "Others"
    OTHER_REASON = "other"

    cancellation_reason = forms.ChoiceField(
        choices=[],  # Empty choices, will be populated in __init__
        required=True,
        label=_("Cancellation Reason"),
    )
    custom_reason = forms.CharField(
        max_length=256,
        required=False,
        label=_("Specify reason"),
        help_text=_("If your reason is not listed, please specify."),
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": _("Please specify your reason here."),
            }
        ),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Dynamically set the choices for cancellation_reason
        self.fields["cancellation_reason"].choices = (
            [("", _("Select a reason"))]
            + [
                (cancellation_reason.id, cancellation_reason.reason)
                for cancellation_reason in UserPlanCancellationReason.objects.filter(
                    hidden=False
                )
            ]
            + [(self.OTHER_REASON, _("Other"))]  # Adding "Other" option
        )

    def clean(self):
        cleaned_data = super().clean()
        cancellation_reason = cleaned_data.get("cancellation_reason")
        custom_reason = cleaned_data.get("custom_reason")

        # If "Others" is selected, ensure the custom reason is provided
        if cancellation_reason == self.OTHER_REASON and not custom_reason:
            raise forms.ValidationError(_("Please provide your custom reason."))

        return cleaned_data


class CancelSubscription(generic.FormView):
    template_name = "oscar/dashboard/subscription/cancel-subscription.html"
    form_class = CancelSubscriptionForm
    success_url = reverse_lazy("dashboard:subscription-view")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dashboard"] = True
        # Don't assign the form class itself, instantiate it instead
        ctx["form"] = self.get_form()

        # Add the current subscription plan and expiration date
        try:
            user_plan = Plan.get_current_plan(self.request.user)
            ctx["current_plan"] = user_plan
            ctx["expiration_date"] = self.request.user.userplan.expire
        except UserPlan.DoesNotExist:
            ctx["current_plan"] = None
            ctx["expiration_date"] = None

        return ctx

    def form_valid(self, form):
        try:
            cancellation_reason = form.cleaned_data["cancellation_reason"]
            custom_reason = form.cleaned_data.get("custom_reason")
            current_plan = self.request.user.userplan
            # Log or save the cancellation reason
            if custom_reason:
                current_plan.cancellation_reason = (
                    UserPlanCancellationReason.objects.create(reason=custom_reason)
                )
            else:
                current_plan.cancellation_reason_id = int(cancellation_reason)
            # Cancel the subscription
            current_plan.cancel()  # will call save()

            messages.success(
                self.request, _("Your subscription has been successfully cancelled.")
            )
            return redirect(self.get_success_url())
        except UserPlan.DoesNotExist:
            messages.error(
                self.request,
                _("Unable to cancel subscription. No active subscription found."),
            )
            return redirect("dashboard:subscription-view")
        except Exception as e:
            print(e)
            messages.error(
                self.request,
                _(
                    "An error occurred while cancelling your subscription. Please try again."
                ),
            )
            return self.form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("dashboard:login")
        return super().dispatch(request, *args, **kwargs)


class ReactivateSubscriptionView(generic.View):
    success_url = reverse_lazy("dashboard:subscription-view")

    def post(self, request, *args, **kwargs):
        user = request.user

        try:
            user_plan = user.userplan

            # Ensure the subscription was canceled
            if not user_plan.is_canceled():
                messages.error(
                    request,
                    _("You don't have a canceled subscription to activate."),
                )
                return redirect(self.success_url)

            # Check if the plan is expired
            if user_plan.is_expired() and user_plan.paid:
                messages.error(
                    request,
                    _(
                        "The subscription plan has expired. Reactivation is not possible."
                    ),
                )
                return redirect(self.success_url)

            # Check if the trial period is expired
            if not user_plan.is_trial() and not user_plan.paid:
                messages.error(
                    request,
                    _("The trial period has expired. Reactivation is not possible."),
                )
                return redirect(self.success_url)

            # Reactivate the subscription
            user_plan.canceled_date = None
            user_plan.cancellation_reason = None
            user_plan.save()

            messages.success(
                request, _("Your subscription has been successfully activated.")
            )
            return redirect(self.success_url)

        except UserPlan.DoesNotExist:
            messages.error(
                request,
                _("Unable to reactivate subscription. No subscription found."),
            )
            return redirect(self.success_url)

        except Exception as e:
            messages.error(
                request,
                _(
                    "An error occurred while activating your subscription. Please try again."
                ),
            )
            return redirect(self.success_url)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("dashboard:login")
        return super().dispatch(request, *args, **kwargs)


class SubscribeView(generic.View):
    template_name = "oscar/dashboard/subscription/subscribe-confirmation.html"
    success_url = reverse_lazy("payments:tap-payment")

    def get(self, request, *args, **kwargs):
        plan_id = request.GET.get("plan_id")
        if not plan_id:
            messages.error(request, _("No plan selected."))
            return redirect(self.success_url)

        try:
            plan = Plan.objects.get(id=plan_id)
            context = self.get_context_data(plan)
            return render(request, self.template_name, context)
        except Plan.DoesNotExist:
            messages.error(request, _("Selected plan does not exist."))
            return redirect(self.success_url)

    def get_context_data(self, plan):
        user = self.request.user
        if hasattr(user, "school"):
            school = user.school
            branches_count = (
                school.school_details.branches_count
                if hasattr(school, "school_details")
                else 1
            )
            students_count = (
                school.school_details.students_count
                if hasattr(school, "school_details")
                else 1
            )
        else:
            vendor = user.vendor
            branches_count = (
                school.business_details.branches_count
                if hasattr(vendor, "business_details")
                else 1
            )
            students_count = 0
        authorize = self.request.GET.get("authorize", None)
        return {
            "plan": plan,
            "currency": settings.PLANS_CURRENCY,
            "dashboard": True,
            "school_reg": True,
            "students_count": students_count,
            "branches_count": branches_count,
            "students_total": plan.price_per_student * students_count,
            "branches_total": plan.price() * branches_count,
            "total_price": (plan.price_per_student * students_count)
            + (plan.price() * branches_count),
            "authorize": authorize,
        }

    def post(self, request, *args, **kwargs):
        plan_id = request.POST.get("plan_id")
        authorize = request.POST.get("authorize", 0)
        branches = int(request.POST.get("branches", 1))
        students = int(request.POST.get("students", 1))
        if not plan_id:
            messages.error(request, _("No plan selected."))
            return redirect(self.success_url)

        if branches < 1:
            messages.error(request, _("Number of branches must be at least 1."))
            return redirect(request.path)
        if students < 1:
            messages.error(request, _("Number of students must be at least 1."))
            return redirect(request.path)
        try:
            # Get the selected plan
            plan = Plan.objects.get(id=plan_id)
            user = request.user

            # Check if user already has an active subscription
            existing_plan = UserPlan.objects.filter(
                user=user,
            ).first()

            if existing_plan:
                existing_plan.plan = plan
                existing_plan.save()
            else:
                UserPlan.objects.create(
                    user=user,
                    plan=plan,
                    active=False,
                    branches=branches,
                    students=students,
                )

            # activate_user_plan.send(
            #     sender=self,
            #     user=user
            # )

            # messages.success(
            #     request,
            #     _("Successfully subscribed to {} with {} branches for {} {}").format(
            #         plan.name,
            #         branches,
            #         total_price,
            #         'USD'
            #     )
            # )

        except Plan.DoesNotExist:
            messages.error(request, _("Selected plan does not exist."))
        except ValueError:
            messages.error(request, _("Invalid number of branches provided."))
        except Exception as e:
            print(e)
            messages.error(
                request,
                _(
                    "An error occurred while processing your subscription. Please try again."
                ),
            )
        redirect_url = self.success_url
        if authorize:
            redirect_url = f"{redirect_url}?authorize=1"
        return redirect(redirect_url)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("dashboard:login")
        return super().dispatch(request, *args, **kwargs)


class ChangeSubscriptionView(generic.View):
    template_name = "oscar/dashboard/subscription/change-subscription.html"
    success_url = reverse_lazy("dashboard:subscription-view")

    def get(self, request, *args, **kwargs):
        plan_id = request.GET.get("plan_id")
        if not plan_id:
            messages.error(request, _("No plan selected for change."))
            return redirect(self.success_url)

        try:
            new_plan = Plan.objects.get(id=plan_id)
            context = self.get_context_data(new_plan)
            return render(request, self.template_name, context)
        except Plan.DoesNotExist:
            messages.error(request, _("Selected plan does not exist."))
            return redirect(self.success_url)

    def get_context_data(self, new_plan):
        user = self.request.user
        try:
            current_plan = self.request.user.userplan
            branches_count = current_plan.branches
            students_count = current_plan.students
            days_left = (
                current_plan.days_left()
                if current_plan.days_left()
                else current_plan.plan.pricing().pricing.period
            )
            context = {
                "new_plan": new_plan,
                "currency": settings.PLANS_CURRENCY,
                "dashboard": True,
                "school_reg": True,
                "students_count": students_count,
                "branches_count": branches_count,
                "old_students_total": current_plan.plan.price_per_student
                * students_count,
                "students_total": new_plan.price_per_student * students_count,
                "branches_total": new_plan.price() * branches_count,
                "old_branches_total": current_plan.plan.price() * branches_count,
                "total_price": (new_plan.price_per_student * students_count)
                + (new_plan.price() * branches_count),
                "old_total_price": (
                    current_plan.plan.price_per_student * students_count
                )
                + (current_plan.plan.price() * branches_count),
                "new_plan_day_cost": StandardPlanChangePolicy()._calculate_day_cost(
                    current_plan, new_plan, days_left
                ),
                "current_plan": current_plan.plan,
                "current_plan_days_left": days_left,
                "current_branches": current_plan.branches,
                "expiration_date": current_plan.expire,
                "current_plan_day_cost": StandardPlanChangePolicy()._calculate_day_cost(
                    current_plan, current_plan.plan, days_left
                ),
                "change_price": StandardPlanChangePolicy().get_change_price(
                    current_plan,
                    current_plan.plan,
                    new_plan,
                    days_left,
                ),
                "current_plan_trial": current_plan.is_trial(),
                "current_plan_trial_end_date": current_plan.trial_end_date,
            }
        except UserPlan.DoesNotExist:
            context.update({"current_plan": None, "expiration_date": None})

        return context

    def post(self, request, *args, **kwargs):
        new_plan_id = request.POST.get("plan_id")
        total_price = float(request.POST.get("total_price", 0.0))

        if not new_plan_id:
            messages.error(request, _("No plan selected for change."))
            return redirect(self.success_url)

        try:
            # Get current and new plans
            current_plan = request.user.userplan
            new_plan = Plan.objects.get(id=new_plan_id)

            if current_plan.plan.id == new_plan.id:
                messages.error(request, _("This is already your current plan."))
                return redirect(self.success_url)

            if current_plan.is_trial():
                current_plan.plan = new_plan
                current_plan.save()
                messages.success(
                    request,
                    _("Successfully changed to plan {} for {} branches").format(
                        new_plan.name, current_plan.branches
                    ),
                )
                return redirect(self.success_url)

            if not total_price:
                current_plan.extend_account(new_plan, None)
                current_plan.save()
                messages.success(
                    request,
                    _("Successfully changed to plan {} for {} branches").format(
                        new_plan.name, current_plan.branches
                    ),
                )
            else:
                gateway = TapPaymentGateway()
                user = self.request.user
                # Create django-plans order
                plans_order = PlansOrder.objects.create(
                    user=user,
                    plan=new_plan,
                    amount=total_price,
                    branches_number=current_plan.branches,
                    students_number=(
                        current_plan.students
                        if new_plan.plan_for == "schools"
                        else None
                    ),
                    currency=settings.PLANS_CURRENCY,
                )
                # Create Tap charge
                tap_response = gateway.create_charge(
                    user=user,
                    order_number=plans_order.pk,
                    amount=float(plans_order.amount),
                    customer=self.get_customer_data(),
                    redirect_url=f"{self.get_redirect_url()}?new_plan={new_plan.pk}",
                    save_card=True,
                )
                # Get the redirect URL and redirect the user
                redirect_url = gateway.get_redirect_url(tap_response)
                return HttpResponseRedirect(redirect_url)

        except UserPlan.DoesNotExist:
            messages.error(
                request, _("You don't have an active subscription to change.")
            )
        except Plan.DoesNotExist:
            messages.error(request, _("Selected plan does not exist."))
        except ValueError as e:
            messages.error(request, _("Invalid number of branches provided."))
        except Exception as e:
            print(e)
            messages.error(
                request,
                _("An error occurred while changing your plan. Please try again."),
            )

        return redirect(self.success_url)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("dashboard:login")
        return super().dispatch(request, *args, **kwargs)

    def get_customer_data(self):
        return {
            "id": self.request.user.tap_customer_id,
            "first_name": self.request.user.first_name,
            "last_name": self.request.user.last_name,
            "email": self.request.user.email,
            "phone": {"country_code": "966", "number": self.request.user.phone_number},
        }

    def get_redirect_url(self):
        return self.request.build_absolute_uri(reverse("payments:tap-callback"))


class UpdateBranchesView(generic.View):
    success_url = reverse_lazy("dashboard:subscription-view")

    def post(self, request, *args, **kwargs):
        branches = int(request.POST.get("branches"))
        students = int(request.POST.get("students"))
        total_price = float(request.POST.get("total_price"))

        current_plan = request.user.userplan
        if current_plan.is_trial():
            current_plan.students = current_plan.students + students
            current_plan.branches = current_plan.branches + branches
            current_plan.save()
            messages.success(
                request, _("Your subscription has been updated successfully.")
            )
        else:
            try:
                if total_price > 0:
                    # Charge the user for additional costs
                    gateway = TapPaymentGateway()
                    user = request.user

                    # Create a new order
                    plans_order = PlansOrder.objects.create(
                        user=user,
                        plan=current_plan.plan,
                        amount=total_price,
                        branches_number=current_plan.branches,
                        students_number=current_plan.students,
                        currency=settings.PLANS_CURRENCY,
                    )

                    # Create Tap charge
                    tap_response = gateway.create_charge(
                        user=user,
                        order_number=plans_order.pk,
                        amount=float(plans_order.amount),
                        customer=self.get_customer_data(),
                        redirect_url=f"{self.get_redirect_url()}?update_plan_id={current_plan.pk}",
                        save_card=True,
                        metadata={
                            "additional_branches": branches,
                            "additional_students": students,
                            "additional_branches_price": float(
                                current_plan.plan.price() * branches
                            ),
                            "additional_students_price": float(
                                current_plan.plan.price_per_student * students
                            ),
                        },
                    )
                    # Get the redirect URL and redirect the user
                    redirect_url = gateway.get_redirect_url(tap_response)
                    return HttpResponseRedirect(redirect_url)

                messages.success(
                    request, _("Your subscription has been updated successfully.")
                )

            except Exception as e:
                messages.error(
                    request,
                    _(
                        "An error occurred while updating your subscription. Please try again."
                    ),
                )
                print(e)

        return redirect(self.success_url)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("dashboard:login")
        return super().dispatch(request, *args, **kwargs)

    def get_customer_data(self):
        return {
            "id": self.request.user.tap_customer_id,
            "first_name": self.request.user.first_name,
            "last_name": self.request.user.last_name,
            "email": self.request.user.email,
            "phone": {"country_code": "966", "number": self.request.user.phone_number},
        }

    def get_redirect_url(self):
        return self.request.build_absolute_uri(reverse("payments:tap-callback"))


class RenewSubscriptionView(generic.View):
    success_url = reverse_lazy("dashboard:subscription-view")

    def post(self, request, *args, **kwargs):
        try:
            # Get the expired plan
            expired_plan = request.user.userplan
            expired_plan.expire = None
            expired_plan.save()

            payment = True
            if payment:
                # Send activation signal
                activate_user_plan.send(sender=self, user=request.user)

                messages.success(
                    request, _("Your subscription has been successfully renewed.")
                )

        except UserPlan.DoesNotExist:
            messages.error(
                request, _("Unable to find the expired subscription to renew.")
            )
            return redirect(self.success_url)
        except Exception as e:
            print(e)
            messages.error(
                request,
                _(
                    "An error occurred while renewing your subscription. Please try again."
                ),
            )
            return redirect(self.success_url)

        return redirect(self.success_url)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("dashboard:login")
        return super().dispatch(request, *args, **kwargs)
