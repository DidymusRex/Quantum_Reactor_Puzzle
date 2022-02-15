"""
basic_ble.py
ref. https://github.com/2black0/MicroPython-ESP32-BLE/blob/main/main.py
"""
from machine import Pin, Timer
from time import sleep_ms
import ubluetooth
from micropython import const

class BLE():
    def __init__(self, name):
        self.name = name

        self.led = Pin(2, Pin.OUT)
        self.led_timer = Timer(0)

        # Event type IDs
        self.IRQ_CENTRAL_CONNECT                = const(1)
        self.IRQ_CENTRAL_DISCONNECT             = const(2)
        self.IRQ_GATTS_WRITE                    = const(3)
        self.IRQ_GATTS_READ_REQUEST             = const(4)
        self.IRQ_SCAN_RESULT                    = const(5)
        self.IRQ_SCAN_DONE                      = const(6)
        self.IRQ_PERIPHERAL_CONNECT             = const(7)
        self.IRQ_PERIPHERAL_DISCONNECT          = const(8)
        self.IRQ_GATTC_SERVICE_RESULT           = const(9)
        self.IRQ_GATTC_SERVICE_DONE             = const(10)
        self.IRQ_GATTC_CHARACTERISTIC_RESULT    = const(11)
        self.IRQ_GATTC_CHARACTERISTIC_DONE      = const(12)
        self.IRQ_GATTC_DESCRIPTOR_RESULT        = const(13)
        self.IRQ_GATTC_DESCRIPTOR_DONE          = const(14)
        self.IRQ_GATTC_READ_RESULT              = const(15)
        self.IRQ_GATTC_READ_DONE                = const(16)
        self.IRQ_GATTC_WRITE_DONE               = const(17)
        self.IRQ_GATTC_NOTIFY                   = const(18)
        self.IRQ_CONNECTION_UPDATE              = const(27)

        # Event type names
        self.event_type = {
            self.IRQ_CENTRAL_CONNECT:           'Central Connect',
            self.IRQ_CENTRAL_DISCONNECT:        'Central Disconnect',
            self.IRQ_GATTS_WRITE:               'S Write',
            self.IRQ_GATTS_READ_REQUEST:        'S Read request',
            self.IRQ_SCAN_RESULT:               'Scan result',
            self.IRQ_SCAN_DONE:                 'Scan done',
            self.IRQ_PERIPHERAL_CONNECT:        'Periph connect',
            self.IRQ_PERIPHERAL_DISCONNECT:     'Periph disconnect',
            self.IRQ_GATTC_SERVICE_RESULT:      'C Service result',
            self.IRQ_GATTC_SERVICE_DONE:        'C Service done',
            self.IRQ_GATTC_CHARACTERISTIC_RESULT:   'C Characteristic result',
            self.IRQ_GATTC_CHARACTERISTIC_DONE :    'C Characteristic done',
            self.IRQ_GATTC_DESCRIPTOR_RESULT:   'C Descriptor result',
            self.IRQ_GATTC_DESCRIPTOR_DONE:     'C Descriptor done',
            self.IRQ_GATTC_READ_RESULT:         'C Read result',
            self.IRQ_GATTC_READ_DONE:           'C Read done',
            self.IRQ_GATTC_WRITE_DONE :         'C Write done',
            self.IRQ_GATTC_NOTIFY:              'C Notify',
            self.IRQ_CONNECTION_UPDATE:         'C Connection update'
        }

        # Event information
        self.event_flag = False
        self.event_id = 0
        self.event_data = ''
        self.event_msg = 'foo'
        self.ble_role = 'Initialized'

        # BLE object
        self.ble = ubluetooth.BLE()
        self.ble.irq(self.ble_irq)
        self.ble.active(True)

        # Scan info
        self.scanning = False
        self.scan_result = ()
        self.scan_count = 0
        self.scan_indicator = ('|', '/', '-', '\\')

        # Connection info
        self.connect_status = False
        self.conn_info = {}

        # Get ready to rumble
        self.disconnected()
        self.register()
        self.advertiser()

    def connected(self):
        self.connect_status = True
        # turn off onboard led when connected
        self.led_timer.deinit()
        self.led(0)

    def disconnected(self):
        self.connect_status = False
        # Blink onboard led when disconnected
        self.led_timer.init(period=200, 
                         mode=Timer.PERIODIC, 
                         callback=lambda t: self.led(not self.led.value())
                        )

    def register(self):
        self.ble_role = 'Server'
        # Nordic UART service UUIDs
        SVC_UUID = ubluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
        TX_UUID  = ubluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E')
        RX_UUID  = ubluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E')
        
        TX_CHAR = (TX_UUID, ubluetooth.FLAG_NOTIFY)  # A characteristic
        RX_CHAR = (RX_UUID, ubluetooth.FLAG_WRITE)   # A characteristic
        BLINK_SVC = (SVC_UUID, (TX_CHAR, RX_CHAR))   # A service with two characteristics
        SERVICES = (BLINK_SVC, )                     # All services to be advertised
        
        ((self.tx, self.rx,), ) = self.ble.gatts_register_services(SERVICES)

    def send(self, data):
        self.ble_role = 'Server'
        self.ble.gatts_notify(0, self.tx, data + '\n')

    def advertiser(self):
        self.ble_role = 'Broadcaster'
        name = bytes(self.name, 'UTF-8')
        adv_data = bytearray('\x02\x01\x02') + bytearray((len(name) + 1, 0x09)) + name
        self.ble.gap_advertise(interval_us=100, adv_data=adv_data)

    def scan(self):
        self.ble_role = 'Observer'
        # duration_ms, interval_us=1280000, window_us=11250, active=False
        # 0 = constant scan
        self.scan_count = 0
        self.ble.gap_scan(0, 1000000, 500000, True)
        self.scanning = True

    def stop_scan(self):
        self.ble_role = 'Observer'
        self.ble.gap_scan(None, 0, 0, False)
        self.scanning = False
                
    def connect(self, addr_type, addr):
        self.ble_role = 'Central'
        # BLE.gap_connect(addr_type, addr, scan_duration_ms=2000, min_conn_interval_us=None, max_conn_interval_us=None)
        self.ble.gap_connect(addr_type, addr, 5000)
        self.stop_scan()

    def disconnect(self, conn_handle):
        self.ble_role = 'Central Peripheral'
        self.ble.gap_disconnect(conn_handle)

    def cancel_connect(self):
        self.ble_role = 'Central Peripheral'
        self.ble.gap_connect(None)

    def discover_service(self, conn_handle, uuid):
        self.ble_role = 'Client'
        self.ble.gattc_discover_services(conn_handle, uuid)

    def discover_characteristic(self, conn_handle, uuid):
        self.ble_role  = 'Client'
        self.ble.gattc_discover_characteristics(conn_handle, 1, 0xffff, uuid)
    
    def discover_descriptor(self, conn_handle):
        self.ble_role = 'Client'
        self.ble.gattc_discover_descriptors(conn_handle, 1, 0xffff)
    
    def write(self, handle, vhandle, message):
        self.ble_role = 'Client'
        print('Write {} to handle {} vhandle {}'.format(message, str(handle), str(vhandle)))
        self.ble.gattc_write(handle, vhandle, message, 1)

    def ble_irq(self, event, data):
        global ble_message

        self.event_flag = True
        self.event_id   = event
        self.event_data = data

        if event == self.IRQ_CENTRAL_CONNECT:
            # A central has connected to this peripheral.
            conn_handle, addr_type, addr            = data
            self.conn_info['conn_handle']           = conn_handle
            self.conn_info['addr_type']             = addr_type
            self.conn_info['addr']                  = bytearray(addr)
            self.connected()

        elif event == self.IRQ_CENTRAL_DISCONNECT:
            # A central has disconnected from this peripheral.
            conn_handle, addr_type, addr            = data
            self.conn_info['conn_handle']           = conn_handle
            self.conn_info['addr_type']             = addr_type
            self.conn_info['addr']                  = bytearray(addr)

            self.advertiser()
            self.disconnected()

        elif event == self.IRQ_PERIPHERAL_CONNECT:
            # A successful gap_connect().
            conn_handle, addr_type, addr = data
            self.conn_info['conn_handle']           = conn_handle
            self.conn_info['addr_type']             = addr_type
            self.conn_info['addr']                  = bytearray(addr)

            self.connected()

        elif event == self.IRQ_PERIPHERAL_DISCONNECT:
            # Connected peripheral has disconnected.
            conn_handle, addr_type, addr = data
            self.conn_info['conn_handle']           = conn_handle
            self.conn_info['addr_type']             = addr_type
            self.conn_info['addr']                  = bytearray(addr)

            self.disconnected()

        elif event == self.IRQ_GATTS_WRITE:
            # A client has written to this characteristic or descriptor.
            conn_handle, attr_handle                = data
            self.conn_info['char_handle']           = conn_handle
            self.conn_info['desc_handle']           = conn_handle
            self.conn_info['attr_handle']           = attr_handle

            buf = self.ble.gatts_read(self.rx)
            self.event_msg = buf.decode('UTF-8').strip()
            print('received[' + self.event_msg + ']')

        elif event == self.IRQ_SCAN_RESULT:
            # A single scan result. Memoryview addr and adv_data converted to bytearray
            addr_type, addr, adv_type, rssi, adv_data = data
            self.scan_result = (addr_type, 
                                bytearray(addr), 
                                adv_type, 
                                rssi, 
                                bytearray(adv_data))

        elif event == self.IRQ_SCAN_DONE:
            # Scan duration finished or manually stopped.
            self.scanning = False
            self.scan_count = 0

        elif event == self.IRQ_PERIPHERAL_CONNECT:
            # A successful gap_connect().
            conn_handle, addr_type, addr            = data
            self.conn_info['peri_conn_handle']      = conn_handle
            self.conn_info['peri_addr_type']        = addr_type
            self.conn_info['peri_addr']             = bytearray(addr)

            self.connected()

        elif event == self.IRQ_PERIPHERAL_DISCONNECT:
            # Connected peripheral has disconnected.
            conn_handle, addr_type, addr            = data
            self.conn_info['peri_conn_handle']      = conn_handle
            self.conn_info['peri_addr_type']        = addr_type
            self.conn_info['peri_addr']             = bytearray(addr)

            self.disconnected()

        elif event == self.IRQ_GATTC_NOTIFY:
            # A server has sent a notify request.
            conn_handle, value_handle, notify_data  = data
            self.conn_info['notify_conn_handle']    = conn_handle
            self.conn_info['notify_value_handle']   = value_handle
            self.conn_info['notify_data']           = bytearray(notify_data)

        elif event == self.IRQ_GATTC_SERVICE_RESULT:
            # Called for each service found by gattc_discover_services().
            conn_handle, start_handle, end_handle, uuid = data
            self.conn_info['serv_conn_handle']      = conn_handle
            self.conn_info['serv_beg_handle']       = start_handle
            self.conn_info['serv_end_handle']       = end_handle
            self.conn_info['serv_uuid']             = ubluetooth.UUID(uuid)

        elif event == self.IRQ_GATTC_SERVICE_DONE:
            # Called once service discovery is complete.
            # Note: Status will be zero on success, implementation-specific value otherwise.
            conn_handle, status                     = data
            self.conn_info['serv_conn_handle']      = conn_handle
            self.conn_info['serv_status']           = status

        elif event == self.IRQ_GATTC_CHARACTERISTIC_RESULT:
            # Called for each characteristic found by gattc_discover_services().
            conn_handle, def_handle, value_handle, properties, uuid = data
            self.conn_info['char_conn_handle']      = conn_handle
            self.conn_info['char_def_handle']       = def_handle
            self.conn_info['char_value_handle']     = value_handle
            self.conn_info['char_properties']       = properties
            self.conn_info['char_uuid']             = ubluetooth.UUID(uuid)

        elif event == self.IRQ_GATTC_CHARACTERISTIC_DONE:
            # Called once service discovery is complete.
            # Note: Status will be zero on success, implementation-specific value otherwise.
            conn_handle, status = data
            self.conn_info['char_conn_handle']      = conn_handle
            self.conn_info['char_status']           = status

        elif event == self.IRQ_GATTC_DESCRIPTOR_RESULT:
            # Called for each descriptor found by gattc_discover_descriptors().
            conn_handle, dsc_handle, uuid           = data
            self.conn_info['desc_conn_handle']      = conn_handle
            self.conn_info['desc_dsc_handle']       = dsc_handle
            self.conn_info['desc_uuid']             = ubluetooth.UUID(uuid)

        elif event == self.IRQ_GATTC_DESCRIPTOR_DONE:
            # Called once service discovery is complete.
            # Note: Status will be zero on success, implementation-specific value otherwise.
            conn_handle, status                     = data
            self.conn_info['desc_conn_handle']      = conn_handle
            self.conn_info['desc_status']           = status

        elif event == self.IRQ_GATTC_READ_RESULT:
            # A gattc_read() has completed.
            conn_handle, value_handle, char_data    = data
            self.conn_info['read_conn_handle']      = conn_handle
            self.conn_info['read_value_handle']     = value_handle
            self.conn_info['data']                  = bytes(char_data)

        elif event == self.IRQ_GATTC_READ_DONE:
            # A gattc_read() has completed.
            # Note: The value_handle will be zero on btstack (but present on NimBLE).
            # Note: Status will be zero on success, implementation-specific value otherwise.
            conn_handle, value_handle, status       = data
            self.conn_info['read_conn_handle']      = conn_handle
            self.conn_info['read_value_handle']     = value_handle
            self.conn_info['read_status']           = status

        elif event == self.IRQ_GATTC_WRITE_DONE:
            # A gattc_write() has completed.
            # Note: The value_handle will be zero on btstack (but present on NimBLE).
            # Note: Status will be zero on success, implementation-specific value otherwise.
            conn_handle, value_handle, status       = data
            self.conn_info['write_conn_handle']     = conn_handle
            self.conn_info['write_value_handle']    = value_handle
            self.conn_info['write_status']          = status

        # useful for deugging
        #for k in sorted(self.conn_info):
        #    print('key: ' + k + ' value ' + str(self.conn_info[k]))
