import logging
from copy import deepcopy
from uuid import uuid4

import pandas as pd
import pytest
import responses
from responses.matchers import header_matcher, json_params_matcher, query_param_matcher

from dataverse.dataverse import DataverseClient
from dataverse.entity import DataverseEntity
from dataverse.errors import DataverseError
from dataverse.metadata.base import BASE_TYPE


@pytest.fixture
def entity_name() -> str:
    return "foo"


@pytest.fixture
def entity_set_name() -> str:
    return "foos"


@pytest.fixture
def primary_id() -> str:
    return "fooid"


@pytest.fixture
def primary_img() -> str:
    return "fooimg"


@pytest.fixture
def altkey_1(primary_id: str) -> tuple[str, list[str]]:
    return "foo_key", [primary_id]


@pytest.fixture
def altkey_2(primary_id: str, primary_img: str) -> tuple[str, list[str]]:
    return "foo_key2", [primary_id, primary_img]


@pytest.fixture
def sample_data():
    return {"value": [{"data": 1}, {"data": 2}]}


@pytest.fixture
def small_data_package():
    return [{"test": str(uuid4())} for _ in range(5)]


@pytest.fixture
def medium_data_package():
    return [{"test": str(uuid4())} for _ in range(100)]


@pytest.fixture
def large_data_package():
    return [{"test": str(uuid4())} for _ in range(2000)]


@pytest.fixture
def entity(
    client: DataverseClient,
    mocked_responses: responses.RequestsMock,
    entity_name: str,
    entity_set_name: str,
    primary_id: str,
    primary_img: str,
    altkey_1: tuple[str, list[str]],
    altkey_2: tuple[str, list[str]],
):
    # Initial call
    columns = ["EntitySetName", "PrimaryIdAttribute", "PrimaryImageAttribute"]
    mocked_responses.get(
        url=client._endpoint + f"EntityDefinitions(LogicalName='{entity_name}')",
        status=200,
        match=[query_param_matcher({"$select": ",".join(columns)})],
        json={"EntitySetName": entity_set_name, "PrimaryIdAttribute": primary_id, "PrimaryImageAttribute": primary_img},
    )

    # Keys call
    columns = ["SchemaName", "KeyAttributes"]
    mocked_responses.get(
        url=client._endpoint + f"EntityDefinitions(LogicalName='{entity_name}')/Keys",
        status=200,
        match=[query_param_matcher({"$select": ",".join(columns)})],
        json={
            "value": [
                {"SchemaName": altkey_1[0], "KeyAttributes": altkey_1[1]},
                {"SchemaName": altkey_2[0], "KeyAttributes": altkey_2[1]},
            ]
        },
    )

    # Action SDK Messages call

    mocked_responses.get(
        url=client._endpoint + "sdkmessagefilters",
        match=[
            query_param_matcher(
                {
                    "$select": "sdkmessagefilterid",
                    "$expand": "sdkmessageid($select=name)",
                    "$filter": (
                        "(sdkmessageid/name eq 'CreateMultiple' or "
                        + "sdkmessageid/name eq 'UpdateMultiple') and "
                        + f"primaryobjecttypecode eq '{entity_name}'"
                    ),
                }
            )
        ],
        json={
            "value": [
                {"sdkmessageid": {"name": "CreateMultiple"}},
                {"sdkmessageid": {"name": "UpdateMultiple"}},
            ]
        },
    )

    return client.entity(entity_name)


def test_entity_instantiation(
    entity: DataverseEntity,
    entity_name: str,
    entity_set_name: str,
    primary_id: str,
    primary_img: str,
    altkey_1: tuple[str, list[str]],
    altkey_2: tuple[str, list[str]],
):
    assert entity.logical_name == entity_name
    assert entity.entity_set_name == entity_set_name
    assert entity.primary_id_attr == primary_id
    assert entity.primary_img_attr == primary_img
    assert len(entity.alternate_keys) == 2
    assert all(i in entity.alternate_keys for i in [altkey_1[0], altkey_2[0]])
    assert entity.alternate_keys[altkey_1[0]] == altkey_1[1]
    assert entity.alternate_keys[altkey_2[0]] == altkey_2[1]
    assert entity.supports_create_multiple is True
    assert entity.supports_update_multiple is True


