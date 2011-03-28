import datetime
from copy import deepcopy

from django import forms
from django.forms.util import ErrorList
from django.forms import widgets

import braintree

from .odict import OrderedDict

class BraintreeForm(forms.Form):
    """
        A base Braintree form that defines common behaviors for all the
        various forms in this file for implementing Braintree transparent
        redirects.

        When creating a new instance of a Braintree form you MUST pass in a 
        result object as returned by BraintreeForm.get_result(...). You SHOULD
        also pass in a redirect_url keyword parameter.

            >>> result = MyForm.get_result(request)
            >>> form = MyForm(result, redirect_url="http://mysite.com/foo")

        Note that result may be None.

        Each BraintreeForm subclass must define a set of fields and its type,
        and can optionally define a set of labels and protected data. This is
        all dependent on the type of transparent redirect, which is documented
        here:

           http://www.braintreepaymentsolutions.com/gateway/transparent-redirect

        You can set any protected data easily:

            >>> form.tr_protected["options"]["submit_for_settlement"] = True

        Before rendering the form you MUST always generate the signed, hidden
        special data via:

            >>> form.generate_tr_data()

        To get the location to post data to you can use the action property in
        your templates:

            <form action="{{ form.action }}" method="POST">
                {{ form.as_table }}
                <button type="submit">Submit order</button>
            </form>
        
    """
    tr_type = ""
    
    # Order of fields matters so we used an ordered dictionary
    tr_fields = OrderedDict()
    tr_labels = {}
    tr_help = {}
    tr_protected = {}

    # A list of fields that should be boolean (checkbox) options
    tr_boolean_fields = []
    
    @classmethod
    def get_result(cls, request):
        """
            Get the result (or None) of a transparent redirect given a Django
            Request object.

                >>> result = MyForm.get_result(request)
                >>> if result.is_success:
                        take_some_action()

            This method uses the request.META["QUERY_STRING"] parameter to get
            the HTTP query string.
        """
        try:
            result = braintree.TransparentRedirect.confirm(request.META["QUERY_STRING"])
        except (KeyError, braintree.exceptions.not_found_error.NotFoundError):
            result = None

        return result

    def __init__(self, result, *args, **kwargs):
        self.redirect_url = kwargs.pop("redirect_url", "")

        # Create the form instance, with initial data if it was given
        if result:
            self.result = result
            data = self._flatten_dictionary(result.params)

            super(BraintreeForm, self).__init__(data, *args, **kwargs)

            # Are there any errors we should display?
            errors = self._flatten_errors(result.errors.errors.data)
            self.errors.update(errors)

        else:
            super(BraintreeForm, self).__init__(*args, **kwargs)

        # Dynamically setup all the required form fields
        # This is required because of the strange naming scheme that uses
        # characters not supported in Python variable names.
        labels = self._flatten_dictionary(self.tr_labels)
        helptext = self._flatten_dictionary(self.tr_help)
        for key in self._flatten_dictionary(self.tr_fields).keys():
            if key in labels:
                label = labels[key]
            else:
                label = key.split("[")[-1].strip("]").replace("_", " ").title()
            
            #override for default field
            if isinstance(self._flatten_dictionary(self.tr_fields)[key], forms.Field): 
                self.fields[key] = self._flatten_dictionary(self.tr_fields)[key]
                self.fields[key].label = label
                continue
            
            if key in self.tr_boolean_fields:
                # A checkbox MUST set value="true" for Braintree to pick
                # it up properly, refer to Braintree ticket #26438
                field = forms.BooleanField(label=label, required=False, widget=widgets.CheckboxInput(attrs={"checked": True, "value": "true", "class": "checkbox"}))
            elif key.endswith("[expiration_month]"):
                # Month selection should be a simple dropdown
                field = forms.ChoiceField(choices=[(x,x) for x in range(1, 13)], required=False, label=label)
            elif key.endswith("[expiration_year]"):
                # Year selection should be a simple dropdown
                year = datetime.date.today().year
                field = forms.ChoiceField(choices=[(x,x) for x in range(year, year + 16)], required=False, label=label)
            else:
                field = forms.CharField(label=label, required=False)

            if key in helptext:
                field.help_text = helptext[key]
                
            self.fields[key] = field

    def _flatten_dictionary(self, params, parent=None):
        """
            Flatten a hierarchical dictionary into a simple dictionary.

                >>> self._flatten_dictionary({
                    "test": {
                        "foo": 12,
                        "bar": "hello",
                    },
                    "baz": False
                })
                {
                    "test[foo]": 12,
                    "test[bar]": hello,
                    "baz": False
                }
                
        """
        data = OrderedDict()
        for key, val in params.items():
            full_key = parent + "[" + key + "]" if parent else key
            if isinstance(val, dict):
                data.update(self._flatten_dictionary(val, full_key))
            else:
                data[full_key] = val
        return data

    def _flatten_errors(self, params, parent=None):
        """
            A modified version of the flatten_dictionary method above used
            to coerce the structure holding errors returned by Braintree into
            a flattened dictionary where the keys are the names of the fields
            and the values the error messages, which can be directly used to
            set the field errors on the Django form object for display in
            templates.
        """
        data = OrderedDict()
        for key, val in params.items():
            full_key = parent + "[" + key + "]" if parent else key
            if full_key.endswith("[errors]"):
                full_key = full_key[:-len("[errors]")]
            if isinstance(val, dict):
                data.update(self._flatten_errors(val, full_key))
            elif key == "errors":
                for error in val:
                    data[full_key + "[" + error["attribute"] + "]"] = [error["message"]]
            else:
                data[full_key] = [val]
        return data

    def _remove_none(self, data):
        """
            Remove all items from a nested dictionary whose value is None.
        """
        for key, value in data.items():
            if value is None:
                del data[key]
            if isinstance(value, dict):
                self._remove_none(data[key])

    def generate_tr_data(self):
        """
            Generate the special signed tr_data field required to properly
            render and submit the form to Braintree. This MUST be called
            prior to rendering the form!
        """
        tr_data = deepcopy(self.tr_fields)
        
        if self._errors:
            tr_data.update(self.tr_protected)
        else:
            tr_data.recursive_update(self.tr_protected)
            
        self._remove_none(tr_data)

        if hasattr(getattr(braintree, self.tr_type), "tr_data_for_sale"):
            signed = getattr(braintree, self.tr_type).tr_data_for_sale(tr_data, self.redirect_url)
        else:
            signed = getattr(braintree, self.tr_type).tr_data_for_create(tr_data, self.redirect_url)
        
        self.fields["tr_data"] = forms.CharField(initial=signed, widget=widgets.HiddenInput())

    def remove_section(self, section):
        """
            Remove a section of fields from the form, e.g. allowing you to
            hide all shipping address information in one quick call if you
            don't care about it.
        """
        for key in self.fields.keys():
            if key.startswith(section):
                del self.fields[key]

    def clean(self):
        if isinstance(self.result, braintree.error_result.ErrorResult) and self.result.transaction:
            raise forms.ValidationError(u"Error Processing Credit Card: %s" % self.result.transaction.processor_response_text)

    @property
    def action(self):
        """
            Get the location to post data to. Use this property in your
            templates, e.g. <form action="{{ form.action }}" method="post">.
        """
        return braintree.TransparentRedirect.url()

