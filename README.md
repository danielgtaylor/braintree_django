Info
====

This module provides an easy to use interface to Braintree using Django's built-in form system to allow Django developers to easily make use of the Braintree transparent redirect functionality to help with PCI DSS compliance issues.

The django_braintree module supports all documented fields in the official transparent redirect documentation. You can selectively turn on/off fields as required by your use scenario (for example, hiding the shipping address in the transaction form).

This module depends on the Braintree Python module, so please install it first.

Braintree API Documentation
---------------------------

 * [Transparent redirect][1]
 * [Python module][2]
 * [Python module API documentation][3]

[1]: http://www.braintreepaymentsolutions.com/gateway/transparent-redirect
[2]: http://www.braintreepaymentsolutions.com/gateway/python
[3]: http://www.braintreepaymentsolutions.com/gateway/python/docs/index.html

Example 1: Simple
-----------------
Download and install the django_braintree module, then create a form in one of your views. Start by installing the module in settings.py:

    import braintree

    INSTALLED_APPS = [
        ...
        "django_braintree",
        ...
    ]

    # Braintree sandbox settings
    BRAINTREE_ENV = braintree.Environment.Sandbox
    BRAINTREE_MERCHANT = 'your_merchant_key'
    BRAINTREE_PUBLIC_KEY = 'your_public_key'
    BRAINTREE_PRIVATE_KEY = 'your_private_key'

    # If you cannot install M2Crypto (e.g. AppEngine):
    BRAINTREE_UNSAFE_SSL = True

Next, create a view to use one of the transparent redirect forms:

    from django_braintree.forms import TransactionForm

    def myview(request):
        result = TransactionForm.get_result(request)

        # If successful redirect to a thank you page
        if result and result.is_success:
            return HttpResponseRedirect("/thanks")

        # Create the form. You MUST pass in the result to get error messages!
        myform = TransactionForm(result, redirect_url="http://mysite.com/myview")

        # Remove items we don't need
        myform.remove_section("transaction[shipping_address]")
        myform.remove_section("transaction[amount]")
        myform.remove_section("transaction[options]")

        # Set fields we want passed along
        myform.tr_fields["transaction"]["amount"] = "19.99"

        # Generate the tr_data signed field; this MUST be called!
        myform.generate_tr_data()

        return render("template.html", {
            "form": myform,
        })

Then, in your template rendering the form is easy:

    <form action="{{ form.action }}" method="POST">
        {{ form.as_table }}
        <button type="submit">Submit order</button>
    </form>

Example 2: Custom Form
----------------------

Creating a custom form like the one below provides an alternative to:

    myform.remove_section("transaction[amount]")
    myform.tr_fields["transaction"]["amount"] = "19.99"

Follow steps shown in Example 1 above. In your Django application, create a
forms.py module, and add the following to it:

    from django_braintree.forms import BraintreeForm
    from django_braintree.odict import OrderedDict

    class ProtectedAmountForm(BraintreeForm):

        tr_type = "Transaction"
        tr_fields = OrderedDict([
            ("transaction", OrderedDict([
                ("customer", OrderedDict([
                    ("first_name", None),
                    ("last_name", None),
                    ("email", None),
                    ("phone", None),]),
                ),
                ("credit_card", OrderedDict([
                    ("cardholder_name", None),
                    ("number", None),
                    ("expiration_month", None),
                    ("expiration_year", None),
                    ("cvv", None)]),
                ),
                ("billing", OrderedDict([
                    ("postal_code", None),
                    ("country_name", None)]),
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
            },
        }
        tr_protected = {
            "transaction": {
                "amount": None,
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
                    "store_in_vault": True
                },
            },
        }

        def __init__(self, amount, result=None, redirect_url=None, *args, **kwargs):
            self.tr_protected["transaction"]["amount"] = amount
            super(ProtectedAmountForm, self).__init__(result, redirect_url=redirect_url, *args, **kwargs)

License
-------
Django Braintree uses the MIT license. Please see the LICENSE file for full details.
