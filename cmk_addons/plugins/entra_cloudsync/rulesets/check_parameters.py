
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _execution_parameter_form():
    return Dictionary(
        elements={
            "freshness_intervals": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Execution freshness thresholds"),
                    help_text=Help(
                        "Configure WARN and CRIT as multiples of the synchronization interval "
                        "reported by Microsoft. For a PT20M interval, 2.0 / 3.0 means WARN "
                        "after 40 minutes and CRIT after 60 minutes."
                    ),
                    form_spec_template=Float(
                        unit_symbol="x interval",
                        custom_validate=(NumberInRange(min_value=0.1),),
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((2.0, 3.0)),
                ),
            ),
        },
    )


def _job_parameter_form():
    return Dictionary(
        elements={
            "notrun_grace_intervals": DictElement(
                required=True,
                parameter_form=Float(
                    title=Title("NotRun grace period"),
                    help_text=Help(
                        "Number of synchronization intervals that an active Cloud Sync job may "
                        "remain in NotRun after start/restart before becoming CRIT. During the "
                        "grace period the service is WARN."
                    ),
                    unit_symbol="x interval",
                    prefill=DefaultValue(2.0),
                    custom_validate=(NumberInRange(min_value=0.1),),
                ),
            ),
        },
    )


rule_spec_entra_cloudsync_execution = CheckParameters(
    name="entra_cloudsync_execution",
    title=Title("Microsoft Entra Cloud Sync execution freshness"),
    topic=Topic.GENERAL,
    parameter_form=_execution_parameter_form,
    condition=HostAndItemCondition(item_title=Title("Cloud Sync configuration")),
)


rule_spec_entra_cloudsync_job = CheckParameters(
    name="entra_cloudsync_job",
    title=Title("Microsoft Entra Cloud Sync job state"),
    topic=Topic.GENERAL,
    parameter_form=_job_parameter_form,
    condition=HostAndItemCondition(item_title=Title("Cloud Sync configuration")),
)