class TransactionForm(BraintreeForm):
    """
        A form to enter transaction details.
    """
    tr_type = "Transaction"
    tr_fields = OrderedDict([
        ("transaction", OrderedDict([
            ("amount", None),
            ("customer", OrderedDict([
                ("first_name", None),
                ("last_name", None),
                ("company", None),
                ("email", None),
                ("phone", None),
                ("fax", None),
                ("website", None)]),
            ),
            ("credit_card", OrderedDict([
                ("cardholder_name", None),
                ("number", None),
                ("expiration_month", None),
                ("expiration_year", None),
                ("cvv", None)]),
            ),
            ("billing", OrderedDict([
                ("first_name", None),
                ("last_name", None),
                ("company", None),
                ("street_address", None),
                ("extended_address", None),
                ("locality", None),
                ("region", None),
                ("postal_code", None),
                ("country_name", None)]),
            ),
            ("shipping", OrderedDict([
                ("first_name", None),
                ("last_name", None),
                ("company", None),
                ("street_address", None),
                ("extended_address", None),
                ("locality", None),
                ("region", None),
                ("postal_code", None),
                ("country_name", None)]),
            ),
            ("options", OrderedDict([
                ("store_in_vault", None),
                ("add_billing_address_to_payment_method", None),
                ("store_shipping_address_in_vault", None)]),
            ),
        ])),
    ])
    tr_labels = {
        "transaction": {
            "credit_card": {
                "cvv": "CVV",
                "expiration_month": "Expiration Month",
                "expiration_year": "Expiration Year",
            },
            "options": {
                "store_in_vault": "Save credit card",
                "add_billing_address_to_payment_method": "Save billing address",
                "store_shipping_address_in_vault": "Save shipping address",
            },
        },
    }
    tr_protected = {
        "transaction": {
            "type": None,
            "order_id": None,
            "customer_id": None,
            "payment_method_token": None,
            "customer": {
                "id": None,
            },
            "credit_card": {
                "token": None,
            },
            "options": {
                "submit_for_settlement": None,
            },
        },
    }
    tr_boolean_fields = [
        "transaction[options][store_in_vault]",
        "transaction[options][add_billing_address_to_payment_method]",
        "transaction[options][store_shipping_address_in_vault]",
    ]

