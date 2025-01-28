from django import forms
from django.core import exceptions
from django.utils.translation import gettext_lazy as _
from server.apps.catalogue.models import ProductBranch
from server.apps.vendor.models import Vendor
from treebeard.forms import movenodeform_factory
from server.apps.service.models import ServicePolicy

from oscar.core.loading import get_class, get_classes, get_model
from oscar.core.utils import slugify
from oscar.forms.widgets import DateTimePickerInput, ImageInput

Store = get_model('stores', 'Store')
Product = get_model("catalogue", "Product")
ProductClass = get_model("catalogue", "ProductClass")
ProductAttribute = get_model("catalogue", "ProductAttribute")
Category = get_model("catalogue", "Category")
StockRecord = get_model("partner", "StockRecord")
ProductCategory = get_model("catalogue", "ProductCategory")
ProductImage = get_model("catalogue", "ProductImage")
ProductRecommendation = get_model("catalogue", "ProductRecommendation")
AttributeOptionGroup = get_model("catalogue", "AttributeOptionGroup")
AttributeOption = get_model("catalogue", "AttributeOption")
Option = get_model("catalogue", "Option")
ProductSelect = get_class("dashboard.catalogue.widgets", "ProductSelect")
Service = get_model("service", "Service")

(RelatedFieldWidgetWrapper, RelatedMultipleFieldWidgetWrapper) = get_classes(
    "dashboard.widgets",
    ("RelatedFieldWidgetWrapper", "RelatedMultipleFieldWidgetWrapper"),
)


BaseCategoryForm = movenodeform_factory(
    Category,
    fields=[
        "name_en",
        "name_ar",
        "slug",
        "description_en",
        "description_ar",
        "image",
        "is_public",
        "order",
        "meta_title",
        "meta_description",
    ],
    exclude=["ancestors_are_public"],
    widgets={"meta_description": forms.Textarea(attrs={"class": "no-widget-init"})},
)


class SEOFormMixin:
    seo_fields = ["meta_title", "meta_description", "slug"]

    def primary_form_fields(self):
        return [
            field
            for field in self
            if not field.is_hidden and not self.is_seo_field(field)
        ]

    def seo_form_fields(self):
        return [field for field in self if self.is_seo_field(field)]

    def is_seo_field(self, field):
        return field.name in self.seo_fields