"""
entity.read()
"""


def test_entity_read(
    entity: DataverseEntity,
    entity_set_name: str,
    mocked_responses: responses.RequestsMock,
    sample_data: dict[str, list[dict[str, int]]],
):
    # Reading without any args
    url = entity._endpoint + entity_set_name
    mocked_responses.get(url=url, json=sample_data)
    resp = entity.read()
    assert resp == sample_data["value"]


def test_entity_read_with_args(
    entity: DataverseEntity,
    mocked_responses: responses.RequestsMock,
    sample_data: dict[str, list[dict[str, int]]],
):
    # Reading with args
    url = entity._endpoint + entity.entity_set_name
    select = "moo"
    filter = "foo"
    expand = "schmoo"
    order_by = "blergh"
    top = 123
    params = {"$select": select, "$filter": filter, "$expand": expand, "$orderby": order_by, "$top": top}

    page_size = 69
    headers = {"Prefer": f"odata.maxpagesize={page_size}"}

    mocked_responses.get(url=url, json=sample_data, match=[query_param_matcher(params), header_matcher(headers)])

    resp = entity.read(select=[select], filter=filter, top=top, order_by=order_by, expand=expand, page_size=page_size)
    assert resp == sample_data["value"]


def test_entity_read_with_paging(
    entity: DataverseEntity,
    mocked_responses: responses.RequestsMock,
    sample_data: dict[str, list[dict[str, int]]],
):
    url = entity._endpoint + entity.entity_set_name
    next_url = entity._endpoint + "foooooo"

    # Mocking responses
    mocked_responses.get(url=next_url, json=sample_data)
    sample_data["@odata.nextLink"] = next_url
    mocked_responses.get(url=url, json=sample_data)

    # Performing action
    resp = entity.read()

    assert len(resp) == 2 * len(sample_data["value"])
    assert resp == sample_data["value"] * 2


"""
entity.create()
"""


def test_entity_create_by_singles(
    entity: DataverseEntity,
    mocked_responses: responses.RequestsMock,
    small_data_package: list[dict[str, str]],
    caplog: pytest.LogCaptureFixture,
):
    # Data package
    url = entity._endpoint + entity.entity_set_name

    # Mock single requests
    for row in small_data_package:
        mocked_responses.post(url=url, match=[json_params_matcher(row)], status=204)

    caplog.set_level(logging.DEBUG)
    resp = entity.create(data=small_data_package)

    assert all([x.status_code == 204 for x in resp])
    assert "Using single inserts" in caplog.text


def test_entity_create_by_createmultiple(
    entity: DataverseEntity,
    mocked_responses: responses.RequestsMock,
    medium_data_package: list[dict[str, str]],
    caplog: pytest.LogCaptureFixture,
):
    # Data package
    out_data = deepcopy(medium_data_package)
    for row in out_data:
        row["@odata.type"] = BASE_TYPE + entity.logical_name
    match_data = {"Targets": out_data}
    url = f"{entity._endpoint}{entity.entity_set_name}/{BASE_TYPE + 'CreateMultiple'}"
    # Mock request
    mocked_responses.post(url=url, match=[json_params_matcher(match_data)], status=204)

    caplog.set_level(logging.DEBUG)
    resp = entity.create(medium_data_package)

    assert all([x.status_code == 204 for x in resp])
    assert "Using CreateMultiple" in caplog.text


