"""Boot HomePASS in a disposable, real Home Assistant installation.

Run inside the official Home Assistant stable/beta image. No pytest fixtures,
dependency-install bypasses, host devices, credentials, or production config are used.
"""

import asyncio
from importlib.metadata import version
import logging
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from homeassistant import bootstrap, config_entries
from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.runner import RuntimeConfig, create_event_loop

from check_core_requirements import check_core_requirements

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "homepass"


class HomePassCompatibilityWarnings(logging.Handler):
    """Turn Core API deprecation reports into an actionable compatibility failure."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if "custom integration 'homepass'" in message:
            self.messages.append(message)


async def check_startup(config_dir: str) -> None:
    """Exercise the production installer, config flow, setup, panel, and reload."""
    hass = await bootstrap.async_setup_hass(RuntimeConfig(config_dir=config_dir))
    assert hass is not None, "Home Assistant bootstrap failed"
    try:
        assert not hass.config.recovery_mode, "Home Assistant entered recovery mode"
        await hass.async_start()
        flow = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert flow["type"] is FlowResultType.FORM, f"HomePASS config flow failed: {flow}"
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], {"instance_name": "Compatibility test"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY, result
        await hass.async_block_till_done()
        entry = result["result"]
        assert entry.state is ConfigEntryState.LOADED, f"HomePASS startup failed: {entry.state}"
        assert hass.services.has_service(DOMAIN, "ping"), "HomePASS services missing"
        assert DOMAIN in hass.data[frontend.DATA_PANELS], "HomePASS sidebar panel missing"
        await hass.services.async_call(DOMAIN, "ping", blocking=True)
        print("PASS: dependency installation, config flow, startup, panel and ping", flush=True)

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.NOT_LOADED
        assert not hass.services.has_service(DOMAIN, "ping")
        assert DOMAIN not in hass.data[frontend.DATA_PANELS]
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        assert DOMAIN in hass.data[frontend.DATA_PANELS]
        await hass.services.async_call(DOMAIN, "ping", blocking=True)
        print("PASS: unload and reload", flush=True)
    finally:
        await hass.async_stop(force=True)


async def run_check(config_dir: str) -> None:
    """Fail a hung startup rather than leave a misleading successful check."""
    logger = logging.getLogger("homeassistant.helpers.frame")
    compatibility_warnings = HomePassCompatibilityWarnings()
    logger.addHandler(compatibility_warnings)
    try:
        async with asyncio.timeout(300):
            await check_startup(config_dir)
        assert not compatibility_warnings.messages, "\n".join(compatibility_warnings.messages)
        print("PASS: no HomePASS Core API deprecation reports", flush=True)
    finally:
        logger.removeHandler(compatibility_warnings)


def main() -> None:
    """Prepare only synthetic, temporary data and use Core's real event loop."""
    print(
        f"Home Assistant {version('homeassistant')}; cryptography {version('cryptography')}",
        flush=True,
    )
    check_core_requirements(ROOT)
    with TemporaryDirectory(prefix="homepass-compatibility-") as config_dir:
        config = Path(config_dir)
        shutil.copytree(ROOT / "custom_components/homepass", config / "custom_components/homepass")
        (config / "configuration.yaml").write_text(
            "homeassistant:\n"
            "  name: HomePASS compatibility test\n"
            "  latitude: 0\n"
            "  longitude: 0\n"
            "  time_zone: UTC\n"
            "http:\n"
            "  server_host: localhost\n"
            "frontend:\n"
        )
        with asyncio.Runner(loop_factory=create_event_loop) as runner:
            runner.run(run_check(config_dir))


if __name__ == "__main__":
    main()
