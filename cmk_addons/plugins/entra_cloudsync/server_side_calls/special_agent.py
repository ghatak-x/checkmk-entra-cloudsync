
from cmk.server_side_calls.v1 import (
    SpecialAgentCommand,
    SpecialAgentConfig,
    noop_parser,
)


def _agent_arguments(params, _host_config):
    yield SpecialAgentCommand(
        command_arguments=[
            "--tenant-id",
            str(params["tenant_id"]),
            "--client-id",
            str(params["client_id"]),
            "--client-secret-id",
            params["client_secret"],
            "--service-principal-id",
            str(params["service_principal_id"]),
            "--log-window-minutes",
            str(params.get("log_window_minutes", 60)),
            "--max-pages",
            str(params.get("max_pages", 10)),
            "--timeout",
            str(params.get("timeout", 30)),
        ]
    )


special_agent_entra_cloudsync = SpecialAgentConfig(
    name="entra_cloudsync",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