def test_entity_create_by_batch(
    entity: DataverseEntity,
    mocked_responses: responses.RequestsMock,
    medium_data_package: list[dict[str, str]],
    caplog: pytest.LogCaptureFixture,
):
    # Setup
    entity._DataverseEntity__supports_create_multiple = False  # Ugh!

    # Data package
    url = f"{entity._endpoint}$batch"

    # Mock request
    mocked_responses.post(url=url, status=204)

    caplog.set_level(logging.DEBUG)
    resp = entity.create(medium_data_package)

    assert all([x.status_code == 204 for x in resp])
    assert "CreateMultiple not supported. Inserting batch." in caplog.text


def test_entity_create_with_args(
    entity: DataverseEntity,
    mocked_responses: responses.RequestsMock,
    small_data_package: list[dict[str, str]],
):
    # Data package
    url = entity._endpoint + entity.entity_set_name
    header = {"MSCRM.SuppressDuplicateDetection": "false", "Prefer": "return=representation"}

    # Mock single requests
    for _ in small_data_package:
        mocked_responses.post(url=url, match=[header_matcher(header)], status=200)

    resp = entity.create(data=small_data_package, detect_duplicates=True, return_created=True)
    assert all([x.status_code == 200 for x in resp])


def test_entity_create_with_df(
    entity: DataverseEntity,
    mocked_responses: responses.RequestsMock,
):
    data = pd.DataFrame([("abc"), ("def")], columns=["test"])
    dict_data = data.to_dict(orient="records")

    url = entity._endpoint + entity.entity_set_name

    for row in dict_data:
        mocked_responses.post(url=url, status=204, match=[json_params_matcher(row)])

    resp = entity.create(data=data)

    assert all([x.status_code == 204 for x in resp])


"""
entity.delete()
"""


def test_entity_delete_singles_all(entity: DataverseEntity, mocked_responses: responses.RequestsMock):
    # Setup
    id = entity.primary_id_attr
    return_payload = [{id: str(i)} for i in range(5)]
    params = {"$select": entity.primary_id_attr}

    # Fetching ids
    mocked_responses.get(
        url=f"{entity._endpoint}{entity.entity_set_name}",
        status=200,
        json={"value": return_payload},
        match=[query_param_matcher(params)],
    )

    # Deleting ids
    for row in return_payload:
        mocked_responses.delete(url=f"{entity._endpoint}{entity.entity_set_name}({row[id]})", status=204)

    resp = entity.delete(filter="all")

    assert all([x.status_code == 204 for x in resp])


def test_entity_delete_batch_all(entity: DataverseEntity, mocked_responses: responses.RequestsMock):
    # Setup
    id = entity.primary_id_attr
    return_payload = [{id: str(i)} for i in range(10)]
    params = {"$select": entity.primary_id_attr}

    # Fetching ids
    mocked_responses.get(
        url=f"{entity._endpoint}{entity.entity_set_name}",
        status=200,
        json={"value": return_payload},
        match=[query_param_matcher(params)],
    )

    # Deleting
    mocked_responses.post(url=f"{entity._endpoint}$batch")

    resp = entity.delete(filter="all")

    for item in return_payload:
        assert f"{entity._endpoint}{entity.entity_set_name}({item[id]})" in resp[0].request.body


def test_entity_delete_singles_ids(entity: DataverseEntity, mocked_responses: responses.RequestsMock):
    # Setup
    delete_ids = {"1", "2", "3"}

    # Deleting ids
    for item in delete_ids:
        mocked_responses.delete(
            url=f"{entity._endpoint}{entity.entity_set_name}({item})",
            status=204,
        )

    resp = entity.delete(ids=delete_ids)

    assert all([x.status_code == 204 for x in resp])


def test_entity_delete_singles_filter(entity: DataverseEntity, mocked_responses: responses.RequestsMock):
    # Setup
    id = entity.primary_id_attr
    filter_str = "foo"
    params = {"$filter": filter_str, "$select": entity.primary_id_attr}
    return_payload = [{id: str(i)} for i in range(5)]

    # Fetching ids
    mocked_responses.get(
        url=f"{entity._endpoint}{entity.entity_set_name}",
        status=200,
        json={"value": return_payload},
        match=[query_param_matcher(params)],
    )

    # Deleting ids
    for row in return_payload:
        mocked_responses.delete(url=f"{entity._endpoint}{entity.entity_set_name}({row[id]})", status=204)

    resp = entity.delete(filter=filter_str)

    assert all([x.status_code == 204 for x in resp])


