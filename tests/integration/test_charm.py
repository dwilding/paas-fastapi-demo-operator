# Copyright 2026 david.wilding@canonical.com
# See LICENSE file for licensing details.
#
# The integration tests use the Jubilant library and the pytest-jubilant plugin.
# See https://documentation.ubuntu.com/ops/latest/howto/write-integration-tests-for-a-charm/
#
# pytest-jubilant provides a module-scoped `juju` fixture that creates a temporary Juju model.
# The `charm` fixture is defined in conftest.py.

import json
import logging
import pathlib
import urllib.request

import jubilant
import pytest
import yaml

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(pathlib.Path("charmcraft.yaml").read_text())
APP_NAME = METADATA["name"]
OCI_NAME = APP_NAME


@pytest.mark.juju_setup
def test_deploy(charm: pathlib.Path, juju: jubilant.Juju):
    """Deploy the charm under test."""
    resources = {"app-image": f"localhost:32000/{OCI_NAME}:latest"}
    juju.deploy(charm, app=APP_NAME, resources=resources)
    juju.wait(jubilant.all_blocked)


@pytest.mark.juju_setup
def test_database_integration(charm: pathlib.Path, juju: jubilant.Juju):
    """Check that the charm integrates with the database."""
    juju.deploy("postgresql-k8s", channel="14/stable", trust=True)
    juju.integrate(APP_NAME, "postgresql-k8s")
    juju.wait(jubilant.all_active)


def test_workload(charm: pathlib.Path, juju: jubilant.Juju):
    """Check that the workload functions correctly after integration."""
    unit_ip = juju.status().apps[APP_NAME].units[f"{APP_NAME}/0"].address
    api_base = f"http://{unit_ip}:8000"
    response = urllib.request.urlopen(f"{api_base}/names")
    assert json.loads(response.read()) == {"names": {}}
    urllib.request.urlopen(
        urllib.request.Request(
            f"{api_base}/addname/",
            data=b"name=elephant",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
    )
    response = urllib.request.urlopen(f"{api_base}/names")
    assert json.loads(response.read()) == {"names": {"1": "elephant"}}
