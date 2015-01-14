import time
import sys
import logging
import logging.handlers

from bgmodule import BlueGigaModule, GATTCharacteristic, GATTService, BlueGigaClient, BlueGigaServer
from cmd_def import gap_discoverable_mode, gap_connectable_mode

CLIENT_SERIAL = "COM9"
SERVER_SERIAL = "COM11"

term = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
term.setFormatter(formatter)
api_logger = logging.getLogger("bgapi")
api_logger.addHandler(term)
api_logger.setLevel(level=logging.INFO)

def example_physical_web():
    ble_client = BlueGigaClient(port=CLIENT_SERIAL, timeout=0.1)
    ble_server = BlueGigaServer(port=SERVER_SERIAL, timeout=0.1)

    ble_client.reset_ble_state()
    ble_server.reset_ble_state()

    ble_server.setup_physical_web("http://www.bluegiga.com")
    ble_server.start_advertisement(adv_mode=gap_discoverable_mode['gap_user_data'],
                                   conn_mode=gap_connectable_mode['gap_undirected_connectable'])
    responses = ble_client.scan_all(timeout=3)

def example_ibeacon():
    ble_client = BlueGigaClient(port=CLIENT_SERIAL, timeout=0.1)
    ble_server = BlueGigaServer(port=SERVER_SERIAL, timeout=0.1)

    ble_server.reset_ble_state()
    ble_client.reset_ble_state()

    ble_server.setup_ibeacon(uuid="e2c56db5-dffb-48d2-b060-d0f5a71096e0",
                                 major=0, minor=0)
    ble_server.start_advertisement(adv_mode=gap_discoverable_mode['gap_user_data'],
                                   conn_mode=gap_connectable_mode['gap_undirected_connectable'])
    responses = ble_client.scan_all(timeout=3)

def example_simultaneous_beacons():
    ble_client = BlueGigaClient(port=CLIENT_SERIAL, timeout=0.1)
    ble_server = BlueGigaServer(port=SERVER_SERIAL, timeout=0.1)

    ble_server.reset_ble_state()
    ble_client.reset_ble_state()

    ble_server.setup_ibeacon(uuid="e2c56db5-dffb-48d2-b060-d0f5a71096e0",
                                 major=0, minor=0)
    ble_server.start_advertisement(adv_mode=gap_discoverable_mode['gap_user_data'],
                                   conn_mode=gap_connectable_mode['gap_undirected_connectable'])
    for i in range(30):
        time.sleep(1)
        ble_server.setup_physical_web("http://www.bluegiga.com")
        time.sleep(1)
        ble_server.setup_ibeacon(uuid="e2c56db5-dffb-48d2-b060-d0f5a71096e0",
                                 major=0, minor=0)

def example_client_operations():
    ble_client = BlueGigaClient(port=CLIENT_SERIAL, timeout=0.1)
    ble_server = BlueGigaServer(port=SERVER_SERIAL, timeout=0.1)

    # BLE Device configuration and start advertising
    ble_server.reset_ble_state()
    ble_server.get_module_info()
    ble_server.set_device_capabilities()
    ble_server.delete_bonding()
    ble_server.allow_bonding()
    ble_server.advertise_general()

    # BLE Client configuration and start scanning
    ble_client.get_module_info()
    ble_client.reset_ble_state()
    ble_client.delete_bonding()
    ble_client.allow_bonding()
    responses = ble_client.scan_all(timeout=2)
    for resp in responses:
        if resp.get_sender_address() == ble_server.get_ble_address():
            target = resp
            break
    else:
        raise Exception("No Advertisements received from server %s" % (ble_server.get_ble_address()))
    connection = ble_client.connect(target=target)
    oob_data = "000102030405060708090A0B0C0D0E0F"
    ble_client.set_out_of_band_data(oob_data)
    ble_server.set_out_of_band_data(oob_data)
    connection.request_encryption(bond=True)
    connection.read_by_group_type(type=GATTService.PRIMARY_SERVICE_UUID)
    connection.read_by_group_type(type=GATTService.SECONDARY_SERVICE_UUID)
    for service in connection.get_services():
        connection.find_information(service=service)
        connection.read_by_type(service=service, type=GATTCharacteristic.CHARACTERISTIC_UUID)
        connection.read_by_type(service=service, type=GATTCharacteristic.CLIENT_CHARACTERISTIC_CONFIG)

    notify_indicate = []
    for characteristic in connection.get_characteristics():
        connection.read_by_handle(characteristic.value_handle)
        if characteristic.has_notify() or characteristic.has_indicate():
            connection.characteristic_subscription(characteristic,
                                                   characteristic.has_indicate(),
                                                   characteristic.has_notify() and not characteristic.has_indicate())
            notify_indicate += [characteristic]
        if characteristic.is_writable():
            time.sleep(0.05)
            connection.write_by_handle(characteristic.handle+1, "YoYo")

    time.sleep(0.1) # Wait for subscriptions to be acknowledged
    for characteristic in notify_indicate:
        time.sleep(0.05) # Without this delay the client cannot handle the throughput
        ble_server.write_attribute(characteristic.handle+1, "%d" % time.time())
    time.sleep(0.5) # Wait for notifications to be delivered

    ble_client.disconnect(connection.handle)
    time.sleep(0.5)  # So that we can see the server disconnect event

if __name__ == "__main__":
    example_client_operations()
    #example_ibeacon()
    #example_physical_web()
    #example_simultaneous_beacons()