"""
Test events of MTB Daemon TCP server using PyTest.

moc = module_output_changed
mic = module_input_changed
"""

import time

import common
from mtbdaemonif import mtb_daemon, MtbDaemonIFace


def test_mic_event() -> None:
    with common.ModuleSubscription(mtb_daemon, [common.TEST_MODULE_ADDR]):
        common.set_single_output(common.TEST_MODULE_ADDR, 0, 1)
        ic_event = mtb_daemon.expect_event('module_inputs_changed')
        common.validate_ic_event(ic_event, common.TEST_MODULE_ADDR, 0, True)

        common.set_single_output(common.TEST_MODULE_ADDR, 0, 0)
        ic_event = mtb_daemon.expect_event('module_inputs_changed')
        common.validate_ic_event(ic_event, common.TEST_MODULE_ADDR, 0, False)

    # Test no event received after unsubscribe
    common.set_single_output(common.TEST_MODULE_ADDR, 0, 1)
    time.sleep(0.2)
    common.set_single_output(common.TEST_MODULE_ADDR, 0, 0)
    time.sleep(0.2)
    mtb_daemon.expect_no_message()


def test_moc_event() -> None:
    with MtbDaemonIFace() as second_daemon, \
            common.ModuleSubscription(second_daemon, [common.TEST_MODULE_ADDR]):
        common.set_single_output(common.TEST_MODULE_ADDR, 1, 1)
        ic_event = second_daemon.expect_event('module_outputs_changed')
        common.validate_oc_event(ic_event, common.TEST_MODULE_ADDR, 1, 1)


def test_module_subscribe_inactive() -> None:
    with common.ModuleSubscription(mtb_daemon, [common.INACTIVE_MODULE_ADDR]):
        pass


def test_no_event_other_module() -> None:
    with MtbDaemonIFace() as second_daemon, \
            common.ModuleSubscription(second_daemon, [common.INACTIVE_MODULE_ADDR]):
        common.set_single_output(common.TEST_MODULE_ADDR, 0, 1)
        common.set_single_output(common.TEST_MODULE_ADDR, 0, 0)
        second_daemon.expect_no_message()


def test_my_module_subscribes_get() -> None:
    response = mtb_daemon.request_response({'command': 'my_module_subscribes'})
    assert 'addresses' in response
    assert response['addresses'] == []

    with common.ModuleSubscription(
        mtb_daemon,
        [common.TEST_MODULE_ADDR, common.INACTIVE_MODULE_ADDR]
    ):
        response = mtb_daemon.request_response({'command': 'my_module_subscribes'})
        assert sorted(response['addresses']) == \
            sorted([common.TEST_MODULE_ADDR, common.INACTIVE_MODULE_ADDR])

    response = mtb_daemon.request_response({'command': 'my_module_subscribes'})
    assert response['addresses'] == []


def test_my_module_subscribes_set() -> None:
    response = mtb_daemon.request_response({
        'command': 'my_module_subscribes',
        'addresses': [common.TEST_MODULE_ADDR, common.INACTIVE_MODULE_ADDR],
    })
    assert response['addresses'] == [common.TEST_MODULE_ADDR, common.INACTIVE_MODULE_ADDR]

    response = mtb_daemon.request_response({
        'command': 'my_module_subscribes',
        'addresses': [],
    })
    assert response['addresses'] == []


def test_subscribe_unknown_addrs() -> None:
    with common.ModuleSubscription(mtb_daemon, [25, 85]):
        response = mtb_daemon.request_response({'command': 'my_module_subscribes'})
        assert sorted(response['addresses']) == [25, 85]


def test_my_module_subscribes_set_unknown_addrs() -> None:
    response = mtb_daemon.request_response({
        'command': 'my_module_subscribes',
        'addresses': [67, 12, 76],
    })
    assert sorted(response['addresses']) == [12, 67, 76]

    response = mtb_daemon.request_response({
        'command': 'module_unsubscribe',
        'addresses': [12],
    })
    assert sorted(response['addresses']) == [12]

    response = mtb_daemon.request_response({'command': 'my_module_subscribes'})
    assert sorted(response['addresses']) == [67, 76]

    response = mtb_daemon.request_response({
        'command': 'module_unsubscribe',
        'addresses': [67, 76],
    })
    assert sorted(response['addresses']) == [67, 76]

    response = mtb_daemon.request_response({'command': 'my_module_subscribes'})
    assert response['addresses'] == []