def test_entity_delete_bad_args(entity: DataverseEntity):
    with pytest.raises(DataverseError, match=r"Function requires either.*"):
        entity.delete()


"""
entity.delete_column()
"""


def test_entity_delete_column_singles_all(entity: DataverseEntity, mocked_responses: responses.RequestsMock):
    # Setup
    id = entity.primary_id_attr
    return_payload = [{id: str(i)} for i in range(3)]
    params = {"$select": entity.primary_id_attr}
    columns = ["Foo", "Bar"]

    # Fetching ids
    mocked_responses.get(
        url=f"{entity._endpoint}{entity.entity_set_name}",
        status=200,
        json={"value": return_payload},
        match=[query_param_matcher(params)],
    )

    # Deleting ids
    for row in return_payload:
        for col in columns:
            mocked_responses.delete(url=f"{entity._endpoint}{entity.entity_set_name}({row[id]})/{col}", status=204)

    resp = entity.delete_columns(columns=columns, filter="all")

    assert all([x.status_code == 204 for x in resp])


def test_entity_delete_column_batch_all(entity: DataverseEntity, mocked_responses: responses.RequestsMock):
    # Setup
    id = entity.primary_id_attr
    return_payload = [{id: str(i)} for i in range(10)]
    params = {"$select": entity.primary_id_attr}
    columns = ["Foo", "Bar"]

    # Fetching ids
    mocked_responses.get(
        url=f"{entity._endpoint}{entity.entity_set_name}",
        status=200,
        json={"value": return_payload},
        match=[query_param_matcher(params)],
    )

    # Deleting
    mocked_responses.post(url=f"{entity._endpoint}$batch")

    resp = entity.delete_columns(columns=columns, filter="all")

    for item in return_payload:
        for i, col in enumerate(columns):
            assert f"{entity._endpoint}{entity.entity_set_name}({item[id]})/{col}" in resp[i].request.body


def test_entity_delete_column_singles_ids(entity: DataverseEntity, mocked_responses: responses.RequestsMock):
    # Setup
    delete_ids = {"1", "2", "3"}
    columns = ["Foo", "Bar"]

    # Deleting ids
    for col in columns:
        for item in delete_ids:
            mocked_responses.delete(
                url=f"{entity._endpoint}{entity.entity_set_name}({item})/{col}",
                status=204,
            )

    resp = entity.delete_columns(columns=columns, ids=delete_ids)

    assert all([x.status_code == 204 for x in resp])


def test_entity_delete_column_singles_filter(entity: DataverseEntity, mocked_responses: responses.RequestsMock):
    # Setup
    id = entity.primary_id_attr
    filter_str = "foo"
    params = {"$filter": filter_str, "$select": entity.primary_id_attr}
    return_payload = [{id: str(i)} for i in range(3)]
    columns = ["Foooo", "Baaar"]

    # Fetching ids
    mocked_responses.get(
        url=f"{entity._endpoint}{entity.entity_set_name}",
        status=200,
        json={"value": return_payload},
        match=[query_param_matcher(params)],
    )

    # Deleting ids
    for row in return_payload:
        for col in columns:
            mocked_responses.delete(url=f"{entity._endpoint}{entity.entity_set_name}({row[id]})/{col}", status=204)

    resp = entity.delete_columns(columns=columns, filter=filter_str)

    assert all([x.status_code == 204 for x in resp])


def test_entity_delete_column_bad_args(entity: DataverseEntity):
    with pytest.raises(DataverseError, match=r"Function requires either.*"):
        entity.delete_columns(columns=["Foo", "Bar"])