class CustomerForm(BraintreeForm):
    """
        A form to enter a new customer.
    """
    tr_type = "Customer"
    tr_fields = OrderedDict([
        ("customer", OrderedDict([
            ("first_name", None),
            ("last_name", None),
            ("company", None),
            ("email", None),
            ("phone", None),
            ("fax", None),
            ("website", None),
            ("credit_card", OrderedDict([
                ("cardholder_name", None),
                ("number", None),
                ("expiration_month", None),
                ("expiration_year", None),
                ("cvv", None),
                ("billing_address", OrderedDict([
                    ("first_name", None),
                    ("last_name", None),
                    ("company", None),
                    ("street_address", None),
                    ("extended_address", None),
                    ("locality", None),
                    ("region", None),
                    ("postal_code", None),
                    ("country_name", None)]),
                )]),
            )]),
        ),
    ])
    tr_labels = {
        "customer": {
            "credit_card": {
                "cvv": "CVV",
            },
        },
    }
    tr_protected = {
        "customer": {
            "id": None,
            "credit_card": {
                "token": None,
                "options": {
                    "verify_card": None,
                },
            },
        },
    }

class CreditCardForm(BraintreeForm):
    """
        A form to enter a new credit card.
    """
    tr_type = "CreditCard"
    tr_fields = OrderedDict([
        ("credit_card", OrderedDict([
            ("cardholder_name", None),
            ("number", None),
            ("expiration_month", None),
            ("expiration_year", None),
            ("cvv", None),
            ("billing_address", OrderedDict([
                ("first_name", None),
                ("last_name", None),
                ("company", None),
                ("street_address", None),
                ("extended_address", None),
                ("locality", None),
                ("region", None),
                ("postal_code", None),
                ("country_name", None)]),
            )]),
        ),
    ])
    tr_labels = {
        "credit_card": {
            "cvv": "CVV",
        },
    }
    tr_protected = {
        "credit_card": {
            "customer_id": None,
            "token": None,
            "options": {
                "verify_card": None,
            },
        },
    }