class CategoryForm(SEOFormMixin, BaseCategoryForm):
    def __init__(self, *args, **kwargs):
        self.vendor = kwargs.pop('vendor', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.vendor:
            instance.vendor = self.vendor
        if commit:
            instance.save()
        return instance


class ProductClassSelectForm(forms.Form):
    """
    Form which is used before creating a product to select it's product class
    """

    product_class = forms.ModelChoiceField(
        label=_("Create a new product of type"),
        empty_label=_("-- Choose type --"),
        queryset=ProductClass.objects.all(),
    )

    def __init__(self, *args, **kwargs):
        """
        If there's only one product class, pre-select it
        """
        super().__init__(*args, **kwargs)
        qs = self.fields["product_class"].queryset
        if not kwargs.get("initial") and len(qs) == 1:
            self.fields["product_class"].initial = qs[0]


class ProductSearchForm(forms.Form):
    # upc = forms.CharField(max_length=64, required=False, label=_("UPC"))
    title = forms.CharField(max_length=255, required=False, label=_("Product title"))

    def clean(self):
        cleaned_data = super().clean()
        # cleaned_data["upc"] = cleaned_data["upc"].strip()
        cleaned_data["title"] = cleaned_data["title"].strip()
        return cleaned_data


class StockRecordForm(forms.ModelForm):
    def __init__(self, product_class, user, *args, **kwargs):
        # The user kwarg is not used by stock StockRecordForm. We pass it
        # anyway in case one wishes to customise the partner queryset
        self.user = user
        super().__init__(*args, **kwargs)

        vendor = Vendor.objects.filter(user=user).first()
        if vendor:
            # For example, only show the user’s own branches
            self.fields['branch'].queryset = Store.objects.filter(vendor=vendor)

        # If you want it required, etc.
        self.fields['branch'].required = True
        
        # Restrict accessible partners for non-staff users
        # if not self.user.is_staff:
        #     self.fields["store"].queryset = self.user.partners.all()

        # If not tracking stock, we hide the fields
        if not product_class.track_stock:
            for field_name in ["num_in_stock", "low_stock_threshold"]:
                if field_name in self.fields:
                    del self.fields[field_name]
        else:
            # for field_name in ["price", "num_in_stock"]:
            for field_name in ["num_in_stock"]:
                if field_name in self.fields:
                    self.fields[field_name].required = True

    class Meta:
        model = StockRecord
        fields = [
            "branch",
            # "partner_sku",
            # "price_currency",
            # "price",
            "num_in_stock",
            "low_stock_threshold",
        ]


def _attr_text_field(attribute):
    return forms.CharField(label=attribute.name, required=attribute.required)


def _attr_textarea_field(attribute):
    return forms.CharField(
        label=attribute.name, widget=forms.Textarea(), required=attribute.required
    )


def _attr_integer_field(attribute):
    return forms.IntegerField(label=attribute.name, required=attribute.required)


def _attr_boolean_field(attribute):
    return forms.BooleanField(label=attribute.name, required=attribute.required)


def _attr_float_field(attribute):
    return forms.FloatField(label=attribute.name, required=attribute.required)


def _attr_date_field(attribute):
    return forms.DateField(
        label=attribute.name,
        required=attribute.required,
        widget=forms.widgets.DateInput,
    )


def _attr_datetime_field(attribute):
    return forms.DateTimeField(
        label=attribute.name, required=attribute.required, widget=DateTimePickerInput()
    )


def _attr_option_field(attribute):
    return forms.ModelChoiceField(
        label=attribute.name,
        required=attribute.required,
        queryset=attribute.option_group.options.all(),
    )


def _attr_multi_option_field(attribute):
    return forms.ModelMultipleChoiceField(
        label=attribute.name,
        required=attribute.required,
        queryset=attribute.option_group.options.all(),
    )


# pylint: disable=unused-argument
def _attr_entity_field(attribute):
    # Product entities don't have out-of-the-box supported in the ProductForm.
    # There is no ModelChoiceField for generic foreign keys, and there's no
    # good default behaviour anyway; offering a choice of *all* model instances
    # is hardly useful.
    return None


def _attr_numeric_field(attribute):
    return forms.FloatField(label=attribute.name, required=attribute.required)


def _attr_file_field(attribute):
    return forms.FileField(label=attribute.name, required=attribute.required)


def _attr_image_field(attribute):
    return forms.ImageField(label=attribute.name, required=attribute.required)


class ProductForm(SEOFormMixin, forms.ModelForm):
    FIELD_FACTORIES = {
        "text": _attr_text_field,
        "richtext": _attr_textarea_field,
        "integer": _attr_integer_field,
        "boolean": _attr_boolean_field,
        "float": _attr_float_field,
        "date": _attr_date_field,
        "datetime": _attr_datetime_field,
        "option": _attr_option_field,
        "multi_option": _attr_multi_option_field,
        "entity": _attr_entity_field,
        "numeric": _attr_numeric_field,
        "file": _attr_file_field,
        "image": _attr_image_field,
    }

    class Meta:
        model = Product
        fields = [
            "title_en",
            "title_ar",
            "upc",
            "description_en",
            "description_ar",
            "is_public",
            # "is_discountable",
            "structure",
            "slug",
            "meta_title",
            "meta_description",
            "original_price",
            "selling_price",
            "price_currency",
        ]
        widgets = {
            "structure": forms.HiddenInput(),
            "meta_description": forms.Textarea(attrs={"class": "no-widget-init"}),
        }

    def __init__(self, product_class, *args, data=None, parent=None, **kwargs):
        self.product_class = product_class
        self.set_initial(product_class, parent, kwargs)
        super().__init__(data, *args, **kwargs)
        if parent:
            self.instance.parent = parent
            # We need to set the correct product structures explicitly to pass
            # attribute validation and child product validation. Note that
            # those changes are not persisted.
            self.instance.structure = Product.CHILD
            self.instance.parent.structure = Product.PARENT

            self.delete_non_child_fields()
        else:
            # Only set product class for non-child products
            self.instance.product_class = product_class
        self.add_attribute_fields(product_class, self.instance.is_parent)

        if "slug" in self.fields:
            self.fields["slug"].required = False
            self.fields["slug"].help_text = _(
                "Leave blank to generate from product title"
            )
        if "title" in self.fields:
            self.fields["title"].widget = forms.TextInput(attrs={"autocomplete": "off"})

        if product_class and product_class.name.lower() == "services":
            self.add_policy_fields()

            if 'instance' in kwargs and kwargs['instance']:
                instance = kwargs['instance']
                try:
                    try:
                        service_policy = instance.service_policy
                    except ServicePolicy.DoesNotExist:
                        service_policy = None
                    self.fields['cancellation_policy'].initial = service_policy.cancellation_policy
                    self.fields['rescheduling_policy'].initial = service_policy.rescheduling_policy
                except ServicePolicy.DoesNotExist:
                    pass

    def add_policy_fields(self):
        """
        Add policy fields dynamically for "services" product class.
        """
        self.fields["cancellation_policy"] = forms.CharField(
            required=False,
            widget=forms.Textarea(attrs={"rows": 3}),
            label=_("Cancellation Policy"),
            help_text=_("Details about the cancellation policy for this service."),
        )
        self.fields["rescheduling_policy"] = forms.CharField(
            required=False,
            widget=forms.Textarea(attrs={"rows": 3}),
            label=_("Rescheduling Policy"),
            help_text=_("Details about the rescheduling policy for this service."),
        )


    def set_initial(self, product_class, parent, kwargs):
        """
        Set initial data for the form. Sets the correct product structure
        and fetches initial values for the dynamically constructed attribute
        fields.
        """
        if "initial" not in kwargs:
            kwargs["initial"] = {}
        self.set_initial_attribute_values(product_class, kwargs)
        if parent:
            kwargs["initial"]["structure"] = Product.CHILD

    def set_initial_attribute_values(self, product_class, kwargs):
        """
        Update the kwargs['initial'] value to have the initial values based on
        the product instance's attributes
        """
        instance = kwargs.get("instance")
        if instance is None:
            return
        for attribute in product_class.attributes.all():
            try:
                value = instance.attribute_values.get(attribute=attribute).value
            except exceptions.ObjectDoesNotExist:
                pass
            else:
                kwargs["initial"]["attr_%s" % attribute.code] = value

    def add_attribute_fields(self, product_class, is_parent=False):
        """
        For each attribute specified by the product class, this method
        dynamically adds form fields to the product form.
        """
        for attribute in product_class.attributes.all():
            field = self.get_attribute_field(attribute)
            if field:
                self.fields["attr_%s" % attribute.code] = field
                # Attributes are not required for a parent product
                if is_parent:
                    self.fields["attr_%s" % attribute.code].required = False

    def get_attribute_field(self, attribute):
        """
        Gets the correct form field for a given attribute type.
        """
        return self.FIELD_FACTORIES[attribute.type](attribute)

    def delete_non_child_fields(self):
        """
        Deletes any fields not needed for child products. Override this if
        you want to e.g. keep the description field.
        """
        for field_name in ["description"]:
            if field_name in self.fields:
                del self.fields[field_name]

    def _post_clean(self):
        """
        Set attributes before ModelForm calls the product's clean method
        (which it does in _post_clean), which in turn validates attributes.
        """
        for attribute in self.instance.attr.get_all_attributes():
            field_name = "attr_%s" % attribute.code
            # An empty text field won't show up in cleaned_data.
            if field_name in self.cleaned_data:
                value = self.cleaned_data[field_name]
                setattr(self.instance.attr, attribute.code, value)
        super()._post_clean()

    def save(self, commit=True):
        # Save the Product instance first
        instance = super().save(commit=False)
        
        if commit:
            instance.save()  # Save the Product instance to the database

        # Now that the Product instance is saved, create/update the ServicePolicy
        if self.product_class and self.product_class.name.lower() == "services":
            ServicePolicy.objects.update_or_create(
                product=instance,
                defaults={
                    "cancellation_policy": self.cleaned_data.get("cancellation_policy", ""),
                    "rescheduling_policy": self.cleaned_data.get("rescheduling_policy", ""),
                },
            )

        return instance

class StockAlertSearchForm(forms.Form):
    status = forms.CharField(label=_("Status"))


class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ("category",)


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["product", "original", "caption", "display_order"]
        # use ImageInput widget to create HTML displaying the
        # actual uploaded image and providing the upload dialog
        # when clicking on the actual image.
        widgets = {
            "original": ImageInput(),
            "display_order": forms.HiddenInput(),
        }

    def __init__(self, *args, data=None, **kwargs):
        self.prefix = kwargs.get("prefix", None)
        instance = kwargs.get("instance", None)
        if not instance:
            initial = {"display_order": self.get_display_order()}
            initial.update(kwargs.get("initial", {}))
            kwargs["initial"] = initial
        super().__init__(data, *args, **kwargs)

    def get_display_order(self):
        return int(self.prefix.split("-").pop())


class ProductRecommendationForm(forms.ModelForm):
    class Meta:
        model = ProductRecommendation
        fields = ["primary", "recommendation", "ranking"]
        widgets = {
            "recommendation": ProductSelect,
        }


class ProductClassForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # pylint: disable=no-member
        remote_field = self._meta.model._meta.get_field("options").remote_field
        self.fields["options"].widget = RelatedMultipleFieldWidgetWrapper(
            self.fields["options"].widget, remote_field
        )

    class Meta:
        model = ProductClass
        fields = ["name", "track_stock", "options"]


class ProductAttributesForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # because we'll allow submission of the form with blank
        # codes so that we can generate them.
        self.fields["code"].required = False

        self.fields["option_group"].help_text = _("Select an option group")

        # pylint: disable=no-member
        remote_field = self._meta.model._meta.get_field("option_group").remote_field
        self.fields["option_group"].widget = RelatedFieldWidgetWrapper(
            self.fields["option_group"].widget, remote_field
        )

    def clean_code(self):
        code = self.cleaned_data.get("code")
        title = self.cleaned_data.get("name")

        if not code and title:
            code = slugify(title)

        return code

    def clean(self):
        attr_type = self.cleaned_data.get("type")
        option_group = self.cleaned_data.get("option_group")
        if (
            attr_type in [ProductAttribute.OPTION, ProductAttribute.MULTI_OPTION]
            and not option_group
        ):
            self.add_error("option_group", _("An option group is required"))

    class Meta:
        model = ProductAttribute
        fields = ["name", "code", "type", "option_group", "required"]


class AttributeOptionGroupForm(forms.ModelForm):
    class Meta:
        model = AttributeOptionGroup
        fields = ["name_en", "name_ar"]


class AttributeOptionForm(forms.ModelForm):
    class Meta:
        model = AttributeOption
        fields = ["option_en", "option_ar", "price"]


class OptionForm(forms.ModelForm):
    class Meta:
        model = Option
        fields = ["name_en", "name_ar", "type", "required", "order", "help_text", "option_group"]

class ProductBranchForm(forms.ModelForm):
    """
    Simple form for handling ProductBranch relationships
    between Product and Store.
    """
    class Meta:
        model = ProductBranch
        fields = ['branch']


class ProductOptionThroughModelForm(forms.ModelForm):
    """
    A form for the through-model (Product.product_options.through).
    Instead of a simple dropdown for 'option', we embed the needed Option fields.
    """

    # Fields from the Option model that you want users to manage inline:
    name = forms.CharField(label=_("Name"), required=True)
    type = forms.ChoiceField(
        label=_("Type"),
        choices=Option.TYPE_CHOICES,
        required=True,
    )
    required = forms.BooleanField(label=_("Required?"), required=False)
    help_text = forms.CharField(
        label=_("Help text"), required=False,
        widget=forms.TextInput()
    )
    order = forms.IntegerField(label=_("Order"), required=False, min_value=0)

    class Meta:
        model = Product.product_options.through
        # We do NOT include 'option' in fields, we manually handle it in .save()
        fields = ['id']  # + possibly other M2M through fields if you have any

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If we are editing an existing through-object, we have self.instance.pk.
        # The existing Option is self.instance.option
        existing_option = getattr(self.instance, 'option', None)
        if existing_option:
            # Pre-populate the fields from the Option instance
            self.fields['name'].initial = existing_option.name
            self.fields['type'].initial = existing_option.type
            self.fields['required'].initial = existing_option.required
            self.fields['help_text'].initial = existing_option.help_text
            self.fields['order'].initial = existing_option.order

    def save(self, commit=True):
        """
        Override save() to create/update the Option object using the inline fields.
        Then assign self.instance.option = that Option.
        Finally, save the through instance.
        """
        # 1) Create/update Option using the posted data
        data = self.cleaned_data

        if self.instance.option_id:
            # Editing an existing Option
            option = self.instance.option
        else:
            # Creating a new Option
            option = Option()

        option.name = data['name']
        option.type = data['type']
        option.required = data['required']
        option.help_text = data['help_text']
        option.order = data['order']

        # Possibly also set option.vendor = self.request.user.vendor (if you want to enforce that).
        # But we can't do that here easily because we don't have request in the form. 
        # One approach: pass the vendor in form's __init__ or do it in the formset.

        if commit:
            option.save()

        # 2) Assign the Option to the through instance
        self.instance.option = option

        # 3) Let ModelForm handle saving the through instance (with commit)
        return super().save(commit=commit)