def test_subscribe_bad_addr() -> None:
    response = mtb_daemon.request_response(
        {
            'command': 'my_module_subscribes',
            'addresses': [0xFF1, 0x101],
        },
        ok=False
    )
    common.check_error(response, common.MtbDaemonError.MODULE_INVALID_ADDR)


def test_subscribe_all_addrs() -> None:
    mtb_daemon.request_response({'command': 'module_subscribe'})
    response = mtb_daemon.request_response({'command': 'my_module_subscribes'})
    assert response['addresses'] == [i for i in range(1, 256)]

    mtb_daemon.request_response({'command': 'module_unsubscribe'})
    response = mtb_daemon.request_response({'command': 'my_module_subscribes'})
    assert response['addresses'] == []


###############################################################################
# Topology

def test_topology_endpoints_exist() -> None:
    with common.TopoSubscription(mtb_daemon):
        pass


def test_module_deleted_event_topo_subscribe() -> None:
    with MtbDaemonIFace() as second_daemon, common.TopoSubscription(second_daemon):
        mtb_daemon.request_response(
            {'command': 'module_delete', 'address': common.INACTIVE_MODULE_ADDR}
        )

        event = second_daemon.expect_event('module_deleted')
        assert 'module' in event
        assert event['module'] == common.INACTIVE_MODULE_ADDR

        module_json = common.MODULES_JSON[common.INACTIVE_MODULE_ADDR]
        mtb_daemon.request_response({
            'command': 'module_set_config',
            'address': common.INACTIVE_MODULE_ADDR,
            'type_code': module_json['type'],
            'name': module_json['name'],
            # omitting 'config' - default config used
        })


def test_module_deleted_event_module_subscribe() -> None:
    with MtbDaemonIFace() as second_daemon, \
            common.ModuleSubscription(second_daemon, [common.INACTIVE_MODULE_ADDR]):
        mtb_daemon.request_response(
            {'command': 'module_delete', 'address': common.INACTIVE_MODULE_ADDR}
        )

        event = second_daemon.expect_event('module_deleted')
        assert 'module' in event
        assert event['module'] == common.INACTIVE_MODULE_ADDR

        module_json = common.MODULES_JSON[common.INACTIVE_MODULE_ADDR]
        mtb_daemon.request_response({
            'command': 'module_set_config',
            'address': common.INACTIVE_MODULE_ADDR,
            'type_code': module_json['type'],
            'name': module_json['name'],
            # omitting 'config' - default config used
        })


def test_module_deleted_no_event_when_not_subscribed() -> None:
    with MtbDaemonIFace() as second_daemon:
        mtb_daemon.request_response(
            {'command': 'module_delete', 'address': common.INACTIVE_MODULE_ADDR}
        )

        second_daemon.expect_no_message()

        module_json = common.MODULES_JSON[common.INACTIVE_MODULE_ADDR]
        mtb_daemon.request_response({
            'command': 'module_set_config',
            'address': common.INACTIVE_MODULE_ADDR,
            'type_code': module_json['type'],
            'name': module_json['name'],
            # omitting 'config' - default config used
        })


###############################################################################
# Module changed

def test_module_changed_event_on_name_edit() -> None:
    with MtbDaemonIFace() as second_daemon, \
            common.ModuleSubscription(second_daemon, [common.TEST_MODULE_ADDR]):

        mtb_daemon.request_response({
            'command': 'module_set_config',
            'address': common.TEST_MODULE_ADDR,
            'name': 'dummyname',
        })

        event = second_daemon.expect_event('module')
        assert 'module' in event
        assert event['module']['address'] == common.TEST_MODULE_ADDR

        second_daemon.expect_no_message()

        mtb_daemon.request_response({
            'command': 'module_set_config',
            'address': common.TEST_MODULE_ADDR,
            'name': common.MODULES_JSON[common.TEST_MODULE_ADDR]['name'],
        })

        event = second_daemon.expect_event('module')
        assert 'module' in event
        assert event['module']['address'] == common.TEST_MODULE_ADDR


# TODO: add some test for 'mtbusb' changed?
# How? It requires e.g. disconnecting of power from a test MTB-UNI module
