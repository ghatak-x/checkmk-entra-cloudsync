
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    Password,
    String,
    migrate_to_password,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _formspec():
    return Dictionary(
        title=Title("Microsoft Entra Cloud Sync"),
        help_text=Help(
            "Monitor Microsoft Entra Cloud Sync through Microsoft Graph. "
            "The app registration requires Synchronization.Read.All, "
            "AuditLog.Read.All and Directory.Read.All application permissions "
            "with administrator consent."
        ),
        elements={
            "tenant_id": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Tenant ID"),
                    help_text=Help("Directory (tenant) ID of the Microsoft Entra tenant."),
                ),
            ),
            "client_id": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Client ID"),
                    help_text=Help("Application (client) ID of the monitoring app registration."),
                ),
            ),
            "client_secret": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Client secret"),
                    help_text=Help(
                        "Client secret of the monitoring app registration. "
                        "Using the Checkmk Password Store is recommended."
                    ),
                    migrate=migrate_to_password,
                ),
            ),
            "service_principal_id": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Cloud Sync service principal object ID"),
                    help_text=Help(
                        "Object ID of the Microsoft Entra service principal that represents "
                        "the Cloud Sync configuration. This is an object ID, not the app/client ID."
                    ),
                ),
            ),
            "log_window_minutes": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Provisioning log window"),
                    help_text=Help(
                        "How many minutes of provisioning-log history should be evaluated. "
                        "Historical failures remain visible as metrics, while the service state "
                        "is based on unresolved failures per object."
                    ),
                    unit_symbol="min",
                    prefill=DefaultValue(60),
                    custom_validate=(NumberInRange(min_value=5, max_value=1440),),
                ),
            ),
            "max_pages": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Maximum provisioning-log pages"),
                    help_text=Help(
                        "Safety limit for Microsoft Graph provisioning-log pagination. "
                        "Each page can contain up to 100 events."
                    ),
                    prefill=DefaultValue(10),
                    custom_validate=(NumberInRange(min_value=1, max_value=100),),
                ),
            ),
            "timeout": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("HTTP timeout"),
                    help_text=Help("Timeout for Microsoft identity and Graph HTTPS requests."),
                    unit_symbol="s",
                    prefill=DefaultValue(30),
                    custom_validate=(NumberInRange(min_value=5, max_value=120),),
                ),
            ),
        },
    )


rule_spec_entra_cloudsync = SpecialAgent(
    topic=Topic.GENERAL,
    name="entra_cloudsync",
    title=Title("Microsoft Entra Cloud Sync"),
    help_text=Help(
        "Collect Cloud Sync job health and object-level provisioning activity through Microsoft Graph."
    ),
    parameter_form=_formspec,
)
